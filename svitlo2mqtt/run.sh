#!/usr/bin/with-contenv bashio
set -e

# Timezone from Supervisor
export TZ="$(bashio::supervisor.timezone)"

# If user left MQTT username/password empty, and MQTT service is available,
# fetch MQTT connection info from Supervisor services and export as env vars
if { bashio::config.is_empty 'mqtt_username' || bashio::config.is_empty 'mqtt_password'; } \
   && bashio::var.has_value "$(bashio::services 'mqtt')"; then
    export MQTT_HOST="$(bashio::services 'mqtt' 'host')"
    export MQTT_PORT="$(bashio::services 'mqtt' 'port')"
    export MQTT_USERNAME="$(bashio::services 'mqtt' 'username')"
    export MQTT_PASSWORD="$(bashio::services 'mqtt' 'password')"
fi

# Allow explicit options to override (if provided)
if bashio::config.has_value 'mqtt_host'; then
    export MQTT_HOST="$(bashio::config 'mqtt_host')"
fi
if bashio::config.has_value 'mqtt_port'; then
    export MQTT_PORT="$(bashio::config 'mqtt_port')"
fi
if bashio::config.has_value 'mqtt_username' && [ "$(bashio::config 'mqtt_username')" != "" ]; then
    export MQTT_USERNAME="$(bashio::config 'mqtt_username')"
fi
if bashio::config.has_value 'mqtt_password' && [ "$(bashio::config 'mqtt_password')" != "" ]; then
    export MQTT_PASSWORD="$(bashio::config 'mqtt_password')"
fi

bashio::log.info "Starting Svitlo -> MQTT..."
exec /venv/bin/python -u /app/telethon_mqtt.py
