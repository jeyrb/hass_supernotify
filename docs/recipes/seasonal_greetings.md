Use a scenario with a condition to identify when in a date range.

```yaml
scenarios:
    xmas:
      alias: Christmas season
      condition:
        condition: or
        conditions:
          - "{{ (12,1) <= (now().month, now().day) <= (12,31) }}"
          - "{{ (1,1) <= (now().month, now().day) <= (1,7) }}"
    halloween:
      alias: Spooky season
      condition:
        condition: and
        conditions:
          - "{{ (10,31) == (now().month, now().day) }}"
      delivery:
          alexa:
            data:
              message_template: '<amazon:effect name="whispered">{{notification_message}}</amazon:effect>'

    birthdays:
      alias: Family birthdays
      condition:
        condition: or
        conditions:
          - "{{ (5,23) == (now().month, now().day) }}"
          - "{{ (11,9) == (now().month, now().day) }}"

```
