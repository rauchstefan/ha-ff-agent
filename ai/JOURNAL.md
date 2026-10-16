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
