# SuperNotifier

Simplified and complicated notifications, including multi-channel notifications, conditional notifications, mobile
actions, chimes and template based HTML emails

## Setup


Configure in the main Home Assistant config yaml, or an included notify.yaml

```yaml
notify:
  - name: SuperNotifier_reloaded
    platform: supernotify
    templates: config/templates/supernotify
    methods:
      email:
        service: notify.smtp
      sms:
        service: notify.mikrotik_sms
      alexa:
        service: notify.alexa
      media:
        service: media_player.play_media
    delivery:
      html_email:
        method: email
        template: default.html.j2 
        priority:
          - critical
          - high
          - medium
          - low
      text_message:    
        method: sms
        occupancy: only_out
        priority:
          - critical
          - high
      alexa_announce:
        method: alexa
        entities:
          - media_player.kitchen
          - media_player.bedroom
          - media_player.studio
        occupancy: any_in
      apple_push:
        method: apple_push
      alexa_show:
        method: media
        entities:
          - media_player.kitchen
      play_chimes:
        method: chime
        entities:
          - script.chime_ding_dong
          - switch.chime_sax
        occupancy: any_in
    recipients:
      - person: person.new_home_owner
        email: me@home.net
        mobile: 
          number: "+44797940404"
          apple_devices:
            - mobile_app.new_iphone
      - person: person.bidey_in
        mobile:
          number: "+4489393013834"

    actions:
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
      - identifier: "ALARM_PANEL_DISARM"
        title: "Disarm Alarm Panel"
        icon: "sfsymbols:bell.slash"
      - identifier: "ALARM_PANEL_RESET"
        title: "Arm Alarm Panel for at Home"
        icon: "sfsymbols:bell"
      - identifier: "ALARM_PANEL_AWAY"
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
* Add mobile action definition
* Rate limiting