# FF Agent für Home Assistant / FF Agent for Home Assistant

<img src="https://raw.githubusercontent.com/rauchstefan/ha-ff-agent/main/custom_components/ff_agent/brand/icon.png" width="128" alt="ha-ff-agent">

[![GitHub Release][releases-shield]][releases-url]
[![Contributors][contributors-shield]][contributors-url]
[![Issues][issues-shield]][issues-url]
[![Discussions][discussions-shield]][discussions-url]
[![HACS Custom][hacs-shield]][hacs-url]
[![Tests][ci-shield]][ci-url]

[![License: MIT][license-shield]][license-url]
![Made with Python][python-shield]

[![In HACS öffnen / Open in HACS][my-hacs-badge]][my-hacs-url]

**Deutsch:** Custom-Integration für [Home Assistant](https://www.home-assistant.io/),
installierbar über [HACS](https://hacs.xyz/), die **FF Agent** (Alarmierungs- und
Einsatzsoftware für Feuerwehren und Hilfsorganisationen) in Home Assistant verfügbar macht.

**English:** Custom integration for [Home Assistant](https://www.home-assistant.io/),
installable through [HACS](https://hacs.xyz/), that makes **FF Agent** (alerting and
mission software for fire brigades and emergency services) available in Home Assistant.

> [!NOTE]
> **Inoffizielles Community-Projekt, nicht mit dem Hersteller von FF Agent verbunden.**
> **Unofficial community project, not affiliated with the vendor of FF Agent.**
>
> **Version 1.0.0:** Test- und Echtalarm aus FF Agent kommen an; Zusage und Absage sind
> noch nicht gegen ein echtes FF Agent getestet. / **Version 1.0.0:** Test and real alarms
> from FF Agent arrive; accepting and declining have not yet been tested against a real
> FF Agent.

**Sprache / Language:** [Deutsch](#deutsch) · [English](#english)

---

# Deutsch

Inhalt: [Haftungsausschluss](#haftungsausschluss) · [Was die Integration tut](#was-die-integration-tut-und-was-nicht) ·
[Voraussetzungen](#voraussetzungen) · [Installation](#installation) ·
[Wie kommt der Alarm an?](#wie-kommt-der-alarm-an) ·
[Einrichtung](#einrichtung-schritt-für-schritt) ·
[Token-Absicherung](#optionale-token-absicherung) · [Optionen](#optionen) ·
[Neu konfigurieren](#neu-konfigurieren) · [Entitäten](#entitäten) · [Actions](#actions) ·
[Beispiele](#beispiel-automationen) · [Datenschutz](#datenschutz) ·
[Einschränkungen](#bekannte-einschränkungen) · [iCal](#optional-ical-über-remote-calendar) ·
[Entfernen](#entfernen) · [Fehlerbehebung](#fehlerbehebung) ·
[Probleme melden](#probleme-melden-und-fragen) · [Mitmachen](#mitmachen) ·
[Unterstützen](#unterstützen) · [Links](#weiterführende-links)

## Haftungsausschluss

> [!WARNING]
> Dies ist ein inoffizielles, unabhängiges Community-Projekt und nicht mit dem Anbieter von
> FF Agent verbunden. Marken- und Produktnamen gehören ihren jeweiligen Inhabern. Die
> Nutzung erfolgt auf eigenes Risiko. Die Integration ist **kein Ersatz** für die offizielle
> Alarmierung (Meldeempfänger/App). Es gibt keine Gewähr für Zustellung, Vollständigkeit
> oder Rechtzeitigkeit von Alarmen.

## Was die Integration tut und was nicht

<!-- docs-high-level-description -->
<!-- docs-data-update -->
<!-- docs-use-cases -->

Die Integration richtet sich an **Einsatzkräfte ohne Admin-Rechte in FF Agent**. Eine
Einrichtung gehört zu genau einer Person. Mehrere Personen in einem Haushalt legen mehrere
Einträge an.

**Sie tut:**

- Sie meldet jeden neuen Alarm (nach der Deduplizierung von 30 s) als **Event** an Home
  Assistant. Damit starten Automationen (Licht an, Benachrichtigung, Tor öffnen).
- Sie zeigt „Alarm aktiv“ (mit Rücksetzzeit) und den Zeitpunkt des letzten Alarms.
- Sie sendet **Zusage und Absage** an FF Agent, per Button oder Action.
- Sie schaltet „Alarm aktiv“ auf Wunsch von Hand aus („Alarm zurücksetzen“), ohne FF Agent
  zu kontaktieren.

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

**Mit einem Klick:** Dieser Button öffnet deine eigene Home-Assistant-Instanz und fügt das
Repository in HACS hinzu. Danach dort „FF Agent“ installieren und Home Assistant neu
starten.

[![In HACS öffnen][my-hacs-badge]][my-hacs-url]

**Über HACS (Custom Repository), alternativ von Hand:**

1. In HACS oben rechts das Menü (⋮) öffnen, *Benutzerdefinierte Repositories* wählen, die
   URL `https://github.com/rauchstefan/ha-ff-agent` eintragen und als Typ „Integration“
   hinzufügen.
2. „FF Agent“ öffnen, die neueste Version (aktuell 1.0.0) wählen, herunterladen und
   Home Assistant neu starten.
3. Unter *Einstellungen → Geräte & Dienste → Integration hinzufügen* „FF Agent“ wählen.

**Manuell:**

1. Den Ordner `custom_components/ff_agent` in das Verzeichnis `custom_components` deiner
   Home-Assistant-Konfiguration kopieren.
2. Home Assistant neu starten.
3. Die Integration wie oben hinzufügen.

> [!NOTE]
> **Nach jedem Update** (HACS und manuell): Home Assistant neu starten und die Seite im
> Browser hart neu laden (Strg+F5, am Mac Cmd+Umschalt+R). In der Companion-App die App neu
> starten bzw. den Frontend-Cache in den App-Einstellungen leeren. Sonst zeigen Dialoge der
> Integration unter Umständen keinen oder alten Text.

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
   - **Standortquelle:** woher der Standort kommt, der bei jeder Zusage mitgesendet wird.
     Zur Auswahl stehen:
     - **Kein Standort** (Standard): Es wird kein Standort gesendet.
     - **Zuhause-Position von Home Assistant:** Die Position wird erst beim Zusagen gelesen,
       Änderungen gelten also sofort. Ist in Home Assistant keine Position gesetzt (0/0),
       wird ohne Standort zugesagt.
     - **Koordinaten manuell eingeben:** Im Folgeschritt „Zusage: Koordinaten“ trägst du
       Breitengrad (-90 bis 90) und Längengrad (-180 bis 180) in Dezimalgrad ein. Vorgeschlagen
       wird die Zuhause-Position von Home Assistant; gespeichert wird dann eine feste Kopie.
     - **Person oder Geräte-Tracker (Live-Standort):** Im Folgeschritt wählst du die Entität.
       Ihr aktueller Standort wird bei jeder Zusage mitgesendet. Hat sie gerade keinen
       Standort, wird ohne Standort zugesagt.

   Die Rückmelde-URL bleibt dabei unverändert; gespeichert werden nur UUID und Host.
   Verkehrsmittel und Standortquelle hängt die Integration bei jeder Zusage an. Jetzt wird
   nichts gesendet. Beide Angaben änderst du später unter *Konfigurieren*. Ein Wechsel der
   Quelle löscht die Werte der alten Quelle; andere Optionen bleiben. Bestehende Einträge
   mit einer Standort-Entität laufen unverändert weiter (sie gelten als Live-Standort).
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
     prüfen ist, mit „Erneut versuchen“ und „Stattdessen ntfy nutzen (kostenlos)“.
   - Nichts davon: Der Einrichtungsdialog „Home Assistant Cloud einrichten“ führt in
     nummerierten Schritten zur Cloud-Seite deines Home Assistant (Link im Dialog), zur
     Anmeldung und zurück zu „Erneut prüfen“. Die Cloud ist ein kostenpflichtiges Abo, das
     du zunächst kostenlos testen kannst. Ab Dezember 2026 heißt sie „Home Assistant
     Link“. Statt der Cloud kannst du auch eine eigene Internetadresse eintragen.
   - Keine Sackgasse: „Stattdessen ntfy nutzen (kostenlos)“ wechselt zu Weg B. „Trotzdem fortfahren (nur Zusagen und Absagen, Alarm später nachrüsten)“
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
   | Header | optional, nur für die Token-Absicherung: `X-FF-Agent-Token` = angezeigtes Token | Erst eintragen und in der Diagnose prüfen, dann die Pflicht einschalten (siehe [Token-Absicherung](#optionale-token-absicherung)). |
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
4. **In der FF-Agent-Einrichtung „Erledigt, Entität suchen“ wählen.** Die Integration sucht
   die Entität des Themas selbst. Nur wenn sie nichts findet, wählst du sie aus (oder ein
   Thema, das du schon abonniert hast). Der Abschlussdialog wiederholt die Werte nur, wenn
   die gewählte Entität eine andere Adresse hat als angezeigt.
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
| Standortquelle | „Kein Standort“ (Standard), „Zuhause-Position von Home Assistant“ (wird beim Zusagen gelesen), „Koordinaten manuell eingeben“ (Breiten- und Längengrad in Dezimalgrad) oder „Person oder Geräte-Tracker (Live-Standort)“. Ein Wechsel der Quelle löscht die Werte der alten Quelle. Bestehende Einträge mit Standort-Entität laufen unverändert weiter. |

> [!IMPORTANT]
> Das Speichern der Optionen lädt die Integration neu. Ein gerade aktiver Alarm
> wird dabei **zurückgesetzt** („Alarm aktiv“ geht aus, das Zeitfenster gegen Doppelalarme
> ist wieder offen). Ändere Optionen deshalb nicht mitten in einem Einsatz.

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
  Home Assistant muss nicht aus dem Internet erreichbar sein). Beim Wechsel führt dich
  derselbe Einrichtungsdialog wie bei der Einrichtung durch die Schritte. Danach den alten
  Webhook in FF Agent löschen. Ein Cloudhook wird beim Wechsel zu ntfy gelöscht. Bleibst
  du bei ntfy und änderst nur die Rückmelde-URL, speichert der Dialog direkt, ohne den
  ntfy-Dialog.
- **Neue geheime Adresse erzeugen:** Beim direkten Weg eine neue Webhook-Adresse und ein
  neues Token, bei ntfy ein neues Thema (die ruhende Webhook-Adresse und das Token werden
  dabei ebenfalls erneuert). Die alte Adresse funktioniert danach nicht mehr. Der Dialog
  zeigt die neuen Werte; trage sie in FF Agent ein. Ist die Token-Pflicht an, lehnt Home
  Assistant Alarme ab, bis der neue Header in FF Agent steht. Sinnvoll, wenn die Adresse
  bekannt geworden ist.
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
| Alarm zurücksetzen | Button | Schaltet „Alarm aktiv“ sofort aus und beendet die Rücksetzzeit. „Letzter Alarm“ bleibt, und das 30-Sekunden-Fenster gegen Doppelalarme läuft weiter: Eine Wiederholung desselben Alarms schaltet „Alarm aktiv“ nicht wieder ein, ein neuer Alarm danach schon. Ohne aktiven Alarm passiert nichts, an FF Agent wird nichts gesendet. |

Die Entity-IDs beginnen mit dem Namen des Eintrags, zum Beispiel
`event.ff_agent_alarm` und `binary_sensor.ff_agent_alarm_aktiv`. Der Rest hängt von Name
und Sprache ab. Suche sie unter *Einstellungen → Geräte & Dienste → FF Agent → Gerät* und
wähle Entitäten in Automationen über die Oberfläche aus, statt IDs abzutippen.

> [!IMPORTANT]
> **Pflichtfilter für Automationen auf die Event-Entität:** Ein `state`-Trigger braucht immer
> `not_from: [unavailable, unknown]` und `not_to: [unavailable, unknown]`. Bei jedem Reload
> und jedem Neustart wird die Event-Entität kurz `unavailable` und stellt danach den alten
> Zeitstempel wieder her. Ohne die Filter hielte die Automation das für einen neuen Alarm
> und würde auslösen, etwa nach dem Speichern der Optionen.

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
  - `latitude` und `longitude` (optional): Standort, nur beide zusammen. Er hat Vorrang vor
    der Standortquelle aus den Optionen. Ohne Angabe gilt die Standortquelle aus den
    Optionen; ist keine gewählt, wird kein Standort gesendet.
- **`ff_agent.reject`** (Absagen)
  - `config_entry_id` (Pflicht)
- **`ff_agent.reset_alarm`** (Alarm zurücksetzen)
  - `config_entry_id` (Pflicht): der Eintrag der Person, deren „Alarm aktiv“ ausgehen soll.
    Wirkt wie der Button: kein Aufruf an FF Agent, ohne aktiven Alarm passiert nichts.

Die Rückmeldung bezieht sich auf den **aktuellen Einsatz** in FF Agent. Zu- und Absage
funktionieren nur, wenn die Person für diesen Einsatz alarmiert wurde (wie in der
FF-Agent-App). Schlägt sie fehl, melden die Buttons und Actions einen Fehler („FF Agent
war nicht erreichbar …“ bzw. „FF Agent hat mit dem HTTP-Status … geantwortet“). Die
Wartezeit auf FF Agent beträgt 10 Sekunden. Eine gleiche Rückmeldung innerhalb von
10 Sekunden nach einem Erfolg wird ohne zweiten Aufruf übersprungen.

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
  Standortquelle gewählt ist (nicht „Kein Standort“). Die Absage sendet nie einen Standort.

## Datenschutz

**Geheimnisse.** Webhook-URL, Token, Rückmelde-URL und (bei ntfy) das Thema sind
Geheimnisse.

- Wer die **Webhook-URL** kennt, kann ohne Token-Pflicht „Alarm aktiv“ auslösen und damit
  deine Automationen starten.
- Wer die **Rückmelde-URL** kennt, kann in deinem Namen zu- oder absagen.
- Abhilfe: *Neu konfigurieren → Neue geheime Adresse erzeugen* (neue URL und neues Token,
  Token-Pflicht einschalten) bzw. in FF Agent eine neue Rückmelde-URL erzeugen und sie
  unter *Neu konfigurieren* eintragen.
- Teile keine Screenshots der Optionen oder des Abschlussdialogs.

**Was gespeichert wird.** Rückmelde-UUID, Host, Webhook-ID, Cloudhook-URL und Token stehen
nur im Config-Eintrag. Von eingehenden Aufrufen wird nur die **Form** erfasst (Methode,
Header-Namen, Schlüssel, Typen, Längen), nie Werte. Kein Geheimnis erscheint in
Entitätsattributen, Entity-Unique-IDs oder den Logs der Integration. Die Diagnose ist
redigiert.

**Home-Assistant-Logs.**

> [!WARNING]
> Teile Home-Assistant-Logs nie ungeprüft. Die Webhook-ID kann auch
> in normalen Warn- und Fehlermeldungen von Home Assistant stehen, z. B. bei einem Aufruf
> an eine alte Webhook-Adresse nach „Neue geheime Adresse erzeugen“. Debug-Logs von
> `homeassistant.components.webhook`, `.http`, `.websocket_api` und `homeassistant.core`
> enthalten zusätzlich Dialoginhalte und Standortdaten. Das liegt in Home Assistant selbst.

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
      - event.<deine_ntfy_entität>  # Event-Entität deines ntfy-Abos, ID unter Einstellungen > Entitäten nachsehen
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
passenden Namen ein oder liste die IDs einzeln unter `entities:` auf. So findest du sie:
*Einstellungen → Geräte & Dienste → FF Agent → Gerät → Entitäten*, oder *Einstellungen →
Entitäten* mit der Suche nach dem Namen des Eintrags. Es sind sieben Entitäten
(Binary-Sensor, Event, zwei Sensoren, drei Buttons).

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

## Optional: iCal über Remote Calendar

<!-- docs-examples -->

Die Integration baut keinen eigenen Kalenderabruf. FF Agent bietet laut Dokumentation einen
persönlichen iCal-Feed, der Einsätze enthält, an denen du teilgenommen hast. Für einen
laufenden Alarm taugt er vermutlich nicht, für den Verlauf schon. Binde ihn über die
Core-Integration **Remote Calendar** ein (ab Home Assistant 2025.4, unterstützt
Basic-Auth, Aktualisierung alle 24 Stunden oder per `homeassistant.update_entity`).

> [!WARNING]
> **Recorder-Warnung:** Kalender-Attribute können Ort und Beschreibung des Einsatzes
> enthalten und landen im Recorder. Schließe die Kalender-Entität bei Bedarf aus, wie oben
> gezeigt.

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

**HACS zeigt statt einer Versionsnummer eine Zeichenfolge wie `7192103`:** Die Installation
stammt vom Branch `main` (aus der Zeit, als es nur Vorabversionen gab). Lösung: In HACS bei
„FF Agent“ das Menü (⋮) → *Erneut herunterladen* wählen, Version v0.4.0 (oder neuer) auswählen
und Home Assistant neu starten.

**„Alarm kommt nicht an“**

- Art der Adresse (`url_kind`): `internal` oder `path_only` erreicht FF Agent nicht. Home
  Assistant Cloud oder eine eigene Adresse einrichten und *Neu konfigurieren* speichern,
  oder dort zu ntfy wechseln.
- In FF Agent: Webhook auf „Aktiv“, URL mit `https://`, Methode GET oder POST,
  Auslöse-Filter (Testalarme, Infoalarme, stille Einsätze) und Zeitplan prüfen.
- `calls_total` in der Diagnose: Zählt er nicht hoch, wurde kein Aufruf angenommen.
  Abgelehnte Aufrufe zählen nur in `rejected_total`. Steigt weder `calls_total` noch
  `rejected_total`, kommt der Aufruf nicht bei Home Assistant an.
- `rejected_total` und Reparatur-Meldung: Ist die Token-Pflicht an und der Header fehlt
  oder ist falsch, wird der Alarm abgelehnt. Header in FF Agent prüfen oder die Pflicht
  ausschalten, besonders bei Nabu Casa.
- Mehrfach-Alarme innerhalb von 30 Sekunden zählen als einer (`deduplicated_total`).

**Alarm über ntfy kommt nicht an**

- Reparatur-Meldung „FF Agent: ntfy-Abo für den Alarm fehlt“: Die ntfy-Entität ist gelöscht oder
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
(siehe [Entitäten](#entitäten)).

**„Alarm aktiv“ ging unerwartet aus:** Ein Neustart, Reload, Speichern der Optionen oder
ein Reconfigure setzt den Zustand zurück. Auch der Button oder die Action „Alarm
zurücksetzen“ schaltet ihn aus, wenn jemand sie ausgelöst hat (zum Beispiel eine
Automation).

**Zusage meldet einen Fehler:** Prüfe die Internetverbindung und, ob in FF Agent für den
aktuellen Einsatz eine Rückmeldung möglich ist (die Person muss dafür alarmiert worden
sein). Prüfe außerdem, ob die Rückmelde-URL noch gilt (*Neu konfigurieren*).

**„Das ist keine gültige Rückmelde-URL“:** Die URL muss `/app2/missionreplies/` enthalten
und auf `/accept` oder `/reject` enden, oder eine blanke UUID sein.

**Fehler melden:** Öffne ein Issue im Repository. Hänge nur die Diagnose an, **keine
Logs** (siehe [Datenschutz](#datenschutz)).

## Probleme melden und Fragen

- **Fehler gefunden?** Öffne ein [Issue][issues-url]. Beschreibe, was du getan hast, was du
  erwartet hast und was passiert ist, und hänge die Diagnose an (siehe
  [Fehlerbehebung](#fehlerbehebung)).
- **Fragen, Ideen, Erfahrungen?** Nutze die [Diskussionen][discussions-url].
- **Debug-Log:** *Einstellungen → Geräte & Dienste → FF Agent → Debug-Protokollierung
  aktivieren*. Problem nachstellen, die Protokollierung beenden; Home Assistant bietet das
  Log dann zum Download an.

> [!WARNING]
> Schwärze vor dem Posten von Logs, Screenshots oder Konfiguration Tokens, Webhook-URLs,
> ntfy-Themen, Namen, Adressen und echte Einsatzdaten. Wer eine Webhook-URL oder ein Thema
> kennt, kann falsche Alarme auslösen (siehe [Datenschutz](#datenschutz)).

## Mitmachen

Beiträge sind willkommen:

- Übersetzungen (Dateien unter `custom_components/ff_agent/translations/`)
- Rückmeldungen aus Tests mit einem echten FF Agent, besonders zu Zusage und Absage
- Pull Requests

Details stehen in [CONTRIBUTING.md](CONTRIBUTING.md).

## Unterstützen

Wenn dir die Integration nützt, freue ich mich über einen Stern auf GitHub. Wer das Projekt
darüber hinaus unterstützen möchte, kann mir einen Kaffee spendieren. Beides ist völlig
freiwillig.

[![Buy me a coffee][bmc-badge]][bmc-url]

## Weiterführende Links

- [Home Assistant](https://www.home-assistant.io/)
- [HACS-Dokumentation zu Custom Repositories](https://hacs.xyz/docs/faq/custom_repositories/)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/architektur.md](docs/architektur.md)
- [Diskussionen][discussions-url]

---

# English

Contents: [Disclaimer](#disclaimer) · [What it does](#what-the-integration-does-and-does-not-do) ·
[Requirements](#requirements) · [Installing](#installing) ·
[How does the alarm arrive?](#how-does-the-alarm-arrive) ·
[Setup](#setup-step-by-step) · [Token protection](#optional-token-protection) ·
[Options](#options) · [Reconfigure](#reconfigure) · [Entities](#entities) ·
[Actions](#actions-services) · [Examples](#example-automations) · [Privacy](#privacy) ·
[Limitations](#known-limitations) · [iCal](#optional-ical-through-remote-calendar) ·
[Removal](#removal) · [Troubleshooting](#troubleshooting) ·
[Issues and questions](#issues-and-questions) · [Contributing](#contributing) ·
[Support](#support-the-project) · [Resources](#further-resources)

The integration's user interface is available in German and English. Names of buttons,
options and entities below are the English texts of the interface. The names of the
FF Agent web UI are German and are quoted as they appear there, with an English
explanation where needed.

## Disclaimer

> [!WARNING]
> This is an unofficial, independent community project and is not affiliated with the
> provider of FF Agent. Trademarks and product names belong to their respective owners. Use
> at your own risk. The integration is **not a replacement** for the official alerting
> (pager/app). There is no guarantee that alarms are delivered, complete or on time.

## What the integration does and does not do

The integration is meant for **responders without admin rights in FF Agent**. One entry
belongs to exactly one person. Several people in one household create several entries.

**It does:**

- It reports every new alarm (after de-duplication of 30 s) to Home Assistant as an
  **event**. Automations start from it (light on, notification, open a gate).
- It shows "Alarm active" (with a reset time) and the time of the last alarm.
- It sends **accept and decline** to FF Agent, through a button or an action.
- It can switch "Alarm active" off by hand ("Reset alarm") without contacting FF Agent.

**It does not:**

- It does **not trigger alarms**. There is no code for the web API of FF Agent.
- It provides **no mission details** (keyword, place, type of alarm). The alarm call from
  FF Agent only counts as "there was an alarm".
- It does not tell a test alarm, a silent mission and a real alarm apart.

How it works: on an alarm, FF Agent calls a **personal webhook**. It points either directly
at Home Assistant (through Home Assistant Cloud or your own internet address) or at the free
service **ntfy**, from which Home Assistant picks up the alarm. For accept and decline, Home
Assistant calls your **personal mission reply URL** at FF Agent. Data only arrives as a push
from FF Agent; nothing is polled.

## Requirements

- an FF Agent account with access to "Automatisierung" (automation) in the web UI
- Home Assistant 2026.3.0 or newer
- for the alarm **one of the two** (see
  [How does the alarm arrive?](#how-does-the-alarm-arrive)):
  - Home Assistant is **reachable from the internet**: Home Assistant Cloud (Nabu Casa) or
    your own internet address with HTTPS, or
  - the core integration **ntfy** (free; Home Assistant does not have to be reachable from
    outside)
- Accept and decline also work without either.

## Installing

**With one click:** this button opens your own Home Assistant and adds the repository to
HACS. Then install "FF Agent" there and restart Home Assistant.

[![Open in HACS][my-hacs-badge]][my-hacs-url]

**Through HACS (custom repository), alternatively by hand:**

1. In HACS open the menu (⋮) at the top right, choose *Custom repositories*, enter the URL
   `https://github.com/rauchstefan/ha-ff-agent` and add it with type "Integration".
2. Open "FF Agent", choose the latest version (currently 1.0.0), download it and restart
   Home Assistant.
3. Under *Settings → Devices & services → Add integration* choose "FF Agent".

**Manually:**

1. Copy the folder `custom_components/ff_agent` into the `custom_components` directory of
   your Home Assistant configuration.
2. Restart Home Assistant.
3. Add the integration as above.

> [!NOTE]
> **After every update** (HACS and manual): restart Home Assistant and hard-reload the page in
> the browser (Ctrl+F5, on a Mac Cmd+Shift+R). In the companion app, restart the app or clear
> the frontend cache in the app settings. Otherwise the dialogs of the integration may show
> no text or old text.

## How does the alarm arrive?

On an alarm, FF Agent has to notify your Home Assistant. There are two ways; the setup asks
you ("Do you use Home Assistant Cloud?") and guides you step by step through the chosen
way. You can switch later at any time under *Reconfigure*.

- **Recommended: Home Assistant Cloud**, if you have it. The alarm arrives directly,
  without another service, and you can use the additional token. Your own internet address
  works the same way.
- **Free alternative: ntfy.** FF Agent sends the alarm to the service ntfy.sh, and the ntfy
  integration in Home Assistant picks it up.

| Way | Cost | Reachable from outside | Additional token | Third party sees alarm times |
|---|---|---|---|---|
| Direct (webhook) | Home Assistant Cloud: subscription; own address: your own effort | yes | yes | Home Assistant Cloud (when using the cloud) |
| ntfy | free | no | no | ntfy.sh |

## Setup step by step

1. **Copy the mission reply URL.** In the FF Agent web UI go to *Personen (persons) → (your
   name) → section "Übung/Einsatz" (exercise/operation) → "Weblinks für Einsatzmeldung"
   (web links for mission reply)* (the page is titled "URLs für Einsatzmeldung") and copy
   the accept URL. It looks like this:
   `https://www.ff-agent.com/app2/missionreplies/<REPLY_ID>/accept?transport=CAR`.
   The decline URL or the bare UUID are accepted as well. The URLs only apply to this person
   and to the currently active mission.
2. **Add the integration.** In Home Assistant choose *Add integration → FF Agent*. Fields:
   - **Name:** label of this entry, for example your name. The name becomes the device name
     and thus part of the entity IDs.
   - **Mission reply URL (accept):** the copied URL.

   The integration sends **nothing** to FF Agent here, because every test would be a real
   acceptance.
3. **Choose the accept settings.** The step "Accepting: transport and location" asks for:
   - **Default transport:** "Car", "On foot" or "Bicycle". It is sent with every acceptance
     if the action does not name one.
   - **Location source:** where the location comes from that is sent with every acceptance.
     The choices are:
     - **No location** (default): no location is sent.
     - **Home position from Home Assistant:** The position is only read when accepting, so
       changes take effect immediately. If Home Assistant has no position set (0/0), the
       acceptance is sent without a location.
     - **Enter coordinates manually:** In the next step "Accepting: coordinates" you enter
       latitude (-90 to 90) and longitude (-180 to 180) in decimal degrees. The Home Assistant
       home position is suggested; the value saved is then a fixed copy.
     - **Person or device tracker (live location):** In the next step you choose the entity.
       Its current location is sent with every acceptance. If it has no location at that
       moment, the acceptance is sent without one.

   The mission reply URL stays unchanged; only the UUID and host are stored. The integration
   appends transport and location source to every acceptance. Nothing is sent now. You change
   both later under *Configure*. Changing the source deletes the values of the old source;
   other options stay. Existing entries with a location entity keep working unchanged (they
   count as live location).
4. **Choose the alarm way.** To the question "Do you use Home Assistant Cloud?" you answer
   "Yes (recommended)" (continue with
   [Route A](#route-a-home-assistant-cloud-or-own-address)) or "No" (a pointer to ntfy,
   continue with [Route B](#route-b-ntfy-free)). If Home Assistant Cloud is already active,
   the question says so, but does not decide for you.

### Route A: Home Assistant Cloud or own address

1. **Reachability.** With "Yes" the setup checks how Home Assistant can be reached:
   - Home Assistant Cloud connected: a cloudhook URL is created, for example
     `https://hooks.nabu.casa/<...>`.
   - your own internet address (under *Settings → System → Network*):
     `https://<your-external-url>/api/webhook/<WEBHOOK_ID>`. If a Home Assistant Cloud
     subscription is active at the same time, the setup uses the cloud address, also
     through the option "I have my own internet address".
   - Home Assistant Cloud set up but not connected: the dialog shows what to check, with
     "Try again" and "Use ntfy instead (free)".
   - none of these: the dialog "Set up Home Assistant Cloud" leads you in numbered steps to
     the cloud page of your Home Assistant (link in the dialog), to signing in, and back to
     "Check again". The cloud is a paid subscription that you can try for free first. From
     December 2026 it is called "Home Assistant Link". Instead of the cloud you can also
     enter your own internet address.
   - No dead end: "Use ntfy instead (free)" switches to Route B. "Continue anyway (accept
     and decline only, add the alarm later)" saves the entry without an alarm; accept and
     decline work, and you add the alarm later under *Reconfigure*.

   A note on DS-Lite connections (many cable and fibre connections in Germany): port
   forwarding from the internet is usually not possible there. Use Home Assistant Cloud or
   ntfy then.
2. **Create the webhook in FF Agent.** In the FF Agent web UI go to *Automatisierung
   (automation) → Persönliche Webhooks (personal webhooks) → Webhook hinzufügen (add
   webhook)* and fill in **every field** according to this table:

   | Field in FF Agent | Value | Reason |
   |---|---|---|
   | Type | Alarm | the only choice |
   | Webhooktyp (webhook type) | Generischer Webhook (generic webhook) | freely configurable, fits Home Assistant |
   | Name | free, e.g. "Home Assistant" | only shown in FF Agent |
   | Aktiv (active) | on | otherwise nothing is called |
   | auch für Testalarme (also for test alarms) | on (for testing) | You can check the whole chain. **Automations then also run for test alarms.** |
   | auch für Infoalarme (also for info alarms) | off | Info alarms are not missions (assumption, unverified) |
   | auch für stille Einsätze (also for silent missions) | as you like, suggestion: on | You are involved. If you do not want an announcement at night, filter in the automation. |
   | Zeitplan aktiviert (schedule enabled) | off | Home Assistant should see every alarm. Time windows can be modelled more precisely in automations. |
   | Methode (method) | POST | Home Assistant default for webhooks, no data in the URL. Home Assistant accepts GET as well. |
   | URL | the displayed webhook URL, with `https://` | FF Agent must be able to reach it from outside |
   | Basis-Authentifizierung (basic authentication) | empty | not used |
   | Header | optional, only for the token protection: `X-FF-Agent-Token` = displayed token | Enter it first and check it in the diagnostics, then switch the requirement on (see [Token protection](#optional-token-protection)). |
   | Inhalt / Query-Parameter (content / query parameters) | empty | placeholders with mission data are not documented |

   FF Agent aborts calls after 5 seconds. Home Assistant answers immediately.
3. **Test.** Have a test alarm triggered (test alarms are on). Afterwards the event entity
   "Alarm" in Home Assistant must show a new timestamp and "Alarm active" must turn on.

A note on repeated calls: several calls within 30 seconds after the last recognised alarm
count as one alarm. You may point up to three webhooks in FF Agent at the same address.

### Route B: ntfy (free)

The setup dialog "Set up the alarm through ntfy" shows a random, secret **topic** (32
characters) and the finished address for FF Agent. Best open the links in the dialog in a
new tab and keep the dialog open.

1. **Add the ntfy integration** (link in the dialog). Keep the service URL
   `https://ntfy.sh`, leave username and password empty. If ntfy is already set up, open the
   ntfy integration and choose "Add topic".
2. **Subscribe to the topic:** "Enter topic", paste the displayed topic, display name
   "FF Agent Alarm". Without a display name the secret topic appears as the name of the
   entity.
3. **Create a generic webhook in FF Agent** (*Automatisierung → Persönliche Webhooks →
   Webhook hinzufügen*): Type Alarm, method **GET**, URL `https://ntfy.sh/<topic>/trigger`
   (exactly as shown in the dialog), active on, also for test alarms on (for testing), also
   for info alarms off, schedule off. Basic authentication, headers, content and query
   parameters stay **empty**.
4. **Choose "Done, find the entity" in the FF Agent setup.** The integration looks for the
   entity of the topic itself. Only if it finds nothing do you choose it yourself (or a
   topic you have already subscribed to). The final dialog only repeats the values if the
   chosen entity has another address than the one shown.
5. **Check with a test alarm:** "Alarm active" turns on.

The order matters: subscribe first, then enter it in FF Agent. ntfy does not deliver a
message that arrived before the subscription. "Use Home Assistant Cloud after all" is also
possible in the dialog at any time.

## Optional token protection

Route A only. With ntfy, custom headers do not reach the subscriber; there the topic is the
only protection.

The webhook URL alone is the secret. Anyone who knows it can trigger a false "Alarm active"
**without the token requirement**. If you attach security-relevant actions to the alarm
(open a gate, unlock a door), switch the token requirement on. The integration always
generates a token during setup.

1. Open *Configure* on the entry. It shows the header name `X-FF-Agent-Token` and the
   token.
2. In FF Agent, add a header with this name and value to the webhook.
3. Trigger a test alarm and download the diagnostics. Under `stats` → `last_call` →
   `header_names` there must be `x-ff-agent-token`.
4. Only then switch on "Require additional token" in the options.

Home Assistant answers calls without a valid token with 401 and discards them. A repair
notice ("FF Agent webhook call rejected") appears and disappears with the next accepted
call. A rejected alarm should not go unnoticed.

The option is **off** by default because it is not proven that Nabu Casa passes custom
headers through. If the header does not arrive there, every alarm would be discarded. If the
diagnostics do not show the header, leave the option off.

## Options

*Settings → Devices & services → FF Agent → Configure.* At the top the dialog shows the
current webhook URL, the kind of address, the header name and the token. With ntfy it shows
the ntfy entity and the address for FF Agent instead; the switch "Require additional token"
does not exist there (a value that was set is kept for a later switch back).

| Option | Meaning |
|---|---|
| Require additional token | As above. Default: off. |
| Reset time of "Alarm active" | Minutes without a new alarm after which "Alarm active" turns off (1 to 1440, default 30). A new alarm restarts the time. |
| Default transport | Sent with an acceptance if the action does not name one. Choices are "Car", "On foot" and "Bicycle". |
| Location source | "No location" (default), "Home position from Home Assistant" (read when accepting), "Enter coordinates manually" (latitude and longitude in decimal degrees) or "Person or device tracker (live location)". Changing the source deletes the values of the old source. Existing entries with a location entity keep working unchanged. |

> [!IMPORTANT]
> Saving the options reloads the integration. An alarm that is active at that
> moment is **reset** ("Alarm active" turns off, the window against duplicate alarms is open
> again). So do not change options in the middle of a mission.

## Reconfigure

*Settings → Devices & services → FF Agent → three-dot menu → Reconfigure.*

- **New mission reply URL (accept):** Only fill in if the URL has changed, for example after
  regenerating the UUID in FF Agent. Empty means unchanged. The current URL is not shown.
  If the new URL belongs to another existing entry, the dialog aborts.
- **How does Home Assistant receive the alarm?** Through Home Assistant Cloud or your own
  internet address (recommended; requires a cloud subscription or an address reachable from
  the internet, i.e. IP address or domain) or free through ntfy (no subscription, Home
  Assistant does not have to be reachable from the internet). When you switch, the same
  setup dialogs as during setup guide you through the steps. Afterwards delete the old
  webhook in FF Agent. A cloudhook is deleted when you switch to ntfy. If you stay with
  ntfy and only change the mission reply URL, the dialog saves directly without the ntfy
  dialog.
- **Create a new secret address:** For the direct way a new webhook address and a new
  token, for ntfy a new topic (the dormant webhook address and token are renewed as well).
  The old address stops working afterwards. The dialog shows the new values; enter them in
  FF Agent. If the token requirement is on, Home Assistant rejects alarms until the new
  header is entered in FF Agent. Useful if the address has become known.
- If the entry was saved with "Continue anyway" (internal address only) and you have since
  got Home Assistant Cloud or your own address: just open *Reconfigure* and save. The setup
  then creates the reachable address.

A reconfigure with a change also **reloads the integration and resets a running alarm.**

## Entities

All entities belong to one device per entry (type service).

| Entity | Kind | Behaviour |
|---|---|---|
| Alarm | Event | Event type `alarm` on every new alarm. The **recommended trigger** for automations. |
| Alarm active | Binary sensor | On at the alarm, off after the reset time. Off after a restart or reload. |
| Last alarm | Sensor (timestamp) | Time of the last alarm. Survives a restart. |
| Last reply | Sensor | `Accepted`, `Declined` or `Failed` |
| Accept | Button | Accepts with the default transport and optionally the location |
| Decline | Button | Declines |
| Reset alarm | Button | Turns "Alarm active" off right away and stops the reset time. "Last alarm" stays, and the 30-second window against duplicate alarms keeps running: a repeat of the same alarm does not turn "Alarm active" on again, a new alarm afterwards does. Without an active alarm nothing happens, and nothing is sent to FF Agent. |

Entity IDs start with the name of the entry, for example `event.ff_agent_alarm`. The rest
depends on the name and the language (with the German interface, for example,
`binary_sensor.ff_agent_alarm_aktiv`). Find them under *Settings → Devices & services → FF
Agent → device* and choose entities in automations through the interface instead of typing
IDs.

> [!IMPORTANT]
> **Mandatory filter for automations on the event entity:** A `state` trigger always needs
> `not_from: [unavailable, unknown]` and `not_to: [unavailable, unknown]`. On every reload
> and every restart the event entity briefly becomes `unavailable` and then restores the old
> timestamp. Without the filters the automation would take that for a new alarm and fire,
> for example after saving the options.

## Actions (services)

All actions need the ID of the entry (`config_entry_id`). Choose it in the interface
through the "Entry" selector.

- **`ff_agent.accept`** (Accept)
  - `config_entry_id` (required): the entry of the person who accepts
  - `transport` (optional): mode of transport `car` (default), `feet` (on foot) or
    `bicycle`. Without it the default transport from the options applies. Home Assistant
    stores the values in lower case; `CAR`, `FEET` and `BICYCLE` are sent to FF Agent.
  - `latitude` and `longitude` (optional): location, only both together. It takes precedence
    over the location source from the options. Without them the location source from the
    options applies; if none is set, no location is sent.
- **`ff_agent.reject`** (Decline)
  - `config_entry_id` (required)
- **`ff_agent.reset_alarm`** (Reset alarm)
  - `config_entry_id` (required): the entry of the person whose "Alarm active" should turn
    off. Works like the button: no call to FF Agent, nothing happens without an active
    alarm.

The reply refers to the **current mission** in FF Agent. Accept and decline only work if the
person was alerted for this mission (as in the FF Agent app). If it fails, the buttons and
actions report an error ("FF Agent could not be reached …" or "FF Agent answered with HTTP
status …"). The wait for FF Agent is 10 seconds. The same reply within 10 seconds after a
success is skipped without a second call.

**A 2xx answer from FF Agent only means "sent", not necessarily "recorded".** How FF Agent
answers an invalid UUID or a missing mission is unverified. Check important replies in FF
Agent.

## Example automations

Replace the entity IDs and `<ENTRY_ID>` with your values. Best choose them in the automation
interface.

### 1. Turn on a light on alarm

```yaml
automation:
  - alias: "Alarm: Licht an"
    description: "Schaltet bei jedem neuen FF-Agent-Alarm das Licht ein."
    triggers:
      - trigger: state
        entity_id: event.ff_agent_alarm  # event entity "Alarm" of the entry
        not_from: [unavailable, unknown]
        not_to: [unavailable, unknown]
    actions:
      - action: light.turn_on
        target:
          entity_id: light.flur
        data:
          brightness_pct: 100
```

Alternative without the event: `trigger: state` on the binary sensor "Alarm active" with
`to: "on"`. It only fires on a change from off to on, so not on a second alarm while the
first one is still active.

### 2. Notification with an "Accept" button (companion app)

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

- For decline, create the same second block with `FF_AGENT_REJECT` and `ff_agent.reject`.
- Optional fields of `ff_agent.accept`: `transport` (`car`, `feet` or `bicycle`) as well as
  `latitude` and `longitude`, only both together.
- If "auch für Testalarme" (also for test alarms) is on in FF Agent, test alarms trigger
  the automation as well.
- The location is only sent if it is given or a location source other than "No location" is set in the options. The rejection never sends a location.
- The text values in the YAML (alias, title, message) are the German originals; translate
  them as you like.

## Privacy

**Secrets.** The webhook URL, the token, the mission reply URL and (with ntfy) the topic are
secrets.

- Anyone who knows the **webhook URL** can trigger "Alarm active" without the token
  requirement and thereby start your automations.
- Anyone who knows the **mission reply URL** can accept or decline on your behalf.
- Remedy: *Reconfigure → Create a new secret address* (new URL and new token, switch the
  token requirement on), or generate a new mission reply URL in FF Agent and enter it under
  *Reconfigure*.
- Do not share screenshots of the options or of the final dialog.

**What is stored.** The reply UUID, host, webhook ID, cloudhook URL and token are only in
the config entry. Of incoming calls only the **shape** is recorded (method, header names,
keys, types, lengths), never values. No secret appears in entity attributes, entity unique
IDs or the logs of the integration. The diagnostics are redacted.

**Home Assistant logs.**

> [!WARNING]
> Never share Home Assistant logs unchecked. The webhook ID can also
> appear in normal warnings and errors of Home Assistant, e.g. on a call to an old webhook
> address after "Create a new secret address". Debug logs of
> `homeassistant.components.webhook`, `.http`, `.websocket_api` and `homeassistant.core`
> additionally contain dialog contents and location data. That is inherent to Home Assistant
> itself.

**Privacy with ntfy.** Every alarm runs through the service ntfy.sh. Its operator sees when
an alarm comes in and keeps the message for up to 12 hours. No mission data is transmitted
as long as nothing is entered under "Inhalt" (content) and "Query-Parameter" in FF Agent.
The topic works like a password: anyone who knows it sees your alarm times and can trigger
false alarms. Keep it secret and do not share screenshots of the setup. The ntfy
integration stores the topic and message in the history of Home Assistant and thus also in
backups. If you do not want that, exclude its entity from the recorder:

```yaml
recorder:
  exclude:
    entities:
      - event.<your_ntfy_entity>  # event entity of your ntfy subscription, look up its ID under Settings > Entities
```

The FF Agent integration itself never names the topic or the entity in logs, entity
attributes or the diagnostics.

**Recorder.** The recorder stores alarm times and replies. These are personal data as well.
If you do not want them in the database, exclude the entities. Example for
`configuration.yaml`:

```yaml
recorder:
  exclude:
    entity_globs:
      - "*<name_of_the_entry>*"  # with the default name "FF Agent": "*ff_agent*"
```

The glob has to match the name of your entry (see Setup, step 2), because the entity IDs
start with the name of the entry in lower case and with underscores. With the default name
"FF Agent" that is `*ff_agent*`; if your entry has another name, insert the matching name or
list the IDs individually under `entities:`. This is how you find them: *Settings → Devices
& services → FF Agent → device → entities*, or *Settings → Entities* with a search for the
name of the entry. There are seven entities (binary sensor, event, two sensors, three
buttons).

## Known limitations

- The webhook carries no content. A test alarm, a silent mission and a real alarm cannot
  be told apart in Home Assistant.
- Trigger filters and schedule are in FF Agent. What is deselected there, Home Assistant
  does not see.
- The token check through Nabu Casa only works once the header demonstrably arrives (see
  diagnostics).
- A restart, a reload, saving the options and a reconfigure reset "Alarm active". Only
  "Last alarm" is restored.
- The reply applies to the active mission. Accept and decline only work if the person was
  alerted for this mission. How FF Agent otherwise answers has not been verified yet
  (assumption A7).
- Success means "HTTP 2xx", not necessarily "recorded by FF Agent".
- No reauth flow: the integration only notices an invalid reply UUID through an error on
  accepting, or not at all if FF Agent answers with 2xx even then (unverified, assumption
  A7).
- Some assumptions about the behaviour of FF Agent (such as retries on errors) have not
  been confirmed in a real test yet.

**Limits of ntfy:**

- An alarm during an interruption (internet down, restart of Home Assistant) is lost. ntfy
  does not deliver later.
- ntfy.sh is an additional point of failure.
- With very many simultaneous alarms a rate limit of ntfy.sh is possible (unverified).
- No additional token: if you attach gates or doors to the alarm, use Route A with the
  token.
- Residual risk of a duplicate alarm: if FF Agent is reloaded in Home Assistant (options,
  reconfigure) while the ntfy connection is interrupted, an alarm from the last 60 seconds
  can count a second time as an alarm.
- Residual risk of loss: if a message arrives at the very moment FF Agent starts or reloads
  (before the integration listens to the ntfy entity), an alarm can be lost. The time
  window is very small.

## Optional: iCal through Remote Calendar

The integration does not build its own calendar retrieval. According to its documentation,
FF Agent offers a personal iCal feed that contains the missions you took part in. It is
probably unsuitable for a running alarm, but fine for the history. Add it through the core
integration **Remote Calendar** (from Home Assistant 2025.4; supports basic auth; refreshes
every 24 hours or through `homeassistant.update_entity`).

> [!WARNING]
> **Recorder warning:** Calendar attributes can contain the place and description of the
> mission and end up in the recorder. Exclude the calendar entity if needed, as shown above.

## Removal

1. *Settings → Devices & services → FF Agent → three-dot menu → Delete.* A Nabu Casa
   cloudhook is deleted with it. With ntfy, remove the topic in the ntfy integration if you
   no longer need it.
2. In FF Agent delete the personal webhook (*Automatisierung → Persönliche Webhooks*).
3. If needed, regenerate the mission reply URL in FF Agent so that the old one becomes
   invalid.
4. HACS: remove the integration in HACS and restart Home Assistant.

## Troubleshooting

**Download diagnostics:** *Settings → Devices & services → FF Agent → three-dot menu →
Download diagnostics.* They contain no secrets and show, among other things, `url_kind`,
`calls_total`, `rejected_total`, the shape of the last call and the result of the last reply
(without the address).

**Dialogs without text or with old text:** The cause is usually the browser cache. A restart
of Home Assistant alone is not enough: hard-reload the page (Ctrl+F5, on a Mac
Cmd+Shift+R). In the companion app, restart the app or clear the frontend cache in the app
settings.

**HACS shows a string such as `7192103` instead of a version number:** The installation comes
from the branch `main` (from the time when there were only pre-releases). Solution: in HACS,
open "FF Agent", choose the menu (⋮) → *Redownload*, select version v0.4.0 (or newer) and
restart Home Assistant.

**"The alarm does not arrive"**

- Kind of address (`url_kind`): FF Agent cannot reach `internal` or `path_only`. Set up Home
  Assistant Cloud or your own address and save *Reconfigure*, or switch to ntfy there.
- In FF Agent: check that the webhook is "Aktiv" (active), the URL has `https://`, the
  method is GET or POST, the trigger filters (test alarms, info alarms, silent missions)
  and the schedule.
- `calls_total` in the diagnostics: if it does not count up, no call was accepted. Rejected
  calls only count in `rejected_total`. If neither `calls_total` nor `rejected_total`
  rises, the call does not reach Home Assistant.
- `rejected_total` and the repair notice: if the token requirement is on and the header is
  missing or wrong, the alarm is rejected. Check the header in FF Agent or switch the
  requirement off, especially with Nabu Casa.
- Multiple alarms within 30 seconds count as one (`deduplicated_total`).

**The alarm through ntfy does not arrive**

- Repair notice "FF Agent: ntfy subscription for the alarm is missing": the ntfy entity is
  deleted or disabled. Subscribe to the same topic in the ntfy integration again; the
  setup finds the new subscription through the topic itself, reloads, and the notice
  disappears. If the notice stays (for example with another topic): choose the new entity
  under *Reconfigure*.
- The ntfy entity is "unavailable": the ntfy integration has no connection. The ntfy
  integration itself shows this.
- Diagnostics, block `ntfy`: `entity_found`, `entity_available`, `events_total` and
  `accepted_total`. `ignored_stale_total` counts old values that were restored after an
  interruption. `last_event` only shows the shape of the last message (`message_length`
  should be 9, "triggered"); a longer text means FF Agent sends content along.
- In FF Agent: method GET and the address from the dialog, topic exactly the same.
- Switch the way through *Reconfigure*; afterwards delete the old webhook in FF Agent.

**An automation fires after a reload or restart:** The filters `not_from`/`not_to` are
missing (see [Entities](#entities)).

**"Alarm active" turned off unexpectedly:** A restart, reload, saving the options or a
reconfigure resets the state. The button or action "Reset alarm" also turns it off if
someone triggered it (for example an automation).

**Accepting reports an error:** Check the internet connection and whether a reply is
possible in FF Agent for the current mission (the person must have been alerted for it).
Also check whether the mission reply URL is still valid (*Reconfigure*).

**"This is not a valid mission reply URL":** The URL must contain `/app2/missionreplies/`
and end with `/accept` or `/reject`, or be a bare UUID.

**Report a bug:** Open an issue in the repository. Attach only the diagnostics, **no logs**
(see [Privacy](#privacy)).

## Issues and questions

- **Found a bug?** Open an [issue][issues-url]. Describe what you did, what you expected
  and what happened, and attach the diagnostics (see [Troubleshooting](#troubleshooting)).
- **Questions, ideas, experiences?** Use the [discussions][discussions-url].
- **Debug log:** *Settings → Devices & services → FF Agent → Enable debug logging*. Reproduce
  the problem, then stop the logging; Home Assistant offers the log as a download.

> [!WARNING]
> Before you post logs, screenshots or configuration, **redact** tokens, webhook URLs,
> ntfy topics, names, addresses and real mission data. Anyone who sees a webhook URL or
> topic can trigger false alarms (see [Privacy](#privacy)).

## Contributing

Contributions are welcome:

- translations (files under `custom_components/ff_agent/translations/`)
- feedback from tests with a real FF Agent, especially accepting and declining
- pull requests

Details are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Support the project

If the integration is useful to you, a star on GitHub is appreciated. If you want to
support the project further, you can buy me a coffee. Both are entirely optional.

[![Buy me a coffee][bmc-badge]][bmc-url]

## Further resources

- [Home Assistant](https://www.home-assistant.io/)
- [HACS documentation on custom repositories](https://hacs.xyz/docs/faq/custom_repositories/)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/architektur.md](docs/architektur.md) (architecture, in German)
- [Discussions][discussions-url]

---

# Entwicklung und Lizenz / Development and license

**Deutsch:** Das Projekt wird mit Claude Code nach einem Rollenmodell entwickelt
(Projektleiter, Architekt, Researcher, Entwickler, Tester, Reviewer, Doku). Einstieg:
[CLAUDE.md](CLAUDE.md) und [docs/orchestrierung.md](docs/orchestrierung.md). Stand der
Quality Scale: [docs/quality-scale.md](docs/quality-scale.md). Die Entwicklerdokumentation
ist deutsch.

**English:** The project is developed with Claude Code using a role model (project lead,
architect, researcher, developer, tester, reviewer, documentation). Start with
[CLAUDE.md](CLAUDE.md) and [docs/orchestrierung.md](docs/orchestrierung.md). Quality scale
status: [docs/quality-scale.md](docs/quality-scale.md). The developer documentation is in
German.

**Lizenz / License:** MIT, siehe / see [LICENSE](LICENSE).

[releases-shield]: https://img.shields.io/github/v/release/rauchstefan/ha-ff-agent?style=for-the-badge
[releases-url]: https://github.com/rauchstefan/ha-ff-agent/releases
[contributors-shield]: https://img.shields.io/github/contributors/rauchstefan/ha-ff-agent?style=for-the-badge
[contributors-url]: https://github.com/rauchstefan/ha-ff-agent/graphs/contributors
[issues-shield]: https://img.shields.io/github/issues/rauchstefan/ha-ff-agent?style=for-the-badge
[issues-url]: https://github.com/rauchstefan/ha-ff-agent/issues
[discussions-shield]: https://img.shields.io/github/discussions/rauchstefan/ha-ff-agent?style=for-the-badge
[discussions-url]: https://github.com/rauchstefan/ha-ff-agent/discussions
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[hacs-url]: https://hacs.xyz/docs/faq/custom_repositories/
[ci-shield]: https://img.shields.io/github/actions/workflow/status/rauchstefan/ha-ff-agent/tests.yml?branch=main&label=Tests&style=for-the-badge
[ci-url]: https://github.com/rauchstefan/ha-ff-agent/actions/workflows/tests.yml
[license-shield]: https://img.shields.io/github/license/rauchstefan/ha-ff-agent?style=for-the-badge
[license-url]: LICENSE
[python-shield]: https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[my-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[my-hacs-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=rauchstefan&repository=ha-ff-agent&category=integration
[bmc-badge]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
[bmc-url]: https://buymeacoffee.com/rauchstefan
