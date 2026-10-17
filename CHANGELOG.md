# Changelog

Alle nennenswerten Änderungen an dieser Integration. Format angelehnt an
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionen nach SemVer.

## [Unreleased]

### Behoben

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

[0.1.0]: https://github.com/rauchstefan/ha-ff-agent/releases/tag/v0.1.0
