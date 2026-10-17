# ADR 0003: Alarmquelle wählbar – Webhook (Home Assistant Cloud / eigene Adresse) oder ntfy

- **Status:** angenommen (Nutzer, 2026-10-17; vorgeschlagen vom Architekten am selben Tag,
  Einstieg in den Flow nach Entscheidung des Nutzers überarbeitet). Ergänzt ADR 0002,
  Abschnitte 1, 3, 5 und 8.
- **Datum:** 2026-10-17
- **TODO:** `261017-ux-erreichbarkeit`
- **Umsetzungsplan:** `docs/plaene/261017-alarmquelle-ntfy.md`
- **Grundlage:** `docs/recherche/261017-erreichbarkeit.md` (Abschnitte 3.1, 3.3, 5.1 bis 5.3)

Kennzeichnung wie in den Recherchen: gesichert [G], abgeleitet [A], unbekannt [U].

## Kontext

ADR 0002 kennt genau einen Alarmeingang: FF Agent ruft einen HA-Webhook auf. Das setzt
voraus, dass Home Assistant aus dem Internet erreichbar ist (Home Assistant Cloud oder eine
eigene HTTPS-Adresse). Viele Einsatzkräfte haben beides nicht. Heute endet die Einrichtung
dann bei `internal`/`path_only` mit einem technischen Text. Der Nutzer hat am 2026-10-17
entschieden:

- **Beide Wege anbieten, der Nutzer wählt:**
  1. Webhook über Home Assistant Cloud (Nabu Casa) oder eine externe URL, wie bisher.
     Fehlt die Erreichbarkeit, erscheint ein verständlicher Text mit dem My-Link
     `https://my.home-assistant.io/redirect/cloud/`. Der Text nennt „Home Assistant Cloud“
     und „Home Assistant Link“ (Umbenennung ab 2. Dezember 2026), aber keinen Preis.
  2. ntfy.sh als kostenlose Alternative, ohne dass HA von außen erreichbar sein muss.
- Der Alarmeingang ist **nicht schutzbedürftig**: Übertragen wird nur, **dass** ein Alarm
  vorliegt. Ein sachlicher Datenschutzhinweis genügt (der Dienst sieht Alarmzeitpunkte, das
  Thema ist geheim zu halten).
- Mindestversion bleibt HA 2026.3.0. FF Agent ruft eine beliebige URL per GET oder POST auf,
  Timeout 5 s, eigene Header und Query-Parameter sind möglich [G, ADR 0002].

**Entscheidungen des Nutzers zum Vorschlag (2026-10-17):**

1. **Einstieg:** „Ich würde es dem Nutzer als empfohlen darstellen, Nabu Casa zu verwenden,
   falls er es bereits hat. Nicht aber erzwingen. Der Nutzer kann sagen, dass er es nicht
   hat, und dann auf ntfy im nächsten Dialog verwiesen werden. Zeig ihm dann bitte jeweils
   für Nabu Casa und für ntfy je nach Selektion einen Einrichtungsdialog mit
   Schritt-für-Schritt-Anweisung.“
   - Die erste Frage lautet „Nutzt du Home Assistant Cloud (Nabu Casa)?“ mit „Ja
     (empfohlen)“ und „Nein“. „Nein“ führt über einen kurzen Hinweis auf die kostenlose
     Alternative ntfy in den ntfy-Pfad.
   - Ein erkanntes Cloud-Abo darf den Text anpassen, erzwingt aber nichts.
   - Der Wechsel zur jeweils anderen Option bleibt möglich.
   - Eine vorhandene externe URL wird im Cloud- bzw. Webhook-Pfad wie bisher erkannt und
     genutzt.
2. **Schritt-für-Schritt-Dialoge je Pfad** mit nummerierten Schritten für Laien. Alle
   Links kommen als `description_placeholders`.
3. **„Trotzdem fortfahren“ bleibt:** nur Zu- und Absage, kein Alarmeingang, später über
   Reconfigure nachrüstbar.
4. **ntfy-Aufruf:** GET auf `/<thema>/trigger`, bestätigt.
5. Vom Projektleiter vorläufig entschieden:
   - Wortlaut „kostenpflichtiges Abo, zunächst kostenlos testbar“, ohne Preis und Dauer
   - kein automatisches Anlegen des ntfy-Abos, höchstens als späteres TODO

### Geprüfter Stand von HA Core (2026-10-17, Tag `2026.3.0` und Branch `dev`)

Quelle jeweils `github.com/home-assistant/core`, Pfad `homeassistant/...`.

| Gegenstand | Befund | Quelle |
|---|---|---|
| ntfy-Integration, Thema | Je abonniertem Thema eine **Config-Subentry** vom Typ `topic` (`SUBENTRY_TYPE_TOPIC = "topic"`) am ntfy-Eintrag. `subentry.data["topic"]` ist das Thema, `unique_id` der Subentry ist das Thema, Titel ist der Anzeigename oder sonst das Thema. Server-Adresse in `entry.data["url"]`, Standard `https://ntfy.sh/`. Anonymer Zugang ist erlaubt. [G] | `components/ntfy/const.py`, `config_flow.py` |
| ntfy, Thema anlegen | Nur über den Subentry-Flow (`TopicSubentryFlowHandler`): Menü „Enter topic“ / „Generate topic name“ (16 Zeichen), dann Formular mit `topic`, `name` und optionalen Filtern. Nach dem Anlegen des ntfy-Eintrags startet der Flow direkt die erste Subentry (`next_flow`). Topic-Regel `^[-_a-zA-Z0-9]{1,64}$`. [G] | `components/ntfy/config_flow.py` |
| ntfy, Event-Entität | `NtfyEventEntity` je Subentry (`config_subentry_id`), `has_entity_name`, `name=None`: Der Entitätsname ist der Gerätename = Subentry-Titel. **Ohne Anzeigenamen steht das Thema im Gerätenamen und in der `entity_id`.** [G] | `components/ntfy/event.py`, `entity.py` |
| ntfy, Event-Typ und Attribute | Nur Meldungen mit passendem Thema und `event == message`. Der Event-Typ wird **dynamisch** auf „Titel: Nachricht“ bzw. die Nachricht gesetzt (bei GET ohne Text: `triggered`). Attribute = `Notification.to_dict()` (u. a. `id`, `time`, `topic`, `message`, `title`, `tags`, `priority`). [G] | `components/ntfy/event.py`, Bibliothek `aiontfy` (`types.py`) |
| ntfy, Verbindung | Watchdog-Schleife: prüft den WebSocket-Task, setzt `_attr_available`, schreibt den State, startet bei Bedarf neu, **schläft dann 10 s** (`RECONNECT_INTERVAL`). `available = True` wird **erst im nächsten Schleifendurchlauf** gesetzt, also bis zu 10 s nach dem Neuaufbau. Kein `since` beim Abo: verpasste Meldungen werden nicht nachgeholt. Geschütztes Thema: Repair-Issue der ntfy-Integration, keine Wiederverbindung. Identisch in 2026.3.0 und `dev`. [G] | `components/ntfy/event.py` |
| `EventEntity` | State = Zeitstempel der HA-Uhr beim `_trigger_event` (`isoformat(timespec="milliseconds")`). Attribute = `event_type` plus Event-Attribute. Restore über `RestoreEntity`: alter Zeitstempel, Typ und Attribute kommen nach Neustart/Reload zurück. [G] | `components/event/__init__.py` (2026.3.0) |
| Tracking | `async_track_state_change_event(hass, entity_ids, action)` und `async_track_entity_registry_updated_event(hass, entity_ids, action)` gibt es in 2026.3.0. Registry-Event `update` liefert `changes` mit den **alten** Werten und bei Umbenennung `old_entity_id`; `remove` liefert nur `entity_id`. [G] | `helpers/event.py`, `helpers/entity_registry.py` |
| Entity-Registry | `RegistryEntry.config_subentry_id` existiert. `async_resolve_entity_id(registry, entity_id_or_uuid) -> str | None` löst eine Registry-UUID in die aktuelle `entity_id` auf. [G] | `helpers/entity_registry.py` |
| Flows | `async_show_menu(step_id, menu_options, sort=False, description_placeholders)`: **keine Vorauswahl**, Reihenfolge = Listenreihenfolge. `async_abort` nimmt `description_placeholders`. [G] | `data_entry_flow.py` (2026.3.0) |
| Selektor | `EntitySelectorConfig(integration=..., domain=...)` filtert in der UI. Die Validierung prüft nur das Format, nicht die Existenz. [G] | `helpers/selector.py` (2026.3.0) |
| hassfest | Übersetzungstexte dürfen **keine URLs** enthalten („use description placeholders instead“), auch bei Custom-Integrationen (`translations/en.json`). Links müssen deshalb als Platzhalter kommen. [G] | `script/hassfest/translations.py` |
| My-Links | `redirect/cloud/` („Home Assistant Cloud“), `redirect/network/`, `redirect/config_flow_start/` („add integration“) und `redirect/integration/` („Show an integration“) existieren [G]. Dass die beiden letzten `?domain=ntfy` auswerten, ist [A] (übliche Nutzung, im Test prüfen). | `my.home-assistant.io` |
| ntfy-Veröffentlichung | `GET /<thema>/trigger` (Alias von `/publish`) ohne Parameter sendet die Nachricht `triggered` [G]. | `docs.ntfy.sh/publish/` |

## Entscheidung

### 1. Zwei Alarmquellen, genau eine aktiv

- Neues Datenfeld `alarm_source` mit den Werten `webhook` und `ntfy`. Je Eintrag ist genau
  eine Quelle aktiv. Beide speisen denselben `AlarmManager`; Entitäten, Dedup (30 s),
  Rücksetzzeit, Event-Entität und Rückmeldung bleiben unverändert.
- **Webhook-Modus:** wie ADR 0002.
- **ntfy-Modus:** Die Integration hört auf die **Event-Entität der Core-Integration `ntfy`**
  (`async_track_state_change_event`) und meldet jeden neuen, frischen Zeitstempel als
  Alarm an den `AlarmManager`. Es gibt **keinen eigenen ntfy-Client** und keine eigene
  Netzwerkverbindung.
- **Im ntfy-Modus wird kein HA-Webhook registriert und kein Cloudhook gehalten.** Ein
  Eintrag hat genau einen offenen Eingang. `webhook_id` und `header_token` bleiben ruhend
  in `entry.data`, damit ein späterer Wechsel zurück ohne Sonderfälle funktioniert. Ein
  vorhandener Cloudhook wird beim Wechsel zu ntfy gelöscht.
- `iot_class` bleibt `cloud_push`, `dependencies`/`after_dependencies` bleiben unverändert.
  `ntfy` kommt **nicht** in `after_dependencies`: Der Filter (3.) braucht keine
  Ladereihenfolge, und Webhook-Nutzer sollen keine Abhängigkeit der ntfy-Integration
  geladen bekommen [A]. Die Integration importiert nichts aus `homeassistant.components.ntfy`
  (dort wird `aiontfy` importiert); die drei nötigen Schlüssel (`ntfy`, `topic`, `url`)
  stehen als eigene Konstanten in `const.py` und sind durch einen Vertragstest abgesichert.

### 2. Thema: von uns erzeugt, vom Nutzer abonniert

- Der Flow erzeugt ein zufälliges Thema mit `secrets.token_hex(16)` (32 Kleinbuchstaben und
  Ziffern, 128 Bit). Kein erkennbares Präfix wie „ff-agent“, denn auch der Zweck soll
  geheim bleiben. Das Format erfüllt die ntfy-Regel.
- **Die Integration legt das Abo nicht selbst an.** Der Nutzer abonniert das Thema in der
  ntfy-Integration („Thema eingeben“, Anzeigename z. B. „FF Agent Alarm“). Der Dialog führt
  ihn mit My-Links und den exakten Werten dahin.
- Danach findet die Integration die Event-Entität über das Thema selbst (ntfy-Einträge →
  Subentry mit `data["topic"]` → Registry-Eintrag mit passender `config_subentry_id`,
  Domain `event`, Plattform `ntfy`). Alternativ wählt der Nutzer die Entität aus
  (`EntitySelector`, `integration="ntfy"`, `domain="event"`). Damit lässt sich auch ein
  schon vorhandenes Abo oder ein eigener ntfy-Server nutzen.
- **Quelle der Wahrheit ist die gewählte Entität.** Das Thema und die Server-Adresse für den
  Abschlussdialog werden aus deren Subentry bzw. ntfy-Eintrag gelesen, sonst gilt das
  erzeugte Thema mit `https://ntfy.sh/`.
- Eine ntfy-Entität darf nur an **einem** FF-Agent-Eintrag hängen. Sonst bekäme eine zweite
  Person dieselben Alarme.

### 3. Laufzeit: Filter für die fremde Event-Entität

Die bekannte Falle aus `docs/architektur.md` gilt hier verschärft: Die ntfy-Entität springt
bei Neustart, Reload und jedem Verbindungsabbruch auf `unavailable` und stellt danach den
alten Zeitstempel wieder her. Ein einfacher Filter `not_from: [unavailable, unknown]`
reicht hier **nicht**, denn er verliert zwei echte Alarme:

- den ersten Alarm nach dem Anlegen des Abos (`unknown` → Zeitstempel),
- einen Alarm, der in den bis zu 10 s nach einem Neuaufbau eintrifft. Die Entität ist
  dann noch `unavailable` und wechselt erst beim nächsten Schleifendurchlauf direkt auf
  den **neuen** Zeitstempel.

Regel je `state_changed`-Ereignis der ntfy-Entität:

1. `new_state` fehlt oder ist `unavailable`/`unknown`: ignorieren.
2. `new_state.state` lässt sich nicht als Zeitstempel lesen: ignorieren.
3. `old_state` fehlt oder ist ein Platzhalter der Registry (Attribut `restored: true`): Die
   Entität wurde gerade (wieder) hinzugefügt, der neue Wert ist also der Restore.
   Zeitstempel als „gesehen“ merken, ignorieren. Den Platzhalter schreibt HA beim Start für
   noch nicht geladene Entitäten und beim Entladen einer Integration
   (`RegistryEntry.write_unavailable_state`, `{restored: true}`, State `unavailable`)
   [G für die Registry; A, dass `Entity.async_remove` ihn beim Entladen schreibt].
4. Zeitstempel gleich dem zuletzt gesehenen: ignorieren (Rückkehr aus `unavailable` mit
   altem Wert, reine Attributänderung).
5. Zeitstempel älter als `NTFY_MAX_EVENT_AGE` (60 s) gegenüber `utcnow()`: merken,
   ignorieren (wiederhergestellter alter Wert, den die Integration vorher nicht gesehen
   hat). Ein Zeitstempel in der Zukunft gilt als frisch, wie im `AlarmManager`.
6. Sonst: merken und `AlarmManager.async_handle_alarm(timestamp)`. Die Deduplizierung
   (30 s) übernimmt der Manager, z. B. bei mehreren FF-Agent-Webhooks auf dasselbe Thema.

Beim Start des Listeners wird der aktuelle State der Entität als „gesehen“ übernommen. Der
Zeitstempel ist die HA-Uhr der ntfy-Entität, daher gibt es keine Uhrabweichung zum Server.
Die Regel hängt nicht an ntfy-Attributen (`id`, `time`), nur an der Semantik von
`EventEntity`.

Weitere Laufzeitregeln:

- Gespeichert wird die **Registry-UUID** der Entität (`ntfy_entity_uuid`), aufgelöst beim
  Setup mit `er.async_resolve_entity_id`. Eine Umbenennung bricht so nichts.
- `async_track_entity_registry_updated_event` auf die Entität: Bei `remove` entsteht das
  Repair-Issue (4.). Bei `update` (Umbenennung, Deaktivierung) wird der Eintrag neu geladen.
- Logs nennen nie Thema, `entity_id` oder Attributwerte, nur den Grund („accepted“,
  „ignored: restored“ usw.). Die `entity_id` kann das Thema enthalten (siehe Befund).

### 4. Repair-Issue `ntfy_entity_missing`

- Entsteht beim Setup oder zur Laufzeit, wenn die gespeicherte Entität nicht auflösbar, nicht
  von der Plattform `ntfy` oder deaktiviert ist. `is_fixable=False`, `severity=error`,
  Platzhalter `title`. Der Text verweist auf „Neu konfigurieren“.
- Das Setup schlägt **nicht** fehl: Rückmeldungen funktionieren weiter.
- Es wird gelöscht bei erfolgreichem Setup mit gültiger Entität, beim Wechsel auf
  `webhook` und in `async_remove_entry`.
- Eine länger `unavailable` stehende ntfy-Entität meldet die Integration nicht selbst; das
  zeigt die ntfy-Integration. Als Folge-Idee steht ein Diagnose-Binärsensor
  „Alarmweg verbunden“ im Plan, nicht in diesem PR.

### 5. Config Flow

- **`user`:** Name und Rückmelde-URL wie bisher. Die Duplikatprüfung (`unique_id`) kommt so
  vor jeder Einrichtung des Alarmwegs. Danach folgt das Menü.
- **Einstiegsfrage (Menü):** „Nutzt du Home Assistant Cloud (Nabu Casa)?“
  - Optionen in dieser Reihenfolge: `cloud` mit „Ja (empfohlen)“ und `no_cloud` mit „Nein“.
    Ein Menü hat keine Vorauswahl [G]. Die Empfehlung steht deshalb im Optionstext, und
    „Ja“ steht oben.
  - Zwei Varianten derselben Frage, weil HA die Beschreibung je Step-ID übersetzt:
    - `alarm_source`: kein Cloud-Abo erkannt
    - `alarm_source_cloud`: Cloud-Abo erkannt. Der Text sagt dann: „Home Assistant Cloud
      ist bei dir bereits aktiv. Mit ‚Ja‘ bekommst du sofort die Adresse.“

    Optionen und Reihenfolge sind gleich. Es wird **nicht** automatisch weitergesprungen.
- **„Nein“ → Menü `no_cloud`:** Kurzer Hinweis, dass ntfy die kostenlose Alternative ist,
  mit einem Satz zum Datenschutz. Optionen:
  - `ntfy`: „Weiter mit ntfy (kostenlos)“, an erster Stelle
  - `cloud`: „Doch Home Assistant Cloud nutzen“
  - `own_address`: „Ich habe eine eigene Internetadresse (für Fortgeschrittene)“. Damit
    landen Technikaffine mit externer URL, die ehrlich „Nein“ sagen, nicht zwangsweise bei
    ntfy.
- **Cloud-Pfad (`cloud`, ebenso `own_address`):** Prüft die Erreichbarkeit ohne
  Nebenwirkung.
  - Cloud-Abo aktiv und verbunden: Cloudhook erzeugen, Abschluss `cloud`.
  - Kein Cloud-Abo, aber eine externe URL: Abschluss `external`, wie bisher.
  - Cloud-Abo aktiv, aber nicht verbunden: Menü `cloud_not_connected` mit „Erneut
    versuchen“ und „Stattdessen ntfy“.
  - Nicht erreichbar: **Einrichtungsdialog `cloud_setup`** (Menü) mit nummerierten
    Schritten:
    1. Home Assistant Cloud über den My-Link öffnen.
    2. Anmelden oder kostenlosen Test starten.
    3. Zurückkommen und „Erneut prüfen“ wählen.

    Dazu der Hinweis auf eine eigene Adresse (My-Link Netzwerk). Optionen: „Erneut
    prüfen“, „Stattdessen ntfy nutzen“ und „Trotzdem fortfahren“. Ab dem zweiten
    erfolglosen Prüfen erscheint `cloud_setup_retry` mit Prüfhinweisen.
  - Die Abschlussdialoge `cloud`/`external` sind die Schritt-für-Schritt-Anleitung für
    FF Agent: Webhook-URL plus alle Feldwerte.
  - „Trotzdem fortfahren“ (`webhook_anyway`) legt den Eintrag wie bisher mit interner
    Adresse bzw. nur dem Pfad an. Die Texte `internal`/`path_only` sind neu formuliert: nur
    Zu- und Absage, Alarmeingang später über „Neu konfigurieren“.
- **ntfy-Pfad:**
  - Zuerst der **Einrichtungsdialog `ntfy`** (Menü) mit nummerierten Schritten:
    1. Integration ntfy über den My-Link hinzufügen.
    2. Das angezeigte Thema abonnieren, mit Anzeigename.
    3. In FF Agent die URL `https://<server>/<thema>/trigger` mit Methode GET eintragen.
    4. „Erledigt“ wählen.

    Optionen: `ntfy_find` („Erledigt, Entität suchen“) und `cloud` („Doch Home Assistant
    Cloud nutzen“).
  - `ntfy_find` sucht die Entität über das Thema. Gefunden: Abschluss `ntfy`. Sonst das
    **Formular `ntfy_select`** mit Fehlerhinweis und optionalem Entitätsfeld. Absenden mit
    leerem Feld sucht erneut, eine gewählte Entität wird geprüft.
  - Abschluss `ntfy`: Er wiederholt die FF-Agent-Werte mit der Server-Adresse des
    tatsächlichen Abos: Methode **GET**, URL `https://<server>/<thema>/trigger`, sonst alles
    leer.
  - Server im Einrichtungsdialog: `ntfy.sh`, oder die Adresse des einzigen vorhandenen
    ntfy-Eintrags.
  - Warum GET auf `/trigger`: Es gibt keinen Body, also kann FF Agent nichts mitschicken, was
    ntfy speichern würde. ntfy setzt dann die Nachricht `triggered` [G]. Der Nutzer hat das
    bestätigt.
- **URLs in Texten** kommen nur über `description_placeholders` (hassfest-Regel).
- **Reconfigure:** Das Formular bekommt das Feld `alarm_source` (Auswahl, Vorbelegung =
  aktuelle Quelle).
  - Wechsel zu bzw. Bleiben bei `ntfy` führt in den Einrichtungsdialog `ntfy`.
  - Wechsel zu `webhook`, „Neue geheime Adresse erzeugen“ oder eine bisher unerreichbare
    Adresse führen in den Cloud-Pfad samt Menüs (`cloud`).
  - Die Schritte unterscheiden am Ende über `self.source`: neuer Eintrag oder Update mit
    Reload.
- **Options Flow:** `init` zeigt je nach Quelle das bisherige Webhook-Formular oder den
  Schritt `ntfy` (ohne „Zusatz-Token verlangen“, mit FF-Agent-Adresse). Die Entität wird nur
  über Reconfigure geändert, weil sie zur Quelle gehört (`data`).

### 6. Zusatz-Token

- Gilt nur im Webhook-Modus. Über ntfy kommen eigene Header nicht beim Abonnenten an
  [A, Recherche 3.3], ein Token wäre wirkungslos.
- Im ntfy-Modus zeigt der Options-Dialog kein Token und keinen Schalter, sondern den Satz:
  Ein Zusatz-Token gibt es bei ntfy nicht, das Thema ist der einzige Schutz.
- Die Option `require_token` bleibt gespeichert und gilt wieder, wenn der Nutzer zurück zum
  Webhook wechselt. Das Issue `webhook_token_rejected` wird im ntfy-Modus beim Setup
  gelöscht.
- Die Doku rät: Wer sicherheitsrelevante Aktionen (Tor, Tür) an den Alarm hängt, nimmt den
  Webhook-Weg mit Zusatz-Token.

### 7. Datenmodell und Migration

- `ConfigFlow.VERSION = 1`, neu `MINOR_VERSION = 2`.
- **`data`**, neue Schlüssel:
  - `alarm_source`: `"webhook"` oder `"ntfy"`
  - `ntfy_entity_uuid`: Registry-UUID oder `None`
  - `ntfy_topic`: Thema oder `None`, **Geheimnis**
  - `ntfy_server`: Server-Adresse oder `None`, nur zur Anzeige
- Die bisherigen Schlüssel (`webhook_id`, `cloudhook`, `cloudhook_url`, `header_token`)
  bleiben in beiden Modi vorhanden.
- **`options`** unverändert.
- **Migration 1.1 → 1.2** in `async_migrate_entry`: `alarm_source = "webhook"` und die drei
  ntfy-Schlüssel mit `None` ergänzen. Einträge mit `version > 1` werden abgelehnt
  (`return False`). Ein Downgrade auf 0.1.0 bleibt möglich, denn HA lädt eine höhere
  Minor-Version ohne Migration. Der alte Code registriert dann den Webhook, das schadet nicht.
- **Redaction:** `TO_REDACT` bekommt `ntfy_topic`, `ntfy_entity_uuid`, `ntfy_entity`,
  `ntfy_publish_url` und `entity_id`. `ntfy_server` bleibt sichtbar; der Diagnosewert hilft
  bei eigenen Servern.

### 8. Diagnostics

- Neu ist `alarm_source`.
- Der Block `webhook` erscheint nur im Webhook-Modus, sonst `null`.
- Neuer Block `ntfy`, nur im ntfy-Modus:
  - `entity_found`, `entity_platform_ok`, `entity_disabled`, `entity_available`
  - `server`
  - Zähler `events_total`, `accepted_total`, `ignored_restored_total`, `ignored_stale_total`,
    `ignored_duplicate_total`
  - `last_event`: `received_at`, `age_seconds` und nur die Form, nämlich `message_length`,
    `has_title`, `tags_count`
- Nie enthalten sind Thema, `entity_id`, Nachrichtentext, Titel oder Tags. Die Form zeigt, ob
  FF Agent doch Inhalte an ntfy schickt (Datenschutz-Frühwarnung, analog A2).

### 9. Datenschutz

- Neue Geheimnisse sind `ntfy_topic` und die daraus gebildete URL. Sie stehen nur in
  `entry.data`, im Abschlussdialog, im Options-Dialog und im Reconfigure-Abschluss. Sie
  erscheinen nie in Logs, Entitätsattributen oder Diagnostics.
- Auch die `entity_id` der ntfy-Entität wird redigiert und nicht geloggt.
- **Hinweis für Nutzer**, kurz und sachlich in Dialog und README:
  - Der Betreiber von ntfy.sh sieht, wann ein Alarm kommt, aber keine Einsatzdaten. Er
    speichert die Meldung bis zu 12 Stunden.
  - Wer das Thema kennt, sieht die Alarmzeitpunkte und kann falsche Alarme auslösen.
  - Die ntfy-Integration speichert Thema und Meldung in den Attributen ihrer Entität, also
    auch im Verlauf (Recorder) und in Backups. Ein Beispiel für `recorder: exclude` steht in
    der README.
- Im Dialog steht kein Preis für Home Assistant Cloud, nur „kostenpflichtig, zunächst
  kostenlos testbar“.
- Im UI erscheinen keine Hersteller- oder Firmennamen von FF Agent (TODO
  `261017-geraeteinfo-hersteller`).

### Qualitätsziel

Unverändert **Bronze** mit den Ausnahmen aus ADR 0002, dazu die schon erfüllten Silber- und
Gold-Regeln. Berührt bzw. gestärkt werden:

- `config-flow` (`data_description` für jedes neue Feld, Menüs)
- `reconfiguration-flow`
- `repair-issues` (neues Issue)
- `diagnostics`
- `test-coverage` (Gate 95 %, Ziel 100 %)
- `docs-*`

`test-before-setup` bleibt eine begründete Ausnahme. Im ntfy-Modus erzeugt eine fehlende
Entität ein Repair-Issue statt eines Setup-Fehlers, weil Rückmeldungen weiter funktionieren.

## Alternativen

| Alternative | Bewertung |
|---|---|
| **Eigener ntfy-Client** (WebSocket/JSON-Stream in unserer Integration) | Verworfen. Er bräuchte Verbindungsmanager, Wiederverbindung, Nachholen über `since`, Auth und Tests. Dazu kämen eine Abhängigkeit (`aiontfy` o. Ä.) und Verantwortung für ein Drittsystem. Vorteile wären ein eigenes `since` (verpasste Alarme nachholen) und ein Abo ohne zweite Integration. Die Core-Integration ist Platin und kann alles andere schon. Neu bewerten, falls verlorene Alarme bei Verbindungsabbrüchen in der Praxis auftreten. |
| **Nur README-Anleitung mit eigener Automation** (ntfy-Event → Action) | Verworfen. Es gibt keine Action, die einen Alarm einspeist. Wir müssten eine bauen (etwa `ff_agent.trigger_alarm`); dann könnte jede Automation und jedes Skript einen „Alarm aktiv“ erzeugen. Das ist eine neue Angriffs- und Fehlerfläche. Jeder Nutzer müsste den Filter aus 3. selbst richtig bauen, und die naheliegende Variante mit `not_from` verliert Alarme. Es gäbe kein Repair-Issue und keine Diagnose. Wer es trotzdem so will, kann heute schon eine eigene Automation auf die ntfy-Entität legen; dafür braucht es unsere Integration nicht. |
| **Integration legt das ntfy-Abo selbst an** (Subentry-Flow der ntfy-Integration programmatisch starten oder `async_add_subentry` auf deren Eintrag) | Verworfen für diesen PR. Es schreibt in den Config-Eintrag einer fremden Integration bzw. steuert deren Flow-Schritte (`add_topic`, Feldnamen, Sektion `filter`) von außen. Ist ntfy gar nicht eingerichtet, müsste zusätzlich deren Haupt-Flow ferngesteuert werden. Das widerspricht der Trennung der Integrationen und bricht bei jeder Änderung des ntfy-Flows. Entschieden vom Projektleiter am 2026-10-17. Mögliches späteres TODO `ntfy-komfort`, falls sich der manuelle Weg im Test als zu schwer erweist. |
| **Thema von der ntfy-Integration erzeugen lassen** („Generate topic name“) und nur die Entität wählen | Teilweise übernommen: Ein vorhandenes Abo ist wählbar. Als Standard nicht, weil das Thema dann ausschließlich aus fremden Interna gelesen werden kann und nur 16 Zeichen hat. Unser Thema ist bekannt, bevor das Abo existiert. |
| **Webhook auch im ntfy-Modus registriert lassen** (beide Eingänge parallel) | Verworfen. Ein zweiter offener Eingang ohne Nutzen. Im ntfy-Modus ist HA meist gar nicht erreichbar. Ein Cloudhook würde nur Ressourcen bei Nabu Casa halten. |
| **Filter `not_from`/`not_to: [unavailable, unknown]`** wie bei Automationen | Verworfen. Er verliert den ersten Alarm nach dem Anlegen des Abos und Alarme im 10-s-Fenster nach einem Neuaufbau (siehe 3.). |
| **Frische über das ntfy-Attribut `time` oder Dedup über `id`** | Verworfen als Hauptregel. Das koppelt an Attribute der Bibliothek, und `time` ist die Server-Uhr. Der State-Zeitstempel kommt von `EventEntity` selbst und ist stabil. |
| **Event-Entität beliebiger Integrationen als Quelle** (allgemeine „Alarmquelle = Event-Entität“) | Vorerst nicht. Die Filterregel funktioniert für jede `EventEntity`. Die Erkennung über das Thema und die Texte sind aber ntfy-spezifisch. Der Listener wird so gebaut, dass er außer bei der Suche nichts von ntfy weiß. Eine spätere Öffnung ist damit billig. |
| **Menü vor der Rückmelde-URL** | Verworfen. Die Duplikatprüfung soll vor dem Einrichten des Alarmwegs kommen. Sonst richtet jemand ntfy ein und erfährt erst danach, dass die Person schon eingerichtet ist. |
| **Neutrale Wahl „Webhook oder ntfy“ als erste Frage** (erster Vorschlag des Architekten) | Verworfen (Nutzer). Laien wissen oft nicht, was ein Webhook ist. Die Frage „Nutzt du Home Assistant Cloud?“ können sie beantworten. Die Cloud ist der empfohlene Weg, weil sie ohne Drittdienst auskommt und das Zusatz-Token erlaubt. |
| **Automatisch weiter bei erkanntem Cloud-Abo** (Frage überspringen) | Verworfen (Nutzer: „nicht erzwingen“). Das erkannte Abo ändert nur den Text der Einstiegsfrage. |
| **Einstieg über drei gleichrangige Optionen** (Cloud, eigene Adresse, ntfy) | Verworfen. Die eigene Adresse ist ein Expertenweg. Sie wird im Cloud-Pfad automatisch erkannt und ist zusätzlich im Menü `no_cloud` als dritte Option erreichbar. |
| **ntfy-Formular mit Entitätsfeld als erster ntfy-Dialog** (erster Vorschlag) | Verworfen. Ein Formular kann kein „Doch Home Assistant Cloud“ anbieten. Der Einrichtungsdialog ist deshalb ein Menü, das Formular `ntfy_select` erscheint nur, wenn die Suche nichts findet. |
| **Preis oder Testdauer im Dialog** | Verworfen (Vorgabe des Nutzers bzw. des Projektleiters; Preise und Testbedingungen ändern sich). Wortlaut: „kostenpflichtiges Abo, zunächst kostenlos testbar“. |

## Konsequenzen

- Nutzer ohne Home Assistant Cloud und ohne eigene Adresse bekommen einen kostenlosen,
  geführten Weg. Die Sackgasse `internal`/`path_only` wird zum Einrichtungsdialog
  `cloud_setup` mit Ausweg zu ntfy oder „Trotzdem fortfahren“.
- Die Einrichtung hat mehr Dialoge als vorher, mindestens Frage, Einrichtungsdialog und
  Abschluss. Jeder Dialog hat dafür nur eine Aufgabe und nummerierte Schritte.
- Zwischen Cloud- und ntfy-Pfad lässt sich in beide Richtungen wechseln, ohne den Flow
  neu zu starten.
- Ein dritter Dienst (ntfy.sh) kennt im ntfy-Modus die Alarmzeitpunkte. Das hat der Nutzer
  akzeptiert, es steht im Datenschutzhinweis.
- **Zuverlässigkeit im ntfy-Modus:**
  - Ein Alarm während einer Verbindungsunterbrechung geht verloren, denn ntfy holt nichts
    nach. Das gilt auch während eines HA-Neustarts.
  - ntfy.sh ist ein zusätzlicher Ausfallpunkt.
  - Teilen sich alle FF-Agent-Aufrufe wenige Absender-IPs, kann das Ratenlimit von ntfy.sh
    je IP bei Großalarmen greifen (HTTP 429) [U].
  - Alles das steht in der README.
- Die Integration koppelt lesend an Interna der ntfy-Integration: Subentry-Typ `topic`,
  `data["topic"]`, `entry.data["url"]`, Semantik der Event-Entität. Ein Vertragstest auf den
  installierten Core-Quellcode schlägt an, wenn sich das ändert. Bricht nur die Suche, bleibt
  die manuelle Auswahl der Entität nutzbar.
- Reconfigure wird umfangreicher. Die Schritte für Webhook und ntfy werden von Einrichtung
  und Reconfigure gemeinsam genutzt.
- Ein Reload bei Umbenennung oder Deaktivierung der ntfy-Entität setzt einen laufenden Alarm
  zurück (wie jede Options-Änderung).
- Rest-Risiko Doppelalarm: Läuft die Rückkehr des alten Werts ausnahmsweise über einen
  echten `unavailable`-State statt über den Platzhalter (Regel 3), und hat der Listener den
  Wert vorher nicht gesehen, zählt er innerhalb von 60 s nach dem Alarm als neuer Alarm.
  Beispiel: Die Integration lädt neu, während die ntfy-Entität gerade `unavailable` ist.
  Das ist selten, dokumentiert und durch einen Test festgeschrieben.

## Annahmen (beim ersten echten ntfy-Test prüfen)

| Nr. | Annahme | Wenn falsch |
|---|---|---|
| N1 | FF Agent akzeptiert `https://ntfy.sh/<thema>/trigger` mit GET, ntfy antwortet innerhalb von 5 s [A]. | Methode POST auf `https://ntfy.sh/<thema>` prüfen; Texte anpassen |
| N2 | Ein GET von FF Agent ohne Einträge unter „Inhalt“ trägt keine Einsatzdaten; ntfy speichert nur `triggered` [A, G für ntfy]. | Diagnose `message_length` zeigt es. Dann Hinweis im Dialog, dass Inhalt/Query leer bleiben müssen |
| N3 | Die Absender-IPs von FF Agent lösen das Ratenlimit von ntfy.sh nicht aus [U]. | README: eigener ntfy-Server oder Webhook-Weg; Frage an den Hersteller |
| N4 | Die Semantik der ntfy-Event-Entität (State = HA-Zeitstempel, Restore, 10-s-Fenster) bleibt so [G heute]. | Vertragstest schlägt an; Filter anpassen |
| N5 | Subentry-Typ `topic`, `data["topic"]` und `entry.data["url"]` bleiben stabil [G heute]. | Vertragstest; die Suche fällt auf die manuelle Auswahl zurück |
| N6 | `redirect/config_flow_start/?domain=ntfy` und `redirect/integration/?domain=ntfy` führen zur ntfy-Einrichtung bzw. -Seite [A]. | Links durch Textanleitung ersetzen |
| N7 | Links in Dialogbeschreibungen öffnen einen neuen Tab, der Flow-Dialog bleibt offen [A]. | Text: „Link in neuem Tab öffnen“; Absenden des ntfy-Formulars ist ohnehin wiederholbar |
| N8 | `redirect/cloud/` bleibt nach der Umbenennung in „Home Assistant Link“ gültig [U]. | Nach dem 2. Dezember 2026 prüfen, Konstante tauschen |
| N9 | 60 s Frischefenster reicht für das 10-s-Fenster der ntfy-Entität [A]. | Konstante `NTFY_MAX_EVENT_AGE` anpassen |
| N10 | Auf ntfy.sh lässt sich ohne Konto anonym veröffentlichen und abonnieren [G, Recherche 3.3]. | Hinweis auf geschütztes Thema bzw. Basis-Authentifizierung |
