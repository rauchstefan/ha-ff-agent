# ADR 0001: Entwicklung über einen Projektleiter mit Rollen-Agenten

- **Status:** angenommen
- **Datum:** 2026-10-16

## Kontext

Das Projekt wird von Claude-Sessions entwickelt. Der Nutzer möchte, dass die
Softwareentwicklung arbeitsteilig nach Rollen (Planung, Recherche, Implementierung,
Testing, Review, Doku) abläuft und alle Aufgaben über eine Projektleitung laufen.

## Entscheidung

- Rollen als Claude-Code-Subagenten unter `.claude/agents/`, je mit eigenem Modell und
  Aufwand (Tabelle in `CLAUDE.md`).
- Die Hauptsession läuft als `projektleiter` (`.claude/settings.json`, Key `agent`).
  Fallback-Regel in `CLAUDE.md`, falls das Setting nicht greift.
- Übergaben über das Repo: `ai/` für Status, Backlog und Journal; `docs/` für
  Recherchen, Pläne und ADRs.
- Qualitäts-Gate vor jedem Merge in `main`: CI grün, `tester` PASS, `reviewer` freigegeben.

## Alternativen

- Eine einzige Session ohne Rollen: weniger Aufwand, aber keine unabhängige Prüfung
  und höhere Kosten, weil alles auf dem teuersten Modell läuft.
- Rollen als parallele Sessions statt Subagenten: mehr Isolation, aber schwerer zu
  steuern; bleibt für große, unabhängige Arbeitspakete möglich.

## Konsequenzen

- Mehr Dokumentation pro Aufgabe, dafür nachvollziehbare Entscheidungen.
- Günstige Modelle (Sonnet, Haiku) für Routinearbeit, Opus für Planung, Steuerung
  und Review.
