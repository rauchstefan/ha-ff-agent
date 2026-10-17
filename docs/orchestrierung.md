# Orchestrierung

Wie Aufgaben in diesem Projekt durch die Rollen laufen. Kurzfassung und Rollentabelle
stehen in `CLAUDE.md`, die Rollendefinitionen in `.claude/agents/`.

## Grundprinzip

```
Nutzer ──Aufgabe──▶ Projektleiter ──Briefing──▶ Fach-Agent
   ▲                     │  ▲                       │
   └──Bericht/Rückfrage──┘  └──────Ergebnis─────────┘
```

- Der Nutzer spricht nur mit dem **Projektleiter**.
- Der Projektleiter delegiert, die Fach-Agenten arbeiten und berichten zurück.
- Fach-Agenten sehen den Chatverlauf nicht. Alles, was sie brauchen, steht im Briefing
  oder im Repo.

## Briefing-Vorlage (Projektleiter → Fach-Agent)

```
Aufgabe: <ein Satz>
TODO-ID: <JJMMTT-thema>
Kontext: <warum, was ist schon entschieden, relevante Dateien/Dokumente>
Auftrag: <was genau zu tun ist>
Randbedingungen: <was nicht verändert werden darf, Branch, Stil>
Definition of Done: <prüfbare Kriterien>
Ergebnis: <wohin schreiben, was zurückmelden>
```

## Standardketten

| Aufgabe | Kette | Gate |
|---|---|---|
| Neues Feature | researcher* → architekt → entwickler → tester → reviewer → doku | tester PASS + reviewer freigegeben + CI grün |
| Bugfix | entwickler → tester → reviewer | wie oben |
| Recherche | researcher → architekt* | Projektleiter prüft Quellenlage |
| Doku | doku | Projektleiter liest gegen |
| Release | tester → reviewer → doku → **Nutzer-Freigabe** | Freigabe im Chat |

`*` nur bei Bedarf.

## Schleifen

- `tester` FAIL oder `reviewer` „nicht freigegeben“ → zurück an `entwickler` mit den
  konkreten Findings. Nach der dritten Runde ohne Erfolg holt der Projektleiter den
  `architekt` dazu oder fragt den Nutzer.
- Offene Fragen, die nur der Nutzer beantworten kann, sammelt der Projektleiter und
  stellt sie gebündelt.
- Nach „nicht freigegeben“ prüft der `reviewer` die Nacharbeit gezielt nach. Erst seine
  neue Freigabe zählt für das Gate.
- Agenten ohne Webzugriff (`doku`, `tester`) schreiben keine externen Fakten (Regellisten,
  API-Verhalten, Versionen) aus dem Gedächtnis. Solche Inhalte liefert der `researcher`
  vorab, oder der `reviewer` prüft sie per WebFetch.

## Gemeinsames Arbeitsverzeichnis

- Subagenten arbeiten im selben Checkout. Ein schreibender Agent checkt seinen
  Feature-Branch aus und kehrt am Ende auf `main` zurück.
- Der Projektleiter committet nur, wenn er `git branch --show-current` geprüft hat, und
  nicht, solange ein schreibender Agent läuft.
- `doku` hat kein Git. Der Projektleiter checkt den Branch vorher aus und committet danach.

## Parallelität

- Unabhängige Lese-Aufgaben (Recherchen, Reviews) dürfen parallel laufen.
- Schreibende Agenten nie gleichzeitig auf denselben Dateien; bei Bedarf eigene
  Branches oder Worktrees.

## Dokumentationspflicht

| Ergebnis | Ablage |
|---|---|
| Recherche | `docs/recherche/JJMMTT-<thema>.md` |
| Umsetzungsplan | `docs/plaene/JJMMTT-<thema>.md` |
| Architekturentscheidung | `docs/adr/NNNN-<titel>.md` |
| Aufgabenstand | `ai/TODO.md` |
| Sessionverlauf | `ai/JOURNAL.md` |
