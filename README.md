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

```
