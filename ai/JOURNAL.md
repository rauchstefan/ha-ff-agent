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

## 2026-10-18 – lokal-2026-10-18-v0-2-feedback – Neues Icon
- **Nutzer-Auftrag:** „Cooles Logo, das Home Assistant/HACS zeigt, mit FF oder FF-Agent;
  nicht das offizielle FF-Agent-Logo.“
- **Vorgehen:** Der Projektleiter hat drei Entwürfe als Skizze gezeigt; der Nutzer wählte
  Entwurf A (rot, Haus-Umriss, „FF“). Die echten Logos von Home Assistant und HACS sind
  bewusst nicht verwendet, sie sind Marken.
- **Delegiert:**
  - entwickler (Sonnet): Rendering per PowerShell/System.Drawing, ohne Downloads
  - reviewer mit `model: sonnet` und tester mit `model: haiku`: kleiner Diff ohne Python-Code
- **Erledigt:** PR rauchstefan/ha-ff-agent#10 per Squash gemergt (2b760c9):
  - `brand/icon.png` und `brand/icon@2x.png` neu
  - Quelle `docs/assets/logo.svg`
  - Logo in der README mit absoluter URL, damit es auch in HACS erscheint
  - CHANGELOG `[Unreleased]`
- **Offen:** Ob HA ohne `brand/logo.png` das Icon als Logo zeigt, ist ungeprüft. Fehlt es in
  der Integrationsansicht, eine Kopie als `logo.png` nachreichen. Das Icon ist noch in
  keinem Release.

## 2026-10-18 – lokal-2026-10-18-v0-2-feedback – Doku zweisprachig, Release v0.3.0
- **Nutzer-Auftrag:** „Doku auf GitHub sauber ziehen, Deutsch und Englisch, dann auf 0.3
  hochziehen und veröffentlichen.“
- **Nutzerentscheidungen:** README zweisprachig in einer Datei; v0.3.0 als Vorabversion.
- **Delegiert:**
  - doku mit `model: sonnet` statt Haiku, weil eine 650-Zeilen-README vollständig zu
    übersetzen und gegen den Code zu prüfen war; ohne Bash, der Projektleiter hat
    committet
  - entwickler (Sonnet) für die Release-Vorbereitung
  - reviewer (Opus) und tester mit `model: haiku` parallel; der Tester musste nur
    CI-Ergebnisse und Release-Artefakte prüfen, es gab keine Code-Änderung
- **Erledigt:**
  - PR rauchstefan/ha-ff-agent#9 per Squash gemergt (619a53e), Pre-Release v0.3.0:
    https://github.com/rauchstefan/ha-ff-agent/releases/tag/v0.3.0
  - Review-Hinweise (volle Menü-Labels, Platzhalter statt `event.ff_agent_alarm` im
    Recorder-Beispiel, Einleitung im CHANGELOG) hat der Projektleiter selbst eingearbeitet;
    es waren reine Doku-Kleinigkeiten.
- **Offen / Übergabe:** Gegenprobe des Nutzers in der echten Instanz. Die
  `docs-*`-Marker der Quality Scale stehen nur im deutschen Teil der README; das ist
  unschädlich.
- **Für die nächste Session:** Release-Notes = Abschnitt `[0.3.0]` aus dem CHANGELOG. Er
  hat DE oben und EN unter `### English`; neue Einträge in beiden Sprachen pflegen.

## 2026-10-18 – lokal-2026-10-18-v0-2-feedback – Rückmeldungen des Nutzers zu v0.2.0
- **Nutzer-Auftrag:** Erst Themen als TODOs sammeln, dann „starte jetzt mit der
  Implementation der ToDos“.
- **Delegiert:**
  - architekt (Opus) für den Plan `docs/plaene/261018-v0-2-feedback.md`; er hatte kein
    Bash, der Projektleiter hat committet
  - entwickler (Sonnet) für die Umsetzung, danach entwickler mit `model: sonnet` explizit
    für die Textkorrekturen aus dem Review
  - tester (Sonnet) und reviewer (Opus) parallel; beide brachen an einem API-Limit ab und
    wurden per SendMessage fortgesetzt
- **Erledigt:**
  - PR rauchstefan/ha-ff-agent#8 per Squash gemergt (24d4f43). tester PASS, reviewer
    freigegeben, CI grün.
  - Sechs TODOs erledigt, `261018-reihenfolge-zusage` verworfen: Der Nutzer will die
    Namen behalten, und HA sortiert die Geräteseite alphabetisch nach Namen.
  - Leere Menütexte nach dem Update: Ursache war der Browser-Cache (Strg+F5 half), kein
    Code-Fehler. Der Hinweis steht jetzt in README und CHANGELOG.
- **Nutzerentscheidungen:**
  - Button-Namen bleiben „Zusagen“/„Absagen“.
  - Reset-Button heißt „Alarm zurücksetzen“ und darf vorne stehen.
  - Standort im Setup wie in den Optionen, nur person/device_tracker, ohne Zonen.
- **Offen / Übergabe:** Nicht in echter HA-Instanz geprüft. Offen ist vor allem, ob der
  alte Geräte-Link verschwindet. Kein Release, ein Versionssprung braucht die Freigabe des
  Nutzers.
- **Für die nächste Session:** Der Worktree-Branch `claude/v0-2-0-reconfig-adjustments-99f09e`
  steht auf `main`; `ai/`-Commits gehen per `git push origin HEAD:main`.

## 2026-10-18 – lokal-2026-10-16-hacs-recherche – Release v0.2.0 (Vorabversion)
- **Nutzer-Aufträge:**
  - „Bereite ein Release v0.2.0 als Vorabversion vor.“
  - Hersteller: neutraler Eintrag (Rückfrage).
  - „Go: Lege Tag und GitHub-Release v0.2.0 als Pre-Release auf dabe583 an.“
- **Delegiert:** entwickler (Sonnet) für den Release-PR, tester (Sonnet) und reviewer (Opus)
  parallel.
- **Erledigt:**
  - PR rauchstefan/ha-ff-agent#7 per Squash gemergt (dabe583):
    - `MANUFACTURER = "ha-ff-agent (inoffiziell)"`
    - Version 0.2.0
    - CHANGELOG `[0.2.0]`
    - README und Testanleitung
    - Test: kein Herstellername in Code und Nutzerdoku
    - Test: Manifest-Version = oberste CHANGELOG-Version
    - Regel in CLAUDE.md
  - tester PASS, reviewer freigegeben. Seine Text-Hinweise hat der Projektleiter direkt
    auf dem Branch korrigiert: Reichweite der Firmennamen-Aussage, Einschränkungen,
    Update-Hinweis, „Vorabversionen“.
  - **Pre-Release v0.2.0** auf dabe583 angelegt; die Release-Notes stammen aus dem
    CHANGELOG plus Installationshinweis.
- **Offen / Übergabe:**
  - 261018-recherche-namen (Entscheidung des Nutzers)
  - Ergebnisse des echten Tests (Rückmeldeliste)
  - 261018-ntfy-feinschliff, 261018-configflow-aufteilen, 261017-zusage-standort-transport,
    261017-quality-todos, 261017-hacs-default

## 2026-10-18 – lokal-2026-10-16-hacs-recherche – Merge von #4 und #6
- **Nutzer-Auftrag:** „Ich bin mit dem Testen fertig. Merge #4 und #6.“
- **Erledigt:**
  - #4 per Squash nach main (5696f51).
  - Die Base von #6 auf main umgestellt. Danach gab es Konflikte, weil #4 als Squash
    gemergt war und #6 dieselben Änderungen als Einzelcommits trug.
  - Gelöst durch Merge von origin/main in den Branch von #6, mit der Fassung von #6 in
    den vier Konfliktdateien (CHANGELOG, de.json, en.json, test_metadata.py).
  - Geprüft: Gegenüber dem freigegebenen Stand f3fa723 ändern sich nur `ai/`-Dateien.
  - CI grün, #6 per Squash gemergt (dddc3f9), beide Branches gelöscht, main grün.
- **Lernpunkt:** Gestapelte PRs, die einzeln per Squash gemergt werden, erzeugen beim
  zweiten PR Konflikte. Künftig entweder den unteren PR mergen und den oberen sofort
  rebasen lassen, oder gestapelte Arbeit in einem PR bündeln.
- **Offen / Übergabe:**
  - Ergebnisse des echten Tests des Nutzers (Rückmeldeliste) stehen noch aus und gehören
    in ADR 0002/0003.
  - Ein Release v0.2.0 nur mit Freigabe.
  - Folge-TODOs: 261018-ntfy-feinschliff, 261018-configflow-aufteilen,
    261017-geraeteinfo-hersteller, 261017-zusage-standort-transport.

## 2026-10-18 – lokal-2026-10-16-hacs-recherche – Wählbare Alarmquelle (ADR 0003), Gate für #4 und #6
- **Nutzer-Aufträge:**
  - „bitte 1 und 2 umsetzen, und dem Nutzer die Wahl geben“ (Nabu Casa und ntfy).
  - Flow: Nabu Casa als empfohlen darstellen, nicht erzwingen; bei „Nein“ zu ntfy; je Weg
    ein Einrichtungsdialog Schritt für Schritt.
  - „Trotzdem fortfahren“ behalten, ntfy per GET `/trigger`.
  - Merge erst, wenn sein Test fertig ist.
- **Delegiert:**
  - architekt (Opus): ADR 0003 und Plan, zwei Runden
  - entwickler mit **Opus statt Sonnet**: viele Flow-Verzweigungen, Migration und der
    heikle Laufzeitfilter für eine fremde Entität
  - tester (Sonnet) und reviewer (Opus) für #4 und #6
  - zwei Runden Nacharbeit, Nachprüfung durch den reviewer
  - Beide Prüfer liefen nach einem API-Limit per SendMessage weiter.
- **Erledigt:**
  - ADR 0003 angenommen, Plan docs/plaene/261017-alarmquelle-ntfy.md.
  - PR rauchstefan/ha-ff-agent#5: `docs/` von ruff ausgenommen, weil Python-Beispiele in
    Plänen main zweimal rot gemacht hatten.
  - PR rauchstefan/ha-ff-agent#6 (Base #4), Stand f3fa723:
    - Einstiegsfrage Cloud ja/nein, geführte Dialoge, ntfy über die Core-Integration
    - Migration 1.1 → 1.2
    - Selbstheilung bei neuem ntfy-Abo
    - `reconfigure_successful_local`
    - 642 Tests, Abdeckung 100 %
  - #4 und #6: tester PASS, reviewer freigegeben. **Nicht gemergt**, wartet auf das Okay
    des Nutzers.
  - Neue TODOs: 261018-ntfy-feinschliff, 261018-configflow-aufteilen.
- **Hinweise:**
  - Der tester hat HA-Wheels von PyPI per curl geladen und nur die
    `translations/de.json` der ntfy-Integration gelesen, nichts ausgeführt. Damit hat er
    die deutschen Labels geprüft; Ergebnis: „Dienst-URL“ statt „Dienstadresse“.
  - Der entwickler hat für #6 einmal node lokal zur Prüfung der Übersetzungen genutzt;
    in der Nacharbeit nicht mehr.
- **Offen / Übergabe:**
  - Merge-Reihenfolge nach dem Okay: #4 → main, Base von #6 auf main umstellen, #6 mergen
    (Squash).
  - Danach ist ein Release-Kandidat möglich (v0.2.0), nur mit Freigabe des Nutzers.
  - Der echte Test des Nutzers läuft noch.

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – Erste Findings aus dem echten Test
- **Nutzer:**
  - Installation über HACS auf der eigenen Instanz ist erledigt.
  - Finding: Der Fundort der Rückmelde-URL ist falsch beschrieben.
  - „Ich möchte, dass die Implementationen erstmal warten, bis ich fertig bin mit testen.“
  - Feature-Wünsche: Standort aus Home Assistant für die Zusage, Verkehrsmittel beim
    Zusagen wählbar.
- **Delegiert:** entwickler (Sonnet) für den Bugfix. Er war fertig, bevor die Bitte zu
  warten kam.
- **Erledigt:**
  - Recherche 3.7: Fundort „Weblinks für Einsatzmeldung“; die offiziellen Hinweise von
    FF Agent klären A8 und A9 (`transport` CAR/FEET/BICYCLE, Standard CAR).
  - PR rauchstefan/ha-ff-agent#4 (Fundort plus Verkehrsmittel), CI grün, **geparkt**,
    nicht gemergt.
  - Neues TODO 261017-zusage-standort-transport.
- **Offen / Übergabe:**
  - Erst nach dem Signal des Nutzers weiter: tester und reviewer für #4, Merge, dann die
    Feature-Planung.
  - Zugriff auf HA per MCP oder SSH bleibt zurückgestellt.

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – Veröffentlichung und Release v0.1.0
- **Nutzer-Auftrag:** „Ich schlage vor, wir schalten es öffentlich und machen die komplette
  Installation einmal durch“
- **Nutzerentscheidungen (per Rückfrage):**
  - Historie umschreiben
  - Repo öffentlich machen
  - v0.1.0 als Pre-Release
  - Nachdem klar war, dass geschlossene PRs die private Mailadresse weiter zeigen
    (`.patch`), entschied der Nutzer: **neues sauberes Repo**, altes Repo wird Archiv.
- **Prüfung vor der Veröffentlichung (Projektleiter):** komplette Git-Historie gescannt.
  - Keine echten UUIDs, Tokens, Koordinaten oder Benutzernamen.
  - Funde: die private Hotmail-Adresse als Commit-Autor in 84 Commits; in einer
    Recherche-Datei die E-Mail-Adresse und eine Kontozuordnung eines Dritten
    (Homey-Entwickler).
- **Erledigt:**
  - Sicherung (Git-Bundle im Scratchpad)
  - `main` per `git filter-branch` umgeschrieben (Autor/Committer auf noreply,
    Drittdaten aus allen Versionen entfernt) und geprüft: 35 Commits, 0 Treffer,
    Dateistand identisch
  - altes Repo umbenannt in `ha-ff-agent-archiv` (privat); neues Repo `ha-ff-agent`
    angelegt, zuerst privat gepusht und geprüft, dann öffentlich mit Beschreibung,
    Topics und Issues
  - lokale `git config user.email` auf noreply gesetzt; Regel in CLAUDE.md
  - PR-Verweise in ai/ und docs/ auf `ha-ff-agent-archiv#N` umgestellt
  - HACS-Validierung erstmals gelaufen: alle 9 Checks bestanden, kein `ignore`
  - Cron täglich (PR rauchstefan/ha-ff-agent#2, nur CI-Zeile, ohne tester/reviewer)
  - CHANGELOG.md, Release **v0.1.0 als Pre-Release** auf grünem Commit
  - README und Testanleitung auf HACS-Installation umgestellt
- **Abweichung vom Standard-Release-Ablauf:** Kein eigener tester- oder reviewer-Lauf für
  das Release. Alle enthaltenen Änderungen hatten das Gate je PR bereits durchlaufen, die
  CI auf dem Release-Commit war grün, das Release ist als Vorabversion markiert, und der
  Nutzer hat es ausdrücklich freigegeben.
- **Offen / Übergabe:**
  - 261017-echter-test: Der Nutzer installiert über HACS und testet nach
    docs/plaene/261017-echter-test-anleitung.md.
  - 261017-dependabot-hassfest (PR rauchstefan/ha-ff-agent#1)
  - 261017-hacs-default
- **Für die nächste Session:**
  - Die Git-Sicherung liegt nur im temporären Scratchpad. Die dauerhafte Sicherung der
    alten Historie ist das Archiv-Repo.
  - Lokale `refs/original/` von filter-branch sind entfernt. Der Remote `archiv` zeigt auf das private Archiv-Repo; nie mit `--all` oder `--mirror` nach `origin` pushen.

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – Freigabe echter Test, Anleitung
- **Nutzer-Auftrag:** „Ich gebe den echten Test frei. Gib mir die
  Schritt-für-Schritt-Anleitung für Installation, Webhook und Testalarm.“
- **Delegiert:** nichts. Die Anleitung hat der Projektleiter aus README, Übersetzungen
  und diagnostics.py zusammengestellt.
- **Erledigt:** docs/plaene/261017-echter-test-anleitung.md mit folgenden Teilen:
  - Vorbereitung (Backup, Version, Erreichbarkeit, Empfänger des Testalarms)
  - manuelle Installation
  - Feldwerte für FF Agent, inklusive Dummy-Header zur Messung von A12
  - Messungen A–C
  - Aufräumen
  - Rückmeldeliste mit Diagnose-Schlüsseln je Annahme
- **Offen / Übergabe:**
  - 261017-echter-test wartet auf die Rückmeldeliste des Nutzers.
  - Danach Annahmen in ADR 0002 und architektur.md eintragen und Folge-TODOs anlegen
    (Redirects, Token-Standard, Einsatzdetails).
- **Für die nächste Session:** Claude führt den Test nicht selbst aus und hat keinen
  Zugriff auf FF Agent oder die HA-Instanz. Ausgewertet werden nur die Angaben des
  Nutzers bzw. redigierte Diagnose-Dateien.

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – MVP PR 6 (Doku und Qualität), MVP fertig
- **Nutzer-Auftrag:** „Ja, starte mit PR 6 (Doku und Qualitätsabschluss).“
- **Delegiert:**
  - entwickler (Sonnet): Datenschutztest über den ganzen Lebenszyklus
  - doku mit **Sonnet statt Haiku**: Das README enthält sicherheitsrelevante
    Einrichtungsschritte und musste fachlich exakt sein.
  - tester (Sonnet) und reviewer (Opus) parallel
  - danach eine neue reviewer-Nachprüfung, weil die erste Instanz ihren Bericht nicht
    zugestellt hat
- **Erledigt:**
  - PR rauchstefan/ha-ff-agent-archiv#7 per Squash gemergt (fa6a52d). Damit ist das MVP
    fertig.
  - reviewer im ersten Durchlauf **nicht freigegeben**: docs/quality-scale.md stammte
    aus dem Gedächtnis und war falsch (`docs-triggers`/`docs-conditions` gehören zu
    Bronze, `common-modules` hat keine Ausnahme, Gold- und Platin-Regeln fehlten).
  - Korrigiert nach der offiziellen Liste (54 Regeln). Der Projektleiter hat sie selbst
    per WebFetch geprüft.
  - README-Warnungen geschärft (Logs, Header-Reihenfolge). Nachprüfung: freigegeben.
- **Lernpunkt:** Agenten ohne Webzugriff (doku) dürfen Regellisten oder API-Fakten nicht
  aus dem Gedächtnis schreiben. Solche Inhalte vorab vom researcher holen lassen oder vom
  reviewer mit WebFetch prüfen lassen.
- **Offen / Übergabe:**
  - 261017-echter-test (Freigabe des Nutzers nötig)
  - 261016-repo-oeffentlich (Entscheidung des Nutzers)
  - 261017-reply-redirects
  - 261017-quality-todos
  - 261017-token-default
  - 261017-einsatzdetails
  - Ein Release (Tag 0.1.0) nur mit Freigabe.

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – MVP PR 5 (Options Flow und Reconfigure)
- **Nutzer-Auftrag:** „Ja, starte mit PR 5 (Options Flow und Reconfigure).“
- **Delegiert:**
  - entwickler (Sonnet): Umsetzung und Härtung
  - tester (Sonnet) und reviewer (Opus) parallel
  - Standardmodelle
- **Entscheidung des Projektleiters:** Ein Reload behält einen laufenden Alarm nicht. Der
  Zustand bleibt flüchtig, der Options-Text weist darauf hin.
- **Erledigt:**
  - PR rauchstefan/ha-ff-agent-archiv#6 per Squash gemergt (348428a), 478 Tests, Abdeckung 100 %
  - tester: PASS; reviewer: freigegeben, ohne „Sollte“-Punkte
  - Härtung: Reload wird vor dem Löschen des alten Cloudhooks geplant; Repair-Issue fällt
    beim neuen Zugang weg
  - 261017-reply-test-k5 mit erledigt
  - Beispiel-Automationen gesichert in docs/plaene/261017-beispiel-automationen.md (stand
    vorher nur im Agentenbericht)
- **Hinweis:**
  - Der entwickler hatte ruff einmal lokal über ein npm-Paket von Astral ausgeführt (Skript
    im Temp-Ordner, nicht im Repo).
  - Danach die Vorgabe gemacht: keine lokalen npm- oder pip-Ausführungen, ruff läuft in
    der CI.
- **Offen / Übergabe:**
  - nächster Schritt 261017-mvp-6-doku-qualitaet (Agent `doku`)
  - danach der echte Test und Release-Vorbereitung, beides nur mit Nutzerfreigabe

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – MVP PR 4 (Zusage/Absage)
- **Nutzer-Auftrag:** „Ja, starte mit PR 4 (Rückmeldung: Zusage/Absage).“
- **Delegiert:**
  - entwickler (Sonnet): Umsetzung und zwei Nacharbeitsrunden
  - tester (Sonnet) und reviewer (Opus) parallel, danach eine gezielte Nachprüfung durch
    den reviewer
  - Standardmodelle
- **Unterbrechung:** Ein API-Limit hat den entwickler mitten in der Arbeit gestoppt. Seine
  uncommitteten Änderungen blieben im Arbeitsverzeichnis, und er hat nach dem Reset per
  SendMessage mit Kontext weitergemacht.
- **Erledigt:**
  - PR rauchstefan/ha-ff-agent-archiv#5 per Squash gemergt (bba8b34), 404 Tests, Abdeckung 100 %.
  - Der reviewer hatte im ersten Durchlauf **nicht freigegeben**, wegen B1: Der
    Wiederholungsschutz merkte sich den Erfolg je Aktion, deshalb wurde bei „Zusagen →
    Absagen → Zusagen“ die dritte Rückmeldung still verschluckt. Behoben: Es zählt nur
    noch der letzte Erfolg; Plan korrigiert. Nachprüfung: freigegeben.
  - Transport in der Action als `car` (übersetzbar, hassfest-konform), Abbildung auf
    `CAR` für FF Agent.
- **Erkenntnis:** HA nutzt seit 2026.9 `probatio`, voluptuous ist nicht mehr installiert.
  `homeassistant/__init__.py` setzt per `probatio.compat.install_as_voluptuous()` einen
  Alias, deshalb funktioniert `import voluptuous as vol` für Custom-Integrationen weiter
  (Blog der HA-Entwickler vom 30.09.2026). Nachgetragen in docs/architektur.md.
- **Offen / Übergabe:**
  - nächster Schritt 261017-mvp-5-options-reconfigure
  - neu: 261017-reply-redirects, 261017-reply-test-k5
  - der echte Test steht weiter aus

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – MVP PR 3 (Alarm-Logik und Entitäten)
- **Nutzer-Auftrag:** „Starte mit PR 3 (Alarm-Logik und Entitäten). Den echten Test machen
  wir später.“
- **Delegiert:**
  - entwickler (Sonnet): Umsetzung und Nacharbeit
  - tester (Sonnet) und reviewer (Opus) parallel
  - Standardmodelle
- **Erledigt:**
  - PR rauchstefan/ha-ff-agent-archiv#4 per Squash gemergt (22a7c4c), 270 Tests, Abdeckung 100 %
  - tester: PASS, 9 Szenario-Tests ergänzt; reviewer: freigegeben
  - Nacharbeit:
    - Uhr-Rücksprung zählt als neuer Alarm
    - Manager wird erst nach dem Lesen des Bodys geholt (Reload-Fenster)
    - Restore ohne Zeitzone wird ignoriert
    - Pflichtfilter der Beispiel-Automation per Test belegt
  - docs/architektur.md: Fallstricke zu Event-Automation, Reload und Uhrzeit
- **Offen / Übergabe:**
  - nächster Schritt 261017-mvp-4-rueckmeldung
  - für PR 5: Hinweise zum Options-Schema und zum Reload-Verhalten
  - für PR 6: Beispiel-Automation mit Filtern
  - der echte Test steht weiter aus (Nutzer: „später“)
- **Für die nächste Session:** In HA 2026.10 wirft `device_registry.async_get_device` in den
  Tests einen Fehler; stattdessen `async_get_device_by_identifier` verwenden.

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – Python-Ziel und MVP PR 2 (Webhook)
- **Nutzer-Auftrag:** „Kläre zuerst die Python-Mindestversion (261017-python-target),
  dann PR 2.“
- **Python-Ziel:** Ohne Code erledigt. Laut PyPI verlangt HA ab 2026.3.0
  Python ≥ 3.14.2. Das passt zu ruff `py314` und ist in docs/architektur.md vermerkt.
- **Delegiert:**
  - entwickler (Sonnet): Umsetzung und Nacharbeit
  - tester (Sonnet) und reviewer (Opus) parallel
  - Standardmodelle
- **Erledigt:**
  - PR rauchstefan/ha-ff-agent-archiv#3 per Squash gemergt (bb533a8)
  - tester: PASS, 14 Randfall-Tests ergänzt; reviewer: freigegeben
  - Nacharbeit: persistentes Repair-Issue, Content-Type nur als Medientyp, Diagnostics
    bei nicht geladenem Eintrag
  - Doku zu den Punkten K2 und K6 im ADR bzw. Plan
  - 215 Tests, Abdeckung 100 %
- **Panne:**
  - Der Doku-Commit des Projektleiters ist auf dem Feature-Branch gelandet, weil der
    entwickler ihn im gemeinsamen Arbeitsverzeichnis ausgecheckt hatte.
  - Folgen: keine, der Commit kam per Squash nach main.
  - Fallstrick in CLAUDE.md ergänzt.
- **Offen / Übergabe:**
  - nächster Schritt 261017-mvp-3-alarm-entitaeten
  - erster echter Test (Anleitung im PR-3-Bericht des entwicklers, siehe PR-Beschreibung)
    nur mit Nutzerfreigabe
  - für PR 5: Repair-Issue beim Setup löschen, wenn `require_token` aus ist
- **Für die nächste Session:** HA Core loggt die Webhook-ID selbst auf DEBUG/INFO/WARNING.
  Das muss in PR 6 in die Nutzerdoku (Debug-Logs von webhook und http nicht teilen).

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – MVP PR 1 (Config Flow)
- **Nutzer-Auftrag:** „ADR 0002 ist freigegeben. Starte mit PR 1 (Config Flow).“
- **Delegiert:**
  - entwickler (Sonnet): Umsetzung und Nacharbeit
  - tester (Sonnet) und reviewer (Opus) parallel
  - alle mit Standardmodell
- **Erledigt:**
  - ADR 0002 auf „angenommen“ gesetzt.
  - PR rauchstefan/ha-ff-agent-archiv#2 per Squash gemergt (0fb459a). tester: PASS (30 Tests
    ergänzt), reviewer: freigegeben.
  - Nacharbeit nach dem Review:
    - Cloudhook-Fehler abgefangen
    - Übersetzung `already_in_progress`
    - Host-Härtung (ASCII, LDH)
    - Fallback bei leerem Namen
    - Vertragstest gegen die echte Cloud-API (per `ast`)
    - Coverage-Gate 95 % (gemessen 100 %)
- **Offen / Übergabe:**
  - nächster Schritt 261017-mvp-2-webhook
  - neu: 261017-python-target (ruff `py314` gegenüber HA-Mindestversion 2026.3)
- **Für die nächste Session:**
  - `homeassistant.components.cloud` lässt sich in der CI nicht importieren (turbojpeg).
    Tests nutzen deshalb `tests/common.py::patch_cloud`.
  - ruff formatiert auch Python-Blöcke in Markdown-Dateien.

## 2026-10-17 – lokal-2026-10-16-hacs-recherche – ADR 0002 Integrationsweg
- **Nutzer-Auftrag:** Screenshots der Rückmelde-URLs und des Dialogs „Webhook hinzufügen“
  (generischer Webhook).
- **Delegiert:** architekt (Opus, Standard). Er hat in einer zweiten Runde die
  Webhook-Dialogfakten eingearbeitet.
- **Erledigt:**
  - Rückmelde-URLs geschwärzt dokumentiert (9c4a66e)
  - ADR 0002 (vorgeschlagen) und Plan docs/plaene/261017-mvp-alarm-zusage.md mit 6 PRs
  - docs/architektur.md aktualisiert
  - TODOs 261017-mvp-1 bis -6, token-default und einsatzdetails angelegt
- **Kernentscheidungen:**
  - Alarm kommt per persönlichem Webhook an einen HA-Webhook (Cloudhook, falls vorhanden)
  - Zusage und Absage per GET auf die persönliche Rückmelde-URL; nur UUID und Host werden
    gespeichert
  - `cloud_push`, `service`
  - ein Config-Eintrag pro Person
  - Zusatz-Token im Header optional
- **Datenschutz:** Die Screenshots des Nutzers enthielten eine echte Rückmelde-UUID, Koordinaten
  und einen vom Browser automatisch eingesetzten Benutzernamen. Nichts davon ist im Repo; per
  grep geprüft.
- **Offen / Übergabe:**
  - Die Freigabe des ADR durch den Nutzer und die Fragen in ADR 0002 stehen aus
    (Annahmen A3–A13).
  - Echte Tests in der HA-Instanz nur mit Freigabe.

## 2026-10-16 – lokal-2026-10-16-hacs-recherche – Vertiefung Webhook und Zusage
- **Nutzer-Auftrag:** Antworten des Nutzers, siehe docs/projekt-brief.md:
  - Admin, aber die Integration ist für Einsatzkräfte gedacht
  - PRO-Lizenz mit Gateway
  - persönliche Webhooks vorhanden
  - MVP: Alarm, Zusage, Einsatzdetails
  - Hersteller ist angefragt
- **Delegiert:** researcher (Sonnet, Standard).
- **Erledigt:** docs/recherche/261016-ffagent-webhook-zusage.md.
  - Persönliche Webhooks sind öffentlich nicht dokumentiert.
  - Für die Zusage wurde kein Endpunkt gefunden.
  - Neu gefunden: ein persönlicher iCal-Feed (Einsatzverlauf) und ein öffentliches
    Homepage-Widget der Einheit.
- **Offen / Übergabe:**
  - Das ADR zum Integrationsweg ist bewusst zurückgestellt, bis die Web-UI-Fragen
    (Abschnitt 6 des Dokuments) und die Antwort des Herstellers vorliegen.
  - TODO 261016-ffagent-klaerung bleibt in Arbeit.
- **Für die nächste Session:** Den Homey-Bundle herunterladen oder App-Verkehr mitschneiden
  nur nach ausdrücklicher Nutzerfreigabe.

## 2026-10-16 – lokal-2026-10-16-hacs-recherche – Recherche FF-Agent-Schnittstellen
- **Nutzer-Auftrag:** „Starte die Recherche zu den FF-Agent-Schnittstellen (API, Webhooks,
  Alarmformate).“
- **Delegiert:** researcher (Sonnet, Standard).
- **Erledigt:**
  - docs/recherche/261016-ffagent-schnittstellen.md
  - Der researcher konnte die Hersteller-PDFs nicht lesen. Der Projektleiter hat sie über
    WebFetch geladen, mit dem Read-Tool gelesen und als Abschnitt 0 nachgetragen.
  - Kenntnisstand in docs/architektur.md übernommen.
- **Ergebnis:**
  - Die WebAPI ist nur eingehend und für Admins der Einheit.
  - Instant Commands (2019) haben keinen Alarm-Auslöser und keine HTTP-Aktion.
  - Eine ausgehende Schnittstelle zu HA ist öffentlich nicht dokumentiert. Es gibt Hinweise
    auf einen Webhook (Homey) und einen Reiter „Fireboard-API“.
- **Offen / Übergabe:** 261016-ffagent-klaerung wartet auf Antworten des Nutzers.
- **Für die nächste Session:** PDFs lassen sich mit WebFetch laden (die Datei landet in
  tool-results) und dann mit dem Read-Tool ohne `pages`-Parameter lesen. pdftoppm fehlt.

## 2026-10-16 – lokal-2026-10-16-hacs-recherche – HACS-Grundgerüst + CI
- **Nutzer-Auftrag:** „Repo bleibt vorerst privat. Bau zuerst das HACS-Grundgerüst mit CI.“
- **Delegiert:** entwickler (Sonnet), dann tester (Sonnet) und reviewer (Opus) parallel,
  danach Review-Nacharbeit durch den entwickler. Alle mit Standardmodell.
- **Erledigt:** PR rauchstefan/ha-ff-agent-archiv#1 per Squash gemergt (1d9ac86). tester: PASS,
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
