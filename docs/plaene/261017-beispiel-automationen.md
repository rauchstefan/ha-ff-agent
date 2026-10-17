# Beispiel-Automationen (Entwurf für README, PR 6)

Stammen aus den Berichten des Entwicklers zu PR 3 und PR 4 (2026-10-17). Beispiel 1 ist
in `tests/test_entities.py` getestet, Beispiel 2 nur in Teilen (Actions und Event-Entität,
nicht die Companion-App selbst).

Die Entity-IDs hängen vom Namen des Eintrags ab. In der Doku die Entität per Auswahl
in der UI wählen lassen, nicht abtippen.

## Pflichtfilter

Ein `state`-Trigger auf die Event-Entität braucht immer
`not_from: [unavailable, unknown]` und `not_to: [unavailable, unknown]`. Ohne die Filter
löst jeder Reload und jeder Neustart die Automation aus (siehe docs/architektur.md,
HA-Fallstricke).

## 1. Bei Alarm Licht einschalten

```yaml
automation:
  - alias: "Alarm: Licht an"
    description: "Schaltet bei jedem neuen FF-Agent-Alarm das Licht ein."
    triggers:
      - trigger: state
        entity_id: event.ff_agent_alarm  # Event-Entität "Alarm" des Eintrags
        not_from: [unavailable, unknown]
        not_to: [unavailable, unknown]
    actions:
      - action: light.turn_on
        target:
          entity_id: light.flur
        data:
          brightness_pct: 100
```

Alternative ohne Event: `trigger: state` auf den Binary-Sensor „Alarm aktiv“ mit
`to: "on"`. Löst nur beim Wechsel von aus nach an aus, also nicht bei einem zweiten
Alarm, solange der erste noch aktiv ist.

## 2. Benachrichtigung mit Knopf „Zusagen“ (Companion-App)

```yaml
automation:
  - alias: "FF Agent: Alarm mit Zusage-Knopf"
    triggers:
      - trigger: state
        entity_id: event.ff_agent_alarm
        not_from: [unavailable, unknown]
        not_to: [unavailable, unknown]
    actions:
      - action: notify.mobile_app_mein_handy
        data:
          title: "Alarm"
          message: "Alarmierung über FF Agent"
          data:
            tag: ff_agent_alarm
            ttl: 0
            priority: high
            actions:
              - action: FF_AGENT_ACCEPT
                title: "Zusagen"
              - action: FF_AGENT_REJECT
                title: "Absagen"

  - alias: "FF Agent: Zusage aus der Benachrichtigung"
    triggers:
      - trigger: event
        event_type: mobile_app_notification_action
        event_data:
          action: FF_AGENT_ACCEPT
    actions:
      - action: ff_agent.accept
        data:
          config_entry_id: "<ENTRY_ID>"
      - action: notify.mobile_app_mein_handy
        data:
          message: "clear_notification"
          data:
            tag: ff_agent_alarm
```

Hinweise für die Doku:

- Für die Absage denselben zweiten Block mit `FF_AGENT_REJECT` und `ff_agent.reject`
  anlegen.
- Optionale Felder bei `ff_agent.accept`:
  - `transport`: `car`, `feet` oder `bicycle`
  - `latitude` und `longitude`, nur beide zusammen
- Ist in FF Agent „auch für Testalarme“ an, lösen Testalarme die Automation ebenfalls aus.
- Der Standort wird nur gesendet, wenn er angegeben ist oder in den Optionen eine
  Standort-Entität gesetzt ist.
- Eine Antwort 200 von FF Agent heißt nur „gesendet“. Ob die Rückmeldung verbucht wurde,
  ist ungeprüft (Annahme A7).
