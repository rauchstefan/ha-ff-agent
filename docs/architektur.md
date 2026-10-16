# Architektur

Gesamtbild der Integration. Wird vom `architekt` gepflegt, sobald die ersten
Entscheidungen gefallen sind. Einzelentscheidungen stehen als ADR in `docs/adr/`.

Stand 2026-10-16: noch kein Design. Siehe `docs/projekt-brief.md`.

## Geplante Struktur (HACS-Konvention)

```
custom_components/ff_agent/
  __init__.py        Setup/Unload des Config-Entries
  manifest.json      Metadaten, Version, Abhängigkeiten
  config_flow.py     Einrichtung über die UI
  const.py           Konstanten
  coordinator.py     Datenabruf (falls Polling)
  translations/      de.json, en.json, handgeschrieben (kein strings.json bei Custom)
  brand/             icon.png (256 px), icon@2x.png (512 px), ab HA 2026.3
  diagnostics.py     Diagnosedaten mit Redaction
tests/               pytest + pytest-homeassistant-custom-component
hacs.json            HACS-Metadaten
```

## HACS-Rahmen (Stand 2026-10-16)

Details: `docs/recherche/261016-hacs-anforderungen.md`.

- HACS funktioniert nur mit **öffentlichen** Repos.
- HACS ermittelt die Version aus dem Tag des neuesten **GitHub-Releases**. Der Tag muss zu
  `manifest.version` passen.
- Die CI prüft mit `validate.yml` (hassfest, HACS-Action ohne `ignore`) und `tests.yml`
  (ruff, pytest).

## FF-Agent-Schnittstellen (Kenntnisstand 2026-10-16)

Details und Quellen: `docs/recherche/261016-ffagent-schnittstellen.md`.

- **WebAPI v1.6 (2019) ist nur eingehend**, extern → FF Agent. Sie bietet die Endpunkte
  `triggerAlarm`, `pushMessage`, `chatMessage` und `updateVehicleStatus` und liefert keine
  Alarme an HA.
  - Auth: Header-Token plus HMAC-SHA256; Live-Lizenzen verlangen zusätzlich ein
    Client-Zertifikat.
  - Konfiguration nur durch Admins der Einheit.
- **Instant Commands (2019)** kennen keinen Auslöser „bei Alarm“ und keine HTTP-Aktion.
- **Ausgehende Schnittstelle zu HA: öffentlich nicht dokumentiert.** Es gibt Hinweise auf
  einen Webhook (Homey-App) und einen Reiter „Fireboard-API“ in der Web-UI.
- Vorläufige Empfehlung: Webhook-Empfang in HA mit `iot_class: cloud_push`. Erst nach
  Klärung mit Nutzer und Hersteller festlegen; im Manifest steht weiterhin
  `cloud_polling` als Platzhalter.
- Von HA aus **keine Alarme auslösen**. Echte Alarmierung ist kein Smart-Home-Feature.
