# KI-ToDo-Liste

Gemeinsame Aufgabenliste aller Sessions. Gepflegt vom Projektleiter. Regeln im Detail:
`CLAUDE.md`, Abschnitt „Session-Protokoll“.

## Regeln in Kürze

- **Eintragen:** Neuer Eintrag unter „Offen“, nach Priorität einsortiert, sofort
  committen und pushen.
- **Übernehmen:** Status `in Arbeit (<session>, <datum>)` setzen, committen und pushen,
  **bevor** die Arbeit beginnt. Konflikt auf genau diesem Status beim Rebase = andere
  Session war schneller.
- **Verwaiste Ansprüche:** länger als 24 h `in Arbeit` ohne Fortschritt im Journal oder
  in Commits → darf übernommen werden, mit Vermerk.
- **Abschließen:** nach „Erledigt“ verschieben (oben einfügen), Status
  `erledigt (<datum>, <commit/PR>)`.
- **ID:** `JJMMTT-<kurzes-thema>`, Datum = Tag des Eintrags.
- **Session-Bezeichnung:** `lokal-<datum>-<thema>` bzw. Branch-Name der Cloud-Session.

## Vorlage

```markdown
### JJMMTT-thema – Titel
- **Status:** offen | in Arbeit (<session>, <datum>) | erledigt (<datum>, <commit/PR>)
- **Priorität:** hoch | mittel | niedrig
- **Rolle(n):** researcher, architekt, ...
- **Beschreibung:** was und warum
- **Definition of Done:** prüfbare Kriterien
- **Verweise:** Issue, Plan, Recherche
```

## Offen

### 261016-repo-oeffentlich – Entscheidung: Repo öffentlich machen
- **Status:** offen (wartet auf Nutzer)
- **Priorität:** hoch
- **Rolle(n):** Nutzer, Projektleiter
- **Beschreibung:** HACS funktioniert nur mit öffentlichen GitHub-Repos, auch als Custom
  Repository. Die Sichtbarkeit zu ändern braucht die Freigabe des Nutzers. Danach
  Beschreibung, Topics und Issues setzen. Außerdem klären, ob Name und Logo von FF Agent
  verwendet werden dürfen.
- **Definition of Done:** Entscheidung dokumentiert. Bei Zustimmung ist das Repo öffentlich
  und hat Beschreibung und Topics.
- **Verweise:** docs/recherche/261016-hacs-anforderungen.md, Abschnitt 3.6

### 261016-hacs-oeffentlich-pruefen – HACS-Job nach Veröffentlichung prüfen
- **Status:** offen (wartet auf 261016-repo-oeffentlich)
- **Priorität:** mittel
- **Rolle(n):** tester, entwickler
- **Beschreibung:** Solange das Repo privat ist, überspringt validate.yml den HACS-Job.
  Nach der Veröffentlichung prüfen, ob er ohne `ignore` grün läuft (Brands-Check,
  Beschreibung, Topics). Dann den Cron in validate.yml wieder auf täglich stellen.
  `hacs/action` ist auf eine SHA von `main` gepinnt, weil das letzte Release von 2022
  ist. Dependabot aktualisiert solche Branch-Pins nicht, also gelegentlich von Hand
  nachziehen. Dasselbe gilt für hassfest@master.
- **Definition of Done:** HACS-Job grün, Cron täglich.
- **Verweise:** PR rauchstefan/ha-ff-agent#1

### MVP Alarm + Zusage (Plan: docs/plaene/261017-mvp-alarm-zusage.md, ADR 0002)

Gemeinsame Angaben für alle sechs Schritte:
- **Rolle(n):** entwickler → tester → reviewer, je ein PR auf `feat/<id>`
- **Reihenfolge:** strikt nacheinander
- **Definition of Done:** wie im Plan beim jeweiligen PR

### 261017-mvp-1-config-flow – Manifest, Rückmelde-URL-Parser, Webhook-URL, Config Flow
- **Status:** erledigt (2026-10-17, PR rauchstefan/ha-ff-agent#2, 0fb459a)
- **Priorität:** hoch

### 261017-mvp-2-webhook – Webhook-Empfang, Zusatz-Token, Diagnostics
- **Status:** erledigt (2026-10-17, PR rauchstefan/ha-ff-agent#3, bb533a8)
- **Priorität:** hoch
- **Beschreibung:** Danach ist der erste echte Test möglich (Annahmen A1–A5, A12), nur mit
  Nutzerfreigabe.

### 261017-mvp-3-alarm-entitaeten – Alarm-Logik, Binary-Sensor, Event, Sensor, Gerät
- **Status:** in Arbeit (lokal-2026-10-16-hacs-recherche, 2026-10-17)
- **Priorität:** hoch

### 261017-mvp-4-rueckmeldung – Rückmelde-Client, Buttons, Actions
- **Status:** offen
- **Priorität:** hoch
- **Beschreibung:** Den echten Test (A6–A9) nur während eines Testalarms und nur mit
  Nutzerfreigabe.

### 261017-mvp-5-options-reconfigure – Options Flow und Reconfigure
- **Status:** offen
- **Priorität:** mittel
- **Zusätzlich (aus PR 1/2):**
  - Texte `internal` und `path_only` vom Rat „Eintrag neu anlegen“ auf Reconfigure umstellen
  - Repair-Issue `webhook_token_rejected` im Setup löschen, wenn `require_token` aus ist

### 261017-mvp-6-doku-qualitaet – README/Einrichtungsanleitung, Quality Scale, Abdeckung
- **Status:** offen
- **Priorität:** mittel
- **Zusätzlich (aus PR 2):** In der Nutzerdoku warnen, dass HA Core die Webhook-ID in Debug-Logs von `homeassistant.components.webhook` und `.http` schreibt; solche Logs nicht teilen.

### 261017-python-target – Python-Mindestversion vs. ruff-Ziel prüfen
- **Status:** erledigt (2026-10-17, ohne Codeänderung: HA 2026.3.0 verlangt Python ≥ 3.14.2, passt zu ruff py314; siehe docs/architektur.md)
- **Priorität:** mittel
- **Rolle(n):** entwickler
- **Beschreibung:**
  - Problem: In `pyproject.toml` ist ruff auf `py314` eingestellt und formatiert z. B.
    `except A, B:` (Syntax ab Python 3.14). `hacs.json` erlaubt aber HA ab 2026.3.0.
  - Zu prüfen: welche Python-Version HA 2026.3 voraussetzt.
  - Ist sie kleiner als 3.14, entweder ruff `target-version` darauf senken oder die
    HA-Mindestversion anheben.
  - Bis dahin weichen PRs mit einer Tupel-Variable aus (Hinweis aus PR 2).
- **Definition of Done:** ruff-Ziel und HA-Mindestversion passen zusammen.

### 261017-token-default – Zusatz-Token standardmäßig an?
- **Status:** offen (nach erstem echten Test)
- **Priorität:** niedrig
- **Beschreibung:** Nach dem Test von A12 entscheiden, ob neue Einträge die Token-Prüfung
  standardmäßig eingeschaltet bekommen.

### 261017-einsatzdetails – Quelle für Einsatzdetails
- **Status:** offen (wartet auf Hersteller und Antwort zu A13)
- **Priorität:** mittel
- **Beschreibung:** Platzhalter im Webhook, Hersteller-API oder iCal-Feed (Remote
  Calendar). Siehe ADR 0002, Abschnitt 7.

## Erledigt

### 261016-ffagent-klaerung – Ausgehende FF-Agent-Schnittstelle klären
- **Status:** erledigt (2026-10-17, ADR 0002 vorgeschlagen)
- **Rolle(n):** Nutzer, researcher, architekt
- **Verweise:** docs/adr/0002-integrationsweg-webhook-und-rueckmelde-url.md,
  docs/recherche/261016-ffagent-webhook-zusage.md

### 261016-ffagent-schnittstellen – Recherche: FF-Agent-Schnittstellen
- **Status:** erledigt (2026-10-16, siehe Commit „docs: add FF Agent interface research“)
- **Rolle(n):** researcher, Projektleiter (PDFs gelesen)
- **Verweise:** docs/recherche/261016-ffagent-schnittstellen.md

### 261016-hacs-geruest – HACS-konformes Grundgerüst + CI
- **Status:** erledigt (2026-10-16, PR rauchstefan/ha-ff-agent#1, 1d9ac86)
- **Rolle(n):** entwickler, tester, reviewer
- **Beschreibung:** custom_components/ff_agent (Manifest, Config-Flow mit
  Bestätigungsschritt, Übersetzungen, Platzhalter-Icons), bereinigte hacs.json,
  Workflows validate.yml und tests.yml, dependabot.yml, Tests.
- **Verweise:** docs/recherche/261016-hacs-anforderungen.md

### 261016-hacs-anforderungen – Recherche: HACS-Kompatibilität
- **Status:** erledigt (2026-10-16, 1aa83ea)
- **Rolle(n):** researcher
- **Beschreibung:** Klären, was eine Integration HACS-kompatibel macht: Repo-Struktur,
  hacs.json, manifest.json, Releases, Brands, CI, Custom Repository und Default-Store.
- **Verweise:** docs/recherche/261016-hacs-anforderungen.md

### 261016-projektsetup – Projekt aufsetzen
- **Status:** erledigt (2026-10-16, Initial-Commit)
- **Rolle(n):** Projektleiter
- **Beschreibung:** Rollen-Agenten, Orchestrierungsregeln, Doku-Struktur, Übergabedateien,
  Repo-Grundgerüst.
