# FF Agent für Home Assistant

Custom-Integration für [Home Assistant](https://www.home-assistant.io/), installierbar
über [HACS](https://hacs.xyz/), die **FF Agent** (Alarmierungs- und Einsatzsoftware für
Feuerwehren und Hilfsorganisationen) in Home Assistant verfügbar macht.

> **Inoffizielles Community-Projekt, nicht mit dem Hersteller von FF Agent verbunden.**
>
> **Vorabversion 0.2.0:** noch nicht gegen ein echtes FF Agent getestet. In HACS bei
> „FF Agent“ die Anzeige von Beta-/Vorabversionen aktivieren, um sie zu installieren.

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

So funktioniert es: FF Agent ruft bei einem Alarm einen **persönlichen Webhook** auf. Er
zeigt entweder direkt auf Home Assistant (über Home Assistant Cloud oder eine eigene
Internetadresse) oder auf den kostenlosen Dienst **ntfy**, bei dem Home Assistant den Alarm
abholt. Für Zusage und Absage ruft Home Assistant deine **persönliche Rückmelde-URL** von FF
Agent auf. Daten kommen ausschließlich per Push von FF Agent, es gibt kein Abfragen.

## Voraussetzungen

<!-- docs-installation-instructions -->

- ein FF-Agent-Konto mit Zugriff auf „Automatisierung“ in der Web-UI
- Home Assistant 2026.3.0 oder neuer
- für den Alarm **eins von beiden** (siehe [Wie kommt der Alarm an?](#wie-kommt-der-alarm-an)):
  - Home Assistant ist **aus dem Internet erreichbar**: Home Assistant Cloud (Nabu Casa)
    oder eine eigene Internetadresse mit HTTPS, oder
  - die Core-Integration **ntfy** (kostenlos, Home Assistant muss dafür nicht von außen
    erreichbar sein)
- Zusage und Absage funktionieren auch ohne beides.

## Installation

<!-- docs-installation-instructions -->

**Über HACS (Custom Repository):**

1. In HACS oben rechts das Menü (⋮) öffnen, *Benutzerdefinierte Repositories* wählen, die
   URL `https://github.com/rauchstefan/ha-ff-agent` eintragen und als Typ „Integration“
   hinzufügen.
2. „FF Agent“ öffnen. Solange es nur Vorabversionen gibt (aktuell 0.2.0): im Menü (⋮) bzw. in den
   Einstellungen des Repositorys Beta-/Vorabversionen aktivieren. Dann herunterladen und Home
   Assistant neu starten.
   **Nach jedem Update:** Home Assistant neu starten und die Seite im Browser hart neu
   laden (Strg+F5, am Mac Cmd+Umschalt+R). In der Companion-App die App neu starten bzw.
   den Frontend-Cache in den App-Einstellungen leeren.
3. Unter *Einstellungen → Geräte & Dienste → Integration hinzufügen* „FF Agent“ wählen.

**Manuell:**

1. Den Ordner `custom_components/ff_agent` in das Verzeichnis `custom_components` deiner
   Home-Assistant-Konfiguration kopieren.
2. Home Assistant neu starten.
   **Nach jedem Update:** Home Assistant neu starten und die Seite im Browser hart neu
   laden (Strg+F5, am Mac Cmd+Umschalt+R). In der Companion-App die App neu starten bzw.
   den Frontend-Cache in den App-Einstellungen leeren.
3. Die Integration wie oben hinzufügen.

## Wie kommt der Alarm an?

<!-- docs-high-level-description -->

Bei einem Alarm muss FF Agent deinem Home Assistant Bescheid geben. Dafür gibt es zwei
Wege; die Einrichtung fragt dich danach („Nutzt du Home Assistant Cloud?“) und führt dich
Schritt für Schritt durch den gewählten Weg. Wechseln kannst du später jederzeit unter
*Neu konfigurieren*.

- **Empfohlen: Home Assistant Cloud**, wenn du sie hast. Der Alarm kommt direkt, ohne
  weiteren Dienst, und du kannst das Zusatz-Token nutzen. Eine eigene Internetadresse geht
  genauso.
- **Kostenlose Alternative: ntfy.** FF Agent schickt den Alarm an den Dienst ntfy.sh, die
  Integration ntfy in Home Assistant holt ihn ab.

| Weg | Kosten | Von außen erreichbar | Zusatz-Token | Dritter sieht Alarmzeitpunkte |
|---|---|---|---|---|
| Direkt (Webhook) | Home Assistant Cloud: Abo; eigene Adresse: eigener Aufwand | ja | ja | Home Assistant Cloud (bei Cloud-Nutzung) |
| ntfy | kostenlos | nein | nein | ntfy.sh |

## Einrichtung Schritt für Schritt

<!-- docs-installation-parameters -->

1. **Rückmelde-URL kopieren.** In der FF-Agent-Web-UI unter *Personen → (dein Name) →
   Bereich „Übung/Einsatz“ → „Weblinks für Einsatzmeldung“* (die Seite heißt „URLs für
   Einsatzmeldung“) die Zusage-URL kopieren. Sie sieht so aus:
   `https://www.ff-agent.com/app2/missionreplies/<REPLY_ID>/accept?transport=CAR`.
   Akzeptiert werden auch die Absage-URL oder die blanke UUID. Die URLs gelten nur für diese
   Person und beziehen sich auf den jeweils aktiven Einsatz.
2. **Integration hinzufügen.** In Home Assistant *Integration hinzufügen → FF Agent*. Felder:
   - **Name:** Bezeichnung dieser Einrichtung, zum Beispiel dein Name. Der Name wird zum
     Gerätenamen und damit Teil der Entity-IDs.
   - **Rückmelde-URL (Zusage):** die kopierte URL.

   Die Integration sendet dabei **nichts** an FF Agent, denn jeder Test wäre eine echte
   Zusage.
3. **Zusage-Einstellungen wählen.** Der Schritt „Zusage: Verkehrsmittel und Standort“ fragt:
   - **Standard-Verkehrsmittel:** „Auto“, „Zu Fuß“ oder „Fahrrad“. Es wird bei jeder
     Zusage mitgesendet, wenn die Action keines angibt.
   - **Standort-Entität (optional):** eine Person oder ein Gerät-Tracker. Sein aktueller
     Standort wird bei jeder Zusage mitgesendet. Leer lassen, um keinen Standort zu senden.

   Die Rückmelde-URL aus Schritt 2 bleibt dabei unverändert und wird nicht gespeichert.
   Die Integration hängt Verkehrsmittel und Standort bei jeder Zusage an. Jetzt wird nichts
   gesendet. Beide Angaben änderst du später unter *Konfigurieren*.
4. **Alarmweg wählen.** Auf die Frage „Nutzt du Home Assistant Cloud?“ antwortest du mit
   „Ja (empfohlen)“ (weiter mit [Weg A](#weg-a-home-assistant-cloud-oder-eigene-adresse))
   oder „Nein“ (Hinweis auf ntfy, weiter mit [Weg B](#weg-b-ntfy-kostenlos)). Ist Home
   Assistant Cloud schon aktiv, sagt die Frage das, entscheidet aber nicht für dich.

### Weg A: Home Assistant Cloud oder eigene Adresse

1. **Erreichbarkeit.** Mit „Ja“ prüft die Einrichtung, wie Home Assistant erreichbar ist:
   - Home Assistant Cloud verbunden: Es entsteht eine Cloudhook-URL, zum Beispiel
     `https://hooks.nabu.casa/<...>`.
   - eigene Internetadresse (unter *Einstellungen → System → Netzwerk*):
     `https://<deine-externe-url>/api/webhook/<WEBHOOK_ID>`. Ist zugleich ein
     Home-Assistant-Cloud-Abo aktiv, verwendet die Einrichtung die Cloud-Adresse, auch
     über die Option „Ich habe eine eigene Internetadresse“.
   - Home Assistant Cloud eingerichtet, aber nicht verbunden: Der Dialog zeigt, was zu
     prüfen ist, mit „Erneut versuchen“ und „Stattdessen ntfy nutzen“.
   - Nichts davon: Der Einrichtungsdialog „Home Assistant Cloud einrichten“ führt in
     nummerierten Schritten zur Cloud-Seite deines Home Assistant (Link im Dialog), zur
     Anmeldung und zurück zu „Erneut prüfen“. Die Cloud ist ein kostenpflichtiges Abo, das
     du zunächst kostenlos testen kannst. Ab Dezember 2026 heißt sie „Home Assistant
     Link“. Statt der Cloud kannst du auch eine eigene Internetadresse eintragen.
   - Keine Sackgasse: „Stattdessen ntfy nutzen“ wechselt zu Weg B. „Trotzdem fortfahren“
     speichert die Einrichtung ohne Alarm; Zusagen und Absagen funktionieren, den Alarm
     rüstest du später unter *Neu konfigurieren* nach.

   Hinweis zu DS-Lite-Anschlüssen (viele Kabel- und Glasfaseranschlüsse): Dort ist eine
   Portfreigabe aus dem Internet meist nicht möglich. Nimm dann Home Assistant Cloud oder
   ntfy.
2. **Webhook in FF Agent anlegen.** In der FF-Agent-Web-UI *Automatisierung → Persönliche
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
3. **Testen.** Einen Testalarm auslösen lassen (Testalarme sind an). Danach muss in Home
   Assistant die Event-Entität „Alarm“ einen neuen Zeitstempel zeigen und „Alarm aktiv“
   einschalten.

Ein Hinweis zu Mehrfachaufrufen: Mehrere Aufrufe innerhalb von 30 Sekunden nach dem
letzten anerkannten Alarm zählen als ein Alarm. Du darfst bis zu drei Webhooks in FF Agent
auf dieselbe Adresse zeigen lassen.

### Weg B: ntfy (kostenlos)

Der Einrichtungsdialog „Alarm über ntfy einrichten“ zeigt ein zufälliges, geheimes
**Thema** (32 Zeichen) und die fertige Adresse für FF Agent. Öffne die Links im Dialog am
besten in einem neuen Tab und lass den Dialog offen.

1. **Integration ntfy hinzufügen** (Link im Dialog). Die Dienst-URL `https://ntfy.sh`
   lässt du unverändert, Benutzername und Passwort bleiben leer. Ist ntfy schon
   eingerichtet, öffne die Integration ntfy und wähle „Thema hinzufügen“.
2. **Thema abonnieren:** „Thema eingeben“, das angezeigte Thema einfügen, als Anzeigename
   „FF Agent Alarm“. Ohne Anzeigenamen erscheint das geheime Thema als Name der Entität.
3. **In FF Agent einen Generischen Webhook anlegen** (*Automatisierung → Persönliche
   Webhooks → Webhook hinzufügen*): Type Alarm, Methode **GET**, URL
   `https://ntfy.sh/<thema>/trigger` (genau wie im Dialog angezeigt), Aktiv an, auch für
   Testalarme an (zum Testen), auch für Infoalarme aus, Zeitplan aus. Basis-Authentifizierung,
   Header, Inhalt und Query-Parameter bleiben **leer**.
4. **In der FF-Agent-Einrichtung „Erledigt“ wählen.** Die Integration sucht die Entität des
   Themas selbst. Nur wenn sie nichts findet, wählst du sie aus (oder ein Thema, das du
   schon abonniert hast). Der Abschlussdialog wiederholt die Werte nur, wenn die gewählte
   Entität eine andere Adresse hat als angezeigt.
5. **Mit einem Testalarm prüfen:** „Alarm aktiv“ springt an.

Die Reihenfolge ist wichtig: Erst abonnieren, dann in FF Agent eintragen. ntfy liefert
keine Meldung nach, die vor dem Abo kam. Auch „Doch Home Assistant Cloud nutzen“ ist im
Dialog jederzeit möglich.

## Optionale Token-Absicherung

<!-- docs-installation-parameters -->

Nur bei Weg A. Bei ntfy kommen eigene Header nicht beim Abonnenten an, dort ist das Thema
der einzige Schutz.

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
aktuelle Webhook-URL, die Art der Adresse, den Header-Namen und das Token. Bei ntfy zeigt
er stattdessen die ntfy-Entität und die Adresse für FF Agent; den Schalter
„Zusatz-Token verlangen“ gibt es dort nicht (ein gesetzter Wert bleibt für einen Wechsel
zurück erhalten).

| Option | Bedeutung |
|---|---|
| Zusatz-Token verlangen | Wie oben. Standard: aus. |
| Rücksetzzeit „Alarm aktiv“ | Minuten ohne neuen Alarm, nach denen „Alarm aktiv“ ausgeht (1 bis 1440, Standard 30). Ein neuer Alarm startet die Zeit neu. |
| Standard-Verkehrsmittel | Wird beim Zusagen gesendet, wenn die Action keines angibt. Zur Auswahl stehen „Auto“, „Zu Fuß“ und „Fahrrad“. |
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
- **Wie bekommt Home Assistant den Alarm?** Über Home Assistant Cloud oder eine eigene
  Internetadresse (empfohlen; Voraussetzung: ein Cloud-Abo oder eine aus dem Internet
  erreichbare Adresse, also IP-Adresse oder Domain) oder kostenlos über ntfy (kein Abo,
  Home Assistant muss nicht aus dem Internet erreichbar sein). Beim
  Wechsel führt dich derselbe Einrichtungsdialog wie bei der Einrichtung durch die
  Schritte. Danach den alten Webhook in FF Agent löschen. Ein Cloudhook wird beim Wechsel
  zu ntfy gelöscht. Bleibst du bei ntfy und änderst nur die Rückmelde-URL, speichert der
  Dialog direkt, ohne den ntfy-Dialog.
- **Neue geheime Adresse erzeugen:** Beim direkten Weg eine neue Webhook-Adresse und ein
  neues Token, bei ntfy ein neues Thema (die ruhende Webhook-Adresse und das Token werden
  dabei ebenfalls erneuert). Die alte Adresse funktioniert danach nicht mehr.
  Der Dialog zeigt die neuen Werte; trage sie in FF Agent ein. Ist die Token-Pflicht an,
  lehnt Home Assistant Alarme ab, bis der neue Header in FF Agent steht. Sinnvoll, wenn die
  Adresse bekannt geworden ist.
- Wurde die Einrichtung mit „Trotzdem fortfahren“ gespeichert (nur interne Adresse), und
  du hast inzwischen Home Assistant Cloud oder eine eigene Adresse: einfach *Neu
  konfigurieren* öffnen und speichern. Die Einrichtung erzeugt dann die erreichbare Adresse.

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
| Alarm zurücksetzen | Button | Schaltet „Alarm aktiv“ sofort aus und beendet die Rücksetzzeit. „Letzter Alarm“ bleibt, und das 30-Sekunden-Fenster gegen Doppelalarme bleibt offen: Eine Wiederholung desselben Alarms schaltet „Alarm aktiv“ nicht wieder ein, ein neuer Alarm danach schon. Ohne aktiven Alarm passiert nichts, an FF Agent wird nichts gesendet. |

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

Alle Actions brauchen die ID des Eintrags (`config_entry_id`). Wähle ihn in der
Oberfläche über die Auswahl „Eintrag“.

- **`ff_agent.accept`** (Zusagen)
  - `config_entry_id` (Pflicht): der Eintrag der Person, die zusagt
  - `transport` (optional): Verkehrsmittel `car` (Auto, Standard), `feet` (zu Fuß) oder
    `bicycle` (Fahrrad). Ohne Angabe gilt das Standard-Verkehrsmittel aus den Optionen.
    Home Assistant speichert die Werte klein geschrieben, an FF Agent gehen `CAR`, `FEET`
    und `BICYCLE`.
  - `latitude` und `longitude` (optional): Standort, nur beide zusammen. Ohne Angabe wird
    der Standort der Standort-Entität aus den Optionen gesendet, falls gesetzt, sonst kein
    Standort.
- **`ff_agent.reject`** (Absagen)
  - `config_entry_id` (Pflicht)
- **`ff_agent.reset_alarm`** (Alarm zurücksetzen)
  - `config_entry_id` (Pflicht): der Eintrag der Person, deren „Alarm aktiv“ ausgehen soll.
    Wirkt wie der Button: kein Aufruf an FF Agent, ohne aktiven Alarm passiert nichts.

Die Rückmeldung bezieht sich auf den **aktuellen Einsatz** in FF Agent. Zu- und Absage
funktionieren nur, wenn die Person für diesen Einsatz alarmiert wurde (wie in der
FF-Agent-App). Schlägt sie fehl, melden die Buttons und Actions einen Fehler („FF Agent
war nicht erreichbar …“ bzw. „FF Agent hat mit dem HTTP-Status … geantwortet“). Eine
gleiche Rückmeldung innerhalb von 10 Sekunden nach einem Erfolg wird ohne zweiten Aufruf
übersprungen.

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
- Optionale Felder bei `ff_agent.accept`: `transport` (`car`, `feet` oder `bicycle`) sowie
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

**Datenschutz bei ntfy.** Jeder Alarm läuft über den Dienst ntfy.sh. Dessen Betreiber
sieht, wann ein Alarm kommt, und speichert die Meldung bis zu 12 Stunden. Einsatzdaten
werden nicht übertragen, solange in FF Agent unter „Inhalt“ und „Query-Parameter“ nichts
eingetragen ist. Das Thema wirkt wie ein Passwort: Wer es kennt, sieht deine
Alarmzeitpunkte und kann falsche Alarme auslösen. Halte es geheim und teile keine
Screenshots der Einrichtung. Die Integration ntfy speichert Thema und Meldung im Verlauf
von Home Assistant und damit auch in Backups. Wer das nicht möchte, schließt ihre Entität
vom Recorder aus:

```yaml
recorder:
  exclude:
    entities:
      - event.ff_agent_alarm  # die Event-Entität deines ntfy-Abos
```

Die Integration FF Agent selbst nennt Thema und Entität nie in Logs, Entitätsattributen oder
der Diagnose.

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
Suche nach dem Namen des Eintrags. Es sind sieben Entitäten (Binary-Sensor, Event,
zwei Sensoren, drei Buttons).

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
- Die Rückmeldung gilt für den aktiven Einsatz. Zu- und Absage funktionieren nur, wenn die
  Person für diesen Einsatz alarmiert wurde. Wie FF Agent sonst antwortet, ist noch nicht
  geprüft (Annahme A7).
- Erfolg heißt „HTTP 2xx“, nicht unbedingt „von FF Agent verbucht“.
- Kein Reauth-Flow: Eine ungültige Rückmelde-UUID erkennt die Integration erst an einem
  Fehler beim Zusagen, oder gar nicht, falls FF Agent auch dann mit 2xx antwortet
  (ungeprüft, Annahme A7).
- Einige Annahmen zum Verhalten von FF Agent (etwa Wiederholungen bei Fehlern) sind noch
  nicht in einem echten Test bestätigt.

**Grenzen von ntfy:**

- Ein Alarm während einer Unterbrechung (Internet weg, Neustart von Home Assistant) geht
  verloren. ntfy liefert nichts nach.
- ntfy.sh ist ein zusätzlicher Ausfallpunkt.
- Bei sehr vielen gleichzeitigen Alarmen ist ein Ratenlimit von ntfy.sh möglich
  (ungeprüft).
- Kein Zusatz-Token: Wer Tore oder Türen an den Alarm hängt, nimmt Weg A mit Token.
- Rest-Risiko Doppelalarm: Wird FF Agent in Home Assistant neu geladen (Optionen, Neu
  konfigurieren), während die ntfy-Verbindung gerade unterbrochen ist, kann ein Alarm aus
  den letzten 60 Sekunden ein zweites Mal als Alarm zählen.
- Rest-Risiko Verlust: Kommt eine Meldung genau in dem Moment an, in dem FF Agent startet
  oder neu lädt (bevor die Integration der ntfy-Entität zuhört), kann ein Alarm verloren
  gehen. Das Zeitfenster ist sehr klein.
- Der Weg über ntfy ist noch nicht gegen ein echtes FF Agent getestet.

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
   Nabu-Casa-Cloudhook wird dabei mitgelöscht. Bei ntfy das Thema in der Integration ntfy
   entfernen, falls du es nicht mehr brauchst.
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

**Dialoge ohne Text oder mit alten Texten:** Die Ursache ist meist der Browser-Cache. Ein
Neustart von Home Assistant allein reicht nicht: Lade die Seite hart neu (Strg+F5, am Mac
Cmd+Umschalt+R). In der Companion-App die App neu starten bzw. den Frontend-Cache in den
App-Einstellungen leeren.

**„Alarm kommt nicht an“**

- Art der Adresse (`url_kind`): `internal` oder `path_only` erreicht FF Agent nicht. Home
  Assistant Cloud oder eine eigene Adresse einrichten und *Neu konfigurieren* speichern,
  oder dort zu ntfy wechseln.
- In FF Agent: Webhook auf „Aktiv“, URL mit `https://`, Methode GET oder POST,
  Auslöse-Filter (Testalarme, Infoalarme, stille Einsätze) und Zeitplan prüfen.
- `calls_total` in der Diagnose: Zählt er nicht hoch, wurde kein Aufruf angenommen. Abgelehnte
  Aufrufe zählen nur in `rejected_total`. Steigt weder `calls_total` noch `rejected_total`,
  kommt der Aufruf nicht bei Home Assistant an.
- `rejected_total` und Reparatur-Meldung: Ist die Token-Pflicht an und der Header fehlt
  oder ist falsch, wird der Alarm abgelehnt. Header in FF Agent prüfen oder die Pflicht
  ausschalten, besonders bei Nabu Casa.
- Mehrfach-Alarme innerhalb von 30 Sekunden zählen als einer (`deduplicated_total`).

**Alarm über ntfy kommt nicht an**

- Reparatur-Meldung „ntfy-Abo für den Alarm fehlt“: Die ntfy-Entität ist gelöscht oder
  deaktiviert. Dasselbe Thema in der Integration ntfy erneut abonnieren; die Einrichtung
  findet das neue Abo über das Thema selbst, lädt neu, und die Meldung verschwindet. Falls
  der Hinweis bleibt (etwa bei einem anderen Thema): unter *Neu konfigurieren* die neue
  Entität wählen.
- Die ntfy-Entität steht auf „nicht verfügbar“: Die Integration ntfy hat keine Verbindung.
  Das zeigt die Integration ntfy selbst.
- Diagnose, Block `ntfy`: `entity_found`, `entity_available`, `events_total` und
  `accepted_total`. `ignored_stale_total` zählt alte Werte, die nach einer Unterbrechung
  wiederhergestellt wurden. `last_event` zeigt nur die Form der letzten Meldung
  (`message_length` sollte 9 sein, „triggered“); ein längerer Text heißt, dass FF Agent
  Inhalte mitschickt.
- In FF Agent: Methode GET und die Adresse aus dem Dialog, Thema exakt gleich.
- Wechsel des Wegs über *Neu konfigurieren*; danach den alten Webhook in FF Agent löschen.

**Automation löst nach Reload oder Neustart aus:** Die Filter `not_from`/`not_to` fehlen
(siehe Entitäten).

**„Alarm aktiv“ ging unerwartet aus:** Ein Neustart, Reload, Speichern der Optionen oder
ein Reconfigure setzt den Zustand zurück. Auch der Button oder die Action „Alarm zurücksetzen“ schaltet ihn aus, wenn jemand sie ausgelöst hat (zum Beispiel eine Automation).

**Zusage meldet einen Fehler:** Prüfe die Internetverbindung und, ob in FF Agent für den
aktuellen Einsatz eine Rückmeldung möglich ist (die Person muss dafür alarmiert worden
sein). Prüfe außerdem, ob die Rückmelde-URL noch
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
fire brigades and emergency services. It is not affiliated with the vendor. Version 0.2.0
is a pre-release that has not yet been tested against a real FF Agent account.

- **What it does:** FF Agent calls a personal webhook on every alarm. It either points at
  Home Assistant directly (Home Assistant Cloud or your own address, recommended) or at
  the free service ntfy.sh, which the core ntfy integration subscribes to, so Home
  Assistant does not have to be reachable from the internet. The setup asks "Do you use
  Home Assistant Cloud?" and guides you step by step; you can switch later under
  "Reconfigure". The integration exposes an `Alarm` event entity (use it as automation trigger), an "Alarm
  active" binary sensor with a configurable reset time, the time of the last alarm, and
  accept/decline buttons and actions (`ff_agent.accept`, `ff_agent.reject`) that call your
  personal reply URL, and a "Reset alarm" button and action (`ff_agent.reset_alarm`) that
  switches "Alarm active" off by hand without contacting FF Agent.
- **What it does not do:** trigger alarms, provide mission details, or tell test alarms from
  real ones.
- **Setup:** copy your accept URL from FF Agent into the config flow, then create a generic
  webhook in FF Agent with the URL shown by Home Assistant (method POST for the direct way,
  GET on `https://ntfy.sh/<topic>/trigger` for ntfy). An optional header token
  (`X-FF-Agent-Token`) hardens the direct webhook. With ntfy, the topic is the only
  secret; ntfy.sh sees when you are alerted, and an alarm during an outage is lost.
- **Automations on the event entity need** `not_from` and `not_to: [unavailable, unknown]`,
  otherwise every reload or restart triggers them.
- **Privacy:** the webhook URL, token and reply URL are secrets. Saving options or
  reconfiguring reloads the integration and resets a running alarm. Never share Home Assistant
  logs unchecked (the webhook ID can appear in normal warnings; debug logs of `webhook`,
  `http`, `websocket_api` and `core` add dialog contents and locations). Consider excluding the entities from the recorder.
- The user interface and this documentation are in German; English UI strings are included.
- License: MIT.
