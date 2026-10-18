# Changelog

Alle nennenswerten Änderungen an dieser Integration. Format angelehnt an
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionen nach SemVer.

## [Unreleased]

## [0.4.0] – 2026-10-18 (Vorabversion)

Vierte Vorabversion. Test- und Echtalarm aus FF Agent sind beim Entwickler über ntfy erfolgreich angekommen; Zusagen und Absagen sind noch nicht gegen ein echtes FF Agent geprüft.

**Update:** Nach dem Update Home Assistant neu starten **und die Seite im Browser hart neu
laden** (Strg+F5, am Mac Cmd+Umschalt+R). In der Companion-App die App neu starten bzw.
den Frontend-Cache in den App-Einstellungen leeren. Sonst zeigen Dialoge der Integration
unter Umständen keinen oder alten Text.

### Geändert

- **Standortquelle statt Standort-Entität:** Das optionale Feld „Standort-Entität“ ist durch
  die Pflicht-Auswahl „Standortquelle“ ersetzt, im Einrichtungsschritt „Zusage: Verkehrsmittel
  und Standort“ und unter „Konfigurieren“. Zur Auswahl stehen „Kein Standort“ (Standard),
  „Zuhause-Position von Home Assistant“ (wird beim Zusagen gelesen), „Koordinaten manuell
  eingeben“ (Breiten- und Längengrad in Dezimalgrad) und „Person oder Geräte-Tracker
  (Live-Standort)“. Bestehende Einträge mit Standort-Entität laufen unverändert weiter.
  Wechsel der Quelle löscht die Werte der alten Quelle. Koordinaten sind in den Diagnosedaten
  geschwärzt und werden nie geloggt. Die Action `ff_agent.accept` mit `latitude` und
  `longitude` hat weiter Vorrang; die Absage sendet nie einen Standort.
- **Neues Symbol:** Das Symbol der Integration ist jetzt ein Haus mit „FF“ auf rotem,
  abgerundetem Quadrat statt des schlichten „FF“-Quadrats. Es ist ein eigenes, allgemeines
  Motiv (kein Logo von FF Agent, Home Assistant oder HACS). Die Quelle liegt unter
  `docs/assets/logo.svg`, die README zeigt das Symbol oben.

### Dokumentation

- **README überarbeitet:** Neue Badge-Leiste (Release, Contributors, Issues, Discussions,
  HACS, Tests, Lizenz), Button „In HACS öffnen“ (My Home Assistant), Hinweisboxen zur
  Vorabversion und zum Datenschutz sowie ein Haftungsausschluss. Neu sind die Abschnitte
  „Probleme melden und Fragen“, „Mitmachen“, „Unterstützen“ und „Weiterführende Links“.
- **CONTRIBUTING.md:** Neue Datei mit Hinweisen zum Mitmachen.
- **GitHub Discussions:** Für Fragen eingeschaltet; die README verlinkt dorthin.

### English

Fourth pre-release. A test alarm and a real alarm from FF Agent have arrived successfully through ntfy on the developer's system; accepting and declining have not yet been checked against a real FF Agent.

**Update:** After updating, restart Home Assistant **and hard-reload the page in the
browser** (Ctrl+F5, on a Mac Cmd+Shift+R). In the companion app, restart the app or clear
the frontend cache in the app settings. Otherwise the dialogs of the integration may show
no text or old text.

#### Changed

- **Location source instead of location entity:** The optional field "Location entity" is
  replaced by the required choice "Location source", in the setup step "Accepting: transport
  and location" and under "Configure". The choices are "No location" (default), "Home position
  from Home Assistant" (read when accepting), "Enter coordinates manually" (latitude and
  longitude in decimal degrees) and "Person or device tracker (live location)". Existing
  entries with a location entity keep working unchanged. Changing the source deletes the
  values of the old source. Coordinates are redacted in the diagnostics and are never logged.
  The action `ff_agent.accept` with `latitude` and `longitude` still takes precedence; a
  rejection never sends a location.
- **New icon:** The icon of the integration is now a house with "FF" on a red rounded
  square instead of the plain "FF" square. It is an original, generic motif (not a logo of
  FF Agent, Home Assistant or HACS). The source is `docs/assets/logo.svg`, and the README
  shows the icon at the top.

#### Documentation

- **README revised:** New badge bar (release, contributors, issues, discussions, HACS, tests,
  license), an "Open in HACS" button (My Home Assistant), notice boxes on the pre-release
  status and on privacy, and a disclaimer. New sections are "Issues and questions",
  "Contributing", "Support the project" and "Further resources".
- **CONTRIBUTING.md:** New file with notes on contributing.
- **GitHub Discussions:** Enabled for questions; the README links there.

## [0.3.0] – 2026-10-18 (Vorabversion)

Dritte Vorabversion. Ein Testalarm und ein echter Alarm aus FF Agent sind beim Entwickler über ntfy erfolgreich angekommen; Zusagen und Absagen sind noch nicht gegen ein echtes FF Agent geprüft.

**Update:** Nach dem Update Home Assistant neu starten **und die Seite im Browser hart neu
laden** (Strg+F5, am Mac Cmd+Umschalt+R). In der Companion-App die App neu starten bzw.
den Frontend-Cache in den App-Einstellungen leeren. Sonst zeigen Dialoge der Integration
unter Umständen keinen oder alten Text.

### Neu

- **Alarm zurücksetzen:** Neuer Button „Alarm zurücksetzen“ und neue Action
  `ff_agent.reset_alarm` schalten „Alarm aktiv“ sofort aus und beenden die Rücksetzzeit.
  „Letzter Alarm“ bleibt, und das 30-Sekunden-Fenster gegen Doppelalarme läuft weiter.
  Ohne aktiven Alarm passiert nichts; an FF Agent wird nichts gesendet.
- **Verkehrsmittel und Standort bei der Einrichtung:** Die Einrichtung fragt jetzt nach der
  Rückmelde-URL das Standard-Verkehrsmittel und die optionale Standort-Entität ab (Person
  oder Geräte-Tracker). Beides war bisher nur unter „Konfigurieren“ einstellbar und bleibt
  dort änderbar.

### Geändert

- **Neukonfiguration:** Die Auswahl des Alarmwegs heißt „Wie bekommt Home Assistant den
  Alarm?“ und nennt die Voraussetzungen (Cloud-Abo oder aus dem Internet erreichbare
  Adresse bzw. kostenlos über ntfy ohne Abo).
- **Kürzerer ntfy-Abschluss:** Der Abschlussdialog wiederholt die Werte für FF Agent nur
  noch, wenn die gewählte Entität eine andere Adresse hat als der Dialog davor. Sonst
  genügt ein Hinweis auf den Testalarm.

### Entfernt

- **Link „Besuchen“ in der Geräte-Info:** Das Gerät verweist nicht mehr auf eine Website.
  Der Link bestehender Geräte verschwindet nach dem Neustart bzw. Neuladen der Integration.

### Dokumentation

- Die README enthält jetzt die vollständige Anleitung auf Deutsch und auf Englisch in einer
  Datei (Sprachumschalter am Anfang) und ist redaktionell überarbeitet.

### English

Third pre-release. A test alarm and a real alarm from FF Agent have arrived successfully through ntfy on the developer's system; accepting and declining have not yet been checked against a real FF Agent.

**Update:** After updating, restart Home Assistant **and hard-reload the page in the
browser** (Ctrl+F5, on a Mac Cmd+Shift+R). In the companion app, restart the app or clear
the frontend cache in the app settings. Otherwise the dialogs of the integration may show
no text or old text.

#### Added

- **Reset alarm:** A new button "Reset alarm" and a new action `ff_agent.reset_alarm` turn
  "Alarm active" off right away and stop the reset time. "Last alarm" stays, and the
  30-second window against duplicate alarms keeps running. Without an active alarm nothing
  happens; nothing is sent to FF Agent.
- **Transport and location during setup:** After the mission reply URL, the setup now asks
  for the default transport and the optional location entity (a person or device tracker).
  Both could previously only be set under "Configure" and stay changeable there.

#### Changed

- **Reconfigure:** The choice of the alarm way is now called "How does Home Assistant
  receive the alarm?" and names the requirements (a cloud subscription or an address
  reachable from the internet, or free through ntfy without a subscription).
- **Shorter ntfy ending:** The final dialog only repeats the values for FF Agent if the
  chosen entity has another address than the dialog before. Otherwise a pointer to the test
  alarm is enough.

#### Documentation

- The README now contains the complete guide in German and English in one file, with a
  language switch at the top, and has been edited throughout.

#### Removed

- **"Visit" link in the device info:** The device no longer points to a website. The link
  on existing devices disappears after a restart or reload of the integration.

## [0.2.0] – 2026-10-18 (Vorabversion)

Zweite Vorabversion. **Noch nicht gegen ein echtes FF Agent getestet.** Besonders der
Weg über ntfy ist bisher nur mit Mocks geprüft, nicht gegen einen echten ntfy-Dienst und
nicht mit einem echten Alarm aus FF Agent.

**Update:** Nach dem Update Home Assistant neu starten. Bestehende Einträge laufen
unverändert über den Webhook weiter. Wer auf ntfy wechseln will, richtet die
Core-Integration ntfy ein und wählt unter „Neu konfigurieren“ den neuen Alarmweg.

### Behoben

- **Neutraler Hersteller in der Geräte-Info:** Die Geräte-Info zeigt jetzt
  „ha-ff-agent (inoffiziell)“ als Hersteller. Das Projekt ist ein inoffizielles
  Community-Projekt; die Integration nennt keinen Firmennamen von FF Agent.
- **Fundort der Rückmelde-URL:** Die URL steht in FF Agent nicht unter „Automatisierung“,
  sondern unter *Personen → (dein Name) → Bereich „Übung/Einsatz“ → „Weblinks für
  Einsatzmeldung“*. Korrigiert sind die Hilfetexte im Einrichtungsdialog (Deutsch und
  Englisch), die README und die Doku. Neu dokumentiert: Die URLs gelten je Person für den
  jeweils aktiven Einsatz, und Zu- und Absage gehen nur, wenn die Person dafür alarmiert
  wurde.

### Neu

- **Verkehrsmittel zu Fuß und Fahrrad:** Neben `car` (Auto) gibt es `feet` (zu Fuß) und
  `bicycle` (Fahrrad), in der Action `ff_agent.accept` und als Standard-Verkehrsmittel in
  den Optionen. An FF Agent gehen `CAR`, `FEET` und `BICYCLE`.
- **Alarm über ntfy:** Ohne Home Assistant Cloud und ohne eigene Internetadresse kommt der
  Alarm jetzt kostenlos über den Dienst ntfy. FF Agent ruft per GET eine ntfy-Adresse auf,
  die Core-Integration ntfy holt die Meldung ab, und FF Agent in Home Assistant wertet ihre
  Event-Entität aus. Neustarts, Reloads und Verbindungsabbrüche lösen in aller Regel keinen
  Fehlalarm aus (seltene Ausnahmen siehe README, „Grenzen von ntfy“). Fehlt die
  ntfy-Entität, erscheint eine Reparatur-Meldung; ein neues Abo mit demselben Thema
  übernimmt die Einrichtung selbst. Im ntfy-Modus ist kein Webhook offen (ADR 0003).
- **Verständliche Hilfe, wenn Home Assistant nicht erreichbar ist:** Die Einrichtung fragt
  „Nutzt du Home Assistant Cloud?“ und führt je Weg mit nummerierten Schritten und Links
  durch die Einrichtung. Statt einer Sackgasse gibt es „Erneut prüfen“, „Stattdessen ntfy
  nutzen“ und „Trotzdem fortfahren“.
- **Weg wechseln:** Unter „Neu konfigurieren“ lässt sich der Alarmweg in beide Richtungen
  wechseln; „Neue geheime Adresse erzeugen“ gilt für Webhook und ntfy.
- Bestehende Einträge werden beim Update automatisch übernommen und bleiben beim Webhook
  (Config-Eintrag Version 1.2).

### Bekannte Einschränkungen

Details in der README unter „Bekannte Einschränkungen“ und „Grenzen von ntfy“. Die
wichtigsten:

- Testalarm und echter Alarm sind in Home Assistant nicht unterscheidbar.
- ntfy: Ein Alarm während einer Unterbrechung der ntfy-Verbindung geht verloren.
- Zu- und Absage gehen nur, wenn die Person für den aktiven Einsatz alarmiert wurde. Eine
  Antwort mit Status 2xx heißt nur „gesendet“, nicht sicher „verbucht“.
- Einsatzdetails gibt es noch nicht.

## [0.1.0] – 2026-10-17 (Vorabversion)

Erste Version. **Noch nicht gegen ein echtes FF Agent getestet.** Deshalb ist sie in
HACS als Vorabversion (Beta) markiert.

### Neu

- **Einrichtung über die UI:** ein Eintrag je Person, mit der persönlichen Rückmelde-URL
  aus FF Agent. Die Webhook-Adresse ermittelt die Integration automatisch: Nabu Casa,
  externe URL oder intern.
- **Alarm-Eingang** über einen persönlichen Webhook aus FF Agent (GET oder POST),
  optional mit Zusatz-Token im Header.
- **Entitäten:**
  - Event „Alarm“
  - Binary-Sensor „Alarm aktiv“ mit einstellbarer Rücksetzzeit
  - Sensoren „Letzter Alarm“ und „Letzte Rückmeldung“
  - Buttons „Zusagen“ und „Absagen“
- **Actions** `ff_agent.accept` (mit Verkehrsmittel und optionalem Standort) und
  `ff_agent.reject`.
- **Optionen und Neu konfigurieren:** Token-Pflicht, Rücksetzzeit, Verkehrsmittel,
  Standort-Entität; neue Rückmelde-URL; Webhook-Zugang neu erzeugen.
- **Datenschutz:** Webhook-Aufrufe werden nur in ihrer Form erfasst, nie mit Werten.
  Diagnose und Logs sind redigiert.
- Deutsche und englische Übersetzung, README mit Einrichtungsanleitung.

### Bekannte Einschränkungen

Siehe README, Abschnitt „Bekannte Einschränkungen“. Die wichtigsten:

- Testalarm und echter Alarm sind in Home Assistant nicht unterscheidbar.
- Einsatzdetails gibt es noch nicht.
- Belegt ist nur das Verkehrsmittel „Auto“.
- Eine Antwort mit Status 2xx heißt nur „gesendet“, nicht sicher „verbucht“.

[Unreleased]: https://github.com/rauchstefan/ha-ff-agent/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/rauchstefan/ha-ff-agent/releases/tag/v0.4.0
[0.3.0]: https://github.com/rauchstefan/ha-ff-agent/releases/tag/v0.3.0
[0.2.0]: https://github.com/rauchstefan/ha-ff-agent/releases/tag/v0.2.0
[0.1.0]: https://github.com/rauchstefan/ha-ff-agent/releases/tag/v0.1.0
