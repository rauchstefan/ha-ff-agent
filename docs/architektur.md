# Architektur

Gesamtbild der Integration. Gepflegt vom `architekt`. Einzelentscheidungen stehen als ADR
in `docs/adr/`.

Stand 2026-10-17. Der Integrationsweg ist in ADR 0002 entschieden und durch ADR 0003
(Alarmquelle Webhook oder ntfy) ergänzt (beide angenommen).
Die Umsetzung folgt `docs/plaene/261017-mvp-alarm-zusage.md`. Der Code im Repo ist noch
das Gerüst; die Struktur unten beschreibt das **Zielbild des MVP**.

## Integrationsweg (ADR 0002)

- **Alarm-Eingang, zwei Quellen (ADR 0003):** Je Eintrag ist genau eine aktiv
  (`data.alarm_source`), beide speisen denselben `AlarmManager`.
  - `webhook`: Ein persönlicher Webhook in FF Agent (Typ „Generischer Webhook“, Methode GET
    oder POST, empfohlen POST) ruft einen HA-Webhook auf, über Home Assistant Cloud
    (Cloudhook) oder eine externe URL. Dabei wird nichts über den Inhalt vorausgesetzt. HA
    antwortet sofort, denn FF Agent bricht nach 5 s ab.
  - `ntfy`: FF Agent ruft `GET https://<server>/<thema>/trigger` auf, die Core-Integration
    ntfy hat das Thema abonniert, und ihre Event-Entität meldet die Nachricht. Die
    Integration hört auf diese Entität (`ntfy_source.py`), ohne eigenen ntfy-Client. HA muss
    dafür nicht von außen erreichbar sein. Im ntfy-Modus ist **kein** HA-Webhook
    registriert und kein Cloudhook vorhanden.
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
  webhook_url.py     Webhook-URL: Cloudhook > extern > intern > Pfad; Erreichbarkeit prüfen
  ntfy_source.py     ntfy-Abo suchen (Subentry/Registry), Listener mit Filterregel
  webhook.py         Handler; erfasst nur die Form des Aufrufs, keine Werte
  alarm.py           AlarmManager: Dedup (30 s), Rücksetz-Timer, Reset von Hand, Dispatcher-Signale
  reply.py           ReplyClient: GET, Timeout 10 s, Lock, Doppelklick-Schutz
  services.py        Actions ff_agent.accept / ff_agent.reject / ff_agent.reset_alarm
  services.yaml      Felder und Selektoren der Actions
  entity.py          Basisentität mit Gerät (DeviceEntryType.SERVICE)
  binary_sensor.py   alarm
  event.py           alarm
  sensor.py          last_alarm, last_reply
  button.py          accept, reject, reset_alarm
  diagnostics.py     redigierte Diagnose
  config_flow.py     user, Menüs je Alarmweg, reconfigure, Options Flow (je Quelle)
  icons.json
  translations/      de.json, en.json, handgeschrieben (kein strings.json bei Custom)
  brand/             icon.png (256 px), icon@2x.png (512 px), ab HA 2026.3
tests/               pytest + pytest-homeassistant-custom-component
hacs.json            HACS-Metadaten
```

Ein `coordinator.py` entfällt, weil es kein Polling gibt.

Zweiter Eingang (ntfy-Modus), statt des Webhooks:

```text
 FF Agent --GET /<thema>/trigger--> ntfy.sh --WebSocket--> Integration ntfy (Core)
                                                              | event.<ntfy-Entität>
                                                              v  state_changed
                                         ntfy_source.py: Filterregel 1-6 (ADR 0003, 3.)
                                                              | async_handle_alarm(ts)
                                                              v
                                                     alarm.py: AlarmManager (wie oben)
```

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
| Binary-Sensor „Alarm aktiv“ | `alarm` | an beim Alarm; aus nach der Rücksetzzeit (Option, Standard 30 min); nach einem Neustart **oder Reload** aus (der AlarmManager startet leer, auch das Dedup-Fenster) | Zustand |
| Event „Alarm“ | `alarm` | Event-Typ `alarm` je neuem Alarm; primärer Trigger | Zeitstempel und `event_type` |
| Sensor „Letzter Alarm“ | `last_alarm` | `TIMESTAMP`, wird nach einem Neustart wiederhergestellt | Zeitstempel |
| Sensor „Letzte Rückmeldung“ | `last_reply` | `ENUM`: `accepted`, `rejected`, `failed` | Zustand |
| Button „Zusagen“ | `accept` | Rückmeldung mit Standard-Verkehrsmittel und optional Standort | Zeitstempel |
| Button „Absagen“ | `reject` | Rückmeldung | Zeitstempel |
| Button „Alarm zurücksetzen“ | `reset_alarm` | schaltet „Alarm aktiv“ sofort aus, stoppt den Timer; `last_alarm` und das Dedup-Fenster bleiben; ohne aktiven Alarm passiert nichts; kein Aufruf an FF Agent | Zeitstempel |

Dazu kommen die Actions `ff_agent.accept` (Felder `config_entry_id`, `transport`,
`latitude`, `longitude`), `ff_agent.reject` und `ff_agent.reset_alarm` (je
`config_entry_id`). Ein eigenes Bus-Event gibt es nicht. Eine Absage setzt „Alarm aktiv“
nicht zurück.

## Config-Eintrag

- **Version 1.2** (`VERSION = 1`, `MINOR_VERSION = 2`). `async_migrate_entry` ergänzt bei
  1.1-Einträgen `alarm_source = "webhook"` und die drei ntfy-Schlüssel mit `None`;
  vorhandene Werte gewinnen. Einträge mit `version > 1` werden abgelehnt.
- **`data`** (alles Geheimnisse außer `reply_host`, `cloudhook`, `alarm_source` und
  `ntfy_server`): `reply_id`, `reply_host`, `alarm_source` (`webhook`/`ntfy`),
  `webhook_id`, `cloudhook`, `cloudhook_url`, `header_token`, `ntfy_entity_uuid`
  (Registry-UUID), `ntfy_topic`, `ntfy_server`. Webhook-ID und Token bleiben im
  ntfy-Modus ruhend erhalten, damit ein Wechsel zurück ohne Sonderfall geht.
- **`options`:** `require_token` (Standard aus), `reset_minutes`, `default_transport`
  (`car`, `feet` oder `bicycle`; an FF Agent gehen `CAR`, `FEET`, `BICYCLE`), `location_entity` (optional, `person` oder `device_tracker`). Beide Werte
  fragt auch der Einrichtungsschritt `reply_settings` ab, sie landen beim Anlegen in `options`.
- **Flows:**
  - `user` mit Name und Rückmelde-URL; ohne Online-Test, weil jeder Test eine echte
    Rückmeldung wäre. Danach der Schritt `reply_settings` (Standard-Verkehrsmittel,
    optional Standort-Entität; ohne Zonen, die Werte hängt `reply.py` bei jeder Zusage
    an, die Rückmelde-URL wird nicht gespeichert) und die Frage „Nutzt du Home Assistant Cloud?“ (Menü
    `alarm_source` bzw. `alarm_source_cloud`) und je Pfad ein Einrichtungsdialog
    (`cloud_setup`/`cloud_setup_retry`/`cloud_not_connected` bzw. `ntfy`, `ntfy_select`).
    Plan: `docs/plaene/261017-alarmquelle-ntfy.md`.
  - `reconfigure`: Rückmelde-URL ändern, Alarmweg wechseln, neue geheime Adresse
    (Webhook-ID und Token bzw. ntfy-Thema) erzeugen
  - Options Flow mit Anzeige der Webhook-URL, des Token-Headers und des Tokens; im
    ntfy-Modus Schritt `ntfy` mit Entität und FF-Agent-Adresse, ohne Token-Schalter
  - Repair-Issue `ntfy_entity_missing`, wenn die ntfy-Entität fehlt, fremd oder
    deaktiviert ist; das Setup schlägt dann nicht fehl. Selbstheilung: Ein neues Abo
    desselben Themas erzeugt eine neue Subentry und Entität. Beim Setup und bei jedem
    Registry-Ereignis `create`, solange die Entität fehlt, sucht die Integration über das
    gespeicherte Thema, übernimmt die neue Registry-UUID und lädt neu (nicht, wenn ein
    anderer Eintrag die Entität nutzt)
  - Reconfigure im ntfy-Modus ohne „Neue geheime Adresse“ und mit gültiger Entität
    speichert nur die Rückmelde-URL, ohne ntfy-Dialog. Ein unlesbares Thema ergibt keine
    URL im Abschluss (`ntfy_topic_unknown`); eine unerreichbare Webhook-Adresse im
    Reconfigure den Abschluss `reconfigure_successful_local`
  - Abschlussdialog, Options-Text und README nennen die empfohlenen Feldwerte für FF Agent
    (ADR 0002, Abschnitt 5a)
  - Reauth erst nach Klärung von Annahme A7

## Datenschutz

- **Geheimnisse:** Rückmelde-UUID, Webhook-ID bzw. Cloudhook-URL, das Header-Token, das
  ntfy-Thema (samt der daraus gebildeten URL), die Registry-UUID und die `entity_id` der
  ntfy-Entität. Die `entity_id` enthält das Thema, wenn das Abo keinen Anzeigenamen hat.
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

- **Automationen auf die Event-Entität brauchen Filter.** Bei Reload oder Neustart wechselt
  die Event-Entität zu `unavailable` und stellt danach den alten Zeitstempel wieder her.
  Ein `state`-Trigger ohne Filter löst dann aus, als gäbe es einen Alarm. Er braucht
  deshalb immer `not_from: [unavailable, unknown]` und `not_to: [unavailable, unknown]`.
  Zwei Tests in `tests/test_entities.py` belegen das (mit Filter löst er nicht aus, ohne
  Filter schon). README und Beispiel-Automation (PR 6) müssen das zeigen.
- **Geräteseite sortiert nach Anzeigename.** Die Entitäten eines Geräts erscheinen
  alphabetisch nach `entry.name ?? original_name` (Systemsprache, `Intl.Collator`). Die
  Reihenfolge im Code, die Registrierung und die Entity-ID wirken nicht; ohne Umbenennung
  gibt es keine Stellschraube.
- **`configuration_url` muss explizit `None` sein, um einen gespeicherten Link zu löschen.**
  Lässt man das Feld in `DeviceInfo` weg, behält `async_get_or_create` den Wert bestehender
  Geräte (`UNDEFINED` wird nicht übernommen); ein ausdrückliches `None` löscht ihn.
- **Reload löscht den laufenden Alarm.** Der `AlarmManager` startet bei jedem Setup leer.
  Jede Options-Änderung und jedes Reconfigure mit Änderung lädt den Eintrag neu (`OptionsFlowWithReload`), damit
  springt „Alarm aktiv“ auf aus und das Dedup-Fenster ist offen. Das ist bewusst so
  (flüchtiger Zustand) und gehört in die Nutzerdoku.
- **Fremde Event-Entität als Alarmquelle (ntfy, ADR 0003, 3.).** Die ntfy-Entität springt
  bei Neustart, Reload und jedem Verbindungsabbruch auf `unavailable` und stellt dann den
  alten Zeitstempel wieder her. `not_from: [unavailable, unknown]` reicht nicht: Er
  verliert den ersten Alarm nach dem Anlegen des Abos (`unknown` -> Zeitstempel) und
  Alarme in den bis zu 10 s nach einem Neuaufbau (die Entität geht dann direkt von
  `unavailable` auf den **neuen** Wert). Die Regel in `ntfy_source.py`: ignorieren, wenn
  kein Zeitstempel; `old_state` fehlt oder hat `restored: true` -> nur merken; gleich dem
  zuletzt gesehenen -> ignorieren; älter als 60 s -> merken, ignorieren; sonst Alarm.
- **Platzhalter-State `restored: true`:** Für Entitäten, die noch nicht geladen sind (beim
  Start) und beim Entladen einer Integration schreibt HA einen State `unavailable` mit
  Attribut `restored: true` (`RegistryEntry.write_unavailable_state`). Der Wert danach ist
  der Restore, kein Alarm.
- **Registry-Ereignisse der ntfy-Entität:** `update` liefert in `changes` die alten Werte,
  bei Umbenennung zusätzlich `old_entity_id`. Die ntfy-Entität ändert ihre `capabilities`
  (`event_types`) mit jeder Meldung; nur `entity_id` und `disabled_by` lösen einen Reload
  aus.
- **hassfest verbietet URLs in Übersetzungen**, auch bei Custom-Integrationen. Links
  (My-Home-Assistant) kommen deshalb als `description_placeholders`.
- **`async_show_menu` hat keine Vorauswahl.** Die Reihenfolge der Optionen ist die
  Anzeigereihenfolge; die Empfehlung steht im Optionstext („Ja (empfohlen)“). Menüoptionen
  sind Step-IDs; eine Step-ID kann mehrere Varianten haben (`alarm_source` und
  `alarm_source_cloud`), ohne eigene Handler.
- **HA 2026.10 lehnt selbst** Einträge mit höherer Hauptversion ab, bevor
  `async_migrate_entry` aufgerufen wird; eine höhere Minor-Version wird geladen.
- **Dedup und Uhrzeit:** Eine negative Zeitdifferenz (Uhr springt zurück, z. B. durch
  NTP) gilt als neuer Alarm. Der Rücksetz-Timer läuft über die monotone Loop-Uhr.

- **Validierung: voluptuous und probatio.** Seit HA 2026.9 ist `probatio` die Validierungsbibliothek, `voluptuous` wird nicht mehr installiert. `homeassistant/__init__.py` setzt beim Start per `probatio.compat.install_as_voluptuous()` einen Alias in `sys.modules`. Deshalb funktioniert `import voluptuous as vol` für Custom-Integrationen weiter, offiziell unterstützt und ohne Abkündigung (contributors.home-assistant.io/blog/2026/09/30/probatio-validation-engine/). Vor 2026.9 ist es das echte voluptuous. Wir nutzen einheitlich `import voluptuous as vol`. Optionsschlüssel von Selektoren (Übersetzung) müssen `[a-z0-9-_]` sein, deshalb heißen die Verkehrsmittel intern `car`, `feet` und `bicycle`.
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
  und `.../reject`. Die UUID wirkt als Geheimnis. `transport` ist optional: `CAR`
  (Standard), `FEET` oder `BICYCLE`. Die URLs gelten je Person für den jeweils aktiven
  Einsatz, und nur, wenn die Person dafür alarmiert wurde. Fundort in der Web-UI:
  *Personen → eigener Name → Bereich „Übung/Einsatz“ → „Weblinks für Einsatzmeldung“*
  (nicht unter „Automatisierung“).
- **Einsatzdetails:** Es gibt keine dokumentierte Nutzer-API. Der persönliche iCal-Feed
  (Stand 2019) enthält nur Einsätze, an denen die Person teilgenommen hat.
- **Offene Annahmen:** A2 bis A13 in ADR 0002, außer A8 und A9 (zusammen mit A1 geklärt). Die Ergebnisse des
  ersten echten Tests werden hier nachgetragen.
