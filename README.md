# Svitlo2MQTT

Home Assistant Add-on listens to selected Telegram chats via Telethon, parses power-related messages, and publishes results to MQTT for your Home Assistant automations.

In short: it listens to and parses service accounts of Kyiv Digital / Yasno and Kyiv group summaries, and puts the data into MQTT so you can build sensors and automations.

## Installation
To add this repository to Home Assistant use the badge below:

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FSergey7up%2Fsvitlo2mqtt)

or add it manually by navigating to `Settings` > `Add-ons` > `Add-on Store`

Select the three dot menu in the upper right, choose `Repositories`, and add the following url:
```
https://github.com/Sergey7up/svitlo2mqtt
```

Refresh the page (hard refresh may be required), scroll down to Svitlo2MQTT and install the add-on.

## Usage

### Prerequisites
- Install and start the Mosquitto broker add-on (core-mosquitto).
- In Svitlo2MQTT add-on configuration, leave mqtt_username and mqtt_password empty to auto-use Supervisor-provided Mosquitto credentials. Otherwise specify your own broker credentials.
- Your Telegram account (the StringSession you configure) must be a member of the specified chats to receive updates.

### Configure sources
Each source is a string in the form:
"\<chat_spec\> \<subtopic\> \<parser\>"
- chat_spec: @username or a numeric ID string (e.g. "-1002233810852")
- subtopic: used in MQTT topics under power/\<subtopic\>/...
- parser: one of parse_kyiv_digital, parse_groups_summary

Example sources:
- "@kyiv_digital_notifications kyiv_digital parse_kyiv_digital"
- "@yasno_schedule_groups yasno_kyiv parse_kyiv_digital"
- "@kyiv_groups2 kyiv_groups parse_groups_summary"
- "@kyiv_groups kyiv_groups1 parse_groups_summary"

### Topics published
- parse_kyiv_digital:
  - power/\<subtopic\>/json/ON/\<group\>
  - power/\<subtopic\>/json/OFF/\<group\>
  - Payload is JSON with keys from the original message (minus group/text/address) and timestamp (UTC). OFF payload may include emergency and time_to.
- parse_groups_summary:
  - power/\<subtopic\>/status → {"total": int, "groups": [ints ordered by group id string]}
  - power/\<subtopic\>/total → integer
  - power/\<subtopic\>/groups/\<group_id\> → integer per group_id (supports dotted IDs like 1.1)
- All publishes are retained; QoS is configurable (default 1).

### MQTT sensors in Home Assistant (YAML)
Below are examples using the built-in MQTT broker. You can place these under mqtt: sensor: or use the classic platform: mqtt under sensor:. For example, under mqtt: sensor: (no platform needed):

```yaml
mqtt:
  sensor:
    - name: "Planned Shutdown Time"
      state_topic: "power/kyiv_digital/json/OFF/1.1"
      unique_id: planned_shutdown_time
      device_class: timestamp
      value_template: >
        {% set timestamp = value_json.timestamp | int %}
        {% set time_to = value_json.time_to | default(10) | int %}
        {% set planned_timestamp = timestamp + (time_to * 60) %}
        {{ planned_timestamp | as_datetime }}

    - name: "Planned Poweron Time"
      state_topic: "power/kyiv_digital/json/ON/1.1"
      unique_id: planned_poweron_time
      device_class: timestamp
      value_template: >
        {% set timestamp = value_json.timestamp | int %}
        {{ timestamp | as_datetime }}

    - name: "Kyiv group power"
      state_topic: "power/kyiv_groups/groups/1"
      unique_id: kyiv_group_power
      unit_of_measurement: "%"
      value_template: "{{ value | int }}"

    - name: "Kyiv group power (1)"
      state_topic: "power/kyiv_groups1/groups/1.1"
      unique_id: kyiv_group_power_1
      unit_of_measurement: "%"
      value_template: "{{ value | int }}"
```

Alternatively, under the classic sensor: with platform: mqtt:

```yaml
sensor:
  - platform: mqtt
    name: "Planned Shutdown Time"
    state_topic: "power/kyiv_digital/json/OFF/1.1"
    unique_id: planned_shutdown_time
    device_class: timestamp
    value_template: >
      {% set timestamp = value_json.timestamp | int %}
      {% set time_to = value_json.time_to | default(10) | int %}
      {% set planned_timestamp = timestamp + (time_to * 60) %}
      {{ planned_timestamp | as_datetime }}
```

### Template helper for automations
Example Jinja condition to check that a group power sensor was updated within the last 5 minutes and is below 85%:

```jinja2
{{ (as_timestamp(now()) - as_timestamp(states.sensor.kyiv_group_power.last_changed)) < 300 and states('sensor.kyiv_group_power') | float(0) < 85 }}
```


## Add-ons

This repository contains the following add-ons:

### [Svitlo2MQTT](./svitlo2mqtt)

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg

_Telegram chatbot messages listener to MQTT for Home Assistant._
