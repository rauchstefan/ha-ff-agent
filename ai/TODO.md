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

<!-- Themensammlung des Nutzers nach Test von v0.2.0 (2026-10-18). Abarbeitung erst nach
     seinem Go. Screenshots liegen nur im Chat, nicht im Repo. -->

### 261018-leere-dialogtexte – Hinweis auf Browser-Cache nach Update (leere Menütexte in v0.2.0)
- **Status:** offen (wartet auf Go des Nutzers); Ursache geklärt, kein Code-Fehler
- **Priorität:** niedrig
- **Rolle(n):** doku
- **Beschreibung:** Rückmeldung des Nutzers nach Installation von v0.2.0 über HACS
  (Nutzerpunkte 2–4): Die Menüs der Einrichtung und der Neukonfiguration zeigten nur
  den Titel „FF Agent“ und Pfeile ohne Texte. Die Neukonfiguration zeigte noch Texte aus
  v0.1.0 („Webhook-Zugang neu erzeugen“), die Auswahl-Optionen dagegen schon neue.
  - Ursache: **Browser-Cache.** Home Assistant war neu gestartet, ohne Wirkung. Erst ein
    harter Reload (Strg+F5) brachte die neuen Texte (Gegenprobe des Nutzers am
    2026-10-18, Menü „Nutzt du Home Assistant Cloud?“ vollständig).
  - Der Tag v0.2.0 enthält die richtigen Übersetzungen; am Code ist nichts zu ändern.
  - Offen bleibt nur ein Hinweis für Nutzer: Nach einem Update Home Assistant neu
    starten und den Browser hart neu laden (Strg+F5, in der App ggf. Cache leeren),
    falls Dialoge leer oder veraltet aussehen.
- **Definition of Done:** README (Abschnitt Installation/Update oder Fehlersuche) und
  CHANGELOG des nächsten Release nennen Neustart plus harten Browser-Reload nach einem
  Update. Kein Herstellername.
- **Verweise:** Nutzerpunkte 2–4 im Chat vom 2026-10-18

### 261018-reconfig-alarmquelle-text – Feld „Alarmquelle“ in der Neukonfiguration als Frage mit Hinweis
- **Status:** offen (wartet auf Go des Nutzers)
- **Priorität:** mittel
- **Rolle(n):** entwickler, tester, reviewer
- **Beschreibung:** Nutzerpunkt 1. In der Neukonfiguration steht über der Auswahl der
  Alarmquelle „alarm_source“; das lag am Browser-Cache (261018-leere-dialogtexte). Der
  aktuelle Text „Weg für den Alarm“ ist ebenfalls nur ein generisches Label. Gewünscht
  ist statt eines generischen Labels eine **Frage**, wie die Integration die Alarme
  erhält, etwa „Wie bekommt Home Assistant den Alarm?“. Bei der Option Home Assistant
  Cloud soll direkt stehen, was sie voraussetzt: ein Abo (Home Assistant Cloud) **oder**
  eine aus dem Internet erreichbare Adresse (IP/Domain) des eigenen Home Assistant.
  Die ntfy-Option bleibt als kostenlose Alternative erkennbar.
- **Definition of Done:** Label des Felds `alarm_source` im Schritt `reconfigure` ist
  eine Frage (de und en). Optionstext oder Feldbeschreibung nennt die Voraussetzung
  (Abo oder erreichbare Adresse). Kein Herstellername. Texte im Screenshot bzw. in
  der Gegenprobe des Nutzers bestätigt.
- **Verweise:** Nutzerpunkt 1 im Chat vom 2026-10-18; `translations/*.json` (`config.step.reconfigure`,
  `selector.alarm_source`)

### 261018-ntfy-abschluss-redundant – Abschlussdialog ntfy wiederholt die Webhook-Werte
- **Status:** offen (wartet auf Go des Nutzers)
- **Priorität:** niedrig
- **Rolle(n):** entwickler, tester, reviewer
- **Beschreibung:** Rückmeldung des Nutzers zur Einrichtung über ntfy. Der Dialog `ntfy`
  (Schritt 3) nennt alle Werte für den Webhook in FF Agent. Nach „Erledigt, Entität
  suchen“ zeigt der Abschlusstext (`config.create_entry.ntfy`) dieselbe Liste noch einmal
  zur Prüfung. Das wirkt redundant.
  - Vorschlag: Der Abschluss bestätigt nur kurz, dass die Einrichtung fertig ist, und
    empfiehlt einen Testalarm. Den Hinweis „Gut zu wissen“ (ntfy sieht Alarmzeitpunkte,
    keine Nachlieferung) behalten oder in den Schritt `ntfy` verschieben.
  - Die volle Liste nur zeigen, wenn sich die Adresse von der in Schritt 3 gezeigten
    unterscheidet. Das ist der Fall, wenn im Schritt `ntfy_select` eine andere Entität
    bzw. ein anderes Thema gewählt wurde. Die Variante `ntfy_topic_unknown` bleibt
    ausführlich, denn dort wurde keine Adresse gezeigt.
  - Gleiches für die Neukonfiguration prüfen (`abort.reconfigure_successful_ntfy`).
- **Definition of Done:** Nach dem Standardweg (Thema aus Schritt 3 gefunden) wiederholt
  der Abschluss die Webhook-Werte nicht. Bei abweichendem oder unbekanntem Thema erhält
  der Nutzer weiter alle nötigen Werte. de und en angepasst, Tests für beide Fälle.
- **Verweise:** Chat vom 2026-10-18 (Screenshot nicht im Repo, enthält ein geheimes
  Thema); `config_flow.py` (`async_step_ntfy_select`), `translations/*.json`

### 261018-geraet-ohne-link – Kein Link zu FF Agent in der Dienst-Info
- **Status:** offen (wartet auf Go des Nutzers)
- **Priorität:** niedrig
- **Rolle(n):** entwickler, tester, reviewer
- **Beschreibung:** Wunsch des Nutzers: Die Karte „Dienst-Informationen“ des Geräts zeigt
  den Button „Besuchen“ mit Link zur Produkt-Website. Der Link soll dort nicht stehen.
  Ursache: `configuration_url=CONFIGURATION_URL` in `entity.py` (`DeviceInfo`).
- **Definition of Done:** `DeviceInfo` ohne `configuration_url`. Die Konstante entfällt,
  wenn sie sonst nicht genutzt wird. Test `tests/test_entities.py` (prüft bisher die URL)
  angepasst, er verlangt jetzt `configuration_url is None`. CHANGELOG-Eintrag.
- **Verweise:** Chat vom 2026-10-18; `custom_components/ff_agent/entity.py`,
  `const.py`, `tests/test_entities.py`

### 261018-einrichtung-zusage-optionen – Verkehrsmittel und Standort schon bei der Einrichtung abfragen
- **Status:** offen (wartet auf Go des Nutzers; Rückfrage zur „Adresse“ offen)
- **Priorität:** mittel
- **Rolle(n):** architekt (kurzes Design), entwickler, tester, reviewer, doku
- **Beschreibung:** Wunsch des Nutzers: Bei der Einrichtung soll man das Verkehrsmittel
  und die Adresse für die Zusage festlegen können. Die Werte sollen in die vom Nutzer
  eingetragene, generische Zusage-URL von FF Agent einfließen. Damit der erste Dialog
  übersichtlich bleibt, kommt diese Abfrage als **eigener Schritt nach** der Eingabe
  der URL (vor der Wahl der Alarmquelle oder danach, im Design festlegen).
  - Stand im Code: Die Integration speichert die URL nicht, sondern nur Host und UUID,
    und hängt beim Zusagen `transport` sowie `lat`/`lng` als Query-Parameter an
    (`reply.py`). Verkehrsmittel (`default_transport`) und Standort-Entität
    (`location_entity`) gibt es bisher nur in den Optionen, nicht in der Einrichtung.
  - Kern der Aufgabe also: beide Felder als Schritt in die Einrichtung übernehmen,
    Vorbelegung wie in den Optionen, später in den Optionen änderbar.
  - **Rückfrage an den Nutzer:** Ist mit „Adresse“ die vorhandene Standort-Entität
    gemeint (z. B. `person.x` oder `device_tracker`), oder eine feste Adresse bzw.
    feste Koordinaten? Eine feste Adresse als Text unterstützt die Integration bisher
    nicht; ob FF Agent einen Adress-Parameter kennt, ist ungeklärt (ggf. researcher).
- **Definition of Done:** Nach der URL folgt ein Schritt mit Verkehrsmittel und Standort
  (optional). Die Werte landen in den Optionen des Eintrags und wirken auf Button und
  Aktion „Zusagen“. de und en, Config-Flow-Tests, README aktualisiert.
- **Verweise:** Chat vom 2026-10-18; `config_flow.py`, `reply.py`, `const.py`
  (`CONF_DEFAULT_TRANSPORT`, `CONF_LOCATION_ENTITY`)

### 261018-reihenfolge-zusage – „Zusagen“ vor „Absagen“ anzeigen
- **Status:** offen (wartet auf Go des Nutzers)
- **Priorität:** niedrig
- **Rolle(n):** researcher (kurz), entwickler, tester, reviewer
- **Beschreibung:** Wunsch des Nutzers: In der Integration (Geräteseite, Bereich
  Steuerelemente) steht „Absagen“ vor „Zusagen“. Gewünscht ist die umgekehrte
  Reihenfolge. Vermutung: Home Assistant sortiert Entitäten dort alphabetisch nach Namen,
  die Reihenfolge in `button.py` wirkt also nicht. Vorher klären, welche Stellschrauben
  es gibt (Namen, z. B. „Rückmeldung: Zusage“/„Rückmeldung: Absage“ ändern nichts an
  der Sortierung; ggf. andere Benennung oder keine Lösung ohne Umbenennung). Mögliche
  Folgen für Entity-IDs und Automationen der Nutzer beachten.
- **Definition of Done:** Auf der Geräteseite steht „Zusagen“ vor „Absagen“, ohne dass
  bestehende Entity-IDs brechen; oder dem Nutzer ist begründet, warum es nicht geht,
  mit Alternativvorschlag.
- **Verweise:** Chat vom 2026-10-18; `custom_components/ff_agent/button.py`,
  `translations/*.json` (`entity.button`)

### 261018-recherche-namen – Namen Dritter in öffentlichen Recherche-Dateien
- **Status:** offen (Entscheidung des Nutzers)
- **Priorität:** mittel
- **Rolle(n):** Nutzer, Projektleiter, doku
- **Beschreibung:** Hinweis des reviewers zu #7: `docs/recherche/261016-ffagent-schnittstellen.md`
  nennt im öffentlichen Repo:
  - den Firmennamen des Herstellers
  - Personennamen (Geschäftsführer, PDF-Autor)
  - die Geschäftsadresse

  Weitere Treffer: `docs/plaene/261017-alarmquelle-ntfy.md` (Prüfpunkt) und dieses TODO.
  Die Angaben stammen aus dem öffentlichen Impressum; ein Sicherheitsproblem ist das
  nicht, es geht um den Auftritt und um Datenschutz.

  Optionen:
  - neutralisieren, etwa „Hersteller von FF Agent“, ohne Personennamen und Adresse
  - so lassen

  Achtung: Neutralisieren wirkt nur ab jetzt, die Git-Historie behält die Angaben. Sie
  ganz zu entfernen hieße, die Historie erneut umzuschreiben.

### 261018-release-0-2-0 – Release v0.2.0 als Vorabversion
- **Status:** erledigt (2026-10-18, Pre-Release v0.2.0 auf dabe583: https://github.com/rauchstefan/ha-ff-agent/releases/tag/v0.2.0; Go des Nutzers im Chat)
- **Priorität:** hoch
- **Rolle(n):** entwickler, tester, reviewer, Projektleiter
- **Beschreibung:** Auftrag des Nutzers: „Bereite ein Release v0.2.0 als Vorabversion
  vor.“ Inhalt:
  - Versionssprung im Manifest auf 0.2.0
  - CHANGELOG `[0.2.0]`
  - README-Hinweise auf 0.2.0
  - neutraler Hersteller (261017-geraeteinfo-hersteller)

  Tag und GitHub-Release erst nach ausdrücklichem Go des Nutzers.
- **Definition of Done:** Release-PR gemergt (Gate bestanden), Go des Nutzers,
  Pre-Release v0.2.0 auf grünem Commit.

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
- **Status:** erledigt (2026-10-18, PR rauchstefan/ha-ff-agent#4, 5696f51; tester PASS,
  reviewer freigegeben)
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

### 261017-ux-erreichbarkeit – Alarmquelle wählbar (Webhook/Nabu Casa oder ntfy), verständlicher Hinweis
- **Status:** erledigt (2026-10-18, PR rauchstefan/ha-ff-agent#6, dddc3f9)
  - Geprüfter Stand f3fa723: CI grün, 642 Tests, Abdeckung 100 %, tester PASS,
    reviewer freigegeben inklusive Nachprüfung.
  - Auftrag des Nutzers: „bitte 1 und 2 umsetzen, und dem Nutzer die Wahl geben“.
    Gemeint sind (1) Nabu Casa mit Einrichtungslink und verständlichem Text, (2) ntfy.sh
    als kostenlose Alternative.
  - Der Nutzer hält den Alarmeingang nicht für kritisch.
  - Folgepunkte: 261018-ntfy-feinschliff.
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
- **Status:** erledigt (2026-10-18, PR rauchstefan/ha-ff-agent#7, dabe583; neutraler Eintrag „ha-ff-agent (inoffiziell)“, Test und Regel in CLAUDE.md)
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

### 261018-ntfy-feinschliff – Kleine Verbesserungen am ntfy-Weg (aus Review zu #6)
- **Status:** offen (nach Merge von PR rauchstefan/ha-ff-agent#6)
- **Priorität:** niedrig
- **Rolle(n):** entwickler, tester, reviewer
- **Beschreibung:**
  1. Der Watcher für neue ntfy-Abos meldet sich nach der ersten erfolgreichen Übernahme
     selbst ab. Sonst gibt es mehrere Reloads hintereinander, aber keine Schleife.
  2. Ein zweites Abo mit gleichem Thema nicht übernehmen, solange die gespeicherte
     Entität nur deaktiviert ist.
  3. Reconfigure im ntfy-Modus: Option „andere Entität wählen“ ohne neue geheime Adresse,
     oder zumindest den Options-Text präzisieren.
  4. Folge-TODOs aus ADR 0003:
     - Diagnose-Sensor „Alarmweg verbunden“
     - echter ntfy-Test der Annahmen N1–N3, N6, N7, N9, N10
     - nach dem 2. Dezember 2026 prüfen, ob `redirect/cloud/` nach der Umbenennung in
       „Home Assistant Link“ noch stimmt

### 261018-configflow-aufteilen – config_flow.py aufteilen
- **Status:** offen (nach Merge von PR rauchstefan/ha-ff-agent#6)
- **Priorität:** niedrig
- **Rolle(n):** entwickler, reviewer
- **Beschreibung:** Hinweis des reviewers zu #6: `config_flow.py` hat rund 820 Zeilen.
  - Vorschlag: `options_flow.py` (FFAgentOptionsFlow) abtrennen und ein ntfy-Mixin
    (`_ntfy_*`, `async_step_ntfy*`, `_async_finish_ntfy`) bilden.
  - Den gemeinsamen Reconfigure-Abschluss von `_async_finish_webhook` und
    `_async_finish_ntfy` in eine Hilfsfunktion legen.
  - Reines Refactoring, Tests bleiben unverändert grün.
- **Zusätzlich (optional):** CI-Matrix auch gegen die Mindestversion HA 2026.3.0
  (heute nur 2026.10.1).

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
