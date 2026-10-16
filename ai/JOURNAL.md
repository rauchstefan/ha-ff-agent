# Session-Journal

Übergabeprotokoll zwischen Sessions. Jede Session schreibt **am Ende** einen Eintrag,
auch bei Abbruch oder Teilstand. Neueste oben. Beim Start die obersten ~5 lesen.

Das Journal ist Verlauf, keine Wissensbasis: Dauerhaftes gehört nach `docs/` oder
`CLAUDE.md`, Offenes nach `ai/TODO.md`. Parallele Einträge erzeugen keine Konflikte
(`merge=union` in `.gitattributes`), deshalb nur neue Einträge hinzufügen.

## Vorlage

```markdown
## JJJJ-MM-TT HH:MM – <session> – <Thema>
- **Nutzer-Auftrag:** kurz, möglichst wörtlich
- **Delegiert:** welche Agenten mit welchem Modell (Abweichungen begründen)
- **Erledigt:** was ist fertig (Commits/PRs)
- **Offen / Übergabe:** angefangen, nicht fertig; berührte TODO-Einträge
- **Für die nächste Session:** Hinweise, Stolperfallen, Kontext
```

---

<!-- Neue Einträge direkt unter dieser Zeile einfügen -->

## 2026-10-16 – lokal-2026-10-16-hacs-recherche – HACS-Grundgerüst + CI
- **Nutzer-Auftrag:** „Repo bleibt vorerst privat. Bau zuerst das HACS-Grundgerüst mit CI.“
- **Delegiert:** entwickler (Sonnet), dann tester (Sonnet) und reviewer (Opus) parallel,
  danach Review-Nacharbeit durch den entwickler. Alle mit Standardmodell.
- **Erledigt:** PR rauchstefan/ha-ff-agent#1 per Squash gemergt (1d9ac86). tester: PASS,
  reviewer: freigegeben, CI grün, der HACS-Job wird wegen des privaten Repos
  übersprungen.
- **Annahmen des Projektleiters:**
  - HA-Mindestversion 2026.3.0 wegen des `brand/`-Ordners
  - `iot_class: cloud_polling` vorläufig
  - `single_config_entry`
  - Config-Flow ohne Felder
  - Platzhalter-Icon statt FF-Agent-Logo
- **Eigene Korrektur:** Der entwickler hatte `hacs/action` auf das Release 22.5.0 von 2022
  gepinnt. Der Projektleiter hat auf die SHA von `main` (2026-06-08) umgestellt, sonst
  liefen veraltete HACS-Checks.
- **Offen / Übergabe:** 261016-repo-oeffentlich (Nutzer), 261016-hacs-oeffentlich-pruefen.
- **Für die nächste Session:** pytest-homeassistant-custom-component 0.13.372 entspricht
  HA 2026.10.1 und Python 3.14. Wenn Dependabot es anhebt, kann sich die Python-Version
  ändern; dann `PYTHON_VERSION` in tests.yml anpassen.

## 2026-10-16 – lokal-2026-10-16-hacs-recherche – Recherche HACS-Kompatibilität
- **Nutzer-Auftrag:** „vollständige Recherche, was notwendig ist, um eine Integration HACS
  kompatibel zu machen. Wie muss das Repo aussehen, was wird wo definiert“
- **Delegiert:** researcher (Sonnet, Standard).
- **Erledigt:** docs/recherche/261016-hacs-anforderungen.md (1aa83ea). Der Projektleiter
  hat zwei Kernaussagen an den Primärquellen nachgeprüft: Private Repos funktionieren
  nicht mit HACS, und Custom-Integrationen haben ab HA 2026.3 einen eigenen
  `brand/`-Ordner.
- **Offen / Übergabe:** Neue TODOs 261016-repo-oeffentlich (Entscheidung des Nutzers) und
  261016-hacs-geruest.
- **Für die nächste Session:** Solange das Repo privat ist, lässt sich nichts über HACS
  testen. Auf diesem Rechner ist kein `python` im PATH, für Skripte Git Bash oder die
  Edit-Tools verwenden.

## 2026-10-16 – lokal-2026-10-16-projektsetup – Projektsetup
- **Nutzer-Auftrag:** Neues Projekt für eine HACS-Integration „FF Agent für Home
  Assistant“ aufsetzen, mit Orchestrierung über Rollen-Subagenten (Planen, Recherche,
  Implementierung, Testing, Projektleitung …), Modellzuordnung je Rolle, Arbeit auf
  GitHub. Aufgaben gehen immer an den Projektleiter.
- **Delegiert:** nichts (Setup durch die Hauptsession).
- **Erledigt:** `.claude/agents/` (7 Rollen), `.claude/settings.json` (Hauptsession =
  `projektleiter`), `CLAUDE.md`, `docs/` (Brief, Orchestrierung, Architektur-Stub,
  ADR 0001), `ai/`, README, Lizenz, `hacs.json`, Initial-Push nach `main`.
- **Offen / Übergabe:** Die erste fachliche Aufgabe kommt vom Nutzer. Vorschläge in
  `ai/TODO.md`.
- **Für die nächste Session:** Das Setting `agent` in `.claude/settings.json` greift erst
  in einer **neu gestarteten** Session. Prüfen, ob die Hauptsession tatsächlich als
  Projektleiter läuft; sonst gilt die Fallback-Regel aus `CLAUDE.md`.
