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
- **Status:** erledigt (2026-10-17: neues öffentliches Repo mit bereinigter Historie, altes als privates Archiv ha-ff-agent-archiv; Beschreibung, Topics, Issues gesetzt)
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
- **Status:** erledigt (2026-10-17: HACS-Validierung 9/9 Checks ohne ignore, Cron täglich per PR rauchstefan/ha-ff-agent#2)
- **Priorität:** mittel
- **Rolle(n):** tester, entwickler
- **Beschreibung:** Solange das Repo privat ist, überspringt validate.yml den HACS-Job.
  Nach der Veröffentlichung prüfen, ob er ohne `ignore` grün läuft (Brands-Check,
  Beschreibung, Topics). Dann den Cron in validate.yml wieder auf täglich stellen.
  `hacs/action` ist auf eine SHA von `main` gepinnt, weil das letzte Release von 2022
  ist. Dependabot aktualisiert solche Branch-Pins nicht, also gelegentlich von Hand
  nachziehen. Dasselbe gilt für hassfest@master.
- **Definition of Done:** HACS-Job grün, Cron täglich.
- **Verweise:** PR rauchstefan/ha-ff-agent-archiv#1

### 261017-echter-test – Erster echter Test mit FF Agent und HA-Instanz
- **Status:** in Arbeit (Freigabe des Nutzers 2026-10-17; Anleitung docs/plaene/261017-echter-test-anleitung.md; wartet auf Rückmeldeliste)
- **Priorität:** hoch
- **Rolle(n):** Nutzer, Projektleiter, tester
- **Beschreibung:**
  - Integration in die echte HA-Instanz installieren (Repo privat, daher manuell kopieren).
  - Persönlichen Webhook in FF Agent nach README anlegen und einen Testalarm auslösen.
  - Während des Testalarms Absagen und Zusagen.
  - Diagnose auswerten: Annahmen A1–A9, A12, A13 aus ADR 0002, dazu das Redirect-Verhalten
    (261017-reply-redirects).
  - Ergebnisse in docs/architektur.md bzw. ADR 0002 eintragen.
- **Definition of Done:** alle Annahmen bestätigt oder widerlegt und dokumentiert,
  Folge-TODOs angelegt.
- **Verweise:** README (Einrichtung, Fehlerbehebung), ADR 0002 (Annahmen)

### 261017-dependabot-hassfest – Dependabot-PR für den hassfest-Pin prüfen
- **Status:** erledigt (2026-10-17, per Ersatz-PR rauchstefan/ha-ff-agent#3; #1 geschlossen. Hinweis: Das gh-Token dieses Rechners hat keinen `workflow`-Scope, deshalb lassen sich Dependabot-PRs auf Workflow-Dateien nicht per gh mergen. Ausweg: Ersatz-PR oder Merge im Browser)
- **Priorität:** niedrig
- **Rolle(n):** reviewer
- **Beschreibung:** Dependabot hat PR rauchstefan/ha-ff-agent#1 geöffnet: Bump des Pins von
  `home-assistant/actions/hassfest`. Prüfen, ob die CI grün ist, dann mergen.
  Grundsätzlich: Dependabot-PRs nur bei grüner CI mergen. Ändert sich mit einem Update von
  pytest-homeassistant-custom-component die Python-Version, `PYTHON_VERSION` in tests.yml
  anpassen.

### 261017-hacs-default – Aufnahme in den HACS-Default-Store
- **Status:** offen (nach bestandenem echten Test und stabilem Release)
- **Priorität:** niedrig
- **Rolle(n):** Nutzer, Projektleiter
- **Beschreibung:** PR an `hacs/default` gemäß docs/recherche/261016-hacs-anforderungen.md
  (Checkliste 5.2). Dazu braucht es ein vollständiges Release, kein Pre-Release, und die
  Klärung der Markenrechte am Namen „FF Agent“ mit dem Hersteller.

### 261017-fundort-transport – Fundort der Rückmelde-URL korrigieren, Verkehrsmittel erweitern
- **Status:** geparkt. PR rauchstefan/ha-ff-agent#4 ist offen, die CI grün. tester und
  reviewer stehen noch aus. Der Nutzer will Implementierungen erst nach Ende seines Tests
  (2026-10-17), deshalb nicht mergen, bis er das Signal gibt.
- **Priorität:** hoch (Finding des Nutzers aus dem echten Test)
- **Rolle(n):** entwickler, tester, reviewer
- **Beschreibung:**
  - Fundort der Rückmelde-URL in Config Flow (de/en), README, Testanleitung und Plan
    korrigieren.
  - Verkehrsmittel `feet` und `bicycle` ergänzen (FF Agent: `FEET`, `BICYCLE`).
  - Annahmen A8 und A9 in ADR 0002 und architektur.md als geklärt eintragen.
- **Verweise:** docs/recherche/261016-ffagent-webhook-zusage.md, Abschnitt 3.7

### 261017-erreichbarkeit-recherche – Wege, HA für FF Agent erreichbar zu machen
- **Status:** erledigt (2026-10-17, docs/recherche/261017-erreichbarkeit.md; My-Link und ntfy-Integration vom Projektleiter geprüft)
- **Priorität:** hoch (Hürde für normale Nutzer)
- **Rolle(n):** researcher, danach architekt
- **Beschreibung:** Nabu Casa (Link zur Einrichtung), Alternativen wie Tunnel-Add-ons
  und kostenlose Webhook-Relays, sowie Wege ohne eingehende Verbindung, bewertet nach
  Aufwand für normale Nutzer, Kosten, Zuverlässigkeit, Latenz und Datenschutz.
- **Definition of Done:** docs/recherche/261017-erreichbarkeit.md mit Empfehlung.

### 261017-ux-erreichbarkeit – Hinweis „keine externe URL“ verständlich machen
- **Status:** offen (nach Ende des Tests; Inhalt abhängig von der Recherche)
- **Priorität:** hoch
- **Rolle(n):** architekt, entwickler, doku
- **Beschreibung:** Finding des Nutzers vom 2026-10-17: Der Abschlussdialog bei interner
  URL bzw. nur Pfad (`internal`/`path_only`) und der Options-Text sind zu technisch.
  - Ziel: Ein normaler Nutzer versteht, was zu tun ist.
  - Für Nabu Casa einen direkten Link zur Einrichtungsseite (z. B. My-Home-Assistant-Link,
    zu prüfen).
  - Alternativen laut Recherche 261017-erreichbarkeit-recherche kurz nennen.
  - README entsprechend.
- **Definition of Done:** neue Texte de/en, README, Tests.

### 261017-geraeteinfo-hersteller – Kein Herstellername in der Geräte-Info
- **Status:** offen (nach Ende des Tests des Nutzers)
- **Priorität:** hoch (Rechtliches, sichtbar in der HA-UI)
- **Rolle(n):** entwickler, tester, reviewer, doku
- **Beschreibung:** Vorgabe des Nutzers vom 2026-10-17: „Erwähne nicht mackoy consulting
  hier, ich besitze nicht die Rechte daran. Es ist eine inoffizielle Integration.“
  - Heute zeigt die Geräte-Info in HA unter dem Gerätenamen den Hersteller
    „mackoy consulting“: `const.py` `MANUFACTURER`, genutzt in `entity.py`
    (`DeviceInfo`); Test `tests/test_entities.py` Zeile 163.
  - Vorschlag:
    - `manufacturer` ganz weglassen oder einen neutralen Eintrag wählen, etwa
      „ha-ff-agent (inoffiziell)“; der Nutzer entscheidet.
    - `model` „FF Agent“ und `configuration_url` prüfen. Nur der Produktname als
      Beschreibung, kein Hinweis auf eine offizielle Herkunft.
  - Auch Plan (docs/plaene/261017-mvp-alarm-zusage.md, Schritt Gerät) und die Doku
    anpassen. Recherche-Fakten in docs/recherche/ bleiben unverändert.
  - Grundsatz für alle Texte, die Nutzer sehen (UI, README, Release-Notes): keine Namen
    des Herstellers bzw. Betreibers; Hinweis „inoffizielles Community-Projekt“.
- **Definition of Done:** Die Geräte-Info zeigt keinen Herstellernamen mehr, die Tests
  sind angepasst, und eine Regel im CLAUDE.md-Abschnitt „Fallstricke“ bzw. im Plan legt
  den Grundsatz fest.

### 261017-zusage-standort-transport – Standort aus HA und Verkehrsmittel beim Zusagen wählen
- **Status:** offen (Feature-Wunsch des Nutzers; erst nach Ende seines Tests planen)
- **Priorität:** mittel
- **Rolle(n):** architekt, entwickler, tester, reviewer
- **Beschreibung:** Wunsch des Nutzers vom 2026-10-17:
  1. Die Koordinaten der Zusage-URL sollen auf den **Home-Assistant-Standort** gesetzt
     werden können.
     - Heute gibt es nur die Option „Standort-Entität“ (`person`/`device_tracker`).
     - Neu wäre die Quelle `zone.home` bzw. der in HA konfigurierte Standort, als
       Auswahl „kein Standort / HA-Standort / Entität“.
  2. Das **Verkehrsmittel soll beim Zusagen wählbar** sein, nicht nur als Standard in den
     Optionen. Mögliche Umsetzungen:
     - eine Select-Entität „Verkehrsmittel“, die der Button „Zusagen“ verwendet
     - je ein Button pro Verkehrsmittel
     - Feld der Action (gibt es bereits)

     Der architekt bewertet die Varianten; der Nutzer entscheidet.

  Baut auf PR rauchstefan/ha-ff-agent#4 auf (drei Verkehrsmittel). Datenschutz beachten:
  Der HA-Standort ist die Wohnadresse und geht nur auf ausdrückliche Wahl an FF Agent.
- **Definition of Done:** Entscheidung des Nutzers, ADR-Ergänzung, umgesetzt und getestet.

### 261017-ha-zugriff – Lesezugriff auf die HA-Instanz des Nutzers (MCP/SSH)
- **Status:** zurückgestellt (Nutzer, 2026-10-17)
- **Priorität:** niedrig
- **Rolle(n):** Nutzer, Projektleiter
- **Beschreibung:** Der Nutzer hat HA (lokal im Heimnetz, SSH auf Port 22) und den
  HA-MCP-Server. Beides ist in Claude Code noch nicht angebunden. Bei Bedarf:
  - MCP: langlebiges Token in HA anlegen, mit
    `claude mcp add --transport http --scope user homeassistant http://<HA>:8123/api/mcp`
    plus Authorization-Header vom Nutzer selbst eintragen lassen (Token nie ins Repo oder
    in den OneDrive-Projektordner). Nur FF-Agent-Entitäten für Assist freigeben.
  - SSH: nur mit Schlüssel, der auf dem PC hinterlegt ist; Benutzername vom Nutzer.
  - Zugriff nur lesend (Dateien, Log, Diagnose); jede Änderung braucht die Freigabe im
    Einzelfall.
- **Definition of Done:** Zugriff eingerichtet und dokumentiert, oder bewusst verworfen.

### 261017-quality-todos – Offene Quality-Scale-Regeln
- **Status:** offen
- **Priorität:** niedrig
- **Rolle(n):** architekt, entwickler
- **Beschreibung:**
  - `entity-category`: „Letzte Rückmeldung“ als `diagnostic`?
  - `strict-typing`: mypy-Gate
  - `reauthentication-flow`: nach A7
  - Siehe docs/quality-scale.md.

### MVP Alarm + Zusage (Plan: docs/plaene/261017-mvp-alarm-zusage.md, ADR 0002) – fertig 2026-10-17

Gemeinsame Angaben für alle sechs Schritte:
- **Rolle(n):** entwickler → tester → reviewer, je ein PR auf `feat/<id>`
- **Reihenfolge:** strikt nacheinander
- **Definition of Done:** wie im Plan beim jeweiligen PR

### 261017-mvp-1-config-flow – Manifest, Rückmelde-URL-Parser, Webhook-URL, Config Flow
- **Status:** erledigt (2026-10-17, PR rauchstefan/ha-ff-agent-archiv#2, 0fb459a)
- **Priorität:** hoch

### 261017-mvp-2-webhook – Webhook-Empfang, Zusatz-Token, Diagnostics
- **Status:** erledigt (2026-10-17, PR rauchstefan/ha-ff-agent-archiv#3, bb533a8)
- **Priorität:** hoch
- **Beschreibung:** Danach ist der erste echte Test möglich (Annahmen A1–A5, A12), nur mit
  Nutzerfreigabe.

### 261017-mvp-3-alarm-entitaeten – Alarm-Logik, Binary-Sensor, Event, Sensor, Gerät
- **Status:** erledigt (2026-10-17, PR rauchstefan/ha-ff-agent-archiv#4, 22a7c4c)
- **Priorität:** hoch

### 261017-mvp-4-rueckmeldung – Rückmelde-Client, Buttons, Actions
- **Status:** erledigt (2026-10-17, PR rauchstefan/ha-ff-agent-archiv#5, bba8b34)
- **Priorität:** hoch
- **Beschreibung:** Den echten Test (A6–A9) nur während eines Testalarms und nur mit
  Nutzerfreigabe.

### 261017-mvp-5-options-reconfigure – Options Flow und Reconfigure
- **Status:** erledigt (2026-10-17, PR rauchstefan/ha-ff-agent-archiv#6)
- **Priorität:** mittel
- **Zusätzlich (aus PR 1/2):**
  - Texte `internal` und `path_only` vom Rat „Eintrag neu anlegen“ auf Reconfigure umstellen
  - Repair-Issue `webhook_token_rejected` im Setup löschen, wenn `require_token` aus ist
  - Options-Schema `reset_minutes` mit `vol.All(vol.Coerce(int), vol.Range(1, 1440))`
  - Entscheiden und dokumentieren, ob ein Reload den laufenden Alarm behalten soll (heute: nein)

### 261017-mvp-6-doku-qualitaet – README/Einrichtungsanleitung, Quality Scale, Abdeckung
- **Status:** erledigt (2026-10-17, PR rauchstefan/ha-ff-agent-archiv#7, fa6a52d)
- **Priorität:** mittel
- **Zusätzlich (aus PR 2):** In der Nutzerdoku warnen, dass HA Core die Webhook-ID in Debug-Logs von `homeassistant.components.webhook` und `.http` schreibt; solche Logs nicht teilen.
- **Zusätzlich (aus PR 3):** Beispiel-Automation nur mit `not_from`/`not_to: [unavailable, unknown]` (siehe docs/architektur.md, HA-Fallstricke). Hinweis, dass Options-Änderungen einen laufenden Alarm zurücksetzen.
- **Zusätzlich (aus PR 4/5):**
  - Companion-App-Beispiel (Benachrichtigung mit Knopf „Zusagen“) aus dem PR-4-Bericht übernehmen
  - Options- und Reconfigure-Ablauf als Textbausteine statt Screenshots
  - Hinweis: Debug-Logs von `websocket_api` können Geheimnisse aus Dialogen enthalten; nicht teilen
  - Hinweis: Eine Antwort 200 von FF Agent heißt nur „gesendet“, nicht sicher „verbucht“ (A7)

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

### 261017-reply-redirects – Redirect-Verhalten der Rückmelde-URL härten
- **Status:** offen (nach erstem echten Test, A6)
- **Priorität:** mittel
- **Rolle(n):** entwickler, reviewer
- **Beschreibung:** `reply.py` folgt Redirects heute zu jedem Host und auch zu http
  (`allow_redirects=True`). Nach dem echten Test entscheiden:
  - Leitet FF Agent nicht um, `allow_redirects=False` setzen; ein 3xx gilt dann als
    Fehler.
  - Leitet es um, Redirects selbst folgen (höchstens 3) und nur `https` auf
    `*.ff-agent.com` zulassen.
- **Definition of Done:** Verhalten entschieden, umgesetzt und getestet.

### 261017-reply-test-k5 – Test „Erfolg, Fehler, gleiche Aktion“ ergänzen
- **Status:** erledigt (2026-10-17, in PR rauchstefan/ha-ff-agent-archiv#6)
- **Priorität:** niedrig
- **Rolle(n):** tester
- **Beschreibung:** Zu testender Ablauf: Zusagen klappt, Absagen schlägt fehl, eine erneute
  Zusage innerhalb von 10 s wird übersprungen. Das Verhalten ist korrekt, aber nicht
  festgeschrieben. Kann mit PR 5 erledigt werden.

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
- **Status:** erledigt (2026-10-16, PR rauchstefan/ha-ff-agent-archiv#1, 1d9ac86)
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
