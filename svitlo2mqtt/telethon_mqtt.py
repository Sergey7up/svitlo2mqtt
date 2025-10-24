# -*- coding: utf-8 -*-
"""
Home Assistant Add-on: Svitlo → MQTT

Listens to multiple Telegram chats via Telethon and publishes parsed data to MQTT.
- Sources are configured as strings: "<chat_spec> <subtopic> <parser>"
- chat_spec: @username or numeric ID string (e.g. "-1002233810852")
- subtopic: subfolder used in MQTT topics under power/<subtopic>/
- parser: one of [parse_kyiv_digital, parse_groups_summary]

Auth: Telethon user StringSession from the add-on config (not a bot).
MQTT: local broker (default core-mosquitto) via Supervisor auto-credentials or explicit options.
Timestamps: Telegram message date (UTC).
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any

import paho.mqtt.client as mqtt
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.utils import get_peer_id

from parse_kyiv import parse_kyiv_digital, parse_groups_summary

# ---------- Logging ----------
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("svitlo2mqtt")

# ---------- Config ----------
OPTIONS_PATH = "/data/options.json"

def load_options() -> dict:
    if not os.path.exists(OPTIONS_PATH):
        log.error("Options file not found: %s", OPTIONS_PATH)
        sys.exit(1)
    with open(OPTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

opts = load_options()

# Required Telegram credentials (validated in main)
TELEGRAM_API_ID = None
TELEGRAM_API_HASH = None
TELEGRAM_STRING_SESSION = None

# Sources loader: expects list of strings "<chat_spec> <subtopic> <parser>"
def _load_sources_specs(o: dict) -> list[str]:
    raw = o.get("sources", [])
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    return []

SOURCES_SPECS = _load_sources_specs(opts)

# Parser registry
PARSER_REGISTRY: Dict[str, Any] = {
    "parse_kyiv_digital": parse_kyiv_digital,
    "parse_groups_summary": parse_groups_summary,
}

# MQTT options; credentials are finalized in main() after env resolution
MQTT_HOST = str(opts.get("mqtt_host", "core-mosquitto"))
MQTT_PORT = int(opts.get("mqtt_port", 1883))
MQTT_USERNAME = str(opts.get("mqtt_username", "")) or None
MQTT_PASSWORD = str(opts.get("mqtt_password", "")) or None
MQTT_QOS = int(opts.get("mqtt_qos", 1))

# Resolve MQTT credentials using options/env prepared by run.sh

def resolve_mqtt_credentials(default_host: str, default_port: int, opt_user: str | None, opt_pass: str | None):
    host = os.environ.get("MQTT_HOST") or default_host
    try:
        port = int(os.environ.get("MQTT_PORT") or default_port)
    except Exception:
        port = default_port
    username = opt_user or os.environ.get("MQTT_USERNAME")
    password = opt_pass or os.environ.get("MQTT_PASSWORD")
    return host, port, username, password

# ---------- MQTT bus ----------
class MqttBus:
    def __init__(self, host: str, port: int, username: str | None, password: str | None, qos: int = 1):
        self.host = host
        self.port = port
        self.username = username
        self.password = password or ""
        self.qos = qos
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="svitlo2mqtt", protocol=mqtt.MQTTv311)
        if self.username:
            self.client.username_pw_set(self.username, self.password)
        self.client.reconnect_delay_set(min_delay=1, max_delay=60)

    def connect(self):
        log.info("MQTT: connecting to %s:%s ...", self.host, self.port)
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()
        log.info("MQTT: connected and loop started")

    def publish_json(self, topic: str, payload: dict, retain: bool = True):
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        log.info("MQTT PUBLISH %s -> %s (retain=%s)", topic, data, retain)
        self.client.publish(topic, data.encode("utf-8"), qos=self.qos, retain=retain)

    def publish_number(self, topic: str, value: int, retain: bool = True):
        payload = str(int(value))
        log.info("MQTT PUBLISH %s -> %s (retain=%s)", topic, payload, retain)
        self.client.publish(topic, payload, qos=self.qos, retain=retain)

    def stop(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

bus: MqttBus | None = None

# ---------- Sources and routing ----------
class Source:
    def __init__(self, chat_spec: str, subtopic: str, parser_name: str, parser_fn: Any):
        self.chat_spec = chat_spec
        self.subtopic = subtopic
        self.parser_name = parser_name
        self.parser_fn = parser_fn
        self.resolved_chat = None  # entity or int id
        self.resolved_id: int | None = None

    def __repr__(self) -> str:
        return f"Source(chat={self.chat_spec}, subtopic={self.subtopic}, parser={self.parser_name}, id={self.resolved_id})"

sources: list[Source] = []
source_by_id: Dict[int, Source] = {}

# ---------- Telegram event handler ----------
async def on_new_message(event):
    if bus is None:
        log.error("MQTT bus is not initialized.")
        return

    chat_id = event.chat_id
    text = event.raw_text or ""
    # Telegram message timestamp (UTC)
    try:
        msg_dt = event.message.date
        now = int(msg_dt.timestamp()) if msg_dt else int(time.time())
    except Exception:
        now = int(time.time())

    src = source_by_id.get(int(chat_id))
    if not src:
        return

    log.info("New message (%s): %s", src, text)

    if src.parser_name == "parse_kyiv_digital":
        parsed = parse_kyiv_digital(text)
        if not parsed:
            log.info("Skipping: parse_kyiv_digital() returned None for %s", src.subtopic)
            return
        typ, grp, payload = parsed
        payload["timestamp"] = now
        topic = f"power/{src.subtopic}/json/{typ}/{grp}"
        bus.publish_json(topic, payload, retain=True)

    elif src.parser_name == "parse_groups_summary":
        pg = parse_groups_summary(text)
        if not pg:
            log.info("Skipping: parse_groups_summary() returned None for %s", src.subtopic)
            return
        total_percent, new_values = pg
        # Order by group id (string)
        groups_list = [val for _, val in sorted(new_values.items(), key=lambda kv: kv[0])]
        if total_percent is None:
            try:
                total_percent = int(round(sum(groups_list) / max(1, len(groups_list))))
            except Exception:
                total_percent = 0
        status_payload = {"total": int(total_percent), "groups": groups_list}
        status_topic = f"power/{src.subtopic}/status"
        total_topic = f"power/{src.subtopic}/total"
        bus.publish_json(status_topic, status_payload, retain=True)
        bus.publish_number(total_topic, int(total_percent), retain=True)
        for gid, val in new_values.items():
            item_topic = f"power/{src.subtopic}/groups/{gid}"
            bus.publish_number(item_topic, int(val), retain=True)

# ---------- Main ----------
async def main():
    global bus

    # Validate Telegram settings
    api_id_raw = opts.get("telegram_api_id")
    api_hash = (opts.get("telegram_api_hash") or "").strip()
    string_session = (opts.get("telegram_string_session") or "").strip()

    if api_id_raw is None or api_hash == "" or string_session == "":
        log.error("Missing required telegram_* settings in /data/options.json. Please set telegram_api_id, telegram_api_hash, telegram_string_session.")
        sys.exit(2)
    try:
        api_id = int(api_id_raw)
    except Exception:
        log.error("telegram_api_id must be an integer. Current value: %r", api_id_raw)
        sys.exit(2)

    # MQTT creds
    host, port, user, pwd = resolve_mqtt_credentials(MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD)
    if not user or not pwd:
        log.error("MQTT credentials are missing. Provide mqtt_username/mqtt_password in options or configure Mosquitto add-on and enable services: mqtt:need so env MQTT_USERNAME/PASSWORD are available.")
        sys.exit(2)
    bus = MqttBus(host, port, user, pwd, qos=MQTT_QOS)
    bus.connect()

    # Logging level
    if bool(opts.get("debug", False)):
        log.setLevel(logging.INFO)
        logging.getLogger().setLevel(logging.INFO)

    # Telegram client
    client = TelegramClient(StringSession(string_session), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        log.error("StringSession is invalid or not authorized.")
        sys.exit(2)

    me = await client.get_me()
    log.info("Telethon: authorized as %s (%s)", getattr(me, 'username', None), me.id)

    # Build sources
    if not SOURCES_SPECS:
        log.error("No sources configured in /data/options.json (options.sources is empty).")
        sys.exit(2)

    async def resolve_chat(spec):
        if spec is None:
            return None
        s = str(spec).strip()
        if s.lstrip('-').isdigit():
            return int(s)
        try:
            entity = await client.get_entity(s)
            return entity
        except Exception as e:
            log.error("Failed to resolve chat '%s': %s", s, e)
            return None

    local_sources: list[Source] = []
    for raw in SOURCES_SPECS:
        spec = str(raw)
        parts = spec.split()
        if len(parts) != 3:
            log.error("Invalid source spec '%s'. Expected '<chat> <subtopic> <parser>' (space-delimited)", spec)
            sys.exit(2)
        chat_spec, subtopic, parser_name = parts
        parser_fn = PARSER_REGISTRY.get(parser_name)
        if not parser_fn:
            log.error("Unknown parser '%s' in source '%s'", parser_name, spec)
            sys.exit(2)
        local_sources.append(Source(chat_spec=chat_spec, subtopic=subtopic, parser_name=parser_name, parser_fn=parser_fn))

    chats_to_listen = []
    for src in local_sources:
        ent = await resolve_chat(src.chat_spec)
        if ent is None:
            log.error("Failed to resolve chat '%s' for source %s", src.chat_spec, src)
            sys.exit(2)
        src.resolved_chat = ent
        try:
            src.resolved_id = get_peer_id(ent)
        except Exception:
            src.resolved_id = int(ent)
        chats_to_listen.append(ent)

    global sources, source_by_id
    sources = local_sources
    source_by_id = {int(s.resolved_id): s for s in sources if s.resolved_id is not None}

    client.add_event_handler(on_new_message, events.NewMessage(chats=chats_to_listen))

    log.info("Listening to %d sources: %s", len(sources), ", ".join([repr(s) for s in sources]))
    await client.run_until_disconnected()

# ---------- Shutdown handling ----------
def shutdown(*_):
    try:
        if bus:
            bus.stop()
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, shutdown)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        shutdown()
