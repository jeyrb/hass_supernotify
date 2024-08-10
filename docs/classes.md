# Core Classes

``` mermaid
classDiagram
  Notification "1" *-- "*" Envelope
  Notification "1" *-- "1" ConfigurationVariables
  Envelope "1" ..> "1" DeliveryMethod
  SupernotificationConfiguration "1" o-- "0..*" Scenario
  SupernotificationConfiguration "1" o-- "0..*" Snooze
```

::: custom_components.supernotify.delivery_method.DeliveryMethod
    handler: python
    heading_level: 2


::: custom_components.supernotify.notification.Notification
    handler: python
    heading_level: 2


::: custom_components.supernotify.envelope.Envelope
    handler: python
    heading_level: 2


::: custom_components.supernotify.scenario.Scenario
    handler: python
    heading_level: 2

::: custom_components.supernotify.snoozer.Snooze
    handler: python
    heading_level: 2

::: custom_components.supernotify.ConditionVariables
    handler: python
    heading_level: 2
