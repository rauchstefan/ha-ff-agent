# Projekt-Brief: ha-ff-agent

## Ziel

Eine Home-Assistant-Custom-Integration, installierbar über HACS, die **FF Agent** in Home
Assistant verfügbar macht. Typische Einsatzzwecke im Smart Home einer Einsatzkraft:
bei Alarm Licht einschalten, Durchsagen/Benachrichtigungen auslösen, Einsatzinfos auf
einem Dashboard zeigen, Verfügbarkeit melden.

## Stand der Klärung

Stand 2026-10-16: Projekt aufgesetzt, fachlich noch nichts recherchiert oder entschieden.
Alles unten ist **offen** und wird über die ersten Aufgaben geklärt.

## Offene Fragen

### An die Recherche
- Welche Schnittstellen bietet FF Agent (REST-API, Webhooks, Monitor-Schnittstelle,
  E-Mail/SMS-Weiterleitung, Schnittstellen für Drittsysteme)? Wie authentifiziert man
  sich, welche Daten kommen in welchem Format?
- Push oder Polling? Gibt es Rate-Limits oder Nutzungsbedingungen für Drittanbieter?
- Gibt es bereits Community-Lösungen (Integrationen, Node-RED-Flows, Skripte)?

### An den Nutzer
- Soll die Integration später öffentlich (HACS-Default-Repository) angeboten werden?

### Antworten des Nutzers (2026-10-16)
- **Rolle:** Der Nutzer ist Admin seiner Einheit. Die Integration ist aber **für
  Einsatzkräfte** gedacht, also für Nutzer ohne Admin-Rechte.
- **Lizenz der Einheit:** PRO, ein Gateway ist vorhanden.
- **Persönliche Webhooks:** Es gibt sie in der Web-UI im Bereich „Automatisierung“,
  neben „Einsatzrückmeldungen“, „Partnerbenachrichtigungen“ und „MoWaS“. Jeder Nutzer
  kann bis zu 3 anlegen, mit Spalten Name, Bemerkung und Zeitplan (Wochentage/Zeit).
  Die Felder im Dialog „Webhook hinzufügen“ und das Format des Aufrufs sind noch unbekannt.
- **MVP:**
  1. Alarm erkennen, um darauf reagieren zu können
  2. Zusage senden
  3. Einsatzdetails anzeigen, soweit verfügbar
- **Erreichbarkeit von HA:** Sie hängt vom einzelnen Nutzer ab. Die Integration muss mit
  und ohne Nabu Casa bzw. externe URL umgehen können.
- **Hersteller-Anfrage:** Der Nutzer hat beim Hersteller eine detailliertere API-Doku
  angefragt; Antwort steht aus.

## Vorläufige Leitplanken

- Config Flow, keine YAML-Konfiguration.
- Alarmdaten sind sensibel: Redaction in Logs und Diagnostics von Anfang an.
- Ziel-Qualität: mindestens „Bronze“ der HA Integration Quality Scale.
