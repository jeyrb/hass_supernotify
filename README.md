[![Rhizomatics Open Source](https://avatars.githubusercontent.com/u/162821163?s=96&v=4)](https://github.com/rhizomatics)

# SuperNotifier

Easy multi-channel rich notifications.

An extension of HomeAssistant's built in `notify.notify` that can greatly simplify multiple notification channels and
complex scenarios, including multi-channel notifications, conditional notifications, mobile actions, chimes and template based HTML emails. Can substitute directly for existing notifications to mobile push, email, etc.

## Features

* Send out notifications on multiple channels from one call, removing repetitive config and code from automations
* Standard `notify` implementation so easy to switch out for other notify implementations, or `notify.group`
* Conditional notification using standard Home Assistant `condition` config
* Reuse chunks of conditional logic as *scenarios* across multiple notifications
* Streamlined conditionals for selecting channels per priority and scenario, or
for sending only to people in or out of the property
* Use `person` for all notification configuration, regardless of channel
  * Unified Person model currently missing from Home Assistant
* HTML email templates, using Jinja2, with a general default template supplied
* Single set up of consistent mobile actions across multiple notifications
* Flexible image snapshots, supporting cameras, MQTT Images and image URLs.
  * Cameras can be repositioned using PTZ before and after a snapshot is taken.
* Defaulting of targets and data in static config, and overridable at notification time
* Generic support for any notification method
  * Plus canned delivery methods to simplify common cases, especially for tricky ones like Apple Push
* Reloadable configuration
* Tunable duplicate notification detection
* Well-behaved `notify` extension, so can use data templating, `notify.group` and other notify features.
* Refactor out repetitive configuration for ease of maintenance
* Debugging support,
  * Optional archival of message structures
  * Additional actions ( previously known as services ) to pull back live configuration or last known notification details.

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
  - action: notify.supernotifier
    data:
        title: Security Notification
        message: '{{state_attr(sensor,"friendly_name")}} triggered'
```

### More features
```yaml
  - action: notify.supernotifier
    data:
        title: Security Notification
        message: '{{state_attr(sensor,"friendly_name")}} triggered'
        target:
          - person.jim_bob
          - person.neighbour
        priority: high
        apply_scenarios:
          - home_security
          - garden
        constrain_scenarios:
        delivery:
            mobile_push:
                data:
                    clickAction: https://my.home.net/dashboard

```
Note here that the `clickAction` is defined only on the `mobile_push` delivery. However
its also possible to define everything at the top level `data` section and let the individual
deliveries pick out the attributes they need. This is helpful either if you don't care about
fine tuning delivery configurations, or using existing notification blueprints, such as the popular
[Frigate Camera Notification Blueprints](https://github.com/SgtBatten/HA_blueprints/tree/main/Frigate%20Camera%20Notifications).

### Templated
```yaml
  - action: notify.supernotifier
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

Although SuperNotifier will automatically set most useful mobile push options,
its also possible to directly set them, as in this example:

```yaml
  - action: notify.supernotifier
    data:
      message: Movement at garden gate
      data:
        priority: high
        media:
          camera_entity_id: camera.porch
          camera_ptz_preset: garden_gate
        action_groups:
          - security_actions
        delivery:
          mobile_push:
            data:
              tag: "backyard-motion-detected"
              presentation_options:
                - alert
                - badge
              push:
                sound:
                  name: "US-EN-Alexa-Motion-Detected-Generic.wav"
                  volume: 1.0
```

### Chime

Provide a list of `switch`, `siren`, `media_player` or `script` entities to use for chimes
and it will call the `switch.turn_on`, `script.turn_on` or `media_player.play_media`
actions automatically for each.

See https://github.com/alandtse/alexa_media_player/wiki#known-available-sounds for
a list of known tunes that work with Alexa devices.

Optionally chime aliases can be set up so that simple names can be given for
Amazon tune paths, or multiple types of chime all mapped to same name. This can
be used in combination with method default targets for concise notifications.

Switches are a little special, in that they are binary on/off. However, since many
433Mhz ones can take an additional melody code, its common to have different melodies
represented by separate `switch` entities for the same underlying devices.


#### Example

```yaml
methods:
  chime:
    target:
      - media_player.kitchen_echo
      - media_player.bedroom
    options:
        chime_aliases:
              doorbell:
                media_player:
                    # resolves to media_player/play_media with sound configured for this path
                    tune: home/amzn_sfx_doorbell_chime_02
                    # device defaults to `target` of method default or action call
                media_player_alt:
                    # Not all the media players are Amazon Alexa based, so override for other flavours
                    domain: media_player
                    tune: raindrops_and_roses.mp4
                    entity_id:
                        - media_player.hall_custom
                switch:
                    # resolves to switch/turn_on with entity id switch.ding_dong
                    entity_id: switch.chime_ding_dong
                siren:
                    # resolves to siren/turn_on with tune bleep, only front door siren called
                    tune: bleep
                    entity_id: siren.front_door
              red_alert:
                # non-dict defaults to a dict keyed on `tune`
                alexa: scifi/amzn_sfx_scifi_alarm_04
                siren: emergency
```

With this chime config, a doorbell notification can be sent to multiple devices just
by selecting a tune.

```yaml
    - action: notify.supernotify
      data:
        message: ""
        delivery:
            chimes:
                data:
                    chime_tune: doorbell
```


### SMS

Uses the `phone_number` attribute of recipient, and truncates message to fit in an SMS.

The `title_only` option can be sent to restrict content to just title, when both title and
message on a notification. Otherwise, the combined title/message is sent out.

### Generic

Use to call any action (previously known in Home Assistant as 'service' ).
If action is in `notify` domain, then `message`,`title`,`target` and `data` will be
passed in the Action (Service) Data, otherwise the `data` supplied will be passed directly
as the Action Data.

```yaml
    - action: notify.supernotify
      data:
        title: "My Home Notification"
        message: "Notify via custom chat"
        delivery:
            chat_notify:
                data:
                    channel: 3456
    - action: notify.supernotify
      data:
        delivery:
            mqtt_notify:
                data:
                  topic: alert/family_all
                  payload: something happened
```

### Email

Can be used for plain or HTML template emails, and handle images as attachments or embedded HTML.

Also supports `message_html` override to supply html that will be ignored for other notification
types, and does not require templates. In this case, HTML will automatically be tagged onto the
end to include any attached images.

### Media Image

Show an image on a media player, e.g. an Alexa Show ( where that actually works, depending on model )

### Alexa

Announce, or speak, a notification using Home Assistant's built-in *Alexa Devices* integration.

*Note* Home Assistant recommend sending multiple notifications to a pre-defined group, rather
than an explicit list of Alexa devices, to minimize the likelihood of Amazon rate-limiting API calls.

### Alexa Media Player

Announce a message on an Alexa Echo device using the [`alexa_media_player`](https://github.com/alandtse/alexa_media_player) integration available via [HACS](https://www.hacs.xyz).

The `title_only` option can be set to `False` to override the restriction of content to just title, when both title and message on a notification. Otherwise, only the title is announced.

### Persistent

Place a notification on Home Assistant application screen.

Pass a notification ID

## Media support

Images can be included by:

- camera entity, as created by any [Camera Integration](https://www.home-assistant.io/integrations/camera/)
- image entity, for example an [MQTT Image](https://www.home-assistant.io/integrations/image.mqtt/), ideal for Frigate or cameras that stream to MQTT
- `snapshot_url`

Additionally a video clip can be referenced by `clip_url` where supported by a delivery method (currently mobile push only).

An optional PTZ preset can also be referenced in `data`, a PTZ delay before snapshot taken,
and a choice of `onvif` or `frigate` for the PTZ control. After the snap, an additional PTZ will be commanded to return to the `ptz_default_preset` defined for the camera.This image will taken once and then reused across all supporting delivery methods.

Some cameras, like Hikvision, add JPEG comment blocks which confuse the very simplistic media
detection in the SMTP integration, and leads to spurious log entries. Supernotify will automatically rewrite JPEGs into simpler standard forms to avoid this, and optionally `JPEG_ARGS`
can be set, for example to reduce image quality for smaller email attachments.

## Flexible Configuration

Delivery configuration can be done in lots of different ways to suit different configurations
and to keep those configuration as minimal as possible.

Priority order of application


| Where                                | When            | Notes                                            |
|--------------------------------------|-----------------|--------------------------------------------------|
| Action Data                          | Runtime call    |                                                  |
| Recipient delivery override          | Runtime call    |                                                  |
| Scenario delivery override           | Runtime call    | Multiple scenarios applied in no special order   |
| Delivery definition                  | Startup         | `message` and `title` override Action Data      |
| Method defaults                      | Startup         |                                                  |
| Target notification action defaults  | Downstream call |                                                  |


1. Action Data passed at runtime call
2. Recipient delivery override
3. Scenario delivery override
4. Delivery definition
5. Method defaults
6. Target notification action defaults, e.g. mail recipients ( this isn't applied inside supernotifier )

## Setup

Register this GitHub repo as a custom repo
in your [HACS]( https://hacs.xyz) configuration.

Configure in the main Home Assistant config yaml, or an included notify.yaml

See `examples` directory for working minimal and maximal configuration examples.

### Cameras

Use this for additional camera info:

* Link a `device_tracker` to the camera
  * Notifications will first check its online, then use an alternative if primary is down
* Define alternative cameras to use if first fails using `alt_camera`
* For ONVIF or Frigate cameras set up for PTZ
  * Home preset can be defined using `ptz_default_preset` so camera can be reset after taking a snapshot
  * Delay between PTZ command and snapshot can be defined using `ptz_delay`
  * Choose between ONVIF or Frigate PTZ control using `ptz_method`
    * Note that ONVIF may have numeric reference for presets while Frigate uses labels

## Delivery Method Options

All of these set by passing an `options` block in delivery config or method defaults.

|Option         |Methods            |Description                                             |
|---------------|-------------------|--------------------------------------------------------|
|chime_aliases  |chime              |Map tunes to device name or config                      |
|jpeg_flags     |mail               |Tune image grabs                                        |
|title_only     |sms, alexa         |Suppress message body                                   |
|timestamp      |all                |Add a timestamp to message.                             |

`jpeg_flags` can also be set per runtime call by passing in the `media` block.

## Snoozing

Snoozing can be done for a set time, or notifications can be silenced until further notice ( or currently until reboot ).

### Mobile Actions

Mobile actions will be handled according to scheme:

SUPERNOTIFY_<COMMAND>_<TargetType>_

## Scenarios

Scenarios can be defined both as a set of conditions which switch on the scenario and/or as
a set of overrides to apply if the scenario is active.

For example, a scenario could be defined by conditions such as alarm panel arm state, occupancy
and time to indicate when notifications should be minimized, and then different chime sounds
could be selected or deliveries switched off.

Scenarios can override specific delivery configurations, general media configuration (such as setting a camera, or specifying which alert sound to use for a mobile push ). A scenario have a
default `delivery_selection` basis of `implicit`, where the scenario inherits all the default
deliveries, or have this switched off by overriding `delivery_selection` to `explicit` or `fixed` (both do the same thing) in which case only the deliveries mentioned in the scenario
are included.

For more on the conditions, see the [ Home Assistant Conditions documentation](https://www.home-assistant.io/docs/scripts/conditions/) since the conditions are all evaluated at time of
notification by the standard Home Assistant module.


### Example Scenarios

This scenario could be used to select more obtrusive notifications, like email or Alexa announcements,
from a combination of conditions, hence simplifying separate notification calls, and providing
one place to tune multiple notifications.

```yaml
more_attention:
        alias: time to make more of a fuss
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
```

In this example, selecting the scenario by name in a notification call switches on
a set of delivery methods, which saves repetitive declaration in many notification calls. Delivery
Selection is made `implicit` so not switching off any other deliveries that would have applied.

```yaml
red_alert:
      delivery_selection: implicit
      delivery:
        chime_red_alert:
        upstairs_siren:
        downstairs_siren:
      media:
        camera_entity_id: camera.porch
```

Delivery selection can also be passed in the `data` of an action call, in which case it can
also be `fixed`, which disables scenarios from enabling or disabling deliveries and leaves it solely
to defaults or what's listed in the action call.

Conditions aren't essential for scenarios, since they can also be switched on by a notification.

For example in this case, where the `home_security` and `garden` scenarios are explicitly
triggered, and so any overrides declared in those scenarios will be applied. The `constrain_scenarios`
prevents any scenario other than `unoccupied` or the ones explicitly applied here ( to switch off all
other scenarios, use `NULL`).

```yaml
  - action: notify.supernotifier
    data:
        title: Security Notification
        message: '{{state_attr(sensor,"friendly_name")}} triggered'
        priority: high
        apply_scenarios:
          - home_security
          - garden
        constrain_scenarios:
          - unoccupied
```

Individual deliveries can be overridden, including the content of the messages using `message_template` and `title_template`.
The templates are regular HomeAssistant `jinja2`, and have the same context variables available as the scenario conditions (see below ). In the example below, Alexa can be made to whisper easily without having to mess with the text of every notification, and this scenario could also have conditions applied, for example to all low priority messages at night.

```yaml
  scenarios:
    emotional:
      delivery:
        alexa:
          data:
            title_template: '<amazon:emotion name="excited" intensity="medium">{{notification_message}}</amazon:emotion>'
```

Multiple scenarios can be applied, in the order provided, and each template will be applied in turn to the results of the previous template. So in the example below, you could apply both the *whisper* and *emotion* Amazon Alexa markup to the same message, or add in some sound effects based on any of the conditions.

A blank `message_template` or `title_template` can also be used to selectively switch off one of those fields for a particular delivery, for example when sending a notification out via email, push and Alexa announcement.

### Additional variables for conditions

Scenario and DeliveryMethod conditions have access to everything that any other Home Assistant conditions can
access, such as entities, templating etc. In addition, supernotifier makes additional variables
automatically available:

|Template Variable              |Description                                                       |
|-------------------------------|------------------------------------------------------------------|
|notification_priority          |Priority of current notification, explicitly selected or default  |
|notification_message           |Message of current notification                                   |
|notification_title             |Title of current notification                                     |
|applied_scenarios              |Scenarios explicitly selected in current notification call        |
|required_scenarios             |Scenarios a notification mandates to be enabled or else suppressed|
|constrain_scenarios            |Restricted list of scenarios                                      |
|occupancy                      |One or more occupancy states, e.g. ALL_HOME, LONE_HOME            |


## Tips

### Message formatting

To send a glob of html to include in email, set `message_html` in action data. This will be ignored
by other delivery methods that don't handle email. This can be also be used to have a notification
with only a title ( that gets picked up for mobile push, alexa and other brief communications ) with
a much more detailed body only for email.

Use `data_template` to build the `data` dictionary with Jinja2 logic from automations or scripts.

## Development

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/:user/:repo/:workflow)
