# Recherche: Persönliche Webhooks, Zusage/Absage und Einsatzdetails für Einsatzkräfte

TODO-ID: `261016-ffagent-klaerung` · Abruf der Quellen: 2026-10-16 · Autor: Researcher

Kennzeichnung wie in `261016-ffagent-schnittstellen.md`: **[G]** gesichert (Quelle gelesen),
**[A]** abgeleitet (eigene Schlussfolgerung), **[U]** unbekannt oder öffentlich nicht dokumentiert.

Randbedingungen eingehalten: keine Anmeldung, keine Accounts, keine Formulare, nichts
ausgeführt. Gelesen wurden nur öffentliche Seiten, öffentliche PDFs und öffentlicher
Quellcode. Zusammenfassungen des Abruf-Tools, die nicht zum Seiteninhalt passten, wurden
verworfen (siehe Abschnitt 7).

## 1. Fragestellung

1. Was ist über die „Persönlichen Webhooks“ (FF Agent → extern bei Alarm) öffentlich bekannt?
2. Wie funktionieren Zu-/Absage der Homey-App (Endpunkt, Authentifizierung)? Gibt es Quellcode?
3. Gibt es andere Clients mit Nutzerebene?
4. Woher kann eine Einsatzkraft ohne Admin-Rechte Einsatzdetails bekommen?
5. Gibt es Aussagen des Herstellers zu inoffiziellen Clients?

## 2. Kurzfazit

- **Persönliche Webhooks sind öffentlich nirgends dokumentiert** [G: Suche, Sitemap mit 74 Seiten, Release Notes, Homey, GitHub]. Konfiguration, Auslöser, Zeitplan, Retry, Signatur und Lizenz sind [U]. Nur die Web-UI des Nutzers kann das klären.
- **Kein Endpunkt für die Zusage gefunden.** Auch keine Authentifizierung dafür. Die Homey-App hat **keinen öffentlichen Quellcode** [G]; die öffentlichen Store-Metadaten enthalten weder Settings noch Pairing-Ansicht.
- Aus den Homey-Metadaten folgt [G]: Der Webhook trägt **keine Daten**, das Trigger-Token ist nur die **Alarmzeit**. Die Zusage kennt „Anfahrt“ (Auto, zu Fuß, Fahrrad) und optional Breite/Länge; sie bezieht sich auf „den aktuell aktiven Einsatz“.
- **Einsatzdetails für Normalnutzer:** Es gibt einen **persönlichen iCal-Kalender-Feed** mit eigener Basic-Auth oder tokenhaltiger URL (`https://api.ff-agent.com/app2/ical/...`), der laut PDF (Stand 2019) „Einsätze, an denen Sie teilgenommen haben“ enthält [G]. Das ist die einzige belegte Nutzer-Schnittstelle mit Daten nach außen, aber nur für abgeschlossene bzw. besuchte Einsätze und im Inhalt unbekannt [U].
- Es gibt zusätzlich einen **öffentlichen, unauthentifizierten Homepage-Widget-Feed** (`https://pd.service.ff-agent.com/hpWidget/<UID>`) mit Einsatzlisten einer Einheit [G, Drittcode]. Er wird von der Einheit freigeschaltet (vermutlich Admin) und liefert nur Veröffentlichtes [A]. Für Alarmdetails an die einzelne Einsatzkraft ungeeignet.
- Keine weiteren Clients (Garmin, Wear OS, Apple Watch, Alexa, Stream Deck, Bibliotheken) gefunden [G für Suchergebnis]. Keine Aussagen des Herstellers zu inoffiziellen Clients; keine AGB-Seite auffindbar.
- **Empfehlung:** Webhook-Empfang in HA ist der richtige Alarm-Trigger (ohne Payload). Die Zusage erst bauen, wenn der Hersteller den Endpunkt bestätigt. Bis dahin Screenshot-/Feldliste aus der Web-UI beschaffen (Abschnitt 6).

## 3. Befunde

### 3.1 Persönliche Webhooks

**Öffentliche Dokumentation: nicht vorhanden.**

- Die Helpcenter-Sitemap listet 74 URLs; keine trägt Webhook, Automatisierung, Profil-Automatisierung, Smart Home, Homey, IFTTT, Alexa oder API im Namen [G] https://helpcenter.ff-agent.com/sitemap.xml
- Release Notes Web-UI (jüngster Eintrag 04.11.2025) und Apps (2026: Android 2.2.0, 2.3.0, iOS 2.1.1, 2.2.0) enthalten keinen Eintrag zu Webhooks oder Automatisierung [G] https://helpcenter.ff-agent.com/neuigkeiten/releases/web-ui/ , https://helpcenter.ff-agent.com/neuigkeiten/releases/apps/ . Die Web-UI-Notes sind offenbar nicht aktuell geführt (nichts nach 11/2025) [A]; die Einführung der Funktion lässt sich daraus **nicht** datieren [U].
- Die Hilfeseiten zu Personen, Überblick und Einsatz-App enthalten nichts zu Webhook, „Einsatzrückmeldungen“ (als Automatisierungs-Reiter), „Partnerbenachrichtigungen“ oder MoWaS [G] https://helpcenter.ff-agent.com/webui/erste-schritte/personen/ , https://helpcenter.ff-agent.com/webui/erste-schritte/ueberblick/ , https://helpcenter.ff-agent.com/apps/ff-agent-app/einsatz/ . Die Personenseite nennt nur „Personen > Bearbeiten > Profil > Alarmierung/Benachrichtigung“ als Ort der persönlichen Benachrichtigungswege [G].
- Die PDF-Übersicht des Helpcenters führt als Automatisierung nur Instant Commands (Tore/Licht) und die Web-API [G] https://helpcenter.ff-agent.com/webui/uebersicht/touren/ .
- Suchen nach „persönliche Webhooks“ + FF Agent, Homey-Forum, Garmin/Alexa ergaben keinen Treffer außer der Homey-App-Seite [G für Suchergebnis; Lücke nicht beweisbar].

**Einzig belegte Außenwirkung:** Die Homey-App löst aus, „wenn FF-Agent den Webhook dieser Feuerwehr aufruft“; der Webhook enthält keine Daten, als Flow-Token steht die Alarmzeit zur Verfügung [G] https://homey.app/en-ae/app/com.stefanbauer.ff-agent/ , https://apps-api.athom.com/api/v1/app/com.stefanbauer.ff-agent . Die Formulierung „dieser Feuerwehr“ (Gerätetyp „Feuerwehr/Wache“) sagt nichts darüber, ob der Aufruf aus einem Nutzer-Webhook oder aus einer Einheitsfunktion stammt [U]. Dass die Homey-App den **persönlichen** Webhook nutzt, ist plausibel (Nutzer-Reiter „Einsatzrückmeldungen“ liegt im selben Menü wie die Webhooks, Zu-/Absage ist personenbezogen) [A], aber nicht belegt.

**Antworten auf die Einzelfragen:**

| Frage | Stand |
|---|---|
| Konfigurierbar: URL, Methode, Header, Body, Platzhalter | [U]. Aus dem Homey-Hinweis „carries no data“ folgt [A], dass der Dienst zumindest in diesem Anwendungsfall ohne Body auskommt; ob es Platzhalter gibt, ist offen. |
| Auslöser (jeder Alarm / nur eigene Alarmierung / Probealarm) | [U]. Plausibel: nur Alarme, an denen die Person alarmiert wird [A]. Probealarm offen. |
| Zweck des Zeitplans (Wochentage/Zeit) | [U]. Wahrscheinlich Zeitfenster, in denen der Webhook feuert (z. B. nur nachts oder nur Wochentage) [A]. Folge für HA: Alarme außerhalb des Fensters kommen nicht an; der Nutzer muss das Fenster bewusst setzen. |
| Wiederholung bei Fehler, Signatur | [U]. Kein Hinweis auf Signatur oder HMAC (die WebAPI-HMAC betrifft die eingehende Richtung). Die Webhook-URL mit Zufalls-ID wäre das einzige Geheimnis [A]. |
| Seit wann, Lizenz | [U]. Die Einheit des Nutzers hat PRO (Antwort Nutzer). Ob die Funktion lizenzabhängig ist, ist offen. |

### 3.2 Homey-App `com.stefanbauer.ff-agent`

- **Quellcode:** nicht gefunden. Das öffentliche Store-JSON nennt `sourceUrl`, `homepage` und GitHub als leer/fehlend; Support nur per E-Mail an den Autor (Adresse auf der Store-Seite), Autor „nicht verifiziert“ [G] https://apps-api.athom.com/api/v1/app/com.stefanbauer.ff-agent . In den GitHub-Repo-Suchen (ff-agent, ffagent, homey + stefanbauer) fand sich kein Repo dazu [G für Suchergebnis]. Der Homey-App-Bundle-Download wurde nicht versucht (binär, und es wäre Herunterladen fremden Codes).
- **Metadaten laut Store [G]** (Version 0.1.4, „Erste Version“, Homey ab 5.0.0, Kategorie Tools, Berechtigung Geolokalisierung, zuletzt vor etwa einem Monat aktualisiert, Plattform `local`):
  - Ein Gerätetyp `wache`, Klasse `sensor`, Capability `ffagent_last_alarm`.
  - Trigger „Ein Einsatz wurde alarmiert“ mit Alarmzeit als Token.
  - Aktion „Einsatz zusagen“: Anfahrt (Auto, zu Fuß, Fahrrad), Breite und Länge optional, sonst aus den Geräteeinstellungen.
  - Aktion „Einsatz absagen“, bezogen auf den aktiven Einsatz.
  - Die Store-Daten enthalten **keine** `settings`-Felder und **keine** Pairing-Ansicht [G]. Ob die App beim Hinzufügen des Geräts Zugangsdaten abfragt, ist damit [U]. Die Geräteeinstellungen für Koordinaten existieren laut Karten-Hinweis [G], ihre Felder sind unbekannt.
- **Endpunkt und Authentifizierung der Zusage:** nicht ermittelbar [U]. Mögliche Varianten (alle [A], nicht belegt): (a) Anmeldung mit FF-Agent-Benutzername und -Passwort, wie die Mobile-App und die Web-UI (der Helpcenter-Text nennt „Nutzername und Passwort“ oder QR-Code-Login als Login-Wege [G] https://helpcenter.ff-agent.com/webui/erste-schritte/ueberblick/ ); (b) ein vom Nutzer erzeugtes Token, etwa aus dem „Einsatzrückmeldungen“-Reiter; (c) eine in den persönlichen Webhook eingebettete Rückmelde-URL. Der Homey-Hinweis „Webhook trägt keine Daten“ spricht gegen (c), sofern nichts in der URL steckt.

### 3.3 Andere Clients mit Nutzerebene

- Gesucht wurde nach Garmin, Wear OS, Apple Watch, Alexa, Stream Deck sowie GitHub-Repos zu `ff-agent`, `ffagent`, `api.service.ff-agent.com`, `app.ff-agent.com`. **Kein Client mit Nutzerebene gefunden** [G für Suchergebnis].
- GitHub-Repo-Suche (API, ungefiltert, Abruf 2026-10-16) fand FF-Agent-bezogen nur: `kvn-stgl/FFAgent2Listmonk` (CSV-Export-Konverter), `michi-s/CardiLink2FFA` (Relay an die Web-API, Client-Zertifikat vom FF-Agent-Support, Stand 2020), `wiwimaster/ff-agent-wp-mission-import` (WordPress-Import, siehe 3.4) [G] https://github.com/kvn-stgl/FFAgent2Listmonk , https://github.com/michi-s/CardiLink2FFA , https://github.com/wiwimaster/ff-agent-wp-mission-import . Alle übrigen „ff-agent“-Repos betreffen andere Themen oder haben keine Beschreibung. Nicht jedes beschreibungslose Repo wurde geöffnet [U].
- Bekannt aus der Vorrecherche: BOSWatch-Plugin und Alarmierungs-Webapp (Admin-Ebene, siehe `261016-ffagent-schnittstellen.md`).
- Über die Endpunkte, mit denen die offizielle Mobile-App Zu-/Absage sendet, ist öffentlich nichts bekannt [U]. Ein Mitschneiden des App-Verkehrs oder Zerlegen der App wurde nicht versucht (außerhalb des Auftrags, Nutzungsbedingungen unklar).

### 3.4 Einsatzdetails für Einsatzkräfte ohne Admin-Rechte

1. **Persönlicher iCal-Kalender (belegt, Nutzerebene).** Laut `Dokumentation_Kalenderabonnements.pdf` (iText-Erstellung 11.02.2019, Stand also 2019) gibt es im persönlichen Profil „Kalenderabonnements“ [G] https://helpcenter.ff-agent.com/webui/uebersicht/touren/pdfs/Dokumentation_Kalenderabonnements.pdf :
   - Zugriff muss pro Nutzer aktiviert werden („Zugriff aktiviert“).
   - Zwei Varianten: Basis-Authentifizierung mit **eigens generiertem** Benutzernamen und Kennwort (also nicht die Login-Daten; „Zugangsdaten neu generieren“ möglich) und eine „integrierte“ URL mit Zugangsdaten in der URL. URL-Muster `https://api.ff-agent.com/app2/ical/<Kennung>`.
   - Inhalt des persönlichen Kalenders: **Einsätze, an denen die Person teilgenommen hat**, geplante Schichten, Übungen, Ressourcenreservierungen, News. Eine Filterung ist „nicht möglich“.
   - Folgerung [A]: Gut für Verlauf und Termine; **nicht verlässlich für den laufenden Alarm**, da „teilgenommen“ vermutlich erst nach Zusage/Abschluss zutrifft. Welche Felder ein Einsatz-VEVENT hat (Stichwort, Ort, Beschreibung), ist [U]; die PDF sagt es nicht. Ob die Funktion 2026 unverändert besteht, ist [U]. HA hat eine eingebaute Kalenderintegration für iCal-URLs (nicht geprüft, [A]); Basic-Auth-Fähigkeit wäre zu prüfen.
2. **Homepage-Widget-Feed (belegt, aber Einheitsebene).** `ff-agent-wp-mission-import` (v0.1.1) liest ohne Authentifizierung JSON von `https://pd.service.ff-agent.com/hpWidget/<UID>` (Wurzel mit Jahresdateien, darin Einsatzlisten; Felder u. a. `alarmDate` in Millisekunden, `id`, `url`/`detailUrl` mit `/mission/`; Einzel-JSON je Einsatz) [G] https://raw.githubusercontent.com/wiwimaster/ff-agent-wp-mission-import/main/ff-agent-wp-mission-import.php , `.../classes/class_scheduler.php` , `.../classes/ff-agent-import/class_single_mission_import.php` . Die UID kennt die Einheit; wer sie freigibt, ist [U] (vermutlich Admin, „Veröffentlichung“ [A]). Die Felder einer Einzelmeldung stehen im nicht gelesenen `ffami_mission`-Code [U]. Das ist eine Veröffentlichungsfunktion (Homepage), kein Alarmkanal [A] und datenschutzrechtlich ein anderer Fall.
3. **Status-Monitor-Widget-API** (inoffiziell, Display-Token, Admin) und **WebAPI** (nur eingehend): unverändert aus der Vorrecherche. Beide nicht für Einsatzkräfte.
4. **Platzhalter im persönlichen Webhook:** [U]. Der Homey-Hinweis „keine Daten“ spricht dafür, dass es zumindest in diesem Fall keinen Body gibt. Die Instant-Commands-Doku (2019) kennt Platzhalter für Einsatzdaten in Benachrichtigungen, aber keine Webhook-Aktion [G, Vorrecherche Abschnitt 0]; ob Persönliche Webhooks diese Platzhalter erben, ist offen.
5. **Push-Benachrichtigung der Mobile-App:** Die PDF „Smartphone-Konfiguration“ (2018/2019) bestätigt, dass Alarme als Push (Latenz laut Hersteller 2–3 s) an registrierte Mobilgeräte der Person gehen; im Personenprofil gibt es die Bereiche Profil, Personendaten, Datenschutz, Mobilgeräte, Fähigkeiten, Benachrichtigung [G] https://helpcenter.ff-agent.com/webui/uebersicht/touren/pdfs/Dokumentation_Smartphone_Konfiguration.pdf . Das heißt: Die Alarmdetails liegen in der App; der HA-Weg dahin wäre nur der Companion-Sensor (Android) wie in der Vorrecherche [A].
6. **Erweiterte Einsatzdaten** (Einsatzdatenvorlagen, ab BASE PLUS, Admin) betreffen Berichte und CSV-Export, kein Nutzer-API [G] https://helpcenter.ff-agent.com/webui/uebersicht/touren/pdfs/Dokumentation_Erweiterte_Einsatzdaten.pdf . Sie unterscheiden „sensible Einsatzdaten“, die bei Abschluss entfernt werden [G]; ein Hinweis, Alarmdaten datensparsam zu behandeln [A].

### 3.5 Rechtliches

- Keine Aussage des Herstellers zu inoffiziellen Clients, Reverse Engineering oder Drittanbieter-Integrationen gefunden [U]. `ff-agent.com/agb.html`, `/nutzungsbedingungen.html`, `/impressum.html` liefern 404; auf der Datenschutzseite stehen keine Aussagen zu Schnittstellen oder Drittclients [G] https://www.ff-agent.com/datenschutz.html .
- Die WebAPI wird laut Hersteller-Doku für eigene Lösungen oder Drittanbietersoftware angeboten [G, Vorrecherche]. Persönliche Webhooks und Kalender-Feeds sind **für den Nutzer selbst gedachte, vom Hersteller bereitgestellte Funktionen** [A]; deren Nutzung durch HA ist deshalb unkritischer als jede Nutzung nicht dokumentierter App-Endpunkte [A]. Zu- und Absage über nicht dokumentierte Endpunkte mit Nutzer-Passwort wäre ein Risiko (Kontosperre, Vertragsverstoß, Bruch bei Änderung) [A] und sollte vor einem öffentlichen Release vom Hersteller bestätigt werden.
- Datenschutz: Zugangsdaten zum Nutzerkonto in HA zu speichern wäre sicherheitskritisch (Konto kann Einsatzdaten Dritter sehen) [A]; ein eigener, widerrufbarer Token (wie beim Kalender-Feed „neu generieren“) wäre vorzuziehen.

## 3.6 Nachtrag 2026-10-17: Zusage-/Absage-URLs (Screenshot des Nutzers)

Der Nutzer hat aus der Web-UI die persönlichen Rückmelde-URLs gezeigt. Darstellung hier
**geschwärzt**: Die Kennung ist ein Geheimnis, die Koordinaten stammen aus dem Beispiel.

```text
Zusage: https://www.ff-agent.com/app2/missionreplies/<REPLY_ID>/accept?transport=CAR&lat=<LAT>&lng=<LNG>
Absage: https://www.ff-agent.com/app2/missionreplies/<REPLY_ID>/reject
```

Was die URLs zeigen [G]:
- `<REPLY_ID>` ist eine UUID. Sie identifiziert und berechtigt zugleich, funktioniert also
  wie ein Token in der URL. Ein Passwort oder eine Anmeldung ist nicht nötig.
- `transport` gibt das Verkehrsmittel an; belegt ist der Wert `CAR`. `lat` und `lng`
  sind offenbar optional.
- Neben den URLs zeigt die UI ein Kopier- und ein Öffnen-Symbol.

Was daraus folgt:
- Ein Aufruf per GET funktioniert vermutlich, weil die URL im Browser geöffnet werden
  kann. Das ist abgeleitet [A], nicht geprüft.
- Die URL nennt keine Einsatz-ID. Sie gilt also für den **aktuell aktiven Einsatz**, wie
  bei der Homey-App [A].

Noch offen [U]:
- weitere `transport`-Werte (Homey kennt Auto, zu Fuß, Fahrrad; vermutlich `FOOT`/`BIKE`
  o. ä.)
- Antwortformat und Statuscodes, Verhalten ohne aktiven Einsatz
- ob die Kennung neu erzeugt werden kann
- ob sie dauerhaft gilt oder sich je Einsatz ändert

Folge fürs Design: Option A aus Abschnitt 4 ist damit praktisch belegt. Der Nutzer
kopiert die Zusage-URL in den Config Flow. HA speichert die Kennung als Geheimnis und
ruft `accept` bzw. `reject` auf. Ein Login braucht es nicht.

## 3.7 Nachtrag 2026-10-17: Fundort und offizielle Hinweise zu den Rückmelde-URLs

Quelle ist ein Screenshot des Nutzers aus der FF-Agent-Web-UI. Kennung, Name und
Koordinaten sind hier nicht wiedergegeben. Alle Aussagen in diesem Abschnitt sind [G].

- **Fundort:** *Personen → (eigener Name) → Bereich „Übung/Einsatz“ → „Weblinks für
  Einsatzmeldung“*. Die Seite heißt „URLs für Einsatzmeldung“ und gehört zu den
  persönlichen Einstellungen der Person. Die frühere Annahme *Automatisierung →
  Einsatzrückmeldungen* war **falsch**.
- **Offizielle Hinweise auf der Seite:**
  - Die URLs sind für eigene Rückmeldefunktionen bzw. -geräte gedacht.
  - Sie gelten jeweils nur für diese Person. Zu- bzw. Absage gelten für den jeweils
    aktiven Einsatz.
  - Wie in der App ist eine Zu- oder Absage nur möglich, wenn die Person für den aktiven
    Einsatz alarmiert wurde.
  - Optionale Parameter bei der Zusage:
    - `transport`: `CAR` (Standard), `FEET` oder `BICYCLE`
    - `lat`, `lng`: GPS-Koordinaten des eigenen Standorts, z. B. bei fest installierten
      Geräten
- **Folgen für die Annahmen in ADR 0002:**
  - **A8 bestätigt:** Die UUID gilt je Person und bezieht sich auf den aktiven Einsatz.
  - **A9 geklärt:** Es gibt drei Verkehrsmittel. `transport` ist optional, der Standard ist
    `CAR`.
  - Neu: Ohne Alarmierung der Person ist keine Rückmeldung möglich. Wie FF Agent dann
    antwortet (Status), bleibt offen (A7).

## 4. Folgerungen für das Design (alle [A], solange Webhook-Details [U])

**Wie richtet der Nutzer den Webhook ein?**
1. Config Flow der Integration legt in HA einen Webhook an (`webhook`-Komponente, Zufalls-ID) und zeigt die vollständige URL an. Die Erreichbarkeit hängt vom Nutzer ab:
   - Mit Nabu Casa: Cloudhook-URL (HA bietet `async_generate_cloudhook`, nicht in diesem Auftrag geprüft).
   - Ohne Nabu Casa: externe URL oder Reverse Proxy; der Config Flow sollte die Erreichbarkeit von außen nicht annehmen, sondern erklären.
2. Der Nutzer kopiert die URL in FF Agent: Automatisierung > Persönliche Webhooks > „Webhook hinzufügen“ (Dialogfelder [U]) und wählt einen Zeitplan, der alle gewünschten Zeiten abdeckt (Standard: täglich/ganztägig, falls möglich).
3. HA muss die HTTP-Methode akzeptieren, die FF Agent verwendet (GET oder POST). Beide zulassen, bis geklärt (HA-Webhooks erlauben dies konfigurierbar, [A] nach HA-Kenntnis, nicht in diesem Auftrag geprüft).
4. Antwort schnell mit `200` beantworten; Verarbeitung asynchron. Eine Retry-Logik von FF Agent ist unbekannt, daher **Deduplizierung** (z. B. Alarme innerhalb weniger Sekunden zusammenfassen) einplanen.

**Was kommt an?** Vermutlich nur ein Signal ohne Nutzdaten [G für Homey-Fall]. Aus HA-Sicht: Binary-Sensor „Alarm aktiv“ (mit Zeitüberlauf oder bis Zusage/Absage), Sensor „letzter Alarm“ mit Zeitstempel (Zeitpunkt = Empfang), Event `ff_agent_alarm`. Sicherheit: Die URL ist das einzige Geheimnis [A]; nicht protokollieren, in Diagnostics schwärzen. Falls Header/Body vorhanden sind, nur in redigierter Form in Diagnostics.

**Wie ließe sich die Zusage umsetzen?** Nicht ohne Endpunkt. Optionen:
- A. **Hersteller-bestätigter Endpunkt** (bevorzugt): Nutzer erzeugt ein Token in der Web-UI; HA speichert es (Config Entry, geschwärzt) und ruft den Endpunkt auf. Services/Buttons `ff_agent.accept` (Verkehrsmittel Auto/zu Fuß/Fahrrad, optional lat/lng) und `ff_agent.decline`. Felder analog zur Homey-App [G].
- B. **Login mit Benutzername/Passwort** (wie Homey-App möglicherweise): nur wenn der Hersteller es freigibt; Passwort als Secret speichern, Re-Auth-Flow, keine Logs. Riskanter (siehe 3.5).
- C. **Ohne Schnittstelle:** Die Zusage bleibt in der FF-Agent-App; HA-Benachrichtigung öffnet die App per Deep Link (Mobile-App-Aktion, nicht geprüft). Das erfüllt MVP-Punkt 2 nicht, ist aber eine ehrliche Rückfalllösung.
- Zusage nur für den **aktiven** Einsatz; HA kennt bei Webhook ohne Nutzdaten keine Einsatz-ID, die Zusage muss also (wie in der Homey-App) ohne ID auskommen, sonst braucht es einen Abruf [A]. Das spricht stark für Variante A oder B mit „aktueller Einsatz“-Semantik.

**Einsatzdetails (MVP-Punkt 3, „soweit verfügbar“):**
- Direkt am Webhook: wahrscheinlich nichts.
- Optional: persönlicher iCal-Feed als zweite Quelle (Basic-Auth oder Token-URL), nach Alarm abgefragt, um Stichwort/Ort anzuzeigen; Inhalt und Aktualität [U] und vor Entwicklung an einem echten Feed zu prüfen (Nutzer als Admin kann seinen eigenen Feed ansehen, ohne Daten weiterzugeben).
- Der Hersteller-Rückmeldung (API-Doku angefragt) abwarten, bevor Abrufwege gebaut werden.

**iot_class:** unverändert `cloud_push` (Webhook von FF Agent) [A]; bei zusätzlichem iCal-Polling bleibt `cloud_push` als Hauptweg vertretbar, der Feed ist nur optionale Ergänzung [A].

## 5. Offene Punkte

- Alle Details der Persönlichen Webhooks (siehe 6).
- Endpunkt und Auth der Zusage (nur Hersteller oder Homey-Entwickler können das beantworten). Der Nutzer könnte den Homey-Entwickler per E-Mail (Adresse auf der Store-Seite) fragen; das ist eine Kontaktaufnahme, die nur der Nutzer auslösen sollte.
- Inhalt und Aktualität des persönlichen iCal-Feeds 2026.
- Ob der Homey-Webhook derselbe Mechanismus ist wie die „Persönlichen Webhooks“.
- Hersteller-Position zu Drittclients und zur Nutzung nicht dokumentierter Endpunkte.

## 6. Fragen, die nur die Web-UI des Nutzers beantwortet

Bitte als Screenshots oder Textabschrift **ohne** Tokens/URL-Geheimnisse:

1. Dialog **„Webhook hinzufügen“**: Welche Felder gibt es (Name, Bemerkung, URL, Methode, Header, Authentifizierung, Body/Vorlage, Platzhalter-Auswahl, Zeitplan, Aktiv-Schalter, Test-Schaltfläche)? Gibt es Hilfetexte oder Info-Icons?
2. Gibt es ein Auswahlfeld für den **Auslöser** (Alarm, Einsatz-Update, Einsatzende, Rückmeldung, Probealarm)?
3. Wie genau wirkt der **Zeitplan** (Wochentage/Uhrzeit als Zeitfenster, in dem der Webhook feuert)? Was passiert mit Alarmen außerhalb?
4. Gibt es eine **Testfunktion** („Webhook testen“) und ein **Protokoll** (letzter Aufruf, HTTP-Status, Fehler)? Das würde Retry und Statuscodes zeigen.
5. Sind in Name/Bemerkung/URL **Platzhalter** wie `{{...}}` dokumentiert?
6. Reiter **„Einsatzrückmeldungen“**: Was lässt sich dort einstellen (z. B. automatische Rückmeldung, Zeitplan, Verkehrsmittel, Standort)? Gibt es dort eine URL, einen Token oder eine Schaltfläche zum Erzeugen eines API-Schlüssels? Das ist die wahrscheinlichste Quelle für die Zusage-Schnittstelle.
7. Reiter **„Partnerbenachrichtigungen“** und **„MoWaS“**: kurze Beschreibung, falls sie Webhooks oder Tokens enthalten.
8. Persönliches Profil > **„Kalenderabonnements“**: vorhanden und aktiv? Welche URL-Struktur (Host, Pfad ohne Kennung)? Enthält der Feed Einsätze mit Stichwort und Ort (Beispiel-Eintrag mit geschwärzten Daten)?
9. Gibt es im Profil weitere Bereiche wie „API-Zugang“, „Zugangsdaten“, „Tokens“ oder „Integrationen“?
10. Die Hinweise zur Lizenz (PRO): Steht bei den Webhooks ein Lizenzvermerk?
11. Wie wird die Homey-App beim Hinzufügen des Geräts konfiguriert (falls der Nutzer sie kennt oder ein Kollege)? Nur zur Klärung, kein Test erforderlich.

## 7. Verworfene oder nicht belastbare Abrufergebnisse

- Das Abruf-Tool meldete für die Homey-Seite zeitweise „Settings: keine Settings-Sektion“ und „Sensor-Capability ffagent_last_alarm“; letzteres stammt aus dem Store-JSON und ist dort belegt, eine Aussage zur Beschaffenheit dieser Capability fehlt.
- Die Auskunft des Tools, die PDFs seien „komprimiert“ und nicht lesbar, traf auf die Kalender-, Einsatzdaten- und Smartphone-PDF nicht zu: Der Lese-Tool-Weg auf die lokal zwischengespeicherte Datei lieferte den Text (Kalender-PDF vollständig, Einsatzdaten-PDF vollständig, Smartphone-PDF vollständig). Die Web-API- und Instant-Commands-PDFs wurden **nicht** erneut gelesen (Abschnitt 0 der Vorrecherche gilt).
- GitHub-Suche: Teile der Trefferliste (Repos ohne Beschreibung) wurden nicht geöffnet.
- Nicht ausgewertet: Fireboard-Schnittstelle von FF Agent (Web-UI-Reiter „Fireboard-API“); die gefundenen Fireboard-Seiten betreffen die Fireboard-Seite des Zielsystems, nicht FF Agent.

## 8. Empfehlung für das weitere Vorgehen

1. **Nutzer:** Screenshots/Abschriften gemäß Abschnitt 6 (Punkte 1 bis 6 und 8 haben Vorrang), dazu die Antwort des Herstellers abwarten.
2. **Hersteller-Anfrage ergänzen:** (a) Dokumentation der Persönlichen Webhooks (Methode, Header, Body, Zeitplan, Retry, Signatur, Lizenz); (b) Endpunkt und Token für Zu-/Absage durch Drittanwendungen (die Homey-App existiert, also muss es einen geben); (c) Erlaubnis zur Nutzung durch eine Open-Source-HA-Integration; (d) Stand des persönlichen iCal-Feeds und Felder.
3. **Entwicklung vorbereiten, nicht starten:** Webhook-Empfang (Config Flow, Binary-Sensor, Event, Entprellung) kann nach den Antworten zu 1. sofort geplant werden (Architekt). Zusage und Details erst nach 2.
4. **Optional:** Den Entwickler der Homey-App (Kontakt über Store-Seite) fragen, ob er Endpunkt und Auth offenlegt; Kontaktaufnahme nur durch den Nutzer.
5. Keine Nutzung nicht dokumentierter App-Endpunkte durch Mitschneiden oder Zerlegen der App ohne ausdrückliche Freigabe.

## 9. Quellen (Abruf 2026-10-16)

- https://homey.app/a/com.stefanbauer.ff-agent , https://homey.app/en-ae/app/com.stefanbauer.ff-agent/
- https://apps-api.athom.com/api/v1/app/com.stefanbauer.ff-agent (öffentliches Store-JSON)
- https://helpcenter.ff-agent.com/sitemap.xml
- https://helpcenter.ff-agent.com/neuigkeiten/releases/web-ui/ , /apps/
- https://helpcenter.ff-agent.com/webui/erste-schritte/personen/ , /ueberblick/ , /weiterfuehrende-konfiguration/
- https://helpcenter.ff-agent.com/apps/ff-agent-app/einsatz/
- https://helpcenter.ff-agent.com/webui/administration/geteilte-informationen/
- https://helpcenter.ff-agent.com/webui/uebersicht/touren/ und die PDFs `Dokumentation_Kalenderabonnements.pdf`, `Dokumentation_Erweiterte_Einsatzdaten.pdf`, `Dokumentation_Smartphone_Konfiguration.pdf` im Unterordner `pdfs/`
- https://www.ff-agent.com/datenschutz.html (404 bei /nutzungsbedingungen.html, /impressum.html)
- https://github.com/wiwimaster/ff-agent-wp-mission-import (Dateien `ff-agent-wp-mission-import.php`, `classes/class_scheduler.php`, `classes/ff-agent-import/class_single_mission_import.php`)
- https://github.com/michi-s/CardiLink2FFA , https://github.com/kvn-stgl/FFAgent2Listmonk
- GitHub-Repo-Suche (api.github.com/search/repositories) nach ff-agent, ffagent, api.service.ff-agent.com, Webhook
- Vorrecherche: `docs/recherche/261016-ffagent-schnittstellen.md`
