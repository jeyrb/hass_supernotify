'''
  domain: automation
  source_url: https://github.com/SgtBatten/HA_blueprints/blob/main/Frigate%20Camera%20Notifications/Beta
  input:
    camera:
      name: Frigate Camera
      description: |
        Select the camera entity that will trigger notifications. 
        If you do not see cameras listed in the drop down, check you have the frigate integration installed.

        Note: The automation relies the frigate camera name matching the entity id in Home Assistant. It will automatically strip '_x' from the end of the entity id where x is a number.
      selector:
        entity:
          integration: frigate
          domain: camera
          device_class: camera
    notify_device:
      name: Mobile Device
      description: Select a device that runs the official Home Assistant app to receive notifications. If you wish to notify a group of devices or and Android/Fire TV use the field below to override this selection. This will be ignored in that case but it still required.
      default: false
      selector:
        device:
          integration: mobile_app
    notify_group:
      name: Notification Group or Android/Fire TV (Optional)
      description: |
        The name of the group or individual TV to send notifications to.
        If set, this will override individual devices above.

        Note: If the group contains both mobile devices and TVs, the TV will not display the snapshot unless 'TV notifications' to true, however this will stop android phones recieving thumbnails.
      default: ""
    base_url:
      name: Base URL (Optional)
      description: |
        The external url for your Home Assistant instance. 
        Recommended for iOS and required for Android/Fire TV.
      default: ""
    mqtt_topic:
      name: MQTT Topic (Advanced)
      description: The MQTT topic frigate sends messages in.
      default: frigate/events
    client_id:
      name: Client ID (Optional-Advanced)
      description: Used to support multiple instances of Frigate. Leave blank if you don't know what to do.
      default: ""
    title:
      name: Notification Title (Optional)
      description: |
        # Notification Customisations

        The title of the notification.
      default: ""
    message:
      name: Notification Message
      description: |
        The message of the notification.
        You can use variables such as {{camera_name}} and {{label}}
        e.g A {{ label }} {{ 'is loitering' if loitering else 'was detected' }} on the {{ camera_name }} camera.

      default: A {{ label }} {{ 'is loitering' if loitering else 'was detected' }} on the {{ camera_name }} camera.
      selector:
        select:
          options:
            - label: "Default:   e.g A Person was detected on the Side camera."
              value: "A {{ label }} {{ 'is loitering' if loitering else 'was detected' }} on the {{ camera_name }} camera."
            - label: "Short:     e.g Person detected - Side"
              value: "{{ label }} detected - {{ camera_name }}"
            - label: "Short with a timestamp HH:MM"
              value: "{{ label }} detected - {{ camera_name }} at {{event['after']['start_time']|timestamp_custom('%H:%M')}}"
            - label: "Long:      e.g A Person was detected on the Side camera in the driveway."
              value: "A {{ label }} {{ 'is loitering' if loitering else 'was detected' }} on the {{ camera_name }} camera{% if enteredzones %} in the {{ enteredzones | join(', ') | replace('_',' ') }}{% endif %}."
            - label: "Long with a timestamp HH:MM"
              value: "A {{ label }} {{ 'is loitering' if loitering else 'was detected' }} on the {{ camera_name }} camera{% if enteredzones %} in the {{ enteredzones | join(', ') | replace('_',' ') }}{% endif %} at {{event['after']['start_time']|timestamp_custom('%H:%M')}}."
          custom_value: true
    subtitle:
      name: Subtitle
      description: A secondary heading you can use in your notifications.
      default: ""
    critical:
      name: Critical Notification (Optional)
      description: |
        Send as a critical notification to the mobile device. This will ignore silent/vibrate modes.
        You can choose to limit critical notifications to certain times using a template (some examples provided but you can enter your own as long as it outputs true or false)
      default: "false"
      selector:
        select:
          options:
            - "false"
            - "true"
            - "{{'false' if now().hour in [8,9,10,11,12,13,14,15,16,17,18] else 'true'}}"
            - "{{'true' if is_state('sun.sun', 'above_horizon') else 'false' }}"
            - "{{ event['after']['top_score'] |float(0) > 0.8 }}"
          custom_value: true
    alert_once:
      name: Alert Once (Optional)
      description: Only the first notification for each event will play a sound. Updates, including new thumbnails will be silent. iOS users who use Critical Notifications above will still hear default critical sounds for updates.
      default: false
      selector:
        boolean:
    attachment:
      name: Attachment
      description: |
        Choose which image to attach to the notification.

        Note: TVs will always get sent the snapshot if TV is true
      default: thumbnail.jpg
      selector:
        select:
          options:
            - label: Thumbnail
              value: thumbnail.jpg
            - label: Snapshot
              value: snapshot.jpg
            - label: Snapshot with bounding box
              value: snapshot.jpg?bbox=1
            - label: Snapshot cropped
              value: snapshot.jpg?crop=1
            - label: Snapshot cropped with bounding box
              value: snapshot.jpg?bbox=1&crop=1
          mode: dropdown
    update_thumbnail:
      name: Update Image (Optional)
      description: Update the notification if a new "better" image is available.
      default: false
      selector:
        boolean:
    video:
      name: Video (Optional)
      description: You can optionally attach the clip to the notification which will replace the thumbnail/snapshot above if available.
      default: ""
      selector:
        select:
          options:
            - label: None
              value: ""
            - label: Clip
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera}}/clip.mp4"
    color:
      name: Notification Color - Android/TV only (Optional)
      description: Set the color of the notification on your Android mobile device or TV.
      default: "#03a9f4"
      selector:
        select:
          options:
            - label: Primary (Steelblue)
              value: "#03a9f4"
            - label: Red
              value: "#f44336"
            - label: Pink
              value: "#e91e63"
            - label: Purple
              value: "#926bc7"
            - label: Deep Purple
              value: "#6e41ab"
            - label: Indigo
              value: "#3f51b5"
            - label: Blue
              value: "#2196f3"
            - label: Light Blue
              value: "#03a9f4"
            - label: Cyan
              value: "#00bcd4"
            - label: Teal
              value: "#009688"
            - label: Green
              value: "#4caf50"
            - label: Light Green
              value: "#8bc34a"
            - label: Lime
              value: "#cddc39"
            - label: Yellow
              value: "#ffeb3b"
            - label: Amber
              value: "#ffc107"
            - label: Orange
              value: "#ff9800"
            - label: Deep Orange
              value: "#ff5722"
            - label: Brown
              value: "#795548"
            - label: Light Grey
              value: "#bdbdbd"
            - label: Grey
              value: "#9e9e9e"
            - label: Dark Grey
              value: "#606060"
            - label: Blue Grey
              value: "#607d8b"
            - label: Black
              value: "#000000"
            - label: White
              value: "#ffffff"
    icon:
      name: Notification Icon (Optional)
      description: Change the icon that displays on the notification. You can enter a single icon or create a template like the example given in the dropdown. You must include 'mdi:' in the icon name.
      default: mdi:home-assistant
      selector:
        select:
          options:
            - mdi:home-assistant
            - mdi:cctv
            - "mdi:{{'account-outline' if label == 'Person' else 'dog' if label == 'Dog' else 'cat' if label == 'Cat' else 'car' if label == 'Car' else 'home-assistant'}}"
          custom_value: true
    group:
      name: Group
      description: The group name that will determine if notifications are grouped on your mobile device. If you want notifications grouped by camera, ensure it contains {{camera}}
      default: "{{camera}}-frigate-notification{{'-loitering' if loitering}}"
    sound:
      name: Notification Sound - iOS only (Optional)
      description: You can specify a soud file on your device that will play for the notifications. You will need to import the sound file into home assistant.
      default: default
      selector:
        select:
          options:
            - default
            - none
          custom_value: true
    ios_live_view:
      name: Live View Entity - iOS only (Optional)
      description: Attach a live view from the selected entity to the notification for iOS devices.
      default: ""
      selector:
        entity:
          domain: camera
    android_auto:
      name: Android Auto
      description: Show the notification on Android Auto if the recieving device is connected.
      default: false
      selector:
        boolean:
    sticky:
      name: Sticky - Android only (Optional)
      description: |
        When enabled, the notification will stay active on the device after tapping it and remain there until cleared.
      default: false
      selector:
        boolean:
    channel:
      name: Notification Channel - Android only (Optional)
      description: Create a new channel for notifications to allow custom notification sounds, vibration patterns and overide of Do Not Disturb mode. Configured directly on the device.
      default: ""
    zone_filter:
      name: Zone Filter on/off (Optional)
      description: |
        # Filters

        Enable to only notify if object has entered a zone listed below.
      default: false
      selector:
        boolean:
    zones:
      name: Required Zones (Optional - Enabled Above)
      description: |
        Enter the name of one zone at a time. It must be lowercase and include underscores as per your frigate config.
        By default any zone is acceptable. if you desire ALL listed zones to be entered before getting a notification, enable the multi toggle below.
      default: []
      selector:
        select:
          options:
            - examples
            - porch
            - front_door
            - side
            - garden
          multiple: true
          custom_value: true
    zone_multi:
      name: Multi Zone (Optional)
      description: Require all zones specified above to be entered, instead of any listed zone. Zone Filter must be enabled also.
      default: false
      selector:
        boolean:
    labels:
      name: Object Filter (Optional)
      description: |
        Enter or select one object at a time.
      default: ""
      selector:
        select:
          options:
            - person
            - dog
            - cat
            - car
            - package
            - bird
          multiple: true
          custom_value: true
    presence_filter:
      name: Presence Filter (Optional)
      description: Only notify if selected presence entity is not "home".
      default: ""
      selector:
        entity:
          domain:
            - device_tracker
            - person
            - group
    state_filter:
      name: State Filter on/off (Optional)
      description: Enable the two State Filter settings below. Only notify if selected entity is in the specified states.
      default: false
      selector:
        boolean:
    state_entity:
      name: State Filter Entity (Optional)
      description: Only notify if selected entity is in the below state. You must enable State Filter above to use this.
      default: ""
      selector:
        entity:
    state_filter_states:
      name: State Filter States (Optional)
      description: Enter the states that the above entity must be in, one at a time.
      default: []
      selector:
        select:
          options: []
          multiple: true
          custom_value: true
    disable_times:
      name: Time Filter (Optional)
      description: Prevent notifications from being sent during the specified hours
      default: []
      selector:
        select:
          multiple: true
          options:
            - label: 00:00 - 00:59
              value: "0"
            - label: 01:00 - 01:59
              value: "1"
            - label: 02:00 - 02:59
              value: "2"
            - label: 03:00 - 03:59
              value: "3"
            - label: 04:00 - 04:59
              value: "4"
            - label: 05:00 - 05:59
              value: "5"
            - label: 06:00 - 06:59
              value: "6"
            - label: 07:00 - 07:59
              value: "7"
            - label: 08:00 - 08:59
              value: "8"
            - label: 09:00 - 09:59
              value: "9"
            - label: 10:00 - 10:59
              value: "10"
            - label: 11:00 - 11:59
              value: "11"
            - label: 12:00 - 12:59
              value: "12"
            - label: 13:00 - 13:59
              value: "13"
            - label: 14:00 - 14:59
              value: "14"
            - label: 15:00 - 15:59
              value: "15"
            - label: 16:00 - 16:59
              value: "16"
            - label: 17:00 - 17:59
              value: "17"
            - label: 18:00 - 18:59
              value: "18"
            - label: 19:00 - 19:59
              value: "19"
            - label: 20:00 - 20:59
              value: "20"
            - label: 21:00 - 21:59
              value: "21"
            - label: 22:00 - 22:59
              value: "22"
            - label: 23:00 - 23:59
              value: "23"
    cooldown:
      name: Cooldown (Optional)
      description: Delay before sending another notification for this camera after the last event.
      default: 30
      selector:
        number:
          max: 86400
          min: 0
          unit_of_measurement: seconds
    custom_filter:
      name: Custom Filter (Optional - Advanced)
      description: A filter that must result in true or false but can be templated as necessary. You will need to ensure it is enclosed with appropriate \"quotes\" and \{\{brackets\}\}.
      default: true
    silence_timer:
      name: Silence New Object Notifications (Optional)
      description: |
        How long to silence notifications for this camera when requested as part of the actionable notification. 
        Note: This only applies to new objects. Existing tracked objects will not be affected.
      default: 30
      selector:
        number:
          max: 3600
          min: 0
          unit_of_measurement: minutes
    loiter_timer:
      name: Loitering Notifications (Optional)
      description: >
        Sends new loitering notification if a stationary object is detected for longer
        than the specified time. 0 is off and will not send notifications.
      default: 0
      selector:
        number:
          max: 3600
          min: 0
          unit_of_measurement: minutes
    initial_delay:
      name: Delay initial notification (Optional)
      description: |
        How long to delay the first notification for each event. 

        Use this if you DO NOT use "update image" and are experiencing notifications without attached images. Start with small numbers.
      default: 0
      selector:
        number:
          max: 15
          min: 0
          unit_of_measurement: seconds
    tap_action:
      name: Tap Action URL
      description: |
        # Action Buttons and URLs

        The url to open when tapping on the notification. Some presets are provided, you can also set you own by typing in the box. 

        These options define the text and urls associated with the three action buttons at the bottom of the notification.
      default: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera}}/clip.mp4"
      selector:
        select:
          options:
            - label: View Clip
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera}}/clip.mp4"
            - label: View Snapshot
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/snapshot.jpg"
            - label: View Stream
              value: "{{base_url}}/api/camera_proxy_stream/camera.{{trigger.payload_json['after']['camera'] | lower | replace('-','_')}}?token={{state_attr( 'camera.' ~ camera, 'access_token')}}"
            - label: Open Home Assistant (web)
              value: "{{base_url}}/lovelace"
            - label: Open Home Assistant (app)
              value: /lovelace
            - label: Open Frigate
              value: /ccab4aaf_frigate/dashboard
            - label: Open Frigate (Full Access)
              value: /ccab4aaf_frigate-fa/dashboard
            - label: Open Frigate (proxy)
              value: /ccab4aaf_frigate-proxy/dashboard
            - label: Open Reolink App (Android)
              value: app://com.mcu.reolink
            - label: Custom Action (Manual Trigger)
              value: custom-{{ camera }}
          custom_value: true
    button_1:
      name: Action Button 1 Text
      description: "The text used on the first Action button at the bottom of the notification. Set the URL below. Default is View Clip"
      default: "View Clip"
    url_1:
      name: Action Button 1 URL
      description: Customise what happens when you press the first Action Button. Select from one of the preconfigured options or enter your own custom URL.
      default: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera}}/clip.mp4"
      selector:
        select:
          options:
            - label: View Clip
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera}}/clip.mp4"
            - label: View Snapshot
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/snapshot.jpg"
            - label: View Stream
              value: "{{base_url}}/api/camera_proxy_stream/camera.{{trigger.payload_json['after']['camera'] | lower | replace('-','_')}}?token={{state_attr( 'camera.' ~ camera, 'access_token')}}"
            - label: Open Home Assistant (web)
              value: "{{base_url}}/lovelace"
            - label: Open Home Assistant (app)
              value: /lovelace
            - label: Open Frigate
              value: /ccab4aaf_frigate/dashboard
            - label: Open Frigate (Full Access)
              value: /ccab4aaf_frigate-fa/dashboard
            - label: Open Frigate (proxy)
              value: /ccab4aaf_frigate-proxy/dashboard
            - label: Open Reolink App (Android)
              value: app://com.mcu.reolink
            - label: Custom Action (Manual Trigger)
              value: custom-{{ camera }}
          custom_value: true
    icon_1:
      name: Action Button 1 icon - iOS Only
      description: Customise the Icon on the first Action Button. Only the iOS SFSymbols library is supported, not mdi:icons. e.g sfsymbols:bell
      default: ""
    button_2:
      name: Action Button 2 Text
      description: "The text used on the second Action button at the bottom of the notification. Set the URL below."
      default: "View Snapshot"
    url_2:
      name: Action Button 2 URL
      description: Customise what happens when you press the second Action Button. Select from one of the preconfigured options or enter your own custom URL.
      default: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/snapshot.jpg"
      selector:
        select:
          options:
            - label: View Clip
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera}}/clip.mp4"
            - label: View Snapshot
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/snapshot.jpg"
            - label: View Stream
              value: "{{base_url}}/api/camera_proxy_stream/camera.{{trigger.payload_json['after']['camera'] | lower | replace('-','_')}}?token={{state_attr( 'camera.' ~ camera, 'access_token')}}"
            - label: Open Home Assistant (web)
              value: "{{base_url}}/lovelace"
            - label: Open Home Assistant (app)
              value: /lovelace
            - label: Open Frigate
              value: /ccab4aaf_frigate/dashboard
            - label: Open Frigate (Full Access)
              value: /ccab4aaf_frigate-fa/dashboard
            - label: Open Frigate (proxy)
              value: /ccab4aaf_frigate-proxy/dashboard
            - label: Open Reolink App (Android)
              value: app://com.mcu.reolink
            - label: Custom Action (Manual Trigger)
              value: custom-{{ camera }}
          custom_value: true
    icon_2:
      name: Action Button 2 icon - iOS Only
      description: Customise the Icon on the second Action Button. Only the iOS SFSymbols library is supported, not mdi:icons. e.g sfsymbols:bell
      default: ""
    button_3:
      name: Action Button 3 Text
      description: "The text used on the third Action button at the bottom of the notification. Set the URL below."
      default: "Silence New Notifications"
    url_3:
      name: Action Button 3 URL
      description: Customise what happens when you press the third Action Button. Select from one of the preconfigured options or enter your own custom URL.
      default: silence-{{ camera }}
      selector:
        select:
          options:
            - label: Silence New Notifications
              value: silence-{{ camera }}
            - label: View Clip
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera}}/clip.mp4"
            - label: View Snapshot
              value: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/snapshot.jpg"
            - label: View Stream
              value: "{{base_url}}/api/camera_proxy_stream/camera.{{trigger.payload_json['after']['camera'] | lower | replace('-','_')}}?token={{state_attr( 'camera.' ~ camera, 'access_token')}}"
            - label: Open Home Assistant (web)
              value: "{{base_url}}/lovelace"
            - label: Open Home Assistant (app)
              value: /lovelace
            - label: Open Frigate
              value: /ccab4aaf_frigate/dashboard
            - label: Open Frigate (Full Access)
              value: /ccab4aaf_frigate-fa/dashboard
            - label: Open Frigate (proxy)
              value: /ccab4aaf_frigate-proxy/dashboard
            - label: Open Reolink App (Android)
              value: app://com.mcu.reolink
            - label: Custom Action (Manual Trigger)
              value: custom-{{ camera }}
          custom_value: true
    icon_3:
      name: Action Button 3 icon - iOS Only
      description: Customise the Icon on the third Action Button. Only the iOS SFSymbols library is supported, not mdi:icons. e.g sfsymbols:bell
      default: ""
    custom_action_manual:
      name: Custom Action (Manual Trigger)
      description: Customisable action that you can trigger with the Custom Action buttons in the notification. Select Custom Action on any Action Button above.
      selector:
        action: {}
      default: []
    custom_action_auto:
      name: Custom Action (Auto Trigger)
      description: Customisable action that will trigger on the initial notification (subject to the all other notification conditions).
      selector:
        action: {}
      default: []
    custom_action_auto_multi:
      name: Custom Action (Auto Trigger in Loop)
      description: Customisable action that will trigger all on subsequent notifications (subject to the all other notification conditions). If you want it to also trigger on the initial notification you need to enter it in both input fields.
      selector:
        action: {}
      default: []
    tv:
      name: TV Notification (Optional)
      description: |
        # TV Notifications

        Set to true if you are notifying an Android/Fire TV
        Can also be used to prioritise snapshots on the TV over android mobile apps when notifying a mixed device group.
        Base URL must be set

        The below settings are for TV notifications only
      default: false
      selector:
        boolean:
    tv_position:
      name: TV Notification Position (Optional)
      description: Set the position of the notification on your TV
      default: center
      selector:
        select:
          mode: dropdown
          options:
            - bottom-right
            - bottom-left
            - top-right
            - top-left
            - center
    tv_size:
      name: TV Notification Size (Optional)
      description: Set the size of the notification on your TV.
      default: large
      selector:
        select:
          mode: dropdown
          options:
            - small
            - medium
            - large
            - max
    tv_duration:
      name: TV Notification Duration (Optional)
      description: The duration (in seconds) the notification will display on your TV.
      default: 10
      selector:
        number:
          max: 300
          min: 0
          unit_of_measurement: seconds
    tv_transparency:
      name: TV notification Transaparency (Optional)
      description: Set the transparency of the notification on your TV.
      default: 0%
      selector:
        select:
          mode: dropdown
          options:
            - 0%
            - 25%
            - 50%
            - 75%
            - 100%
    tv_interrupt:
      name: TV Notification Interrupt (Optional)
      description: "If set to true the notification is interactive and can be dismissed or selected to display more details. Depending on the running app (e.g., Netflix), this may stop playback."
      default: false
      selector:
        boolean:
    debug:
      name: Debug
      description: |
        # DEBUG

        Enable to send debug messsages to the home assistant logbook.
      default: false
      selector:
        boolean:
mode: parallel
trigger_variables:
  input_camera: !input camera
  camera: "{{ input_camera | regex_replace('^camera\\.|_\\d+$', '') }}"
  mqtt_topic: !input mqtt_topic
trigger:
  - platform: event
    event_type: mobile_app_notification_action
    event_data:
      action: "silence-{{ camera }}"
    id: silence
  - platform: mqtt
    topic: "{{mqtt_topic}}"
    payload: "{{ camera }}/new"
    value_template: "{{ value_json['after']['camera'] | lower | replace('-','_') }}/{{ value_json['type']}}"
    id: frigate-event
variables:
  input_camera: !input camera
  camera: "{{ input_camera | regex_replace('^camera\\.', '') }}"
  camera_name: "{{ camera | replace('_', ' ') | title }}"
  input_base_url: !input base_url
  base_url: "{{ input_base_url.rstrip('/')}}"
  input_client_id: !input client_id
  client_id: "{{input_client_id if not input_client_id else '/' + input_client_id if '/' not in input_client_id else input_client_id }}"
  attachment: !input attachment
  alert_once: !input alert_once
  update_thumbnail: !input update_thumbnail
  ios_live_view: !input ios_live_view
  android_auto: !input android_auto
  notify_group: !input notify_group
  notify_group_target: "{{ notify_group | lower | regex_replace('^notify\\.', '') | replace(' ','_') }}"
  zone_only: !input zone_filter
  input_zones: !input zones
  zones: "{{ input_zones }}"
  zone_multi: !input zone_multi
  input_labels: !input labels
  labels: "{{ input_labels | list | lower }}"
  presence_entity: !input presence_filter
  disable_times: !input disable_times
  cooldown: !input cooldown
  loitering: false
  loiter_timer: !input loiter_timer
  initial_delay: !input initial_delay
  fps: "{{ states('sensor.' + camera + '_camera_fps')|int(5) }}"
  state_only: !input state_filter
  input_entity: !input state_entity
  input_states: !input state_filter_states
  states_filter: "{{ input_states | list | lower }}"
  color: !input color
  sound: !input sound
  sticky: !input sticky
  tv: !input tv
  tv_position: !input tv_position
  tv_size: !input tv_size
  tv_duration: !input tv_duration
  tv_transparency: !input tv_transparency
  tv_interrupt: !input tv_interrupt
  debug: !input debug
action:
  - choose:
      - alias: "Silence New Object Notifications"
        conditions:
          - condition: trigger
            id: silence
        sequence:
          - service: automation.turn_off
            target:
              entity_id: "{{ this.entity_id }}"
            data:
              stop_actions: false
          - delay:
              minutes: !input silence_timer
          - service: automation.turn_on
            target:
              entity_id: "{{ this.entity_id }}"
      - alias: "Custom Action Manual"
        conditions:
          - condition: trigger
            id: custom
        sequence: !input "custom_action_manual"
      - alias: "Frigate Event"
        conditions:
          - condition: trigger
            id: "frigate-event"
          - "{{ is_state(this.entity_id, 'on') }}"
          - "{{ not this.attributes.last_triggered or (now() - this.attributes.last_triggered).seconds > cooldown }}"
          - "{{ not disable_times|length or not now().hour in disable_times|map('int')|list }}"
        sequence:
          - variables:
              event: "{{ trigger.payload_json }}"
              id: "{{ trigger.payload_json['after']['id'] }}"
              object: "{{ trigger.payload_json['after']['label'] }}"
              label: "{{ object | title }}"
              # Dynamic Variables per event
              initial_home: "{{ presence_entity != '' and is_state(presence_entity, 'home') }}"
              enteredzones: "{{ trigger.payload_json['after']['entered_zones']}}"
              zone_multi_filter: "{{zone_only and zone_multi and enteredzones|length and zones and zones |reject('in', enteredzones) |list |length == 0 }}"
              loitering: false
              # Customisation of text
              title: !input title
              message: !input message
              subtitle: !input subtitle
              tap_action: !input tap_action
              button_1: !input button_1
              button_2: !input button_2
              button_3: !input button_3
              url_1: !input url_1
              url_2: !input url_2
              url_3: !input url_3
              icon_1: !input icon_1
              icon_2: !input icon_2
              icon_3: !input icon_3
              # other things that can be templated and might need info from the event
              critical_input: !input critical
              critical: "{{ true if critical_input == 'true' else true if critical_input == True else false }}"
              custom_filter: !input custom_filter
              icon: !input icon
              group: !input group
              channel: !input channel
              video: !input video
              custom_action_auto: !input custom_action_auto
          - alias: "Debug: write to Log"
            choose:
              - conditions:
                  - "{{debug}}"
                sequence:
                  - service: logbook.log
                    data_template:
                      name: Frigate Notification
                      message: |
                        DEBUG: 
                          Info:
                            fps: {{fps}}, 
                            frigate event id: {{id}}{{', Frigate client ID: ' + client_id if client_id else ''}}, 
                            object (formatted): {{object}} ({{label}}),
                          Config: 
                            camera(formatted): {{camera}}({{camera_name}}), 
                            Base URL: {{base_url}}, 
                            critical: {{critical}}, 
                            alert once: {{alert_once}}, 
                            Update Thumbnails: {{update_thumbnail}}, 
                            Video: {{video}}, 
                            Target: {{'group (input/formatted): ' + notify_group + '/' + notify_group_target + ', ' if notify_group else 'Mobile Device'}}
                            cooldown: {{cooldown}}s, 
                            loiter timer: {{loiter_timer}}s, 
                            initial delay: {{initial_delay}}s, 
                            color: {{color}}, 
                            sound: {{sound}}, 
                            android_auto: {{android_auto}}, 
                            Group: {{group}}, 
                            Channel: {{channel}}, 
                            Sticky: {{sticky}}, 
                            Title: {{title}}, 
                            Message: {{message}},
                            Subtitle: {{subtitle}}, 
                            tap_action: {{tap_action}}, 
                            button 1 Text/URL/Icon: {{iif(button_1, button_1, 'unset')}} ({{url_1}}) {{icon_1}}, 
                            button 2 Text/URL/Icon: {{button_2}} ({{url_2}}) {{icon_2}}, 
                            button 3 Text/URL/Icon: {{button_3}} ({{url_3}}) {{icon_3}}, 
                            icon: {{icon}}
                            tv: {{ tv }}, 
                            tv_position: {{tv_position}}, 
                            tv_size: {{tv_size}}, 
                            tv_duration: {{tv_duration}}, 
                            tv_transparency: {{tv_transparency}}, 
                            tv_interrupt: {{tv_interrupt}}, 
                          Filters: 
                            Zones: 
                              zone filter toggle on: {{zone_only}}, 
                              Multi Zone toggle on: {{zone_multi}}, 
                              Required zones: {{input_zones}}, 
                              Entered Zones: {{enteredzones}}, 
                              Zone Filter TEST: {{'PASS (Multi)' if zone_multi_filter else 'PASS' if ( not zone_only or not zone_multi and zones|select('in', enteredzones)|list|length ) else 'FAIL (Multi)' if zone_multi else 'FAIL' }}, 
                            Required objects TEST: 
                              Input: {{input_labels}}, 
                              TEST: {{'PASS' if not labels|length or object in labels else 'FAIL'}}
                            presence entity (not home):
                              Entity: {{presence_entity}}
                              TEST:  {{'PASS' if not initial_home else 'FAIL'}}, 
                            disabled times: {{disable_times}}, 
                            State Filter: 
                              state filter toggle on: {{state_only}}, 
                              state filter entity: {{input_entity}}, 
                              required states: {{input_states}}, 
                              State Filter TEST: {{'PASS' if not state_only or states(input_entity) in states_filter else 'FAIL' }},
                            Custom Filter: {{custom_filter}},
          - alias: "Notifications enabled for object label"
            condition: template
            value_template: "{{ not labels|length or object in labels }}"
          - alias: "Delay for image"
            choose:
              - conditions:
                  - "{{initial_delay > 0}}"
                sequence:
                  - delay:
                      seconds: "{{initial_delay}}"
          - alias: "Custom Action Auto"
            choose:
              - conditions:
                  - "{{ custom_action_auto |length > 0 }}"
                  - "{{ not zone_only or (not zone_multi and zones|select('in', enteredzones)|list|length > 0) or (zone_multi and enteredzones|length > 0 and zones |reject('in', enteredzones) |list |length == 0) }}"
                  - "{{ not initial_home }}"
                  - "{{ not state_only or states(input_entity) in states_filter }}"
                sequence: !input "custom_action_auto"
          - alias: "Notify on new object"
            choose:
              - conditions:
                  - "{{ not zone_only or (not zone_multi and zones|select('in', enteredzones)|list|length > 0) or (zone_multi and enteredzones|length > 0 and zones |reject('in', enteredzones) |list |length == 0) }}"
                  - "{{ not initial_home }}"
                  - "{{ not state_only or states(input_entity) in states_filter }}"
                  - "{{ custom_filter }}"
                sequence:
                  - choose:
                      - conditions: "{{ not notify_group_target }}"
                        sequence:
                          - device_id: !input notify_device
                            domain: mobile_app
                            type: notify
                            title: "{{title}}"
                            message: "{{message}}"
                            data:
                              tag: "{{ id }}"
                              group: "{{ group }}"
                              color: "{{color}}"
                              # Android Specific
                              subject: "{{subtitle}}"
                              image: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}{{'&' if '?' in attachment else '?'}}format=android"
                              video: "{{video}}"
                              clickAction: "{{tap_action}}"
                              ttl: 0
                              priority: high
                              notification_icon: "{{icon}}"
                              sticky: "{{sticky}}"
                              channel: "{{'alarm_stream' if critical else channel}}"
                              car_ui: "{{android_auto}}"
                              # iOS Specific
                              subtitle: "{{subtitle}}"
                              url: "{{tap_action}}"
                              attachment:
                                url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}"
                              push:
                                sound: "{{sound}}"
                                interruption-level: "{{ iif(critical, 'critical', 'active') }}"
                              entity_id: "{{ios_live_view}}"
                              # Actions
                              actions:
                                - action: URI
                                  title: "{{button_1}}"
                                  uri: "{{url_1}}"
                                  icon: "{{icon_1}}"
                                - action: URI
                                  title: "{{button_2}}"
                                  uri: "{{url_2}}"
                                  icon: "{{icon_2}}"
                                - action: "{{ 'URI' if '/' in url_3 else url_3 }}"
                                  title: "{{button_3}}"
                                  uri: "{{url_3}}"
                                  icon: "{{icon_3}}"
                                  destructive: true
                      - conditions: "{{ tv }}"
                        sequence:
                          - service: "notify.{{ notify_group_target }}"
                            data:
                              title: "{{title}}"
                              message: "{{message}}"
                              data:
                                tag: "{{ id }}"
                                group: "{{ group }}"
                                color: "{{color}}"
                                # Android Specific
                                subject: "{{subtitle}}"
                                clickAction: "{{tap_action}}"
                                ttl: 0
                                priority: high
                                notification_icon: "{{icon}}"
                                sticky: "{{sticky}}"
                                channel: "{{'alarm_stream' if critical else channel}}"
                                car_ui: "{{android_auto}}"
                                # Android/Fire TV
                                image:
                                  url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/snapshot.jpg"
                                fontsize: "{{tv_size}}"
                                position: "{{tv_position}}"
                                duration: "{{tv_duration}}"
                                transparency: "{{tv_transparency}}"
                                interrupt: "{{tv_interrupt}}"
                                timeout: 30
                                # iOS Specific
                                subtitle: "{{subtitle}}"
                                url: "{{tap_action}}"
                                attachment:
                                  url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}"
                                push:
                                  sound: "{{sound}}"
                                  interruption-level: "{{ iif(critical, 'critical', 'active') }}"
                                entity_id: "{{ios_live_view}}"
                                # Actions
                                actions:
                                  - action: URI
                                    title: "{{button_1}}"
                                    uri: "{{url_1}}"
                                    icon: "{{icon_1}}"
                                  - action: URI
                                    title: "{{button_2}}"
                                    uri: "{{url_2}}"
                                    icon: "{{icon_2}}"
                                  - action: "{{ 'URI' if '/' in url_3 else url_3 }}"
                                    title: "{{button_3}}"
                                    uri: "{{url_3}}"
                                    icon: "{{icon_3}}"
                                    destructive: true
                    default:
                      - service: "notify.{{ notify_group_target }}"
                        data:
                          title: "{{title}}"
                          message: "{{message}}"
                          data:
                            tag: "{{ id }}{{'-loitering' if loitering}}"
                            group: "{{ camera }}-frigate-notification{{'-loitering' if loitering}}"
                            color: "{{color}}"
                            # Android Specific
                            subject: "{{subtitle}}"
                            image: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}{{'&' if '?' in attachment else '?'}}format=android"
                            video: "{{video}}"
                            clickAction: "{{tap_action}}"
                            ttl: 0
                            priority: high
                            notification_icon: "{{icon}}"
                            sticky: "{{sticky}}"
                            channel: "{{'alarm_stream' if critical else channel}}"
                            car_ui: "{{android_auto}}"
                            # Android/Fire TV
                            subtitle: "{{subtitle}}"
                            fontsize: "{{tv_size}}"
                            position: "{{tv_position}}"
                            duration: "{{tv_duration}}"
                            transparency: "{{tv_transparency}}"
                            interrupt: "{{tv_interrupt}}"
                            # iOS Specific
                            url: "{{tap_action}}"
                            attachment:
                              url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}"
                            push:
                              sound: "{{sound}}"
                              interruption-level: "{{ iif(critical, 'critical', 'active') }}"
                            entity_id: "{{ios_live_view}}"
                            # Actions
                            actions:
                              - action: URI
                                title: "{{button_1}}"
                                uri: "{{url_1}}"
                                icon: "{{icon_1}}"
                              - action: URI
                                title: "{{button_2}}"
                                uri: "{{url_2}}"
                                icon: "{{icon_2}}"
                              - action: "{{ 'URI' if '/' in url_3 else url_3 }}"
                                title: "{{button_3}}"
                                uri: "{{url_3}}"
                                icon: "{{icon_3}}"
                                destructive: true
          - repeat:
              sequence:
                - wait_for_trigger:
                    - platform: mqtt
                      topic: "{{mqtt_topic}}"
                      payload: "{{ id }}"
                      value_template: "{{ value_json['after']['id'] }}"
                  timeout:
                    minutes: 2
                  continue_on_timeout: false
                - variables:
                    event: "{{ wait.trigger.payload_json }}"
                    loitering: "{{ loiter_timer and event['before']['motionless_count']/fps/60 < loiter_timer and event['after']['motionless_count']/fps/60 >= loiter_timer }}"
                    new_snapshot: "{{ update_thumbnail and event['before']['snapshot_time'] != event['after']['snapshot_time'] }}"
                    home: "{{ presence_entity != '' and is_state(presence_entity, 'home') }}"
                    presence_changed: "{{ presence_entity != '' and as_datetime(event['before']['frame_time']) < states[presence_entity].last_changed }}"
                    last_zones: "{{ event['before']['entered_zones'] |lower}}"
                    enteredzones: "{{ event['after']['entered_zones'] |lower}}"
                    zone_filter: "{{ not zone_only or zones|select('in', enteredzones)|list|length > 0 }}"
                    zone_multi_filter: "{{not zone_only or not zone_multi or ( enteredzones|list|length > 0 and zones and zones|reject('in', enteredzones)|list|length == 0 ) }}"
                    stationary_moved: "{{ event['after']['position_changes'] > event['before']['position_changes'] }}"
                    zone_only_changed: "{{ zone_only and (enteredzones|length > 0 and not last_zones|length) }}"
                    entered_zones_changed: "{{ zones|length > 0 and (zones|select('in', enteredzones)|list|length > 0 and not zones|select('in', last_zones)|list|length) }}"
                    state_true: "{{ not state_only or states(input_entity) in states_filter }}"
                    sub_label: >
                      {% if event['after']['sub_label'] %} 
                        {{event['after']['sub_label'][0]}}
                      {%else%}
                        {{event['after']['sub_label']}}
                      {%endif%}
                    sub_label_before: >
                      {% if event['before']['sub_label'] %} 
                        {{event['before']['sub_label'][0]}}
                      {%else%}
                        {{event['before']['sub_label']}}
                      {%endif%}
                    sub_label_changed: "{{ sub_label != sub_label_before }}"
                    update: "{{ alert_once or (new_snapshot and not loitering and not presence_changed and not zone_only_changed and not entered_zones_changed and not sub_label_changed) }}"
                    critical_input: !input critical
                    critical: "{{ true if critical_input == 'true' else true if critical_input == True else false }}"
                    title: >
                      {% if sub_label %} 
                        {{title | replace('A Person', sub_label|title) | replace('Person', sub_label|title)}}
                      {%else%}
                        {{title}}
                      {%endif%}
                    message: >
                      {% if sub_label %} 
                        {{message | replace('A Person', sub_label|title) | replace('Person', sub_label|title)}}
                      {%else%}
                        {{message}}
                      {%endif%}
                    custom_action_auto_multi: !input custom_action_auto_multi
                - alias: "Update thumbnail at end of event"
                  choose:
                    - conditions:
                        - "{{wait.trigger.payload_json['type'] == 'end' }}"
                        - "{{('snapshot' in attachment and update_thumbnail) or video|length > 0}}"
                      sequence:
                        - delay:
                            seconds: 5
                        - variables:
                            new_snapshot: "{{update_thumbnail}}"
                - alias: "Debug: write to Log"
                  choose:
                    - conditions:
                        - "{{debug}}"
                      sequence:
                        - service: logbook.log
                          data_template:
                            name: Frigate Notification
                            message: |
                              DEBUG (in loop): 
                                Info: 
                                  Last Zones: {{last_zones}}, 
                                  Current zones: {{enteredzones}}, 
                                  sublabel: {{sub_label}}, 
                                  iOS sound: {{update if not critical else 'yes due critical notifications'}}, 
                                  Android Sound: {{'disabled by alert once' if alert_once else 'enabled'}}, 
                                  iOS url: /api/frigate{{client_id}}/notifications/{{id}}/{{camera + '/clip.mp4' if video|length>0 and wait.trigger.payload_json['type'] == 'end' else attachment }}
                                  video: "{{video}}"
                                  critical: {{critical}}, 
                                Triggers: 
                                  New Snapshot: {{new_snapshot}}, 
                                  Presence Changed: {{presence_changed}}, 
                                  stationary moved: {{stationary_moved}}, 
                                  entered zones changed: {{entered_zones_changed}}, 
                                  sublabel changed: {{sub_label_changed}}, 
                                Conditions: 
                                  Loitering: {{loitering}}
                                    or 
                                  Presence Entity not home: {{'ON' if presence_entity != '' else 'OFF'}} - {{'PASS' if not home else 'FAIL'}}, 
                                  zone filter TEST: {{'ON' if zone_only else 'OFF'}} - {{'PASS' if zone_filter else 'FAIL'}}, 
                                  multi-zone filter: {{'OFF' if not zone_only or not zone_multi else 'ON'}} - {{'PASS' if not zone_only or not zone_multi or ( enteredzones|length and zones and zones |reject('in', enteredzones) |list |length == 0 ) else 'FAIL'}}, 
                                  state filter TEST: {{'ON' if state_only else 'OFF'}} - {{'PASS' if state_true else 'FAIL'}}, 
                                  Custom Filter: {{'ON' if custom_filter != '' else 'OFF'}} - {{'PASS' if custom_filter else 'FAIL'}}, 
                                  image: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}"
                - alias: "Custom Action Auto Multi"
                  choose:
                    - conditions:
                        - "{{ custom_action_auto_multi | length > 0 }}"
                        - "{{ loitering or (not home and zone_filter and zone_multi_filter and state_true and (new_snapshot or presence_changed or stationary_moved or zone_only_changed or entered_zones_changed or sub_label_changed)) }}"
                      sequence: !input "custom_action_auto_multi"
                - alias: "Notify on loitering or significant change"
                  choose:
                    - conditions: "{{ loitering or (custom_filter and not home and zone_filter and zone_multi_filter and state_true and (new_snapshot or presence_changed or stationary_moved or zone_only_changed or entered_zones_changed or sub_label_changed)) }}"
                      sequence:
                        - choose:
                            - conditions: "{{ not notify_group_target }}"
                              sequence:
                                - device_id: !input notify_device
                                  domain: mobile_app
                                  type: notify
                                  title: "{{title}}"
                                  message: "{{message}}"
                                  data:
                                    tag: "{{ id }}{{'-loitering' if loitering}}"
                                    group: "{{ group }}"
                                    color: "{{color}}"
                                    # Android Specific
                                    subject: "{{subtitle}}"
                                    image: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}{{'&' if '?' in attachment else '?'}}format=android"
                                    video: "{{video}}"
                                    clickAction: "{{tap_action}}"
                                    ttl: 0
                                    priority: high
                                    alert_once: "{{ alert_once }}"
                                    notification_icon: "{{icon}}"
                                    sticky: "{{sticky}}"
                                    channel: "{{'alarm_stream' if critical else channel}}"
                                    car_ui: "{{android_auto}}"
                                    # iOS Specific
                                    subtitle: "{{subtitle}}"
                                    url: "{{tap_action}}"
                                    attachment:
                                      url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera + '/clip.mp4' if video|length>0 and wait.trigger.payload_json['type'] == 'end' else attachment }}"
                                    push:
                                      sound: "{{ iif(update, 'none', sound) }}"
                                      interruption-level: "{{ iif(critical, 'critical', 'active') }}"
                                    entity_id: "{{ios_live_view}}"
                                    # Actions
                                    actions:
                                      - action: URI
                                        title: "{{button_1}}"
                                        uri: "{{url_1}}"
                                        icon: "{{icon_1}}"
                                      - action: URI
                                        title: "{{button_2}}"
                                        uri: "{{url_2}}"
                                        icon: "{{icon_2}}"
                                      - action: "{{ 'URI' if '/' in url_3 else url_3 }}"
                                        title: "{{button_3}}"
                                        uri: "{{url_3}}"
                                        icon: "{{icon_3}}"
                                        destructive: true
                            - conditions: "{{ tv }}"
                              sequence:
                                - service: "notify.{{ notify_group_target }}"
                                  data:
                                    title: "{{title}}"
                                    message: "{{message}}"
                                    data:
                                      tag: "{{ id }}{{'-loitering' if loitering}}"
                                      group: "{{ group }}"
                                      color: "{{color}}"
                                      # Android Specific
                                      subject: "{{subtitle}}"
                                      clickAction: "{{tap_action}}"
                                      ttl: 0
                                      priority: high
                                      alert_once: "{{ alert_once }}"
                                      notification_icon: "{{icon}}"
                                      sticky: "{{sticky}}"
                                      channel: "{{'alarm_stream' if critical else channel}}"
                                      car_ui: "{{android_auto}}"
                                      # Android/Fire TV
                                      image:
                                        url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/snapshot.jpg"
                                      video: "{{video}}"
                                      fontsize: "{{tv_size}}"
                                      position: "{{tv_position}}"
                                      duration: "{{tv_duration}}"
                                      transparency: "{{tv_transparency}}"
                                      interrupt: "{{tv_interrupt}}"
                                      timeout: 30
                                      # iOS Specific
                                      subtitle: "{{subtitle}}"
                                      url: "{{tap_action}}"
                                      attachment:
                                        url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera + '/clip.mp4' if video|length>0 and wait.trigger.payload_json['type'] == 'end' else attachment }}"
                                      push:
                                        sound: "{{ iif(update, 'none', sound) }}"
                                        interruption-level: "{{ iif(critical, 'critical', 'active') }}"
                                      entity_id: "{{ios_live_view}}"
                                      # Actions
                                      actions:
                                        - action: URI
                                          title: "{{button_1}}"
                                          uri: "{{url_1}}"
                                          icon: "{{icon_1}}"
                                        - action: URI
                                          title: "{{button_2}}"
                                          uri: "{{url_2}}"
                                          icon: "{{icon_2}}"
                                        - action: "{{ 'URI' if '/' in url_3 else url_3 }}"
                                          title: "{{button_3}}"
                                          uri: "{{url_3}}"
                                          icon: "{{icon_3}}"
                                          destructive: true
                          default:
                            - service: "notify.{{ notify_group_target }}"
                              data:
                                title: "{{title}}"
                                message: "{{message}}"
                                data:
                                  tag: "{{ id }}{{'-loitering' if loitering}}"
                                  group: "{{ group }}"
                                  color: "{{color}}"
                                  # Android Specific
                                  subject: "{{subtitle}}"
                                  image: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}{{'&' if '?' in attachment else '?'}}format=android"
                                  video: "{{video}}"
                                  clickAction: "{{tap_action}}"
                                  ttl: 0
                                  priority: high
                                  alert_once: "{{ alert_once }}"
                                  notification_icon: "{{icon}}"
                                  sticky: "{{sticky}}"
                                  channel: "{{'alarm_stream' if critical else channel}}"
                                  car_ui: "{{android_auto}}"
                                  # Android/Fire TV
                                  fontsize: "{{tv_size}}"
                                  position: "{{tv_position}}"
                                  duration: "{{tv_duration}}"
                                  transparency: "{{tv_transparency}}"
                                  interrupt: "{{tv_interrupt}}"
                                  # iOS Specific
                                  subtitle: "{{subtitle}}"
                                  url: "{{tap_action}}"
                                  attachment:
                                    url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{camera + '/clip.mp4' if video|length>0 and wait.trigger.payload_json['type'] == 'end' else attachment }}"
                                  push:
                                    sound: "{{ iif(update, 'none', sound) }}"
                                    interruption-level: "{{ iif(critical, 'critical', 'active') }}"
                                  entity_id: "{{ios_live_view}}"
                                  # Actions
                                  actions:
                                    - action: URI
                                      title: "{{button_1}}"
                                      uri: "{{url_1}}"
                                      icon: "{{icon_1}}"
                                    - action: URI
                                      title: "{{button_2}}"
                                      uri: "{{url_2}}"
                                      icon: "{{icon_2}}"
                                    - action: "{{ 'URI' if '/' in url_3 else url_3 }}"
                                      title: "{{button_3}}"
                                      uri: "{{url_3}}"
                                      icon: "{{icon_3}}"
                                      destructive: true
              until: "{{ not wait.trigger or wait.trigger.payload_json['type'] == 'end' }}"
'''