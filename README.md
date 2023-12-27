# SuperNotifier

Simplified and complicated notifications, including multi-channel notifications, chimes and template based emails

## Setup


Configure in the main Home Assistant config yaml, or an included notify.yaml

```yaml
- name: SuperNotifier
  platform: supernotifier
  alexa_targets:
    - media_player.bedroom
    - media_player.kitchen
  alexa_show_targets:
    - media_player.bedroom
  sms_targets:
    - +447675818181
  apple_targets:
    - apple_devices
  actions:

```

TODO:

* Configurable SMTP service name
* Configurable SMS service
* Auto notify for multiple channels
* Migrate driveway camera handling incl PTZ
* Delivery priority to translate to push priority for apple
* Selectable methods
* Default targets
* Person extension to associate device and phone number with occupancy
* Configurable links for email
* Add mobile action definition
