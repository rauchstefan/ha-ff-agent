# ADR 0002: Integrationsweg über persönlichen Webhook und persönliche Rückmelde-URL

- **Status:** angenommen (Nutzer, 2026-10-17; vorgeschlagen vom Architekten am selben Tag). Gilt unter dem Vorbehalt der Annahmen
  am Ende; sie werden beim ersten echten Test geprüft.
- **Datum:** 2026-10-17
- **TODO:** `261016-ffagent-klaerung`
- **Umsetzungsplan:** `docs/plaene/261017-mvp-alarm-zusage.md`

## Kontext

Die Integration richtet sich an **Einsatzkräfte ohne Admin-Rechte**. Die Lizenzen der
Einheiten sind unterschiedlich; der Nutzer selbst hat PRO. Das MVP umfasst drei Punkte:

1. einen Alarm erkennen, damit Automationen reagieren können,
2. Zusage und Absage senden,
3. Einsatzdetails anzeigen, soweit verfügbar.

Was über die Schnittstellen von FF Agent bekannt ist (Quellen:
`docs/recherche/261016-ffagent-schnittstellen.md`, `docs/recherche/261016-ffagent-webhook-zusage.md`):

- Die **WebAPI** arbeitet nur eingehend (extern → FF Agent), braucht Admin-Zugangsdaten und
  ein Client-Zertifikat und kann Alarme auslösen. Für Einsatzkräfte ist sie ungeeignet und
  aus Sicherheitsgründen tabu.
- **Persönliche Webhooks:** In der Web-UI unter „Automatisierung“ kann jede Person bis zu 3
  davon anlegen (Details im Nachtrag unten). Ob Platzhalter mit Einsatzdaten möglich sind,
  ist unbekannt. Der
  Präzedenzfall aus der Homey-App spricht für einen Aufruf **ohne Nutzdaten**.
- **Persönliche Rückmelde-URLs:** Sie stehen ebenfalls in der Web-UI:
  `https://www.ff-agent.com/app2/missionreplies/<REPLY_ID>/accept?transport=CAR&lat=..&lng=..`
  und `.../<REPLY_ID>/reject`. `REPLY_ID` ist eine UUID und wirkt als Geheimnis. Eine
  Anmeldung ist nicht nötig. Die URLs beziehen sich vermutlich auf den aktiven Einsatz.
- **Einsatzdetails:** Es gibt keine dokumentierte lesende Nutzer-API. Belegt ist nur ein
  persönlicher iCal-Feed (Stand 2019, Inhalt: „Einsätze, an denen Sie teilgenommen haben“).
  Die Anfrage beim Hersteller läuft noch.
- **Erreichbarkeit von HA:** Manche Nutzer haben Nabu Casa, manche eine eigene externe URL,
  manche nur eine interne Adresse.

**Nachtrag 2026-10-17: Dialog „Webhook hinzufügen“** (Screenshots des Nutzers, gesichert [G]):

- **Type:** einzige Auswahl „Alarm“.
- **Webhooktyp:** u. a. „Generischer Webhook“, „IFTTT Maker“, „Homee Webhook“ und mehrere
  Shelly-Typen. Für HA ist „Generischer Webhook“ der passende Typ.
- **Allgemein:**
  - Name und Checkbox „Aktiv“
  - Auslösung „Alarm“ mit den Checkboxen „auch für Testalarme“, „auch für Infoalarme“ und
    „auch für stille Einsätze“
  - „Zeitplan aktiviert“ ist eine Checkbox, der Zeitplan ist also optional.
- **Generischer Webhook:**
  - Methode **GET oder POST**
  - Schema `https://` (vermutlich auch `http://`) plus Host und Pfad. Query-Parameter sind
    in der URL oder separat erlaubt.
  - **Timeout je 5 s** für Verbindungsaufbau und Verarbeitung
  - optionale **Basis-Authentifizierung**
  - **frei definierbare Header**
  - unter „Inhalt“: Query-Parameter (uncodiert) als Name/Wert-Paare bei GET
- **Weiter offen [U]:** ob POST einen Body-Bereich hat, ob Werte Platzhalter mit
  Einsatzdaten erlauben, ob FF Agent bei Fehlern wiederholt.

HA-Core-Befund zum Cloudhook (`homeassistant/components/cloud/client.py`,
`async_webhook_message`, Stand `dev` 2026-10-17) [G]: HA baut aus der Cloud-Nachricht einen
`MockRequest` mit `headers`, `method`, `query` und `body` der Nachricht, **ohne Filter**.
Ob der Nabu-Casa-Server eigene Header (z. B. `X-FF-Agent-Token`) unverändert an HA
weitergibt, lässt sich im offenen Code nicht prüfen [A: wahrscheinlich ja].

Für die HA-APIs gilt der Stand von HA 2026.3.0 (Mindestversion laut `hacs.json`) und HA
`dev` (geprüft am 2026-10-17 im Core-Quellcode):

- `webhook.async_register(hass, domain, name, webhook_id, handler, *, local_only=False, allowed_methods=None)`.
  Standardmethoden sind POST und PUT; unterstützt werden GET, HEAD, POST und PUT. Ist HEAD
  nicht freigegeben, antwortet HA trotzdem mit 200.
- `webhook.async_generate_url(...)` mit `allow_cloud=False`. Die Funktion ruft `get_url` auf,
  das `NoURLAvailableError` werfen kann.
- `cloud.async_active_subscription`, `cloud.async_is_connected`,
  `cloud.async_get_or_create_cloudhook`, `cloud.async_delete_cloudhook`,
  `CloudNotAvailable` und `CloudNotConnected` gibt es in 2026.3.0 und in `dev`.
- Cloudhook-Aufrufe kommen als `MockRequest` an. Dieses Objekt hat `text()`, `json()`,
  `post()`, `query`, `headers` und `content.read()`, aber **kein `read()`**.

## Entscheidung

### 1. Integrationsweg und `iot_class`

- **Alarm-Eingang:** Die Integration registriert je Config-Eintrag einen HA-Webhook. Die
  Einsatzkraft trägt dessen URL in FF Agent als persönlichen Webhook ein. Ein Aufruf
  bedeutet „Alarm“; Nutzdaten werden nicht vorausgesetzt.
- **Zusage und Absage:** HA ruft die persönliche Rückmelde-URL auf. Gespeichert werden nur
  die UUID und der geprüfte Host, nie die vollständige URL mit Parametern.
- **Einsatzdetails:** Im MVP gibt es keine eigene Datenquelle. Die Architektur sieht einen
  Erweiterungspunkt vor (siehe 7.).
- **`iot_class: cloud_push`**, denn die Cloud von FF Agent meldet Alarme an HA. Die
  Rückmeldung ist eine Aktion des Nutzers, kein Polling. Deshalb ist `cloud_polling` falsch.
- **`integration_type: service`**: Ein Eintrag entspricht dem persönlichen Zugang einer
  Person zu einem Cloud-Dienst, nicht einem Hub mit Geräten.
- Manifest: `dependencies: ["webhook"]`, `after_dependencies: ["cloud"]` (wie bei
  Core-Integrationen mit Cloudhook, z. B. `withings`), `requirements: []`.
- **Von HA aus wird niemals ein Alarm ausgelöst.** Die Integration enthält keinen Code für
  die WebAPI.

### 2. Mehrere Einträge statt `single_config_entry`

- `single_config_entry` entfällt. **Ein Config-Eintrag entspricht einer Person** (eigene
  Rückmelde-UUID, eigener Webhook). So können mehrere Einsatzkräfte in einem Haushalt die
  Integration nutzen.
- Die `unique_id` des Eintrags ist `sha256(reply_id)`, gekürzt auf 16 Hex-Zeichen. Das
  verhindert doppelte Einträge für dieselbe Person, ohne die UUID im Klartext als
  `unique_id` zu speichern.
- Die `unique_id` der Entitäten lautet `"{entry_id}_{key}"`. Sie bleibt stabil, auch wenn die
  Person ihre Rückmelde-UUID neu erzeugt.
- Eine Person kann bis zu drei FF-Agent-Webhooks auf **dieselbe** HA-URL zeigen lassen, z. B.
  mit verschiedenen Zeitplänen. Die Deduplizierung fängt Doppelaufrufe ab.

### 3. Config Flow

- **`user`**: Felder `name` (Anzeigename, Standard „FF Agent“) und `reply_url`. Akzeptiert
  werden die Zusage- oder die Absage-URL oder die blanke UUID.
  - Prüfung: Schema `https`; Host `ff-agent.com` oder eine Subdomain davon; Pfad
    `/app2/missionreplies/<uuid>/(accept|reject)`; die UUID muss sich parsen lassen.
  - Gespeichert werden `reply_id` (UUID in Kleinbuchstaben) und `reply_host`.
- **Kein Verbindungstest.** Jeder Aufruf der Rückmelde-URL wäre eine echte Zu- oder Absage.
  Die Regel `test-before-configure` gilt deshalb als begründete Ausnahme.
- **Webhook:** Der Flow erzeugt die ID mit `webhook.async_generate_id()`. Die URL wird in
  dieser Reihenfolge bestimmt:
  1. Cloudhook (`async_get_or_create_cloudhook`), wenn ein Nabu-Casa-Abo aktiv ist.
     Ist die Cloud dabei nicht verbunden, zeigt der Flow den Fehler `cloud_not_connected`
     und der Nutzer kann es erneut versuchen.
  2. Sonst die externe URL.
  3. Sonst die interne URL, mit deutlicher Warnung.
  4. Sonst nur der Pfad.

  Die URL erscheint im Abschlussdialog. Der Text richtet sich nach der Art der URL
  (`create_entry`-Übersetzungen `cloud`, `external`, `internal`, `path_only`). Er enthält
  eine **Kurzanleitung mit den exakten Feldwerten für FF Agent** (siehe 5.).
- Der Flow erzeugt außerdem immer ein **Zusatz-Token** (`secrets.token_urlsafe(32)`) und
  speichert es in `entry.data`. Ob HA es prüft, steuert eine Option (siehe 5.).
- **Options Flow** (`OptionsFlowWithReload`):
  - zeigt die aktuelle Webhook-URL sowie Header-Name und Token an
  - Schalter „Zusatz-Token verlangen“ (Standard aus)
  - Rücksetzzeit „Alarm aktiv“ in Minuten
  - Standard-Verkehrsmittel
  - optional eine Standort-Entität (`person`, `device_tracker`) für `lat`/`lng`
- **Reconfigure:**
  - neue Rückmelde-URL eintragen (z. B. nach dem Neuerzeugen der UUID)
  - optional den Webhook-Zugang neu erzeugen: neue Webhook-ID und neues Zusatz-Token. Der
    alte Cloudhook wird gelöscht, die neue URL und das neue Token werden angezeigt.

  Ein Reauth-Flow folgt erst, wenn bekannt ist, wie FF Agent eine ungültige UUID beantwortet
  (Annahme A7).

### 4. Entitäten

Alle Entitäten gehören zu einem Gerät je Eintrag (`DeviceEntryType.SERVICE`), haben
`has_entity_name` und werden über `translation_key` übersetzt.

| Plattform | Key | Zweck |
|---|---|---|
| `binary_sensor` | `alarm` | „Alarm aktiv“: an beim Alarm, aus nach Ablauf der Rücksetzzeit (Standard 30 min). Ein neuer Alarm startet die Zeit neu. |
| `event` | `alarm` | Event-Typ `alarm` bei jedem neuen Alarm, nach der Deduplizierung. Primärer Trigger für Automationen. |
| `sensor` | `last_alarm` | Zeitstempel (`TIMESTAMP`) des letzten Alarms, wird nach einem Neustart wiederhergestellt |
| `sensor` | `last_reply` | Ergebnis der letzten Rückmeldung (`ENUM`: `accepted`, `rejected`, `failed`) |
| `button` | `accept` | Zusagen mit dem Standard-Verkehrsmittel und optional dem Standort |
| `button` | `reject` | Absagen |

- Dazu kommen zwei Actions: `ff_agent.accept` (`config_entry_id`, optional `transport`,
  `latitude`/`longitude`) und `ff_agent.reject` (`config_entry_id`). Sie werden in
  `async_setup` registriert.
- **Kein eigenes Bus-Event.** Die Event-Entität ist der von HA vorgesehene Weg für
  zustandslose Ereignisse. Sie erscheint im UI, ist geräte- und eintragsbezogen und erzeugt
  keine zweite, doppelt dokumentierte Trigger-Quelle.

### 5. Webhook-Handler

- Registrierung mit `allowed_methods=["GET", "POST"]`, also genau die Methoden, die FF Agent
  anbietet [G], und ausdrücklich `local_only=False`, weil FF Agent aus dem Internet aufruft.
  HEAD beantwortet HA ohnehin mit 200.
- **Antwortzeit:** FF Agent bricht nach 5 s ab [G]. Der Handler führt deshalb keine
  externen Aufrufe aus und wartet auf nichts außer dem Lesen des Bodys. Die Verarbeitung im
  `AlarmManager` ist synchron und nur im Speicher, Entitäten werden per Dispatcher
  aktualisiert. Der Handler antwortet mit 200, auch bei Parse-Fehlern; einzige Ausnahme ist
  ein fehlendes Zusatz-Token (siehe unten).
- **Nichts wird vorausgesetzt.** Der Handler liest den Body über `request.text()` (das geht
  auch bei `MockRequest`) und erfasst nur die **Form** des Aufrufs:
  - Methode, Content-Type, Länge
  - Header-Namen und der User-Agent
  - Query-Schlüssel
  - die JSON- bzw. Formular-Struktur mit Typen statt Werten

  Werte werden nicht gespeichert.
- **Deduplizierung:** Aufrufe innerhalb von 30 s nach dem letzten anerkannten Alarm werden
  nur gezählt.
- **Sicherheit, Grundlage:** Die Webhook-ID (64 Hex-Zeichen) bzw. die Cloudhook-URL ist
  das Basisgeheimnis. Sie lässt sich über Reconfigure neu erzeugen.
- **Zusatz-Token im Header: optional, Standard aus.**
  - Header-Name `X-FF-Agent-Token`, Wert ist das Token aus `entry.data`.
  - Ist die Option „Zusatz-Token verlangen“ an, prüft der Handler den Header **vor** der
    Erfassung mit `hmac.compare_digest`.
  - Fehlt der Header oder ist er falsch, antwortet HA mit 401 und verwirft den Aufruf. Er
    zählt in `rejected_total`, und es entsteht ein Repair-Issue
    `webhook_token_rejected` (nicht reparierbar, nur Hinweis). Der nächste gültige Aufruf
    löscht das Issue. Ein abgelehnter Alarm darf nicht unbemerkt bleiben.
  - Begründung:
    - Mehrwert: Header stehen nicht in der URL. Damit schützt das Token gegen die typischen
      Lecks der URL: Access-Logs von Reverse Proxies, die HA-Warnung mit Webhook-ID bei
      falscher Methode, Screenshots, Browserverlauf, geteilte Automationen. Das zählt, weil
      Nutzer an „Alarm“ auch sicherheitsrelevante Aktionen hängen können (Tor öffnen,
      Haustür entriegeln). Ein gefälschter Alarm wäre dann mehr als ein falsches Licht.
    - Aufwand: klein (ein Vergleich, ein Feld in `data`, ein Options-Schalter, ein
      Repair-Issue).
    - Kosten für den Nutzer: In FF Agent ist ein Header-Paar mehr einzutragen.
  - **Warum nicht Pflicht:** Ob der Nabu-Casa-Server eigene Header durchreicht, ist nicht
    belegt (A12). Ein Pflicht-Token, das unterwegs verloren geht, würde **jeden Alarm
    verwerfen**. Für eine Alarmfunktion ist das schlimmer als das Restrisiko. Nach dem
    ersten echten Test mit Cloudhook und Token wird geprüft, ob neue Einträge die Option
    standardmäßig an bekommen (Folge-TODO).
  - **Kein Token als Query-Parameter:** Er stünde in der URL und hätte dasselbe Leckprofil
    wie die Webhook-ID; Mehrwert fast null.
  - **Keine Basis-Authentifizierung:** Der `Authorization`-Header wird auch von der
    HA-Auth-Middleware ausgewertet. Ein eigener Header vermeidet dieses Zusammenspiel [A].
- Die Nutzerdoku nennt das Restrisiko: Mit der URL (und ohne Token-Pflicht) lässt sich ein
  falscher „Alarm aktiv“ auslösen. Wer sicherheitsrelevante Aktionen anhängt, soll die
  Token-Pflicht einschalten.

### 5a. Empfohlene Einstellungen in FF Agent (für Abschlussdialog und README)

| Feld in FF Agent | Empfohlener Wert | Begründung |
|---|---|---|
| Type | Alarm | einzige Auswahl |
| Webhooktyp | Generischer Webhook | frei konfigurierbar |
| Name | z. B. „Home Assistant“ | frei |
| Aktiv | an | |
| auch für Testalarme | **an** | Der Nutzer kann die Kette testen. Die Doku warnt, dass Automationen dann auch bei Testalarmen laufen. |
| auch für Infoalarme | **aus** | Infoalarme sind keine Einsätze [A]. |
| auch für stille Einsätze | nach Wunsch, Vorschlag **an** | Die Person ist beteiligt. Wer nachts keine Durchsage will, filtert in der Automation [A]. |
| Zeitplan aktiviert | **aus** | HA soll jeden Alarm sehen. Zeitfenster lassen sich in HA-Automationen genauer abbilden. |
| Bemerkung | frei | |
| Methode | **POST** | HA-Standard für Webhooks; keine Daten in der URL. HA nimmt auch GET an. |
| URL | die angezeigte Webhook-URL, mit `https://` | |
| Basis-Authentifizierung | leer | wird nicht genutzt |
| Header | `X-FF-Agent-Token` = angezeigtes Token, nur bei eingeschalteter Option | |
| Inhalt / Query-Parameter | leer | Platzhalter sind unbekannt (A13). |

Keine der Auslöse-Optionen lässt sich in HA unterscheiden, solange der Aufruf keine Daten
trägt. Testalarm, stiller Einsatz und echter Alarm sehen für HA gleich aus.

### 6. Rückmelde-Client

- Aufruf per `GET https://<reply_host>/app2/missionreplies/<reply_id>/<accept|reject>` mit
  `transport`, `lat` und `lng` als Query-Parametern.
- Er nutzt `async_get_clientsession(hass)` mit 10 s Gesamt-Timeout und folgt Redirects.
  Erfolg bedeutet einen Status 2xx.
- Fehlerbehandlung:
  - Fehler werden auf `HomeAssistantError` mit Übersetzung abgebildet. Der Button zeigt
    sie als Toast, eine Automation schlägt sichtbar fehl.
  - Eingabefehler erzeugen `ServiceValidationError`.
  - Persistent Notifications gibt es nicht.
- **Schutz vor Doppelklick:** Ein Lock je Eintrag. Eine gleiche Rückmeldung innerhalb von
  10 s nach einem Erfolg wird ohne zweiten HTTP-Aufruf übersprungen. Eine andere
  Rückmeldung (Zusage, dann Absage) bleibt erlaubt.
- **Keine UUID im Log.** Weder URL noch Query noch `str()` einer aiohttp-Exception werden
  geloggt; `ClientResponseError` enthält die URL. Geloggt werden nur der Exception-Typ und
  der Statuscode.

### 7. Einsatzdetails: Erweiterungspunkt, kein Bau im MVP

- **Erweiterungspunkt:** Der Handler gibt jeden Aufruf als `WebhookCall` an den
  `AlarmManager`. Der Rohtext ist darin nur flüchtig verfügbar. Der Manager erzeugt ein
  `AlarmEvent`. Später kann ein Parser bzw. eine `DetailsSource` dort ein Feld `details`
  füllen, entweder aus dem Payload, falls FF Agent Platzhalter kennt, oder aus einer
  Abrufquelle. Neue Detail-Entitäten nehmen ihre Attribute dann in `_unrecorded_attributes`
  auf.
- **Der aussichtsreichste Weg zu Details** ist der Webhook selbst: FF Agent erlaubt freie
  Query-Parameter (und eventuell einen POST-Body). Erlauben diese Werte Platzhalter mit
  Einsatzdaten (A13), lässt sich MVP-Punkt 3 ohne weitere Schnittstelle lösen. Der Nutzer
  trägt dann z. B. `keyword=<Platzhalter>` ein, und ein Parser am Erweiterungspunkt liest
  bekannte Schlüssel. Bis das geklärt ist, bleibt es beim Erweiterungspunkt.
- **iCal-Feed:** Ein eigener Abruf wird nicht gebaut. Der Feed enthält laut Doku nur
  Einsätze, an denen die Person teilgenommen hat. Für einen laufenden Alarm taugt er
  deshalb vermutlich nicht. Wer ihn will, bindet ihn über die Core-Integration **Remote
  Calendar** ein (ab HA 2025.4, Basic-Auth wird unterstützt, Aktualisierung alle 24 h oder
  per `homeassistant.update_entity`). Die Doku erhält dafür einen Hinweis inklusive
  Recorder-Warnung, weil Kalender-Attribute Ort und Beschreibung enthalten.

### 8. Datenschutz

- **Geheimnisse:** `reply_id`, `webhook_id`, `cloudhook_url` und `header_token` stehen
  nur in `entry.data`. Werte eingehender Header werden nie gespeichert oder geloggt, nur
  ihre Namen; Ausnahmen sind der Medientyp aus dem Content-Type und der auf 120 Zeichen gekürzte User-Agent (siehe 5). In Diagnostics werden sie redigiert, ebenso `unique_id`, `title` und
  `location_entity`. Sie erscheinen in keinem Log und keinem Entitätsattribut.
- **Recorder:** Die MVP-Entitäten haben keine Attribute mit Einsatzinhalt. Gespeichert werden
  nur Zeitpunkte und Zustände. Dass die Alarmzeitpunkte selbst personenbezogen sind, steht
  in der Doku, mit einem Beispiel für `recorder: exclude`.
- **Payload-Inhalte:** Sie werden weder gespeichert noch geloggt, nur ihre Form.

### Qualitätsziel

Angestrebt ist **Bronze** der Integration Quality Scale, mit begründeten Ausnahmen:

- `appropriate-polling`: kein Polling
- `test-before-configure`, `test-before-setup`: Ein Test würde eine echte Rückmeldung senden
  und die Webhook-Erreichbarkeit lässt sich aus HA nicht prüfen
- `docs-conditions`: keine Conditions

Zusätzlich gelten diese Regeln aus Silber und Gold, weil sie fast nichts kosten:

- `action-exceptions`, `config-entry-unloading`, `parallel-updates`, `test-coverage`
- `devices`, `diagnostics`, `entity-translations`, `exception-translations`,
  `icon-translations`, `reconfiguration-flow`

## Alternativen

| Alternative | Warum verworfen |
|---|---|
| WebAPI (`triggerAlarm` u. a.) | nur eingehend; Admin-Rechte, Token, HMAC und Client-Zertifikat; kann echte Alarme auslösen |
| Inoffizielle Status-Monitor-Widget-API (Polling) | Admin-Display-Token, inoffiziell, viele Personendaten, ohne Zustimmung des Herstellers unzulässig |
| Login mit Benutzername und Passwort, App-Endpunkte | nicht dokumentiert; Konto-Zugangsdaten in HA wären sicherheitskritisch; Sperrrisiko |
| Companion-App „Last Notification“ | nur Android, Textparsing, keine Rückmeldung; bleibt ein möglicher Doku-Tipp, kein Teil der Integration |
| IMAP-Auswertung der Alarm-Mail | Postfachzugang, Parsing, Alarmtext im Recorder; unverhältnismäßig für das MVP |
| Gateway PLUS mit Node-RED | nur für Admins mit Hardware; passt nicht zur Zielgruppe |
| `single_config_entry` beibehalten | schließt mehrere Personen in einem Haushalt aus; kein technischer Vorteil |
| Webhook-ID als einziges `unique_id`-Merkmal | Doppelte Einträge derselben Person wären möglich, weil jeder Flow eine neue ID erzeugt |
| Bus-Event `ff_agent_alarm` zusätzlich zur Event-Entität | doppelte Trigger-Quelle; Bus-Events landen samt Daten in der Events-Tabelle des Recorders |
| Zusatz-Token als Pflicht | Geht der Header über Nabu Casa verloren (A12), würde jeder Alarm verworfen. Neu bewerten nach dem ersten Test. |
| Zusatz-Token als Query-Parameter | steht in der URL, gleiches Leckprofil wie die Webhook-ID |
| Basis-Authentifizierung von FF Agent | Der `Authorization`-Header wird auch von der HA-Auth-Middleware ausgewertet; eigener Header ist eindeutiger. |
| Kein Zusatz-Token | Bei sicherheitsrelevanten Automationen (Tor, Tür) wäre die URL allein ein zu schwacher Schutz. |
| Persistent Notification als Rückmeldung | nicht HA-konform für Aktionen; Exceptions erscheinen im UI und in Automationstraces |
| POST statt GET für die Rückmeldung | Die UI bietet die URL zum Öffnen im Browser an, das spricht für GET. Die Methode ist eine Konstante und lässt sich leicht ändern (A6). |
| Eigener iCal-Abruf | Nutzen für laufende Alarme unklar; die Core-Integration Remote Calendar deckt den Fall ab |

## Konsequenzen

- Die Einrichtung braucht zwei manuelle Kopiervorgänge: die Rückmelde-URL von FF Agent nach
  HA und die Webhook-URL von HA nach FF Agent. Optional kommt das Header-Token dazu. Die
  Doku braucht dafür eine Schritt-für-Schritt-Anleitung mit den Feldwerten aus 5a.
- Ohne Nabu Casa oder externe URL kommt kein Alarm an. Die Integration sagt das bei der
  Einrichtung deutlich, verhindert die Einrichtung aber nicht, weil Rückmeldungen trotzdem
  funktionieren.
- Die Auslöse-Filter (Test-, Info-, stille Alarme) und der optionale Zeitplan liegen in
  FF Agent. Was dort abgewählt ist, sieht HA nicht. HA selbst kann die Alarmarten nicht
  unterscheiden.
- Mit eingeschalteter Token-Pflicht verwirft HA Aufrufe ohne gültiges Token. Ein
  Repair-Issue macht das sichtbar.
- Nach einem HA-Neustart ist „Alarm aktiv“ aus, auch wenn die Rücksetzzeit noch läuft.
  Wiederhergestellt wird nur der Zeitstempel des letzten Alarms. Das ist eine bewusste
  Vereinfachung im MVP.
- `AlarmManager`, `ReplyClient` und die Erfassung der Aufruf-Form lassen sich ohne
  FF-Agent-Zugang testen (`hass_client_no_auth`, `aioclient_mock`, `MockRequest`).
- Ändert der Hersteller die URL-Struktur, betrifft das nur `reply_url.py` und `reply.py`.

## Annahmen (vor bzw. beim ersten echten Test prüfen)

Kennzeichnung wie in den Recherchen: unbestätigt [U], abgeleitet [A].

| Nr. | Annahme | Wenn falsch |
|---|---|---|
| A1 | **Erledigt [G]:** Methode wählbar GET oder POST. | – (HA nimmt genau diese beiden an) |
| A2 | Ohne eigene Einträge unter „Inhalt“ trägt der Aufruf keine Einsatzdaten [A, Homey]. Der Nutzer kann aber selbst statische Query-Parameter und Header setzen [G]. | Die Diagnostics zeigen die Form. Liefert FF Agent doch Daten, folgt ein Parser-Plan (7.). |
| A3 | Der Webhook feuert je Alarm (Type „Alarm“ ist die einzige Auslösung [G]). Ob Nachalarmierungen oder Änderungen desselben Einsatzes erneut auslösen und ob FF Agent bei Fehlern wiederholt, ist [U]. | Mehrfachaufrufe innerhalb von 30 s fängt die Deduplizierung ab. Bei späteren Wiederholungen entsteht ein zweites Event; dann das Dedup-Fenster als Option anbieten. |
| A4 | FF Agent akzeptiert HTTPS-URLs mit beliebigem Host und Pfad, auch `hooks.nabu.casa` [G für das Formular, A für den Cloudhook-Host]. Timeout je 5 s [G]. Ob FF Agent den Antwortstatus auswertet, ist [U]. | Hinweis in der Doku; der Handler antwortet ohnehin sofort |
| A5 | Testalarme, Infoalarme und stille Einsätze lassen sich in FF Agent einzeln zuschalten; der Zeitplan ist optional [G]. Dass ein persönlicher Webhook nur bei Alarmen feuert, für die die Person alarmiert wird, ist [A]. | Doku anpassen. HA kann die Alarmarten nur mit Platzhaltern unterscheiden (A13). |
| A6 | Die Rückmeldung funktioniert per GET ohne weitere Header und liefert bei Erfolg 2xx [A]. | Methode bzw. Header in `reply.py` anpassen |
| A7 | Die Antwort bei ungültiger UUID oder ohne aktiven Einsatz ist unbekannt; vermutlich 4xx oder 200 mit HTML [U]. | Liefert sie immer 200, meldet die Integration nur „gesendet“, nicht „bestätigt“. Liefert sie bei ungültiger UUID einen eindeutigen Status, kommt ein Reauth-Flow dazu. |
| A8 | `REPLY_ID` gilt dauerhaft je Person und bezieht sich auf den aktiven Einsatz [A]. | Ändert sie sich je Einsatz, ist der Weg so nicht nutzbar. Dann braucht es eine Herstellerlösung. |
| A9 | Belegt ist nur `transport=CAR`. `transport` darf vermutlich fehlen; `lat`/`lng` sind optional und nutzen den Dezimalpunkt [U]. | Werteliste in `const.TRANSPORTS` ergänzen; Pflichtparameter erzwingen |
| A10 | Der Host ist bei allen Lizenzen `www.ff-agent.com` oder eine Subdomain von `ff-agent.com` [A]. | Prüfregel für den Host erweitern |
| A11 | Der Hersteller hat keine Einwände gegen die automatisierte Nutzung der persönlichen URLs [A]. | Vor einer Veröffentlichung klären; die Hersteller-Anfrage läuft bereits |
| A12 | Der Nabu-Casa-Server reicht eigene Header und Query-Parameter an HA durch. HA selbst gibt sie ungefiltert weiter [G, Core-Code]; den Server kann man nicht einsehen [A]. | Token-Prüfung bei Cloudhook nicht nutzbar: in Options-Text und Doku darauf hinweisen. Die Option bleibt standardmäßig aus. |
| A13 | Ob Query-Parameter, Header oder ein POST-Body in FF Agent Platzhalter mit Einsatzdaten (Stichwort, Ort, Alarmart) erlauben, ist [U]. | Falls ja: MVP-Punkt 3 über den Webhook lösen (Parser-Plan) und Alarmarten unterscheiden. Falls nein: bleibt beim Erweiterungspunkt. |
