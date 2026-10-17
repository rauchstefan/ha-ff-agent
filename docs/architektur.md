# Architektur

Gesamtbild der Integration. Gepflegt vom `architekt`. Einzelentscheidungen stehen als ADR
in `docs/adr/`.

Stand 2026-10-17. Der Integrationsweg ist in ADR 0002 entschieden (Status: angenommen).
Die Umsetzung folgt `docs/plaene/261017-mvp-alarm-zusage.md`. Der Code im Repo ist noch
das Gerüst; die Struktur unten beschreibt das **Zielbild des MVP**.

## Integrationsweg (ADR 0002)

- **Alarm-Eingang:** Ein persönlicher Webhook in FF Agent (Typ „Generischer Webhook“,
  Methode GET oder POST, empfohlen POST) ruft einen HA-Webhook auf. Dabei wird nichts über
  den Inhalt vorausgesetzt. HA antwortet sofort, denn FF Agent bricht nach 5 s ab.
- **Zusatz-Token (optional, Standard aus):** Header `X-FF-Agent-Token`, Prüfung mit
  `hmac.compare_digest`. Bei Fehlschlag gibt es 401 und ein Repair-Issue. Es ist keine
  Pflicht, solange nicht belegt ist, dass Nabu Casa den Header durchreicht (A12).
- **Zusage und Absage:** HA ruft die persönliche Rückmelde-URL auf
  (`https://<host>/app2/missionreplies/<REPLY_ID>/<accept|reject>`).
- **Einsatzdetails:** Im MVP gibt es keine Quelle; der Erweiterungspunkt ist vorgesehen.
- `iot_class: cloud_push` und `integration_type: service`.
- `dependencies: ["webhook"]`, `after_dependencies: ["cloud"]`.
- **Ein Config-Eintrag entspricht einer Person.** Mehrere Einträge sind erlaubt. Die
  `unique_id` ist ein SHA-256-Hash der UUID, gekürzt auf 16 Zeichen.
- **Von HA aus werden niemals Alarme ausgelöst.** Die WebAPI wird nicht genutzt.

## Struktur (Zielbild MVP)

```text
custom_components/ff_agent/
  __init__.py        Setup/Unload/Remove, Webhook-Registrierung, Actions (async_setup)
  manifest.json      cloud_push, service, webhook/cloud
  const.py           Konstanten, Optionen, Grenzwerte
  models.py          WebhookCall, AlarmEvent, ReplyResult, FFAgentData (runtime_data)
  reply_url.py       Rückmelde-URL prüfen, UUID und Host extrahieren
  webhook_url.py     Webhook-URL: Cloudhook > extern > intern > Pfad
  webhook.py         Handler; erfasst nur die Form des Aufrufs, keine Werte
  alarm.py           AlarmManager: Dedup (30 s), Rücksetz-Timer, Dispatcher-Signale
  reply.py           ReplyClient: GET, Timeout 10 s, Lock, Doppelklick-Schutz
  services.py        Actions ff_agent.accept / ff_agent.reject
  services.yaml      Felder und Selektoren der Actions
  entity.py          Basisentität mit Gerät (DeviceEntryType.SERVICE)
  binary_sensor.py   alarm
  event.py           alarm
  sensor.py          last_alarm, last_reply
  button.py          accept, reject
  diagnostics.py     redigierte Diagnose
  config_flow.py     user, reconfigure, Options Flow
  icons.json
  translations/      de.json, en.json, handgeschrieben (kein strings.json bei Custom)
  brand/             icon.png (256 px), icon@2x.png (512 px), ab HA 2026.3
tests/               pytest + pytest-homeassistant-custom-component
hacs.json            HACS-Metadaten
```

Ein `coordinator.py` entfällt, weil es kein Polling gibt.

## Datenfluss

```text
        FF Agent (Cloud)                               Home Assistant
 +------------------------------+        +-------------------------------------------+
 | Persönlicher Webhook (<=3)   |  HTTPS | Nabu-Casa-Cloudhook / externe URL         |
 | Generisch, POST, bei Alarm   |------->|   /api/webhook/<webhook_id>               |
 | (+ Test-/stille Alarme opt.) |  5 s   |        |                                  |
 | opt. Header X-FF-Agent-Token |        |        v                                  |
 +------------------------------+        | webhook.py: [Token prüfen -> 401+Repair]  |
                                         |   Form erfassen, 200 antworten            |
                                         |        |  WebhookCall (ohne Werte)        |
                                         |        v                                  |
                                         | alarm.py: AlarmManager                    |
                                         |   Dedup 30 s, Rücksetz-Timer              |
                                         |        |  Dispatcher-Signale              |
                                         |        v                                  |
                                         | event.alarm  binary_sensor.alarm          |
                                         | sensor.last_alarm      --> Automationen   |
                                         |                                           |
 +------------------------------+  HTTPS | button.accept/reject, ff_agent.accept/... |
 | /app2/missionreplies/<id>/   |<-------|   reply.py: GET, Lock, Timeout            |
 |   accept?transport=..&lat..  |        |        |  ReplyResult                     |
 |   reject                     |        |        v                                  |
 +------------------------------+        | sensor.last_reply, Fehler als Exception   |
                                         +-------------------------------------------+
```

## Entitäten (je Eintrag bzw. Person, ein Gerät)

| Entität | Key | Verhalten | Recorder |
|---|---|---|---|
| Binary-Sensor „Alarm aktiv“ | `alarm` | an beim Alarm; aus nach der Rücksetzzeit (Option, Standard 30 min); nach einem Neustart aus | Zustand |
| Event „Alarm“ | `alarm` | Event-Typ `alarm` je neuem Alarm; primärer Trigger | Zeitstempel und `event_type` |
| Sensor „Letzter Alarm“ | `last_alarm` | `TIMESTAMP`, wird nach einem Neustart wiederhergestellt | Zeitstempel |
| Sensor „Letzte Rückmeldung“ | `last_reply` | `ENUM`: `accepted`, `rejected`, `failed` | Zustand |
| Button „Zusagen“ | `accept` | Rückmeldung mit Standard-Verkehrsmittel und optional Standort | Zeitstempel |
| Button „Absagen“ | `reject` | Rückmeldung | Zeitstempel |

Dazu kommen die Actions `ff_agent.accept` (Felder `config_entry_id`, `transport`,
`latitude`, `longitude`) und `ff_agent.reject` (`config_entry_id`). Ein eigenes Bus-Event
gibt es nicht.

## Config-Eintrag

- **`data`** (alles Geheimnisse außer `reply_host` und `cloudhook`): `reply_id`,
  `reply_host`, `webhook_id`, `cloudhook`, `cloudhook_url`, `header_token`
- **`options`:** `require_token` (Standard aus), `reset_minutes`, `default_transport`
  (belegt ist nur `CAR`), `location_entity` (optional, `person` oder `device_tracker`)
- **Flows:**
  - `user` mit Name und Rückmelde-URL; ohne Online-Test, weil jeder Test eine echte
    Rückmeldung wäre
  - `reconfigure`: Rückmelde-URL ändern, Webhook-Zugang (ID und Token) neu erzeugen
  - Options Flow mit Anzeige der Webhook-URL, des Token-Headers und des Tokens
  - Abschlussdialog, Options-Text und README nennen die empfohlenen Feldwerte für FF Agent
    (ADR 0002, Abschnitt 5a)
  - Reauth erst nach Klärung von Annahme A7

## Datenschutz

- **Geheimnisse:** Rückmelde-UUID, Webhook-ID bzw. Cloudhook-URL und das Header-Token.
  Von eingehenden Headern wird nur der Name erfasst, nie der Wert. Die Geheimnisse stehen nie in
  Logs, Entitätsattributen oder `unique_id`s. In Diagnostics werden sie redigiert, ebenso
  Titel und `location_entity`.
- **Webhook-Inhalt:** Gespeichert wird nur seine Form (Schlüssel, Typen, Längen), keine
  Werte.
- **Recorder:** Er speichert nur Zeitpunkte und Zustände. Spätere Detail-Entitäten nutzen
  `_unrecorded_attributes`. Einsatzinhalte gehören nicht in Event-Attribute, weil
  `RestoreEntity` sie in `core.restore_state` ablegt.
- **Exceptions von aiohttp** enthalten die URL. Deshalb werden nur Typname und Statuscode
  geloggt, und es gilt `raise ... from None`.

## Erweiterungspunkt Einsatzdetails

- **Payload:** Falls der Webhook Inhalte liefert (Annahme A2), bekommt der `AlarmManager`
  einen Parser. `AlarmEvent` erhält dann das Feld `details`. Aussichtsreichster Weg:
  Platzhalter in den frei definierbaren Query-Parametern oder Headern des Generischen
  Webhooks (A13). Damit ließen sich auch Testalarme unterscheiden.
- **Abrufquelle:** Eine Hersteller-API oder Ähnliches wird als `DetailsSource`
  angeschlossen. Sie wird durch den Alarm angestoßen; `iot_class` bleibt `cloud_push`.
- **iCal-Feed:** Er wird nicht selbst gebaut. Für den Verlauf empfiehlt die Doku die
  Core-Integration „Remote Calendar“.

## HA-Fallstricke (geprüft 2026-10-17, HA 2026.3.0 und dev)

- **Python-Version:** Laut `requires_python` auf PyPI verlangt HA 2026.1/2026.2
  Python ≥ 3.13.2 und HA ab 2026.3.0 Python ≥ 3.14.2. Unsere Mindestversion
  (`hacs.json`: 2026.3.0) passt deshalb zu ruff `target-version = "py314"`. Syntax ab
  3.14, etwa `except A, B:` ohne Klammern, ist erlaubt. Wird die HA-Mindestversion je
  unter 2026.3 gesenkt, muss das ruff-Ziel mit.

- Cloudhook-Aufrufe kommen als `MockRequest`. Es gibt **kein `request.read()`**; stattdessen
  `request.text()` verwenden.
- `webhook.async_register`:
  - Standardmethoden sind nur POST und PUT; GET muss ausdrücklich erlaubt werden.
  - Ist HEAD nicht freigegeben, antwortet HA trotzdem mit 200.
  - Eine nicht erlaubte Methode protokolliert HA als WARNING, und zwar mit der Webhook-ID.
- Cloudhook: `cloud/client.py` (`async_webhook_message`) reicht Header, Methode, Query und
  Body der Cloud-Nachricht ungefiltert in den `MockRequest` (`remote=None`). Ob der
  Nabu-Casa-Server eigene Header vorher durchlässt, ist nicht einsehbar (A12).
- `webhook.async_generate_url` ignoriert die Cloud (`allow_cloud=False`). Den Cloudhook
  erzeugt `cloud.async_get_or_create_cloudhook`. `get_url` wirft `NoURLAvailableError`.
- `cloud` nur lazy importieren und vorher `"cloud" in hass.config.components` prüfen.
- `service.async_get_config_entry` verlangt in 2026.3 eine `entry_id`; einen Fallback auf
  einen einzelnen Eintrag gibt es dort noch nicht.
- `EventEntity._trigger_event` schreibt den State nicht selbst. Danach muss
  `async_write_ha_state()` folgen.

## HACS-Rahmen (Stand 2026-10-16)

Details: `docs/recherche/261016-hacs-anforderungen.md`.

- HACS funktioniert nur mit **öffentlichen** Repos.
- HACS ermittelt die Version aus dem Tag des neuesten **GitHub-Releases**. Der Tag muss zu
  `manifest.version` passen.
- Die CI prüft mit `validate.yml` (hassfest, HACS-Action ohne `ignore`) und `tests.yml`
  (ruff, pytest).

## FF-Agent-Schnittstellen (Kenntnisstand 2026-10-17)

Details und Quellen: `docs/recherche/261016-ffagent-schnittstellen.md` und
`docs/recherche/261016-ffagent-webhook-zusage.md`.

- **WebAPI v1.6 (2019) ist nur eingehend** (extern → FF Agent) und braucht Admin-Rechte,
  HMAC und ein Client-Zertifikat. Für diese Integration ist sie tabu.
- **Persönliche Webhooks** (Dialog „Webhook hinzufügen“, Screenshots 2026-10-17, gesichert):
  - In der Web-UI unter „Automatisierung“ kann jede Person bis zu 3 davon anlegen.
  - Type „Alarm“ (einzige Auswahl). Die Checkboxen „auch für Testalarme“, „auch für
    Infoalarme“ und „auch für stille Einsätze“ sind einzeln wählbar. Ein Zeitplan ist
    optional.
  - Webhooktypen: Generischer Webhook, IFTTT Maker, Homee, Shelly. Für HA zählt
    „Generischer Webhook“.
  - Generischer Webhook: Methode GET oder POST, URL mit `https://`, Query-Parameter frei,
    optionale Basis-Authentifizierung, freie Header. Timeout je 5 s für Verbindung und
    Verarbeitung.
  - Offen: Body bei POST, Platzhalter mit Einsatzdaten, Retry. Ohne eigene Einträge
    spricht alles (auch die Homey-App) für einen Aufruf ohne Nutzdaten.
- **Persönliche Rückmelde-URLs:** `.../app2/missionreplies/<UUID>/accept?transport=CAR&lat=&lng=`
  und `.../reject`. Die UUID wirkt als Geheimnis; belegt ist nur `CAR`.
- **Einsatzdetails:** Es gibt keine dokumentierte Nutzer-API. Der persönliche iCal-Feed
  (Stand 2019) enthält nur Einsätze, an denen die Person teilgenommen hat.
- **Offene Annahmen:** A2 bis A13 in ADR 0002 (A1 ist erledigt). Die Ergebnisse des ersten echten Tests
  werden hier nachgetragen.
