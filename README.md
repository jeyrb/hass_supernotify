# SuperNotifier

Simplified and complicated notifications, including multi-channel notifications, chimes and template based emails

## Setup


Configure in the main Home Assistant config yaml, or an included notify.yaml

```yaml
- name: SuperNotifier
  platform: supernotifier
      services:
      email: smtp
      sms: mikrotik_sms
    chime_devices:
      - script.chime_ding_dong
      - switch.chime_sax
    alexa_devices:
      - media_player.bedroom
      - media_player.studio
    alexa_show_devices:
      - media_player.kitchen_2
    recipients:
      - person: person.new_home_owner
        email: me@homemail.net
        mobile:
          number: "+4477777000111"
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


```

TODO:

* Auto notify for multiple channels
* Migrate driveway camera handling incl PTZ
* Delivery priority to translate to push priority for apple
* Configurable links for email
* Add mobile action definition
