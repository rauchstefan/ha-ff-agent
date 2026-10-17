# FF Agent für Home Assistant

Custom-Integration für [Home Assistant](https://www.home-assistant.io/), installierbar
über [HACS](https://hacs.xyz/), die **FF Agent** (Alarmierungs- und Einsatzsoftware für
Feuerwehren und Hilfsorganisationen) in Home Assistant verfügbar macht.

> **Inoffizielles Community-Projekt, nicht mit dem Hersteller von FF Agent verbunden.**
> Das Repository ist noch privat. Die Installation über HACS funktioniert erst nach der
> Veröffentlichung.

## Was die Integration tut und was nicht

<!-- docs-high-level-description -->
<!-- docs-data-update -->
<!-- docs-use-cases -->

Die Integration richtet sich an **Einsatzkräfte ohne Admin-Rechte in FF Agent**. Eine
Einrichtung gehört zu genau einer Person. Mehrere Personen in einem Haushalt legen mehrere
Einträge an.

**Sie tut:**

- Sie meldet jeden neuen Alarm (nach der Deduplizierung von 30 s) als **Event** an Home Assistant. Damit starten Automationen
  (Licht an, Benachrichtigung, Tor öffnen).
- Sie zeigt „Alarm aktiv“ (mit Rücksetzzeit) und den Zeitpunkt des letzten Alarms.
- Sie sendet **Zusage und Absage** an FF Agent, per Button oder Action.

**Sie tut nicht:**

- Sie löst **keine Alarme** aus. Es gibt keinen Code für die WebAPI von FF Agent.
- Sie liefert **keine Einsatzdetails** (Stichwort, Ort, Alarmart). Der Alarm-Aufruf von FF
  Agent wird nur als „es gab einen Alarm“ gewertet.
- Sie unterscheidet nicht zwischen Testalarm, stillem Einsatz und echtem Alarm.

So funktioniert es: FF Agent ruft bei einem Alarm einen **persönlichen Webhook** auf, den
die Integration in Home Assistant bereitstellt. Für Zusage und Absage ruft Home Assistant
deine **persönliche Rückmelde-URL** von FF Agent auf. Daten kommen ausschließlich per Push
von FF Agent, es gibt kein Abfragen.

## Voraussetzungen

<!-- docs-installation-instructions -->

- ein FF-Agent-Konto mit Zugriff auf „Automatisierung“ in der Web-UI
- Home Assistant 2026.3.0 oder neuer
- Home Assistant muss **aus dem Internet erreichbar** sein, damit FF Agent den Webhook
  aufrufen kann: Home Assistant Cloud (Nabu Casa) oder eine externe URL mit HTTPS.
  Zusage und Absage funktionieren auch ohne.

## Installation

<!-- docs-installation-instructions -->

**Über HACS (Custom Repository), sobald das Repository öffentlich ist:**

1. In HACS oben rechts das Menü (⋮) öffnen, *Benutzerdefinierte Repositories* wählen, die
   URL `https://github.com/rauchstefan/ha-ff-agent` eintragen und als Typ „Integration“
   hinzufügen.
2. „FF Agent“ installieren und Home Assistant neu starten.
3. Unter *Einstellungen → Geräte & Dienste → Integration hinzufügen* „FF Agent“ wählen.

**Manuell:**

1. Den Ordner `custom_components/ff_agent` in das Verzeichnis `custom_components` deiner
   Home-Assistant-Konfiguration kopieren.
2. Home Assistant neu starten.
3. Die Integration wie oben hinzufügen.

## Einrichtung Schritt für Schritt

<!-- docs-installation-parameters -->

1. **Rückmelde-URL kopieren.** In der FF-Agent-Web-UI unter *Automatisierung →
   Einsatzrückmeldungen* die Zusage-URL kopieren. Sie sieht so aus:
   `https://www.ff-agent.com/app2/missionreplies/<REPLY_ID>/accept?transport=CAR`.
   Akzeptiert werden auch die Absage-URL oder die blanke UUID.
2. **Integration hinzufügen.** In Home Assistant *Integration hinzufügen → FF Agent*. Felder:
   - **Name:** Bezeichnung dieser Einrichtung, zum Beispiel dein Name. Der Name wird zum
     Gerätenamen und damit Teil der Entity-IDs.
   - **Rückmelde-URL (Zusage):** die kopierte URL.

   Die Integration sendet dabei **nichts** an FF Agent, denn jeder Test wäre eine echte
   Zusage.
3. **Webhook-URL kopieren.** Der Abschlussdialog zeigt die Webhook-URL. Die Art der Adresse
   hängt von deiner Installation ab:
   - Nabu Casa: eine Cloudhook-URL, zum Beispiel `https://hooks.nabu.casa/<...>`
   - externe URL: `https://<deine-externe-url>/api/webhook/<WEBHOOK_ID>`
   - nur interne Adresse oder nur Pfad: FF Agent erreicht sie **nicht**. Richte eine externe
     URL oder Nabu Casa ein und wähle danach beim Eintrag „Neu konfigurieren“ mit
     „Webhook-Zugang neu erzeugen“.
4. **Webhook in FF Agent anlegen.** In der FF-Agent-Web-UI *Automatisierung → Persönliche
   Webhooks → Webhook hinzufügen* und **jedes Feld** nach dieser Tabelle ausfüllen:

   | Feld in FF Agent | Wert | Begründung |
   |---|---|---|
   | Type | Alarm | einzige Auswahl |
   | Webhooktyp | Generischer Webhook | frei konfigurierbar, passt zu Home Assistant |
   | Name | frei, z. B. „Home Assistant“ | nur zur Anzeige in FF Agent |
   | Aktiv | an | sonst wird nichts aufgerufen |
   | auch für Testalarme | an (zum Testen) | Du kannst die ganze Kette prüfen. **Automationen laufen dann auch bei Testalarmen.** |
   | auch für Infoalarme | aus | Infoalarme sind keine Einsätze (Annahme, ungeprüft) |
   | auch für stille Einsätze | nach Wunsch, Vorschlag an | Du bist beteiligt. Wer nachts keine Durchsage will, filtert in der Automation. |
   | Zeitplan aktiviert | aus | Home Assistant soll jeden Alarm sehen. Zeitfenster lassen sich in Automationen genauer abbilden. |
   | Methode | POST | Home-Assistant-Standard für Webhooks, keine Daten in der URL. Home Assistant nimmt auch GET an. |
   | URL | die angezeigte Webhook-URL, mit `https://` | FF Agent muss sie von außen erreichen |
   | Basis-Authentifizierung | leer | wird nicht genutzt |
   | Header | optional, nur für die Token-Absicherung: `X-FF-Agent-Token` = angezeigtes Token | Erst eintragen und in der Diagnose prüfen, dann die Pflicht einschalten (siehe nächster Abschnitt). |
   | Inhalt / Query-Parameter | leer | Platzhalter mit Einsatzdaten sind nicht belegt |

   FF Agent bricht Aufrufe nach 5 Sekunden ab. Home Assistant antwortet sofort.
5. **Testen.** Einen Testalarm auslösen lassen (Testalarme sind an). Danach muss in Home
   Assistant die Event-Entität „Alarm“ einen neuen Zeitstempel zeigen und „Alarm aktiv“
   einschalten.

Ein Hinweis zu Mehrfachaufrufen: Mehrere Aufrufe innerhalb von 30 Sekunden nach dem
letzten anerkannten Alarm zählen als ein Alarm. Du darfst bis zu drei Webhooks in FF Agent
auf dieselbe Adresse zeigen lassen.

## Optionale Token-Absicherung

<!-- docs-installation-parameters -->

Die Webhook-URL allein ist das Geheimnis. Wer sie kennt, kann **ohne Token-Pflicht** einen
falschen „Alarm aktiv“ auslösen. Hängst du sicherheitsrelevante Aktionen an den Alarm (Tor
öffnen, Tür entriegeln), schalte die Token-Pflicht ein. Die Integration erzeugt dafür bei
der Einrichtung immer ein Token.

1. Öffne beim Eintrag *Konfigurieren*. Dort stehen Header-Name `X-FF-Agent-Token` und das
   Token.
2. Trage in FF Agent im Webhook einen Header mit diesem Namen und Wert ein.
3. Löse einen Testalarm aus und lade die Diagnose herunter. Unter `stats` →
   `last_call` → `header_names` muss `x-ff-agent-token` stehen.
4. Schalte erst dann in den Optionen „Zusatz-Token verlangen“ ein.

Aufrufe ohne gültiges Token beantwortet Home Assistant mit 401 und verwirft sie. Dazu
erscheint eine Reparatur-Meldung („FF-Agent-Webhook-Aufruf abgelehnt“), die beim nächsten
angenommenen Aufruf verschwindet. Ein abgelehnter Alarm soll nicht unbemerkt bleiben.

Die Option ist standardmäßig **aus**, weil nicht belegt ist, dass Nabu Casa eigene Header
durchreicht. Kommt der Header dort nicht an, würde jeder Alarm verworfen. Zeigt die
Diagnose den Header nicht, lass die Option aus.

## Optionen

<!-- docs-configuration-parameters -->

*Einstellungen → Geräte & Dienste → FF Agent → Konfigurieren.* Oben zeigt der Dialog die
aktuelle Webhook-URL, die Art der Adresse, den Header-Namen und das Token.

| Option | Bedeutung |
|---|---|
| Zusatz-Token verlangen | Wie oben. Standard: aus. |
| Rücksetzzeit „Alarm aktiv“ | Minuten ohne neuen Alarm, nach denen „Alarm aktiv“ ausgeht (1 bis 1440, Standard 30). Ein neuer Alarm startet die Zeit neu. |
| Standard-Verkehrsmittel | Wird beim Zusagen gesendet, wenn die Action keines angibt. Zur Auswahl steht nur „Auto“. |
| Standort-Entität | Optional: eine Person oder ein Gerät-Tracker. Sein Standort wird beim Zusagen mitgesendet. Leer lassen, um keinen Standort zu senden. |

**Wichtig:** Das Speichern der Optionen lädt die Integration neu. Ein gerade aktiver Alarm
wird dabei **zurückgesetzt** („Alarm aktiv“ geht aus, das Zeitfenster gegen Doppelalarme
ist wieder offen). Ändere Optionen deshalb nicht mitten in einem Einsatz.

## Neu konfigurieren

<!-- docs-configuration-parameters -->

*Einstellungen → Geräte & Dienste → FF Agent → Drei-Punkte-Menü → Neu konfigurieren.*

- **Neue Rückmelde-URL (Zusage):** Nur ausfüllen, wenn sich die URL geändert hat, zum
  Beispiel nach dem Neuerzeugen der UUID in FF Agent. Leer bedeutet unverändert. Die
  bisherige URL wird nicht angezeigt. Gehört die neue URL zu einer anderen vorhandenen
  Einrichtung, bricht der Dialog ab.
- **Webhook-Zugang neu erzeugen:** Erzeugt eine neue Webhook-Adresse und ein neues Token.
  Der alte Zugang funktioniert danach nicht mehr. Der Dialog zeigt die neuen Werte; trage
  sie in FF Agent ein. Ist die Token-Pflicht an, lehnt Home Assistant Alarme ab, bis der
  neue Header in FF Agent steht. Sinnvoll, wenn die Adresse bekannt geworden ist oder wenn
  erst nach der Einrichtung eine externe URL oder Nabu Casa dazukam.

Auch ein Reconfigure mit Änderung **lädt die Integration neu und setzt einen laufenden
Alarm zurück.**

## Entitäten

<!-- docs-supported-functions -->

Alle Entitäten gehören zu einem Gerät je Eintrag (Typ Dienst).

| Entität | Art | Verhalten |
|---|---|---|
| Alarm | Event | Event-Typ `alarm` bei jedem neuen Alarm. Der **empfohlene Trigger** für Automationen. |
| Alarm aktiv | Binary-Sensor | An beim Alarm, aus nach der Rücksetzzeit. Nach einem Neustart oder Reload aus. |
| Letzter Alarm | Sensor (Zeitstempel) | Zeitpunkt des letzten Alarms. Bleibt nach einem Neustart erhalten. |
| Letzte Rückmeldung | Sensor | `Zugesagt`, `Abgesagt` oder `Fehlgeschlagen` |
| Zusagen | Button | Sagt mit Standard-Verkehrsmittel und optional Standort zu |
| Absagen | Button | Sagt ab |

Die Entity-IDs beginnen mit dem Namen des Eintrags, zum Beispiel
`event.ff_agent_alarm` und `binary_sensor.ff_agent_alarm_aktiv`. Der Rest hängt von Name
und Sprache ab. Suche sie unter *Einstellungen → Geräte & Dienste → FF Agent → Gerät* und
wähle Entitäten in Automationen über die Oberfläche aus, statt IDs abzutippen.

**Pflichtfilter für Automationen auf die Event-Entität:** Ein `state`-Trigger braucht immer
`not_from: [unavailable, unknown]` und `not_to: [unavailable, unknown]`. Bei jedem Reload
und jedem Neustart wird die Event-Entität kurz `unavailable` und stellt danach den alten
Zeitstempel wieder her. Ohne die Filter hielte die Automation das für einen neuen Alarm
und würde auslösen, etwa nach dem Speichern der Optionen.

## Actions

<!-- docs-actions -->

Beide Actions brauchen die ID des Eintrags (`config_entry_id`). Wähle ihn in der
Oberfläche über die Auswahl „Eintrag“.

- **`ff_agent.accept`** (Zusagen)
  - `config_entry_id` (Pflicht): der Eintrag der Person, die zusagt
  - `transport` (optional): Verkehrsmittel, nur `car` (Auto). Ohne Angabe gilt das Standard-Verkehrsmittel
    aus den Optionen. Home Assistant speichert `car`, an FF Agent geht `CAR`. Nur dieser Wert ist
    belegt.
  - `latitude` und `longitude` (optional): Standort, nur beide zusammen. Ohne Angabe wird
    der Standort der Standort-Entität aus den Optionen gesendet, falls gesetzt, sonst kein
    Standort.
- **`ff_agent.reject`** (Absagen)
  - `config_entry_id` (Pflicht)

Die Rückmeldung bezieht sich auf den **aktuellen Einsatz** in FF Agent. Schlägt sie fehl,
melden die Buttons und Actions einen Fehler („FF Agent war nicht erreichbar …“ bzw. „FF
Agent hat mit dem HTTP-Status … geantwortet“). Eine gleiche Rückmeldung innerhalb von 10
Sekunden nach einem Erfolg wird ohne zweiten Aufruf übersprungen.

**Eine Antwort 2xx von FF Agent heißt nur „gesendet“, nicht sicher „verbucht“.** Wie FF
Agent auf eine ungültige UUID oder einen fehlenden Einsatz antwortet, ist ungeprüft.
Kontrolliere wichtige Rückmeldungen in FF Agent.

## Beispiel-Automationen

<!-- docs-examples -->

Ersetze die Entity-IDs und `<ENTRY_ID>` durch deine Werte. Wähle sie am besten in der
Automations-Oberfläche aus.

### 1. Bei Alarm Licht einschalten

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

### 2. Benachrichtigung mit Knopf „Zusagen“ (Companion-App)

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

- Für die Absage denselben zweiten Block mit `FF_AGENT_REJECT` und `ff_agent.reject`
  anlegen.
- Optionale Felder bei `ff_agent.accept`: `transport: car` (einziger belegter Wert) sowie
  `latitude` und `longitude`, nur beide zusammen.
- Ist in FF Agent „auch für Testalarme“ an, lösen Testalarme die Automation ebenfalls aus.
- Der Standort wird nur gesendet, wenn er angegeben ist oder in den Optionen eine
  Standort-Entität gesetzt ist.

## Datenschutz

**Geheimnisse.** Webhook-URL, Token und Rückmelde-URL sind Geheimnisse.

- Wer die **Webhook-URL** kennt, kann ohne Token-Pflicht „Alarm aktiv“ auslösen und damit
  deine Automationen starten.
- Wer die **Rückmelde-URL** kennt, kann in deinem Namen zu- oder absagen.
- Abhilfe: *Neu konfigurieren → Webhook-Zugang neu erzeugen* (neue URL und neues Token,
  Token-Pflicht einschalten) bzw. in FF Agent eine neue Rückmelde-URL erzeugen und sie
  unter *Neu konfigurieren* eintragen.
- Teile keine Screenshots der Optionen oder des Abschlussdialogs.

**Was gespeichert wird.** Rückmelde-UUID, Host, Webhook-ID, Cloudhook-URL und Token stehen
nur im Config-Eintrag. Von eingehenden Aufrufen wird nur die **Form** erfasst (Methode,
Header-Namen, Schlüssel, Typen, Längen), nie Werte. Kein Geheimnis erscheint in Entitäts-
attributen, Entity-Unique-IDs oder den Logs der Integration. Die Diagnose ist redigiert.

**Home-Assistant-Logs.** Teile Home-Assistant-Logs nie ungeprüft. Die Webhook-ID kann auch
in normalen Warn- und Fehlermeldungen von Home Assistant stehen, z. B. bei einem Aufruf
an eine alte Webhook-Adresse nach „Webhook-Zugang neu erzeugen“. Debug-Logs von
`homeassistant.components.webhook`, `.http`, `.websocket_api` und `homeassistant.core`
enthalten zusätzlich Dialoginhalte und Standortdaten. Das liegt in Home Assistant selbst.

**Recorder.** Der Recorder speichert Alarmzeitpunkte und Rückmeldungen. Auch das sind
personenbezogene Daten. Willst du sie nicht in der Datenbank haben, schließe die Entitäten
aus. Beispiel für `configuration.yaml`:

```yaml
recorder:
  exclude:
    entity_globs:
      - "*<name_des_eintrags>*"  # beim Standardnamen "FF Agent": "*ff_agent*"
```

Der Glob muss zum Namen deines Eintrags passen (siehe Einrichtung, Schritt 2), denn die
Entity-IDs beginnen mit dem Namen des Eintrags in Kleinbuchstaben und mit Unterstrichen.
Beim Standardnamen „FF Agent“ ist das `*ff_agent*`; heißt dein Eintrag anders, setze den
passenden Namen ein oder liste die IDs einzeln unter `entities:` auf. So findest du sie: *Einstellungen →
Geräte & Dienste → FF Agent → Gerät → Entitäten*, oder *Einstellungen → Entitäten* mit der
Suche nach dem Namen des Eintrags. Es sind sechs Entitäten (Binary-Sensor, Event,
zwei Sensoren, zwei Buttons).

## Bekannte Einschränkungen

<!-- docs-known-limitations -->

- Der Webhook trägt keinen Inhalt. Testalarm, stiller Einsatz und echter Alarm sind in
  Home Assistant nicht unterscheidbar.
- Auslöse-Filter und Zeitplan liegen in FF Agent. Was dort abgewählt ist, sieht Home
  Assistant nicht.
- Die Token-Prüfung über Nabu Casa funktioniert erst, wenn der Header nachweislich
  ankommt (siehe Diagnose).
- Ein Neustart, ein Reload, das Speichern der Optionen und ein Reconfigure setzen „Alarm
  aktiv“ zurück. Wiederhergestellt wird nur „Letzter Alarm“.
- Als Verkehrsmittel ist nur `car` (an FF Agent `CAR`) belegt.
- Die Rückmeldung gilt für den aktiven Einsatz.
- Erfolg heißt „HTTP 2xx“, nicht unbedingt „von FF Agent verbucht“.
- Kein Reauth-Flow: Eine ungültige Rückmelde-UUID erkennt die Integration erst an einem
  Fehler beim Zusagen, oder gar nicht, falls FF Agent auch dann mit 2xx antwortet
  (ungeprüft, Annahme A7).
- Einige Annahmen zum Verhalten von FF Agent (etwa Wiederholungen bei Fehlern) sind noch
  nicht in einem echten Test bestätigt.

## Optional: iCal über Remote Calendar

<!-- docs-examples -->

Die Integration baut keinen eigenen Kalenderabruf. FF Agent bietet laut Dokumentation einen
persönlichen iCal-Feed, der Einsätze enthält, an denen du teilgenommen hast. Für einen
laufenden Alarm taugt er vermutlich nicht, für den Verlauf schon. Binde ihn über die
Core-Integration **Remote Calendar** ein (ab Home Assistant 2025.4, unterstützt
Basic-Auth, Aktualisierung alle 24 Stunden oder per `homeassistant.update_entity`).

**Recorder-Warnung:** Kalender-Attribute können Ort und Beschreibung des Einsatzes
enthalten und landen im Recorder. Schließe die Kalender-Entität bei Bedarf aus, wie oben
gezeigt.

## Entfernen

<!-- docs-removal-instructions -->

1. *Einstellungen → Geräte & Dienste → FF Agent → Drei-Punkte-Menü → Löschen.* Ein
   Nabu-Casa-Cloudhook wird dabei mitgelöscht.
2. In FF Agent den persönlichen Webhook löschen (*Automatisierung → Persönliche
   Webhooks*).
3. Bei Bedarf in FF Agent die Rückmelde-URL neu erzeugen, damit die alte ungültig wird.
4. HACS: Integration in HACS entfernen und Home Assistant neu starten.

## Fehlerbehebung

<!-- docs-troubleshooting -->

**Diagnose herunterladen:** *Einstellungen → Geräte & Dienste → FF Agent → Drei-Punkte-Menü
→ Diagnose herunterladen.* Sie enthält keine Geheimnisse und zeigt unter anderem
`url_kind`, `calls_total`, `rejected_total`, die Form des letzten Aufrufs und das Ergebnis
der letzten Rückmeldung (ohne Adresse).

**„Alarm kommt nicht an“**

- Art der Adresse (`url_kind`): `internal` oder `path_only` erreicht FF Agent nicht. Externe
  URL oder Nabu Casa einrichten, dann *Neu konfigurieren → Webhook-Zugang neu erzeugen*.
- In FF Agent: Webhook auf „Aktiv“, URL mit `https://`, Methode GET oder POST,
  Auslöse-Filter (Testalarme, Infoalarme, stille Einsätze) und Zeitplan prüfen.
- `calls_total` in der Diagnose: Zählt er nicht hoch, wurde kein Aufruf angenommen. Abgelehnte
  Aufrufe zählen nur in `rejected_total`. Steigt weder `calls_total` noch `rejected_total`,
  kommt der Aufruf nicht bei Home Assistant an.
- `rejected_total` und Reparatur-Meldung: Ist die Token-Pflicht an und der Header fehlt
  oder ist falsch, wird der Alarm abgelehnt. Header in FF Agent prüfen oder die Pflicht
  ausschalten, besonders bei Nabu Casa.
- Mehrfach-Alarme innerhalb von 30 Sekunden zählen als einer (`deduplicated_total`).

**Automation löst nach Reload oder Neustart aus:** Die Filter `not_from`/`not_to` fehlen
(siehe Entitäten).

**„Alarm aktiv“ ging unerwartet aus:** Ein Neustart, Reload, Speichern der Optionen oder
ein Reconfigure setzt den Zustand zurück.

**Zusage meldet einen Fehler:** Prüfe die Internetverbindung und, ob in FF Agent für den
aktuellen Einsatz eine Rückmeldung möglich ist. Prüfe außerdem, ob die Rückmelde-URL noch
gilt (*Neu konfigurieren*).

**„Das ist keine gültige Rückmelde-URL“:** Die URL muss `/app2/missionreplies/` enthalten
und auf `/accept` oder `/reject` enden, oder eine blanke UUID sein.

**Fehler melden:** Öffne ein Issue im Repository. Hänge nur die Diagnose an, **keine
Logs** (siehe Datenschutz).

## Entwicklung

Das Projekt wird mit Claude Code nach einem Rollenmodell entwickelt (Projektleiter,
Architekt, Researcher, Entwickler, Tester, Reviewer, Doku). Einstieg:
[CLAUDE.md](CLAUDE.md) und [docs/orchestrierung.md](docs/orchestrierung.md). Stand der
Quality Scale: [docs/quality-scale.md](docs/quality-scale.md).

## Lizenz

MIT, siehe [LICENSE](LICENSE).

## English summary

Unofficial Home Assistant custom integration (HACS) for **FF Agent**, an alerting app for
fire brigades and emergency services. It is not affiliated with the vendor. The repository
is still private, so HACS installation works only after publication.

- **What it does:** FF Agent calls a personal webhook in Home Assistant on every alarm. The
  integration exposes an `Alarm` event entity (use it as automation trigger), an "Alarm
  active" binary sensor with a configurable reset time, the time of the last alarm, and
  accept/decline buttons and actions (`ff_agent.accept`, `ff_agent.reject`) that call your
  personal reply URL.
- **What it does not do:** trigger alarms, provide mission details, or tell test alarms from
  real ones.
- **Setup:** copy your accept URL from FF Agent into the config flow, then create a generic
  webhook (method POST) in FF Agent with the URL shown by Home Assistant. Home Assistant must
  be reachable from the internet (Nabu Casa or an external HTTPS URL). An optional header
  token (`X-FF-Agent-Token`) hardens the webhook.
- **Automations on the event entity need** `not_from` and `not_to: [unavailable, unknown]`,
  otherwise every reload or restart triggers them.
- **Privacy:** the webhook URL, token and reply URL are secrets. Saving options or
  reconfiguring reloads the integration and resets a running alarm. Never share Home Assistant
  logs unchecked (the webhook ID can appear in normal warnings; debug logs of `webhook`,
  `http`, `websocket_api` and `core` add dialog contents and locations). Consider excluding the entities from the recorder.
- The user interface and this documentation are in German; English UI strings are included.
- License: MIT.
