# Recherche: Schnittstellen von FF Agent und Integrationsweg für Home Assistant

TODO-ID: `261016-ffagent-schnittstellen` · Stand/Abruf der Quellen: 2026-10-16 · Autor: Researcher

Kennzeichnung: **[G]** gesichert (Quelle gelesen), **[A]** abgeleitet (eigene Schlussfolgerung),
**[U]** unsicher/unbekannt/öffentlich nicht dokumentiert.

Methodische Einschränkung: Die offiziellen PDFs `Dokumentation_WebAPI.pdf` (v1.6) und
`Dokumentation_InstantCommands.pdf` (Stand 05.03.2019) sind abrufbar, ließen sich mit den
verfügbaren Werkzeugen aber **nicht als Text lesen** (nur Binärdaten). Ihre Existenz und
die Versionsnummern sind belegt, ihr Inhalt nicht. Aussagen zur WebAPI stützen sich auf zwei
Drittprojekte, die sie nutzen (BOSWatch-Plugin, Alarmierungs-Webapp). Die PDFs müssen vor
einer Implementierung mit PDF-Werkzeug oder von einem Menschen gelesen werden.

## 0. Nachtrag Projektleiter (2026-10-16): PDFs gelesen

Der Projektleiter hat beide PDFs nach der Recherche im Volltext gelesen. Die Einschränkung
oben ist damit aufgehoben. Ergebnis, alles **[G]** aus den PDFs:

**Dokumentation_WebAPI.pdf, v1.6 vom 28.11.2019** (Hersteller von FF Agent)

- **Richtung:** Die WebAPI ist nur **eingehend**, also extern → FF Agent, etwa für
  Organisationen mit fremdem Alarmierungssystem. Sie bietet genau vier Endpunkte, alle als
  POST mit JSON:
  - `triggerAlarm`
  - `pushMessage`
  - `chatMessage`
  - `updateVehicleStatus` (nicht in der FREE-Lizenz)
- **Keine Daten nach außen:** Die Doku nennt keinen lesenden Endpunkt und keinen Callback.
- **Basis-URLs:** `https://api.service.ff-agent.com/v1/WebService/` (Live) und
  `https://free.api.service.ff-agent.com/v1/WebService/` (Free).
- **Authentifizierung:**
  - Header `webApiToken` (Organisation) und `hmac`: HMAC-SHA256 mit dem WebAPI-Schlüssel
    über eine feste Verkettung.
  - Bei `triggerAlarm` zusätzlich `accessToken` (Soft-Gateway) und `selectiveCallCode`
    (Schleife).
  - Die Live-Version verlangt außerdem ein von FF Agent ausgestelltes Client-Zertifikat.
- **Rechte:** Die Konfiguration liegt unter *Admin > Einstellungen > Sicherheit* und
  *Admin > Gateways > Soft-Gateway Devices*, also nur für Admins der Einheit. Das
  Soft-Gateway kennt einen IP-Filter und einen „Alarmerkennungsabstand“ gegen
  Mehrfachauslösung.
- **Alarmfelder von `triggerAlarm`:**
  - Zeit und Kennung: `alarmDate`, `operationId`, `keyword`, `type`
  - Texte: `message`, `note` (veraltet), `details`, `caller`, `patient`, `alarmMessage`
    (Rohtext eines digitalen Melders)
  - Einordnung: `criticalIncident`, `operationSchedule`, `object`, `operationResources`
  - Ort: `additionalAddressInfo`, `location`, `district`, `lat`/`lng`,
    `easting`/`northing`

  Diese Felder beschreiben vermutlich auch das interne Einsatzmodell [A].
- **Neuer Hinweis [U]:** Die Sicherheitsseite der Web-UI zeigt neben „WebAPI“ die Reiter
  **„Status-Seiten“** und **„Fireboard-API“**. Fireboard ist ein externes System;
  möglicherweise gibt FF Agent über diese Schnittstelle Einsatzdaten **aus**. Das ist ein
  Ansatzpunkt für die Hersteller-Anfrage und für die Screenshots des Nutzers.

**Dokumentation_InstantCommands.pdf, Stand 05.03.2019**

- **Rechte:** Instant Commands liegen unter *Admin / Einstellungen*. Bearbeiten und manuell
  auslösen braucht die Berechtigung „Einstellungen bearbeiten“.
- **Auslöser:** Laut Doku gibt es nur zwei: eine TETRA-SDS im Format
  `FFACMD_V1:<Domain>;<Kommando>;<Token>` und einen eingehenden Fahrzeugstatus.
  **„Bei Alarm“ ist kein Auslöser.**
- **Aktionen:**
  - Benachrichtigung per E-Mail, Push, SMS oder TETRA-SDS, wahlweise mit Platzhaltern für
    Einsatzdaten
  - Fahrzeugstatus setzen
  - vorkonfigurierten Alarm auslösen

  Eine **HTTP- bzw. Webhook-Aktion gibt es in diesem Stand nicht**.
- **Folgerung [A]:** Der „Webhook der Feuerwehr“ aus der Homey-App kommt entweder aus einer
  neueren Funktion (nach 2019, nicht öffentlich dokumentiert), aus Gateway PLUS/Node-RED
  oder aus einem anderen Mechanismus. Die Frage an Nutzer und Hersteller bleibt zentral.
  Die Empfehlung (Webhook-Empfang, `cloud_push`) gilt weiter unter Vorbehalt. Die
  WebAPI-Aufrufe aus HA heraus (Push, Chat, Status) wären technisch möglich, brauchen
  aber Admin-Zugangsdaten und ein Client-Zertifikat der Einheit. Für eine
  Endnutzer-Integration ist das nicht angemessen.

## 1. Fragestellung

Welche Schnittstellen bietet FF Agent, mit welchem Transport, welcher Authentifizierung und
welchen Daten, und welcher Weg eignet sich für eine HA-Integration (`ff_agent`)? Welche
`iot_class` ist richtig? Was brauchen wir vom Nutzer und vom Hersteller?

## 2. Kurzfazit

- Hersteller ist ein Unternehmen, dessen Name und Anschrift im Impressum der Produkt-Website stehen; Produkt „FF-Agent“, Domain ff-agent.com [G]. „FF Agent GmbH“ ist nicht belegt.
- Die offizielle **WebAPI geht in Richtung extern → FF Agent** (Alarm auslösen, Push-Nachricht, Chat) [G für Existenz, A für Richtung]. Auth: Token + HMAC-SHA256, im Live-Betrieb zusätzlich Client-Zertifikat (mTLS) [G aus Drittcode]. Sie liefert Alarme **nicht** an HA.
- Für **FF Agent → HA** gibt es öffentlich nur einen Hinweis: Eine Homey-App wird von einem „Webhook der Feuerwehr“ ohne Nutzdaten getriggert [G]. Wie dieser Webhook in FF Agent eingerichtet wird (Rolle, Lizenz, Format), ist **öffentlich nicht dokumentiert** [U].
- Es gibt **keine** bestehende HA-Integration, keinen Node-RED-Flow und keinen Forenbeitrag für FF Agent in HA [G: nichts gefunden].
- Empfohlener Weg: **Webhook-Empfang in HA** (Alarm-Trigger, ohne Nutzdaten), Rückmeldung/Details erst nach Hersteller-Klärung; **`iot_class: cloud_push`** (FF Agent ist ein Cloud-Dienst, der HA aufruft). `local_push` nur beim lokalen Gateway-PLUS-Weg.
- Fallbacks ohne Herstellerhilfe: Companion-App „Last Notification“ (nur Android) oder IMAP-Auswertung; beides Notlösungen.
- Vermutlich nötig: Admin-Rechte in FF Agent und Lizenz ab BASE PLUS (Instant Commands/Gerätehaus-Automatisierung) [A].
- Wichtigste Lücke: Inhalt der beiden PDFs und Einrichtung des Webhooks. Erst danach Manifest ändern.

## 3. Befunde

### 3.1 Produktüberblick (Frage 1)

- Betreiber: der Hersteller von FF Agent; Name, Anschrift und Ansprechpartner stehen im Impressum [G] https://www.ff-agent.com/kontakt.html , https://www.ff-agent.com/datenschutz.html . Die WebAPI-PDF nennt einen Autor beim Hersteller [G, Titel der PDF] https://helpcenter.ff-agent.com/webui/uebersicht/touren/pdfs/Dokumentation_WebAPI.pdf .
- Produktteile [G] https://www.ff-agent.com : Alarmierung (Push, E-Mail, SMS, Anruf), FF-Agent Mobile App (iOS/Android), Commander App, BOS-Chat, Status-Monitor (Widgets, Browser oder Raspberry Pi), Lageboard, Verwaltung (Übungen, Einsatzobjekte, Fahrtenbuch, Sirenenüberwachung, Gerätehaus-Automatisierung), Web-UI, **FF-Agent Gateway** (Hardware vor Ort: 5-Ton, POCSAG, Fax), Gateway PLUS (mit Node-RED), verbundene Produkte FF-Inventory, FF-Agent Teams, Accounting.
- Lizenzmodelle [G] https://www.ff-agent.com/kosten.html (netto): FREE (0 €, 10 Einsätze/Monat, 1 Alarmregel, 1 Gerät je Nutzer), STARTER (ab 49 €/Jahr), BASE (ab 7,90 €/Monat), BASE PLUS (ab 15,90 €/Monat), PRO (ab 31,90 €/Monat). Schnittstellen wie SMS-Eingang, Gateway, Eurofunk eMID/MQTT, EDP4, TETRA, WDX3, LARDIS, Leitstelle Tirol sind kostenpflichtige Optionen. **Alarmweiterleitung/Gebäudeautomatisierung über Gateway PLUS inkl. Node-RED: kostenpflichtige Option ab BASE PLUS.** Ein API-Zugang wird dort nicht als Lizenzmerkmal beschrieben.
- Rechte: Berechtigungsgruppen mit sechs Bereichen (Personen, Übungen, Einsätze, Mobile App & Alarminhalt, Kommunikation, Admin); Standardnutzer starten ohne Rechte [G] https://helpcenter.ff-agent.com/webui/erste-schritte/berechtigungen/ . Wer Schnittstellen/Instant Commands konfigurieren darf, steht dort nicht. Instant Commands liegen unter „Admin / Einstellungen“ [G] https://helpcenter.ff-agent.com/technik/gateway/tor-und-lichtsteuerung/ , also Admin-Bereich [A].

### 3.2 Schnittstellen im Einzelnen (Frage 2)

**Schnittstellen im Überblick**

| Schnittstelle | Richtung | Transport | Auth | Format | Rolle/Lizenz | Einzelnutzer vs. Admin | Status |
|---|---|---|---|---|---|---|---|
| WebAPI `triggerAlarm`/`pushMessage`/`chatMessage` | extern → FF Agent | HTTPS POST | Token + HMAC-SHA256, Live zusätzlich Client-Zertifikat | JSON | virtueller Anschluss, Lizenz [U] | Admin/Anschlussbetreiber [A] | [G] Drittcode, PDF ungelesen |
| URL-Alarm (z. B. Web-IO) | extern → FF Agent | HTTPS GET, Port 443 | keine laut Seite | URL | vorkonfigurierter Alarm, BASE PLUS + Gateway | Admin | [G] |
| Webhook bei Alarm | FF Agent → extern | HTTP(S), Methode [U] | [U] | ohne Payload | [U] | vermutlich Admin [A] | [G] nur über Homey-Beschreibung |
| Instant Commands | FF Agent → Haustechnik/IFTTT | je Aktion | je Gerät | – | ab BASE PLUS | Admin | [G]; HTTP-Aktion [U] |
| Gateway PLUS / Node-RED | lokal, bidirektional | lokal; MQTTS 8883 zur Cloud | Hub-Benutzer/Passwort | frei | BASE PLUS + Hardware | Admin | [G] |
| Status-Monitor-Widget-API | FF Agent → extern (Abruf) | HTTPS POST | Display-Token + Cookie | JSON [A] | Status-Monitor | Admin gibt Token | [G] Drittcode, inoffiziell |
| Alarm-Eingänge (E-Mail, SMS, Fax, 5-Ton, POCSAG, eMID, EDP4, TETRA, LARDIS) | extern → FF Agent | je Anschluss | je Anschluss | je Quelle | teils kostenpflichtig | Admin | [G] |
| Rückmeldung (Zu-/Absage) | extern → FF Agent | [U] | [U] | Verkehrsmittel, optional Koordinaten | [U] | Einzelnutzer [A] | [G] Homey-App, Details [U] |
| Push auf Smartphone | FF Agent → App | Push | App-Login | Notification | alle | Einzelnutzer | [G]; per Companion-Sensor nur Android |

**REST/WebAPI (extern → FF Agent).** [G, Drittcode] Endpunkte `POST https://api.service.ff-agent.com/v1/WebService/triggerAlarm` und `.../pushMessage` (Live); Free-Variante `https://free.api.service.ff-agent.com/v1/WebService/...`; laut Suchtreffer zur v1.5-PDF auch `chatMessage` [U, Snippet]. Auth: Header `webApiToken`, `accessToken`, `selectiveCallCode`, `hmac`; HMAC-SHA256 (Hex) über `webApiToken + selectiveCallCode + accessToken + JSON-Body` mit dem `webApiKey`; Live zusätzlich **Client-Zertifikat** (PKCS#12). Body JSON. Quellen: https://raw.githubusercontent.com/Schrolli91/BOSWatch/master/plugins/FFAgent/FFAgent.py , https://github.com/Richard5A/FF-Agent-Alarmierungsapp-GF (README und `api/index.js`). IP-Filter und Aktivierung je virtuellem Anschluss laut Snippet zur PDF [U]. Wo ein Einzelnutzer Token, Key und Zertifikat bekommt, ist [U]; vermutlich nur über FF Agent bzw. Organisations-Admin [A]. Das README der Webapp nennt nicht, wie man das Zertifikat erhält [G]. Anschlüsse legt laut Doku die Organisation nur für Pager selbst an, andere FF Agent oder eine Superorganisation [G] https://helpcenter.ff-agent.com/webui/erste-schritte/alarmierung/ .

**Lesende Schnittstelle (Abruf).** Eine dokumentierte lesende REST-API wurde **nicht** gefunden [U]. Es existiert die interne **Widget-API des Status-Monitors**: `POST https://www.ff-agent.com/status-monitor-v2/WidgetViewApi/ajax_data/{endpoint}?displayToken=…` mit Cookie `organisationToken`; Endpunkte `ACTIVE_MISSION_INFO`, `TEAM_STATUS`, `PERSONS_AVAILABILITY` [G aus Drittcode] https://github.com/Richard5A/FF-Agent-Alarmierungsapp-GF (`api/index.js`). Sie ist nicht als öffentliche API dokumentiert und kann sich ohne Ankündigung ändern [A]. Die Tokens stammen laut README aus einer Anfrage beim Status-Monitor (Admin-Bereich [A]).

**Webhook / HTTP-Aufruf bei Alarm (FF Agent → extern).** [G] Die Homey-App (v0.1.4) triggert, wenn „FF-Agent den Webhook der Feuerwehr anpingt“; der Webhook enthält **keine Daten**. https://homey.app/a/com.stefanbauer.ff-agent , https://homey.app/en-ae/app/com.stefanbauer.ff-agent/ . Ob das ein Instant Command mit HTTP-Aktion, ein IFTTT-Trigger oder eine andere Funktion ist, ist **nicht dokumentiert** [U]. Auf ff-agent.com steht, Instant Commands können „Systeme über IFTTT steuern“ [G] https://www.ff-agent.com/alarmierung.html . Ein Loxforum-Beitrag von 2021 nennt als Schnittstelle „eine IFTTT-Regel“ (Seite lieferte 403, nur Suchsnippet [U]) https://www.loxforum.com/forum/german/software-konfiguration-programm-und-visualisierung/331026-ifttt-zu-loxone .

**Instant Commands.** [G] Auslöser: Alarm, Fahrzeugstatusänderung, WebAPI-Aufruf; Aktionen steuern Shelly, Web-IO, KNX, WAGO, Tetra SDS, IFTTT; umgekehrt kann ein externes Gerät (BMA) per URL einen vorkonfigurierten Alarm auslösen. https://helpcenter.ff-agent.com/technik/gateway-plus/automatisierungstechnik/ , https://helpcenter.ff-agent.com/technik/gateway/tor-und-lichtsteuerung/ , https://www.ff-agent.com/geraetehaus-automatisierung.html . Voraussetzung dort: mindestens BASE PLUS und ein Gateway im Gerätehaus (lokale Variante). Ob es eine **generische HTTP/Webhook-Aktion** gibt, ist offen [U]; Home Assistant, HTTP und Webhook werden auf den Seiten nicht genannt [G].

**Gateway PLUS mit Node-RED.** [G] Node-RED läuft lokal auf dem Gateway PLUS, Anlage als „Node-RED Hub“ unter Einstellungen > IoT-Hubs mit Name, Benutzer, Passwort; Nodes per „Palette verwalten“ nachinstallierbar. https://helpcenter.ff-agent.com/technik/gateway-plus/automatisierungstechnik/ . Das erlaubt einen lokalen Weg zu HA (Flow sendet HTTP/MQTT an HA) [A], setzt aber Gateway-PLUS-Hardware und BASE PLUS voraus. Das Gateway verbindet sich ausgehend über 80/443 und MQTTS 8883 mit dem FF-Agent-Rechenzentrum [G] https://helpcenter.ff-agent.com/technik/gateway/voraussetzungen/ . Ob es Daten an einen lokalen MQTT-Broker ausgibt, ist [U].

**Monitor-/Alarmdisplay.** [G] Status-Monitor läuft im Browser oder auf Raspberry Pi, Konfiguration im Status-Monitor-Editor, Widgets u. a. Team-Status, Einsatzinformationen, Karten, Ausrückanordnung. Datenabruf, Auth und Schnittstelle sind auf der Seite nicht beschrieben. https://helpcenter.ff-agent.com/technik/status-monitor/ueberblick/ . Ein iframe im HA-Dashboard wäre denkbar [A], nicht geprüft (Login/Token, Datenschutz).

**E-Mail/SMS/Fax (Eingang).** [G] FF Agent wertet Alarmquellen aus: 5-Ton, POCSAG/DME, E-Mail, Fax (Gateway), SMS (kostenpflichtig), TETRA SDS/Callout, Eurofunk eMID, EDP4 u. a. https://www.ff-agent.com/alarmierung.html , https://www.ff-agent.com/kosten.html . Das betrifft den Eingang in FF Agent, nicht die Ausgabe an HA. Alarmwege an Personen sind Push, Anruf, Mail [G] https://helpcenter.ff-agent.com/webui/erste-schritte/alarmierung/ ; Inhalt/Format der Mail [U]. IMAP-Auswertung in HA wäre möglich [A], wenn die Alarm-Mail in einem Postfach des Nutzers ankommt.

**Leitstellen/Drittsysteme.** [G] Genannt werden Eurofunk eMID/MQTT, EDP4, TETRA, WDX3, LARDIS, Leitstelle Tirol, Alarmfax (alles Eingang). Alamos, FE2 und Divera werden auf den Produktseiten **nicht** genannt [G] https://www.ff-agent.com/alarmierung.html ; eine Kompatibilität ist nicht belegt [U]. BOSWatch hat ein FFAgent-Plugin (Alarm per WebAPI einspeisen) [G] https://github.com/Schrolli91/BOSWatch/tree/master/plugins .

**Rückmeldungen und Verfügbarkeit.** [G] App: Zu-/Absage inkl. Verkehrsmittel, Standortfreigabe, voraussichtliche Anfahrtszeit; Verfügbarkeit manuell, geplant oder per GPS-Radius (Standard 10 km) bzw. Zeitplan; Status in der Personenübersicht rot/gelb. https://helpcenter.ff-agent.com/apps/ff-agent-app/einsatz/ , https://helpcenter.ff-agent.com/apps/ff-agent-app/einstellungen/ . Die Homey-App kann per Flow zu-/absagen (Verkehrsmittel, optional Breite/Länge) [G] https://homey.app/a/com.stefanbauer.ff-agent ; es gibt also eine Schnittstelle für Einzelnutzer [A], Endpunkt und Auth sind öffentlich nicht dokumentiert [U]. Verfügbarkeit **setzen** per API: [U]. Verfügbarkeit **lesen**: nur inoffiziell über `PERSONS_AVAILABILITY` (s. o.).

**Push auf dem Smartphone.** [G] Der Companion-App-Sensor „Last Notification“ (Android) liest per NotificationListenerService die zuletzt gepostete Benachrichtigung (Titel, Text, Paketname, Kanal-ID); er braucht eine Sonderberechtigung und eine Allow-List; **nur Android**. https://companion.home-assistant.io/docs/core/sensors . Damit lässt sich die FF-Agent-Push abgreifen [A]. Einschränkungen [A]: nur der Text der Benachrichtigung; Zuverlässigkeit hängt von Akku-Optimierung ab; kein iOS; Alarmtext landet im HA-Recorder; keine Rückmeldung möglich.

### 3.3 Alarmformat (Frage 3)

Ein öffentlich dokumentiertes Format der **ausgehenden** Daten an HA gibt es nicht; der Homey-Webhook hat **keinen Payload** [G]. Für die **eingehende** WebAPI (`triggerAlarm`) zeigt das BOSWatch-Plugin die JSON-Feldnamen [G, Drittcode, ca. 2019/2020, mit bekannten Fehlern]: `keyword` (Stichwort), `district` (Ortsteil), `object`, `location`, `note`, `message`, sowie leer gesetzt `alarmDate`, `type`, `operationResources`, `operationSchedule`, `lat`, `lng`, `easting`, `northing`, `alarmMessage`. Das deutet auf ein internes Einsatzmodell mit Stichwort, Ort, Koordinaten (WGS84 und Hoch-/Rechtswert), Einsatzmitteln und Zeitplan hin [A]. Die App zeigt zusätzlich Meldebild, Anlass, Mitteiler/Patient, Einsatzort, Ausrückanordnung, Hydrantendaten, Anfahrtskarte [G] https://helpcenter.ff-agent.com/webui/erste-schritte/alarmierung/ , https://www.ff-agent.com/alarmierung.html . Die Antwortstruktur von `ACTIVE_MISSION_INFO` ist unbekannt (Drittcode wertet nur das Feld `error` aus) [G]. Echte Beispielpayloads wurden nicht gefunden und nicht übernommen.

### 3.4 Push oder Polling, Limits, AGB, Datenschutz (Frage 4)

- Push: FF Agent alarmiert per Push an die App [G]. Ein Webhook-Push an Dritte ist als Homey-Muster belegt [G], offizielle Beschreibung [U].
- Polling: nur über die inoffizielle Widget-API (Webapp pollt alle 15 s, [G] README) belegt; offizielle Polling-API [U].
- Rate-Limits: öffentlich **nicht dokumentiert** [U]. (DiveraControl nennt zum Vergleich ein Minimum von 5 s als Selbstbeschränkung [G].)
- AGB/Bedingungen für Drittanbieter-Integrationen: Auf der Startseite ist keine AGB-Seite verlinkt, `/agb.html` liefert 404 [G]. Aussagen zu Drittintegrationen: nichts gefunden [U]. Die WebAPI wird als „für eigene Lösungen oder Drittanbietersoftware“ beworben [G] https://www.ff-agent.com/alarmierung.html ; ihre PDFs sind öffentlich abrufbar [G].
- Datenschutz: Verantwortlicher ist der Hersteller, Datenschutz-Kontakt genannt [G] https://www.ff-agent.com/datenschutz.html . Der Abschnitt zu „Alarmdaten und Schnittstellen“ ist inhaltsleer [G]. Alarmdaten enthalten Adressen, ggf. Patientendaten und Personenstatus, also personenbezogene, teils besonders schützenswerte Daten [A]. Folgerungen [A]: Daten minimal halten (Webhook ohne Payload ist datensparsam), keine Alarminhalte in Logs/Diagnostics, Hinweis an Nutzer, dass der HA-Recorder Alarmtexte speichert, Weitergabe von Einsatzdaten nur mit Zustimmung der Einheit (Wehrführung/Datenschutzbeauftragter).

### 3.5 Community-Lösungen und Vergleich (Frage 5)

FF Agent:
- **Keine** HA-Integration, kein Node-RED-Flow, kein HA-Forum- oder Reddit-Beitrag gefunden (mehrere Suchen, 2026-10-16) [G für Suchergebnis; Lücke nicht beweisbar].
- Homey-App von Stefan Bauer, v0.1.4 (Webhook-Trigger, Zu-/Absage) [G] https://homey.app/a/com.stefanbauer.ff-agent . Ein öffentliches Repo wurde nicht gefunden [U]; der Entwickler ist laut Seite per E-Mail erreichbar (Adresse dort).
- BOSWatch-Plugin „FFAgent“ (Alarm einspeisen) [G]; Webapp „FF-Agent-Alarmierungsapp-GF“ (Alarm auslösen, Personenstatus alle 15 s) [G] https://github.com/Richard5A/FF-Agent-Alarmierungsapp-GF .

Vergleichssysteme (übertragbare Muster):
- **DIVERA 24/7:** HACS-Integration `moehrem/DiveraControl` nutzt Divera API v2, Auth per Benutzer/Passwort oder API-Key, **Polling** (Vorschlag 60 s, bei Einsatz 30 s, Minimum 5 s), Events für Alarm geöffnet/aktualisiert/geschlossen, Sensoren, Device-Tracker, Kalender, Schreibfunktionen mit Rollenprüfung; für Echtzeit ein **HA-Webhook**, den Divera bei neuem Alarm aufruft und der nur einen Datenabruf auslöst [G] https://github.com/moehrem/DiveraControl . Ioboker-Adapter für Divera pollt `/api/last-alarm` [G] https://forum.iobroker.net/post/563482 . Ein weiteres Repo `fwmarcel/home-assistant-divera` kam in Suchtreffern vor, war aber per Abruf 404 [U]. **Muster:** Webhook (ohne/mit wenig Payload) als Trigger plus anschließender Abruf. Bei FF Agent fehlt dafür die dokumentierte Abruf-API.
- **Alamos FE2:** keine HA-Integration gefunden [U]. **BOSMon:** Anbindung über BOSWatch-Plugin (Eingang); kein HA-Muster geprüft [U].
- Wachalarm-IP (Leitstelle Lausitz) als HA-Add-on mit MQTT-Discovery [G] https://community.simon42.com/t/wachalarm-ip-bridge-einsatzdaten-der-leitstelle-lausitz-in-home-assistant/90329 : anderes System, Muster „Bridge → MQTT“.

### 3.6 Bewertung der Integrationswege (Frage 6)

Bewertungsmatrix (alle Bewertungen [A]):

| Weg | Machbarkeit | Nötige Rechte/Lizenz | Latenz | Robustheit | Datenschutz | Datenumfang |
|---|---|---|---|---|---|---|
| A. Webhook von FF Agent an HA (`webhook`-Komponente, Config Flow erzeugt URL) | hoch, **wenn** FF Agent den Webhook sendet (Homey-Beleg); Einrichtung [U] | vermutlich Admin, ggf. BASE PLUS [U] | Sekunden | mittel: HA muss aus dem Internet erreichbar sein (Nabu Casa oder Reverse Proxy), Retry unbekannt | gut: kein Payload, URL ist das Geheimnis | nur „Alarm ist da“ |
| B. Polling der Status-Monitor-Widget-API | technisch erprobt (Drittapp) | Admin muss Display-Token geben | 15–60 s | niedrig: inoffiziell, kann brechen; Bedingungen unklar | schwach: viele Personendaten, Token nötig | hoch (aktiver Einsatz, Teamstatus, Verfügbarkeit) |
| C. Polling einer offiziellen REST-API | **nicht belegt** [U] | – | – | – | – | – |
| D. Companion-App „Last Notification“ | hoch auf Android, nicht auf iOS | keine FF-Rechte, Einzelnutzer | Sekunden | niedrig-mittel: Akku/OS, Textparsing | mittel: Alarmtext im HA-Verlauf | Text der Notification |
| E. E-Mail über IMAP | machbar | Alarmweg „Mail“, Postfach; Format [U] | Sekunden bis Minuten | mittel: Parsing, Mailserver | mittel bis schlecht: Postfach-Zugang, Alarmtext | je nach Mailtext |
| F. Gateway PLUS + Node-RED → HA | hoch für Gerätehaus-Admins | Admin, BASE PLUS, Hardware | niedrig | hoch (lokal) | gut (lokal) | frei konfigurierbar [U] |
| G. WebAPI von HA nach FF Agent (Alarm/Nachricht senden) | technisch möglich | Token, Key, Zertifikat, Anschluss | niedrig | hoch | riskant: löst **echte Alarmierung** aus | – |

Einschätzung [A]: Weg A ist das passende Muster (Push, entspricht Homey- und Divera-Praxis) und datensparsam. Weg F ist der robusteste, aber nur für Einheiten mit Gateway PLUS. Weg D ist für Einzelnutzer ohne Admin-Rechte der einzige Weg ohne FF-Agent-Konfiguration. B nur als Notlösung und nur mit Zustimmung des Herstellers. G nicht anbieten ohne ausdrückliche Nutzerfreigabe.

### 3.7 Empfehlung `iot_class`

Definitionen laut HA: `cloud_push` = Verbindung über die Cloud, die Cloud meldet Änderungen; `local_push` = direkte Verbindung zum Gerät, das Gerät meldet Änderungen; `cloud_polling` = Cloud, Abfrage in Intervallen [G] https://contributors.home-assistant.io/core/integrations/manifest/ .

**Empfehlung: `cloud_push`** [A] für Weg A: FF Agent (Cloud-Dienst) ruft den Webhook in HA auf. `local_push` wäre nur bei Weg F (lokales Gateway) zutreffend, `cloud_polling` nur, wenn Weg B oder C die Hauptquelle wird. Das Manifest erst ändern, wenn der Webhook-Weg vom Hersteller oder Nutzer bestätigt ist.

## 4. Fragen und offene Punkte

### 4.1 Fragen an den Nutzer

1. Welche Rolle hat der Nutzer in FF Agent: nur Einsatzkraft oder Admin der Einheit (Zugriff auf Web-UI > Admin > Instant Commands / Gateways und Anschlüsse)?
2. Welche Lizenz hat die Einheit (FREE/STARTER/BASE/BASE PLUS/PRO)? Gibt es ein Gateway, Gateway PLUS oder einen Node-RED-Hub?
3. Android oder iOS (wegen Companion-Sensor)? Ist HA von außen erreichbar (Nabu Casa, Reverse Proxy)?
4. MVP-Umfang: nur Alarm-Trigger, oder auch Einsatzdetails, Zu-/Absage, Verfügbarkeit?
5. Ist die Einheit (Wehrführung/Datenschutzbeauftragter) mit einer Anbindung einverstanden? Soll die Integration später öffentlich werden?
6. Gibt es in der Web-UI des Nutzers einen Eintrag wie „Webhook“ bzw. Instant Commands mit HTTP-Aktion? Screenshots ohne Tokens wären hilfreich. (Der Researcher meldet sich nicht bei FF Agent an.)
7. Kann der Nutzer die beiden PDFs (WebAPI v1.6, Instant Commands) im Klartext liefern?

### 4.2 Fragen an den Hersteller

1. Wie wird der „Webhook der Feuerwehr“ (Homey-Trigger) eingerichtet; welche Rolle/Lizenz? Methode, Header, Wiederholungen bei Fehler, Signatur?
2. Gibt es einen Webhook mit Payload (Stichwort, Ort, Koordinaten, Alarm-ID) oder ist er geplant?
3. Gibt es eine offizielle lesende API (aktiver Einsatz, Historie, Rückmeldungen, Verfügbarkeit) mit Einzelnutzer-Token statt Display-Token?
4. Wie authentifiziert die Rückmeldung (Zu-/Absage) der Homey-App, und darf eine HA-Integration sie nutzen?
5. Gibt es Rate-Limits, AGB oder ein Freigabeverfahren für Drittanbieter-Integrationen? Ist eine öffentliche Open-Source-Integration erwünscht?
6. Ist das Client-Zertifikat der WebAPI für Einzelnutzer erhältlich oder nur für Anschlussbetreiber?
7. Ist die IFTTT-Schnittstelle noch in Betrieb?

### 4.3 Offene Punkte / Unsicherheiten

- Inhalt von `Dokumentation_WebAPI.pdf` (v1.6) und `Dokumentation_InstantCommands.pdf` nicht gelesen [U]; wichtigste Primärquelle.
- Einrichtung, Format und Payload des Alarm-Webhooks, HTTP-Aktion bei Instant Commands: [U].
- Richtung und Umfang der WebAPI (nur eingehend?) aus Drittcode abgeleitet [A].
- Widget-API inoffiziell; Stabilität und Zulässigkeit [U].
- Die Helpcenter-Seite `technik/gateway/` ergab keinen verwertbaren Text; dazu gelieferte Zusammenfassungen wurden verworfen.
- Loxforum-Beitrag nur als Snippet (403).
- Keine AGB-Seite gefunden; Datenschutzerklärung ohne Inhalt zu Alarmdaten/Schnittstellen.

## 5. Empfehlung für das weitere Vorgehen

1. **Vor jeder Implementierung** die beiden PDFs im Klartext beschaffen (Nutzer oder Werkzeug mit PDF-Textextraktion) und eine kurze Folgerecherche starten.
2. Parallel eine Anfrage an den Hersteller (Fragen 4.2) durch den Nutzer; sie klärt Webhook, Payload, lesende API und Rückmeldung.
3. MVP-Architektur: Config Flow erzeugt eine Webhook-ID und zeigt die URL an; Binary-Sensor „Alarm aktiv“ plus HA-Event `ff_agent_alarm`; Payload (falls vorhanden) in Diagnostics redigiert. `iot_class: cloud_push`.
4. Optionale Zusatzwege dokumentieren: Blueprint für Companion-App „Last Notification“ (Android) und Hinweis auf Node-RED/Gateway PLUS für Admins. Keine Nutzung der inoffiziellen Widget-API ohne Zustimmung des Herstellers.
5. Rückmeldung (Zu-/Absage) und Verfügbarkeit erst als zweite Ausbaustufe, wenn der Hersteller die Authentifizierung bestätigt.
6. Alarmauslösung per WebAPI nicht umsetzen (echte Alarmierung), außer auf ausdrückliche Nutzerfreigabe.
7. Hinweis: Das Repo ist privat; HACS braucht öffentliche Repos (siehe `261016-hacs-anforderungen.md`).

## 6. Quellenverzeichnis (Abruf 2026-10-16)

- https://www.ff-agent.com , /alarmierung.html , /kosten.html , /geraetehaus-automatisierung.html , /kontakt.html , /datenschutz.html
- https://helpcenter.ff-agent.com (Sitemap: https://helpcenter.ff-agent.com/sitemap.xml)
- https://helpcenter.ff-agent.com/webui/erste-schritte/alarmierung/
- https://helpcenter.ff-agent.com/webui/erste-schritte/berechtigungen/
- https://helpcenter.ff-agent.com/technik/gateway-plus/automatisierungstechnik/
- https://helpcenter.ff-agent.com/technik/gateway/tor-und-lichtsteuerung/
- https://helpcenter.ff-agent.com/technik/gateway/voraussetzungen/
- https://helpcenter.ff-agent.com/technik/status-monitor/ueberblick/
- https://helpcenter.ff-agent.com/apps/ff-agent-app/einsatz/ und /einstellungen/
- https://helpcenter.ff-agent.com/webui/uebersicht/touren/pdfs/Dokumentation_WebAPI.pdf (v1.6, nicht lesbar)
- https://helpcenter.ff-agent.com/webui/uebersicht/touren/pdfs/Dokumentation_InstantCommands.pdf (Stand 2019, nicht lesbar)
- https://free.ff-agent.com/app/public/docs/Dokumentation_WebAPI.pdf (v1.5, nicht lesbar)
- https://homey.app/a/com.stefanbauer.ff-agent , https://homey.app/en-ae/app/com.stefanbauer.ff-agent/
- https://raw.githubusercontent.com/Schrolli91/BOSWatch/master/plugins/FFAgent/FFAgent.py
- https://github.com/Schrolli91/BOSWatch/issues/356
- https://github.com/Richard5A/FF-Agent-Alarmierungsapp-GF
- https://github.com/moehrem/DiveraControl
- https://forum.iobroker.net/post/563482
- https://community.simon42.com/t/wachalarm-ip-bridge-einsatzdaten-der-leitstelle-lausitz-in-home-assistant/90329
- https://www.loxforum.com/forum/german/software-konfiguration-programm-und-visualisierung/331026-ifttt-zu-loxone (nur Snippet)
- https://companion.home-assistant.io/docs/core/sensors
- https://contributors.home-assistant.io/core/integrations/manifest/
