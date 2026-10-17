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
  - PR rauchstefan/ha-ff-agent#7 per Squash gemergt (fa6a52d). Damit ist das MVP
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
  - PR rauchstefan/ha-ff-agent#6 per Squash gemergt (348428a), 478 Tests, Abdeckung 100 %
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
  - PR rauchstefan/ha-ff-agent#5 per Squash gemergt (bba8b34), 404 Tests, Abdeckung 100 %.
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
  - PR rauchstefan/ha-ff-agent#4 per Squash gemergt (22a7c4c), 270 Tests, Abdeckung 100 %
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
  - PR rauchstefan/ha-ff-agent#3 per Squash gemergt (bb533a8)
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
  - PR rauchstefan/ha-ff-agent#2 per Squash gemergt (0fb459a). tester: PASS (30 Tests
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
