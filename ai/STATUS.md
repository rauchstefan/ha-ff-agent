# Projektstand

Was ist der aktuelle Stand der Integration? Diese Datei beantwortet das für jede neue
Session. Von Hand gepflegt.

- **Version:** 0.4.0. GitHub-Release `v0.4.0` als **reguläres Release** (Latest; 2026-10-18, Tag auf
  e05621a, rauchstefan/ha-ff-agent#13). Davor `v0.3.0` (619a53e), `v0.2.0` (dabe583) und
  `v0.1.0`, alle Vorabversionen.
- **Neu in v0.4.0:** Standortquelle wählbar (keine, HA-Zuhause, Koordinaten, Entität;
  rauchstefan/ha-ff-agent#11), neues Symbol (#10), README mit Badges, HACS-Button,
  Hinweisboxen und Community-Abschnitten, CONTRIBUTING.md, Discussions eingeschaltet
  (#12). 782 Tests grün.
- **Neu in v0.3.0:** README zweisprachig (Deutsch und Englisch in einer Datei),
  CHANGELOG mit englischer Fassung, dazu alles aus rauchstefan/ha-ff-agent#8 (siehe unten).
  679 Tests, Abdeckung 100 %. Ein echter Testalarm aus FF Agent kam beim Nutzer an.
- **Neu in v0.2.0:**
  - neutraler Hersteller „ha-ff-agent (inoffiziell)“ (rauchstefan/ha-ff-agent#7)
  - Fundort der Rückmelde-URL korrigiert; Verkehrsmittel `car`/`feet`/`bicycle`
    (rauchstefan/ha-ff-agent#4)
  - Alarmquelle wählbar, Home Assistant Cloud/Webhook oder ntfy, mit geführten
    Einrichtungsdialogen; Migration 1.1 → 1.2; Selbstheilung bei neuem ntfy-Abo
    (rauchstefan/ha-ff-agent#6, ADR 0003)
  - 642 Tests, Abdeckung 100 %
- **Aus #8 in v0.3.0** (rauchstefan/ha-ff-agent#8,
  24d4f43): Einrichtungsschritt Verkehrsmittel/Standort, Button und Action
  `ff_agent.reset_alarm`, verkürzter ntfy-Abschluss, Alarmquelle als Frage in der
  Neukonfiguration, Geräte-Info ohne Link, Update-Hinweis (Browser hart neu laden).
- **Repo:** öffentlich seit 2026-10-17, über HACS als Custom Repository installierbar. Die
  HACS-Validierung besteht alle 9 Checks ohne `ignore`. Die alte Historie mit den PRs
  liegt im privaten Archiv `rauchstefan/ha-ff-agent-archiv`.
- **Integration:** MVP fertig (ADR 0002, Plan docs/plaene/261017-mvp-alarm-zusage.md,
  PRs rauchstefan/ha-ff-agent-archiv#2 bis #7):
  - Config Flow (eine Person je Eintrag), Parser für die Rückmelde-URL, Webhook-URL
    (Cloudhook, extern, intern)
  - Webhook-Empfang (GET/POST) mit optionalem Zusatz-Token und Repair-Issue. Erfasst wird
    nur die Form des Aufrufs, die Diagnostics sind redigiert.
  - Alarm-Logik (Dedup 30 s, Rücksetzzeit) mit den Entitäten Event „Alarm“, Binary-Sensor
    „Alarm aktiv“ und Sensor „Letzter Alarm“, alle an einem Gerät je Person
  - Rückmeldung:
    - Buttons „Zusagen“/„Absagen“
    - Actions `ff_agent.accept`/`ff_agent.reject` (Verkehrsmittel `car`, optional
      Standort)
    - Sensor „Letzte Rückmeldung“
    - Schutz vor Doppelklick
  - Optionen und Reconfigure (neue Rückmelde-URL, Webhook-Zugang neu erzeugen)
  - README mit Einrichtungsanleitung, Datenschutz, Beispielen und Fehlerbehebung;
    docs/quality-scale.md mit allen 54 Regeln
- **CI:**
  - `validate.yml`: hassfest, HACS-Action
  - `tests.yml`: ruff, pytest mit pytest-homeassistant-custom-component, Python 3.14,
    Abdeckungs-Gate 95 %, aktuell 100 %
  - Dependabot
- **Letzte Änderung:** 2026-10-18 – Pre-Release v0.4.0

## Was funktioniert

- Alle Funktionen des MVP sind in der CI getestet: 480 Tests, Abdeckung 100 %, ein
  Datenschutztest über den ganzen Lebenszyklus.
- Quality Scale: Bronze erfüllt (Ausnahmen begründet), Silber bis auf
  `reauthentication-flow`, Gold weitgehend (siehe docs/quality-scale.md).

## Bekannte Einschränkungen

- **Nicht real getestet:** Die Integration lief noch nie gegen echtes FF Agent oder eine
  echte HA-Instanz. Die Annahmen A1–A13 aus ADR 0002 sind offen
  (TODO 261017-echter-test, braucht die Freigabe des Nutzers).
- Solange es nur die Vorabversion gibt, müssen Nutzer in HACS Beta-/Vorabversionen
  aktivieren.
- Automationen auf die Event-Entität brauchen die Filter `not_from`/`not_to`.
- Speichern der Optionen oder ein Reconfigure lädt die Integration neu und setzt einen
  laufenden Alarm zurück (bewusst so).
- Die Icons sind Platzhalter, die Rechte am FF-Agent-Logo sind ungeklärt.
- Lokal gibt es kein Python. Tests laufen nur in GitHub Actions.

## Zugänge und Testumgebung

- FF Agent: Der Nutzer ist Admin einer Einheit mit PRO-Lizenz. Persönliche Webhooks und
  Rückmelde-URLs sind vorhanden.
- Home-Assistant-Testinstanz: die Instanz des Nutzers. Ein Test nur mit Freigabe im
  Einzelfall.
