# Svitlo → MQTT (Home Assistant Add-on)

Svitlo → MQTT listens to selected Telegram chats via Telethon, parses power-related messages, and publishes results to MQTT for your Home Assistant automations.

In short: it listens to and parses service accounts of Kyiv Digital / Yasno and Kyiv group summaries, and puts the data into MQTT so you can build sensors and automations.

Important: Your Telegram account (StringSession) must be a member of the specified chats to receive updates.

---

## Creating your Telegram Application
Follow the official guide: https://core.telegram.org/api/obtaining_api_id
You will obtain your App api_id and api_hash, required by the add-on.

### Generate Telegram String Session
You need a StringSession for your personal Telegram account (not a bot). The account must have access to the chats you configure in the add-on.
You can use a helper as described in the upstream project: https://github.com/Sergey7up/svitlo2mqtt

Requirements:
- Python
- telethon==1.41.1

Example:
```
pip install telethon==1.41.1
python ./utils/session_generator.py
```
After completion, check your Telegram “Saved Messages” to copy the generated string session.

---

## Configuration
All options are available in the add-on UI.

- telegram_api_id: Your Telegram API ID (https://my.telegram.org)
- telegram_api_hash: Your Telegram API hash
- telegram_string_session: Exported StringSession of your Telegram account (not a bot). This account must be in the specified chats.
- sources: list of strings, each in the form:
  "<chat_spec> <subtopic> <parser>"
  - chat_spec: @username or numeric chat ID (as a string, e.g. "-1002233810852")
  - subtopic: subfolder in MQTT topics, e.g. `kyiv_digital` → power/kyiv_digital/…
  - parser: one of `parse_kyiv_digital`, `parse_groups_summary`

### Parsers
- parse_kyiv_digital
  - Input: messages from Kyiv Digital-like channels that contain a JSON object.
  - The parser extracts the JSON between the first '{' and the last '}', requires `group` and `power` to be present, and returns ON/OFF status.
  - Published topics:
    - power/<subtopic>/json/ON/<group>
    - power/<subtopic>/json/OFF/<group>
  - Payload: original JSON minus `group`, `text`, `address`, plus `timestamp` (UTC).

- parse_groups_summary
  - Input: a summary text with a header total percentage and per-group lines like:
    "Група 1.1: 31% 11:37 📈"
  - Supports dotted group IDs (e.g., "1.1"). Group IDs are treated as strings.
  - Published topics:
    - power/<subtopic>/status → {"total": int, "groups": [ints ordered by group id string]}
    - power/<subtopic>/total → integer total
    - power/<subtopic>/groups/<group_id> → integer for each group

### MQTT
- Default broker host: core-mosquitto (MQTT add-on)
- QoS: configurable (default 1)
- Messages are retained

### Debug
- Set `debug: true` to enable INFO-level logs.

---

# Українська версія

Svitlo → MQTT слухає вибрані чати Telegram через Telethon, парсить повідомлення щодо електропостачання та публікує результати в MQTT для ваших автоматизацій у Home Assistant.

Коротко: аддон слухає та парсить сервісні акаунти сповіщень Київ Цифровий / Ясно та зведення по київських групах і складає дані в MQTT для подальших автоматизацій.

Важливо: ваш Telegram-акаунт (StringSession) має бути учасником вказаних чатів, щоб отримувати оновлення.

## Як створити Telegram Application
Інструкція: https://core.telegram.org/api/obtaining_api_id
Після цього ви отримаєте api_id та api_hash — вони потрібні для аддона.

### Генерація Telegram String Session
Потрібен StringSession вашого особистого Telegram-акаунта (не бота). Акаунт має мати доступ до вказаних у конфігурації чатів.
Скористайтесь інструментом з проєкту: https://github.com/Sergey7up/svitlo2mqtt

Вимоги:
- Python
- telethon==1.41.1

Приклад:
```
pip install telethon==1.41.1
python ./utils/session_generator.py
```
Після завершення перевірте “Збережені повідомлення” у Telegram та скопіюйте згенерований StringSession.

## Налаштування
- telegram_api_id / telegram_api_hash / telegram_string_session — облікові дані Telegram (https://my.telegram.org). StringSession має належати акаунту, який є в заданих чатах.
- sources — список рядків: "<chat_spec> <subtopic> <parser>"
  - chat_spec: @username або числовий ID (рядком)
  - subtopic: підпапка у темах MQTT (power/<subtopic>/…)
  - parser: `parse_kyiv_digital` або `parse_groups_summary`

### Парсери
- parse_kyiv_digital
  - Вхід: повідомлення з JSON (Kyiv Digital тощо).
  - Виділяє JSON між першою «{» і останньою «}», потребує `group` і `power`.
  - Топіки:
    - power/<subtopic>/json/ON/<group>
    - power/<subtopic>/json/OFF/<group>
  - Навантаження: JSON без `group`, `text`, `address` + `timestamp` (UTC).

- parse_groups_summary
  - Вхід: зведення з загальним відсотком та рядками по групах, напр.: «Група 1.1: 31% 11:37 📈».
  - Підтримуються ID груп з крапкою (рядком).
  - Топіки:
    - power/<subtopic>/status → {"total": int, "groups": [інти у порядку ключів груп]}
    - power/<subtopic>/total → загальний відсоток
    - power/<subtopic>/groups/<group_id> → значення для кожної групи

### MQTT
- Типовий брокер: core-mosquitto (аддон Mosquitto)
- QoS налаштовується (типово 1)
- Повідомлення з прапорцем retained

### Налагодження
- Увімкніть `debug: true`, щоб бачити докладні INFO-логи.

---

## Additional Documentation
- Github repository: Svitlo2MQTT — https://github.com/Sergey7up/svitlo2mqtt