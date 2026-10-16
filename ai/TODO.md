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

### 261016-hacs-anforderungen – Recherche: HACS-Kompatibilität
- **Status:** in Arbeit (lokal-2026-10-16-hacs-recherche, 2026-10-16)
- **Priorität:** hoch
- **Rolle(n):** researcher
- **Beschreibung:** Vollständig klären, was eine Integration HACS-kompatibel macht:
  Repo-Struktur, `hacs.json`, `manifest.json`, Releases/Versionen, Brands, Validierung
  (HACS-Action, hassfest), Aufnahme in den Default-Store vs. Custom Repository.
- **Definition of Done:** `docs/recherche/261016-hacs-anforderungen.md` mit belegten
  Quellen, Checkliste und Abgleich mit dem aktuellen Repo.
- **Verweise:** –

Vorschläge des Projektleiters für den Einstieg (noch nicht beauftragt):
1. Recherche der FF-Agent-Schnittstellen (`researcher`), siehe Fragen in
   `docs/projekt-brief.md`.
2. MVP-Umfang mit dem Nutzer festlegen, danach Architektur-ADR (`architekt`).
3. Grundgerüst der Integration mit CI (hassfest, HACS-Action, pytest, ruff)
   (`entwickler`, `tester`).

## Erledigt

### 261016-projektsetup – Projekt aufsetzen
- **Status:** erledigt (2026-10-16, Initial-Commit)
- **Rolle(n):** Projektleiter
- **Beschreibung:** Rollen-Agenten, Orchestrierungsregeln, Doku-Struktur, Übergabedateien,
  Repo-Grundgerüst.
