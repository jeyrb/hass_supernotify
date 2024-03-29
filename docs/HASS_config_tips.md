# Home Assistant Notification Config Tips

Hints and suggestions for configuring non-SuperNotify notification in HomeAssistant.

## Self-hosted SMS

If you have a Mikrotik 4G router for broadband or fallback, then you can probably
send SMS notifications through it, using *Mikrotik SMS* custom component.

Set it up by adding `https://github.com/jeyrb/hass_mikrotik_sms` as a custom repo in HACS.

## Configuring an MQTT Siren with Zigbee2MQTT

Home Assistant added MQTT Siren support in 2022, though as of writing its not
yet automatically provisioned by Zigbee2MQTT, and its fussy to set up.

Here is an example working config for a Heiman HS2WD-E plugin Zigbee siren


``` yaml
  - unique_id: downstairs_hall_heiman
    name: "Downstairs Hall Siren"
    object_id: downstairs
    json_attributes_topic: "zigbee2mqtt/Downstairs Siren"
    command_topic: "zigbee2mqtt/Downstairs Siren/set"
    availability:
      - topic: "zigbee2mqtt/Downstairs Siren/availability"
        value_template: "{{ value_json.state }}"
        payload_available: online
        payload_not_available: offline
    command_template: >
      {"warning": 
        {"duration": {{int(duration,30)}},
         "level":"{% if volume_level is none or volume_level >= 0.75%}very_high{% elif volume_level >= 0.5%}high{% elif volume_level>=0.25 %}medium{% else %}low{% endif %}",
         "mode": "{{tone|default("emergency")}}", 
         "strobe": true,
         "strobe_duty_cycle": 10,
         "strobe_level": "very_high"
         }}
    command_off_template: '{"warning": {"duration": 1, "mode": "stop"}}'
    icon: mdi:alarm-light
    qos: 0
    optimistic: false
    retain: true
    support_duration: true
    support_volume_set: true
    available_tones:
      - emergency
      - fire
      - burgular
      - stop
      - police_panic
      - emergency_panic
      - fire_panic

```

### Richer email notifications

``` yaml
 action:
    service: notify.supernotifier
    data_template:
      title: "Home Assistant Restart"
      message: "Home Assistant has started up."
      data:
        message_html: |
          <table>
            <tr>
              <th>Component</th><th>Installed Version</th><th>Latest Version</th>
            </tr>
            <tr>
              <td>Core</td>
              <td>{{ states.update.home_assistant_supervisor_update.attributes['installed_version']}}</td>
              <td>{{ states.update.home_assistant_supervisor_update.attributes['latest_version']}}</td>
            </tr>
            <tr>
              <td>Supervisor</td>
              <td>{{ states.update.home_assistant_core_update.attributes['installed_version']}}</td>
              <td>{{ states.update.home_assistant_core_update.attributes['latest_version']}}</td>
              </tr>
            <tr>
              <td>OS</td>
              <td>{{ states.update.home_assistant_operating_system_update.attributes['installed_version']}}</td>
              <td>{{ states.update.home_assistant_operating_system_update.attributes['latest_version']}}</td>
            </tr>
          <table>
```

### Other Ideas

See the `maximal.yaml` example configuration in the `examples` directory of this repo
for more ideas of how to use SuperNotify.


