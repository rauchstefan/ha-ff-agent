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
- Welche Rolle hat der Nutzer in FF Agent (Einsatzkraft, Admin der Einheit)? Welche
  Zugänge und Lizenzen sind vorhanden?
- Welche Funktionen sind Pflicht für eine erste Version (MVP)?
- Soll die Integration später öffentlich (HACS-Default-Repository) angeboten werden?

## Vorläufige Leitplanken

- Config Flow, keine YAML-Konfiguration.
- Alarmdaten sind sensibel: Redaction in Logs und Diagnostics von Anfang an.
- Ziel-Qualität: mindestens „Bronze“ der HA Integration Quality Scale.
