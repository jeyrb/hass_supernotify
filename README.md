# SuperNotifier

Simplified notifications for complex scenarios, including multi-channel notifications, conditional notifications, mobile actions, chimes and template based HTML emails.

## Features

* Send out notifications on multiple channels from one call, removing repetitive config and code from automations
* Conditional notification using standard Home Assistant `condition` config
* Reuse chunks of conditional logic as scenarios across multiple notifications
* Streamlined conditionals for selecting channels per priority and scenario, or
for sending only to people in or out of the property
* Use `person` for all notification configuration, regardless of channel, using a unified Person model currently missing from Home Assistant
* HTML email templates, using Jinja2, with a general default template supplied
* Single set up of mobile actions across multiple notifications
* Defaulting of targets and data in static config, and overridable at notification time
* Generic support for any notification method, plus canned delivery methods to simplify common cases, especially for tricky ones like Apple Push
* Reloadable configuration

## Usage

### Minimal
```yaml
  - service: notify.supernotifier
    data:
        title: Security Notification
        message: '{{state_attr(sensor,"friendly_name")}} triggered'                    
```

### More features
```yaml
  - service: notify.supernotifier
    data:
        title: Security Notification
        message: '{{state_attr(sensor,"friendly_name")}} triggered'
        target: 
          - person.jim_bob
          - person.neighbour
        priority: high
        scenarios:
          - home_security
          - garden
        delivery:
            mobile_push:
                data:
                    clickAction: https://my.home.net/dashboard
                    
```

## Delivery Methods

### Mobile Push

Send a push message out, with option for camera integration, mobile actions, and
translate general priority to Apple specific push priority. 

Some functionality may also work with Android push, though has not been tested.

### Chime

Provide a list of `switch`, `media_player` or `script` entities to use for chimes
and it will call the `switch.turn_on`, `script.turn_on` or `media_player.play_media`
services automatically for each.

See https://github.com/alandtse/alexa_media_player/wiki#known-available-sounds for
a list of known tunes that work with Alexa devices.

### SMS

Uses the `phone_number` attribute of recipient, and truncates message to fit in an SMS

### Generic

Use to call any service.
If service is in `notify` domain, then `message`,`title`,`target` and `data` will be
passed in the Service Data, otherwise the `data` supplied will be passed directly
as the Service Data.

```yaml
    - service: notify.supernotify
      data:
        title: "My Home Notification"
        message: "Notify via custom chat"
        delivery:
            chat_notify:
                data:
                    channel: 3456
    - service: notify.supernotify
      data:
        delivery:
            mqtt_notify:
                data:
                  topic: alert/family_all
                  payload: something happened
```

### Email

Can be used for plain or HTML template emails, and handle images as attachments
or HTML embed

### Media Image

Show an image on a media player, e.g. an Alexa Show where that actually works

### Alexa Announce

Announce a message on an Alexa Echo device using the `alexa_media_player` integration

### Persistent

Place a notification on Home Assistant application screen.

## Setup

Register this GitHub repo as a custom repo 
in your [HACS]( https://hacs.xyz) configuration. 

Configure in the main Home Assistant config yaml, or an included notify.yaml

```yaml
notify:
  - name: SuperNotifier_reloaded
    platform: supernotify
    templates: config/templates/supernotify        
    delivery:
      html_email:
        method: email
        template: default.html.j2
        condition:
          condition: or
          conditions:
            - condition: state
              entity_id: alarm_control_panel.home_alarm_control
              state:
                - armed_away
                - armed_home
                - armed_night
            - condition: state
              entity_id: supernotify.delivery_priority
              state:
                - critical
                - high     
        priority:
          - critical
          - high
          - medium
          - low
        
      backup_mail:
        method: email
        fallback: on_error
      text_message:    
        method: sms
        service: notify.mikrotik_sms
        occupancy: only_out
        priority:
          - critical
          - high
      alexa_announce:
        method: alexa
        service: notify.alexa
        occupancy: any_in
      mobile_push:
        method: mobile_push
      alexa_show:
        method: media
        service: media_player.play_media
        target:
          - media_player.kitchen_2
      play_chimes:
        method: chime
        target:
          - script.chime_ding_dong
          - switch.chime_sax
          - media_player.echo_lobby
        occupancy: any_in
      doorbell:
        method: chime
        target:
          - media_player.echo_lobby
        data:
          chime_tune: amzn_sfx_doorbell_chime_01
        scenarios:
          - doorbell
      upstairs_siren:
        method: generic
        service: mqtt.publish
        priority:
          - critical
        data:
          topic: zigbee2mqtt/Upstairs Siren/set
          payload: '{"warning": {"duration": 30, "mode": "emergency", "strobe": true }}'
      sleigh_bells:
        method: chime
        target:
          - media_player.echo_lobby
        data:
          chime_tune: christmas_05
        condition: 
          condition: template
          alias: Xmas
          value_template: >
            {% set n = now() %}
            {{ n.month == 12 and 15 <= n.day }}
    recipients:
      - person: person.new_home_owner
        email: jrb@jeymail.net
        phone_number: "+447989408889"
        delivery:
          mobile_push: 
            target:
              - mobile_app.new_iphone
            data:
              push:
                sound:
                  name: default
          alexa_announce:
            target:
              - media_player.echo_study
      - person: person.bidey_in
        phone_number: "+4489393013834"
    overrides:
      image_url:
        base: http://10.1.1.100
        replace: https://myhomeserver.org/images
    methods:
      email:
        service: notify.smtp
      alexa:
        target:
          - media_player.kitchen_2
          - media_player.bedroom
          - media_player.hall_flex
          - media_player.old_kitchen_flex
          - media_player.studio
      
    scenarios:
      ordinary_day:
        alias: nothing special
        condition:
          condition: and
          conditions:
            - not:
                - condition: state
                  entity_id: alarm_control_panel.home_alarm_control
                  state: disarmed
            - condition: time
              after: "21:30:00"
              before: "06:30:00"
      mostly:
        alias: nothing special
        condition:
          condition: and
          conditions:
            - not:
                - condition: state
                  entity_id: alarm_control_panel.home_alarm_control
                  state: unknown
            - condition: time
              after: "06:30:00"
              before: "21:30:00"

    actions:
      examples:
        - identifier: action-1
          title: Example Mobile Action
          icon: "sfsymbols:bell"
          uri: http://10.111.10.111:8123
          activationMode: foreground
          authenticationRequired: false
          destructive: false
          behavior: default
          textInputButtonTitle: Input Button Title
          textInputPlaceholder: Input Placeholder Text
      frigate:
        - action_template: silence-{{camera.entity_id}}
          title_template: Silence Notifications for {{camera.entity_id}}
          icon: "sfsymbols:bell.slash"
      alarm_panel:
        - action: "ALARM_PANEL_DISARM"
          title: "Disarm Alarm Panel"
          icon: "sfsymbols:bell.slash"
        - action: "ALARM_PANEL_RESET"
          title: "Arm Alarm Panel for at Home"
          icon: "sfsymbols:bell"
        - action: "ALARM_PANEL_AWAY"
          title: "Arm Alarm Panel for Going Away"
          icon: "sfsymbols:airplane"
    links:
      - url: http://frigate
        icon: "mdi:camera"
        name: Frigate
        description: Frigate CCTV

```

TODO:

* Migrate driveway camera handling incl PTZ
* Configurable links for email
* Rate limiting


            