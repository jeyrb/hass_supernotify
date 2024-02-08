# SuperNotifier

An extension of HomeAssistant's built in `notify.notify` that can greatly simplify multiple notification channels and
complex scenarios, including multi-channel notifications, conditional notifications, mobile actions, chimes and template based HTML emails.

## Features

* Send out notifications on multiple channels from one call, removing repetitive config and code from automations
* Conditional notification using standard Home Assistant `condition` config
* Reuse chunks of conditional logic as scenarios across multiple notifications
* Streamlined conditionals for selecting channels per priority and scenario, or
for sending only to people in or out of the property
* Use `person` for all notification configuration, regardless of channel, using a unified Person model currently missing from Home Assistant
* HTML email templates, using Jinja2, with a general default template supplied
* Single set up of consistent mobile actions across multiple notifications
* Defaulting of targets and data in static config, and overridable at notification time
* Generic support for any notification method, plus canned delivery methods to simplify common cases, especially for tricky ones like Apple Push
* Reloadable configuration
* Tunable duplicate notification detection
* Well-behaved `notify` extension, so can use data templating, `notify.group` and other notify features.

## Installation

* Add git repo to HACS as custom repo
* Select *SuperNotify* in the list of available integrations in HACS and install
* Add a `notify` config for the `supernotifier` integration, see `examples` folder
* In order to use email attachments, e.g. from camera snapshot or a `snapshot_url`,
you must set the `allowlist_external_dirs` in main HomeAssistant config to the same as
`media_path` in the supernotify configuration


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

### Templated
```yaml
  - service: notify.supernotifier
    data:
        message:
    data_template:
        title: Tank Notification
        message:  "Fuel tank depth is {{ state_attr('sensor.tank', 'depth') }}"
        data:
            priority: {% if {{ state_attr('sensor.tank', 'depth') }}<10 }critical{% else %}medium {% endif %}               
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

## Flexible Configuration

Delivery configuration can be done in lots of different ways to suit different configurations
and to keep those configuration as minimal as possible.

Priority order of application


| Where                                | When            | Notes                                            |
|--------------------------------------|-----------------|--------------------------------------------------|
| Service Data                         | Runtime call    |                                                  |
| Recipient delivery override          | Runtime call    |                                                  |
| Scenario delivery override           | Runtime call    | Multiple scenarios applied in no special order   |
| Delivery definition                  | Startup         | `message` and `title` override Service Data      |
| Method defaults                      | Startup         |                                                  |
| Target notification service defaults | Downstream call |                                                  |


1. Service Data passed at runtime call
2. Recipient delivery override 
3. Scenario delivery override
4. Delivery definition
5. Method defaults
6. Target notification service defaults, e.g. mail recipients ( this isn't applied inside supernotifier )

## Setup

Register this GitHub repo as a custom repo 
in your [HACS]( https://hacs.xyz) configuration. 

Configure in the main Home Assistant config yaml, or an included notify.yaml

See `examples` directory for working minimal and maximal configuration examples.

### Cameras

Use this for additional camera info:

* Link a `device_tracker` to the camera, so notifications will first check its online, then use an alternative
* Define alternative cameras to use if first fails
* For ONVIF cameras, a PTZ home preset can be defined, and a delay between PTZ command and snapshot

## Tips

### Message formatting

To send a glob of html to include in email, set `message_html` in service_data. This will be ignored
by other delivery methods that don't handle email. This can be also be used to have a notification
with only a title ( that gets picked up for mobile push, alexa and other brief communications ) with
a much more detailed body only for email.

Use `data_template` to build the `data` dictionary with Jinja2 logic from automations or scripts.


            