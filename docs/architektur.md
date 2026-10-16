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
  strings.json       Texte, plus translations/de.json, en.json
  diagnostics.py     Diagnosedaten mit Redaction
tests/               pytest + pytest-homeassistant-custom-component
hacs.json            HACS-Metadaten
```
