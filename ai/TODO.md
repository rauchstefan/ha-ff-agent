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

### 261016-hacs-geruest – HACS-konformes Grundgerüst + CI
- **Status:** offen
- **Priorität:** hoch
- **Rolle(n):** architekt (Mindest-HA-Version, iot_class), entwickler, tester, reviewer
- **Beschreibung:** `custom_components/ff_agent/` mit manifest.json, translations/en.json
  und brand/icon.png anlegen. In hacs.json `render_readme` und `content_in_root`
  entfernen, `homeassistant` ggf. auf 2026.3.0 setzen. `.github/workflows/validate.yml`
  (hacs/action + hassfest) und dependabot.yml anlegen.
- **Definition of Done:** validate.yml läuft ohne `ignore` grün (erst möglich, wenn das
  Repo öffentlich ist).
- **Verweise:** docs/recherche/261016-hacs-anforderungen.md, Abschnitte 4 bis 6

Vorschläge des Projektleiters für den Einstieg (noch nicht beauftragt):
1. Recherche der FF-Agent-Schnittstellen (`researcher`), siehe Fragen in
   `docs/projekt-brief.md`.
2. MVP-Umfang mit dem Nutzer festlegen, danach Architektur-ADR (`architekt`).
3. Grundgerüst der Integration mit CI (hassfest, HACS-Action, pytest, ruff)
   (`entwickler`, `tester`).

## Erledigt

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
