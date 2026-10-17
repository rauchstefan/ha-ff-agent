# CLAUDE.md – ha-ff-agent

Einstiegspunkt für **jede** Claude-Session in diesem Repo, lokal wie in der Cloud.
**Was nicht im Repo steht, existiert für die nächste Session nicht.**

## Projekt in Kürze

Home-Assistant-Custom-Integration, installierbar über **HACS**, die **FF Agent**
(Alarmierungs- und Einsatzsoftware für Feuerwehren und Hilfsorganisationen) in Home
Assistant verfügbar macht. Ziel und offene Fragen: `docs/projekt-brief.md`.

- Repo: `github.com/rauchstefan/ha-ff-agent` (privat), Standard-Branch `main`
- Integrations-Domain: `ff_agent`, Code unter `custom_components/ff_agent/`
- Sprache: Doku und Kommentare Deutsch, Code-Bezeichner und Commit-Messages Englisch

## Orchestrierung – verbindlich

**Jede Aufgabe des Nutzers geht an den Projektleiter.** Der Projektleiter plant,
delegiert an die Fach-Agenten, prüft deren Ergebnisse und berichtet dem Nutzer.

- `.claude/settings.json` startet die Hauptsession als Agent `projektleiter`.
- Läuft eine Session trotzdem nicht als Projektleiter (z. B. andere Umgebung, Setting
  überschrieben), **übernimmt die Hauptsession die Rolle selbst**: Sie liest
  `.claude/agents/projektleiter.md` und handelt danach. Sie setzt Aufgaben nicht direkt
  um, sondern delegiert über das Agent-Tool an die Fach-Agenten.
- Fach-Agenten nehmen Aufträge nur vom Projektleiter an und berichten an ihn zurück.
  Subagenten können keine weiteren Subagenten starten; Ketten steuert der Projektleiter.
- Ablauf, Übergaben und Qualitäts-Gates im Detail: `docs/orchestrierung.md`.

### Rollen

Definitionen unter `.claude/agents/`.

| Rolle | Agent | Modell | Aufwand | Warum dieses Modell |
|---|---|---|---|---|
| Projektleitung / Orchestrierung | `projektleiter` | Opus | high | Zerlegen, Priorisieren, Ergebnisse beurteilen: braucht das stärkste Urteilsvermögen |
| Planung / Architektur | `architekt` | Opus | high | Designfehler sind später am teuersten |
| Recherche | `researcher` | Sonnet | medium | Viel Lesen und Zusammenfassen, gutes Verhältnis von Qualität zu Kosten |
| Implementierung | `entwickler` | Sonnet | high | Starkes Coding-Modell, Aufwand hoch für sauberen HA-Code |
| Testing / QA | `tester` | Sonnet | medium | Tests schreiben und ausführen, eher methodisch als kreativ |
| Code-Review | `reviewer` | Opus | medium | Findet subtile Fehler, liest nur Diffs |
| Dokumentation / Release-Notes | `doku` | Haiku | low | Strukturierte Texte nach Vorlage, schnell und günstig |

Der Projektleiter darf je Auftrag ein anderes Modell wählen (Begründung im Journal).

## Übergabepunkt `ai/`

| Datei | Zweck |
|---|---|
| `ai/STATUS.md` | Aktueller Projektstand: Version, was funktioniert, was nicht |
| `ai/TODO.md` | Gemeinsame Aufgabenliste (Backlog), Regeln oben in der Datei |
| `ai/JOURNAL.md` | Übergabeprotokoll, ein Eintrag je Session, neueste oben (`merge=union`) |

Weitere Ablagen: `docs/plaene/` (Umsetzungspläne), `docs/adr/` (Architekturentscheidungen),
`docs/recherche/` (Rechercheergebnisse), `docs/architektur.md` (Gesamtbild).

## Session-Protokoll

### Start
1. `git pull --rebase` (Cloud: `git fetch origin && git merge origin/main`).
2. Lesen: `ai/STATUS.md`, oberste ~5 Einträge `ai/JOURNAL.md`, `ai/TODO.md`.
3. Liegengebliebenes prüfen: offene PRs (`gh pr list`), rote Läufe (`gh run list --limit 5`).
4. Aufgabe in `ai/TODO.md` beanspruchen (Status setzen, committen, pushen), dann starten.

### Während der Arbeit
- Nach jedem abgeschlossenen Schritt committen und pushen.
- Findings, die nicht sofort erledigt werden, sofort in `ai/TODO.md`.
- Dauerhaftes Wissen (API-Verhalten von FF Agent, HA-Fallstricke) gehört nach
  `docs/architektur.md`, in ein ADR oder in diese Datei, nicht nur ins Journal.

### Ende (auch bei Abbruch)
1. `ai/TODO.md` aktualisieren.
2. Journal-Eintrag oben in `ai/JOURNAL.md`.
3. `ai/STATUS.md` anpassen, wenn sich der Stand geändert hat.
4. Committen, pushen, Push prüfen.

## Git-Workflow

- `main` ist immer lauffähig und geschützt durch das Qualitäts-Gate.
- Code-Änderungen an der Integration laufen über Branches `feat/<todo-id>` bzw.
  `fix/<todo-id>` und einen Pull Request.
- Merge in `main` erst, wenn CI grün, `tester` PASS und `reviewer` „freigegeben“ gemeldet
  haben. Merge-Methode: Squash.
- Reine Doku- und `ai/`-Änderungen dürfen direkt auf `main`.
- Cloud-Sessions arbeiten auf ihrem `claude/<name>`-Branch und öffnen einen PR.
- Commit-Messages Englisch, Conventional-Commits-Stil (`feat:`, `fix:`, `docs:`,
  `test:`, `chore:`).
- **Keine Secrets committen:** FF-Agent-Zugangsdaten, API-Keys, Webhook-URLs, echte
  Einsatzdaten. Vor jedem Commit `git status` prüfen.
- Auth lokal über den Git Credential Manager / `gh` (Account `rauchstefan`, hieß bis 2026-10 `AldiTuete93`).

## Freigaben

**Ohne Rückfrage erlaubt:** Code und Doku ändern, Branches und PRs anlegen, pushen,
PRs nach bestandenem Qualitäts-Gate mergen, `ai/`-Dateien pflegen, GitHub-Issues anlegen.

**Nur nach ausdrücklicher Bestätigung des Nutzers, je Einzelfall:**
- Release: Git-Tag, GitHub-Release, Versionssprung in `manifest.json` für ein Release
- Installation oder Änderung in der echten Home-Assistant-Instanz des Nutzers
- Zugriff auf einen echten FF-Agent-Account, Auslösen von Test-Alarmen
- Repo-Einstellungen (Sichtbarkeit, Branch-Protection, Secrets, Collaborators)
- `git push --force`, `git reset --hard`, History umschreiben

## Fallstricke

- **Repo-Dateien nicht mit PowerShell `Set-Content`/`Out-File`/`>` schreiben** (zerstört
  UTF-8, setzt BOM). Edit/Write-Tools oder Git Bash verwenden.
- Der Ordner liegt in OneDrive: virtuelle Umgebungen (`.venv/`) und Caches sind
  gitignored, sollten aber möglichst außerhalb von OneDrive liegen.
- **Subagenten teilen sich das Arbeitsverzeichnis.** Checkt ein `entwickler` oder `tester`
  einen Feature-Branch aus, landen Commits des Projektleiters auf diesem Branch. Vor
  direkten Commits auf `main` deshalb `git branch --show-current` prüfen. Während ein
  schreibender Agent läuft, nichts direkt committen.
- **Lokal gibt es kein Python** (nur den Store-Platzhalter `python3`). Tests, ruff und
  hassfest laufen ausschließlich in GitHub Actions.
