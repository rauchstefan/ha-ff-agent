# Recherche: HACS-Anforderungen für eine Home-Assistant-Custom-Integration

TODO-ID: `261016-hacs-anforderungen` · Stand/Abruf der Quellen: 2026-10-16 · Autor: Researcher

Kennzeichnung: **[G]** gesichert (Primärquelle gelesen), **[A]** abgeleitet (eigene Schlussfolgerung),
**[U]** unsicher/unbekannt.

## 1. Fragestellung

Was muss das Repo `rauchstefan/ha-ff-agent` (Domain `ff_agent`) erfüllen, damit es (a) als Custom
Repository in HACS installierbar ist und (b) in den HACS-Default-Store aufgenommen werden kann?
Zehn Teilfragen laut Auftrag (Struktur, hacs.json, manifest.json, Versionierung, Brands, GitHub-Repo,
CI, zwei Wege, Zusatzdateien, Stolperfallen).

## 2. Kurzfazit

- **Das Repo muss öffentlich sein.** HACS kann private GitHub-Repos „gar nicht" nutzen [G]; das gilt auch für Custom Repositories. Ein Token behebt das nicht (er dient nur den Rate-Limits). Solange das Repo privat ist, ist keine Installation per HACS testbar.
- Pflicht-Layout: genau ein Ordner `custom_components/ff_agent/` mit `manifest.json`; `hacs.json` im Root mit mindestens `name` [G].
- `manifest.json` braucht für HACS: `domain`, `name`, `version`, `codeowners`, `documentation`, `issue_tracker` [G]. Für HA zusätzlich `iot_class`, ggf. `config_flow`, `integration_type` [G].
- **Brands neu:** Seit HA 2026.3 liegen Icons im Integrationsordner (`custom_components/ff_agent/brand/icon.png`); `home-assistant/brands` ist für Custom-Integrationen „legacy" [G]. HACS verlangt mindestens `icon.png` dort [G].
- **Releases:** HACS nutzt den Tag-Namen des neuesten GitHub-**Releases** als Version; reine Tags reichen nicht [G]. Für den Default-Store ist mindestens ein echtes Release Pflicht [G].
- CI: `hacs/action` (category `integration`) und `home-assistant/actions/hassfest`; für den Default-Store müssen beide **ohne ignorierte Checks** grün sein [G].
- Default-Store: PR an `hacs/default`, Wartezeit laut HACS „Monate" [G]. Empfehlung: zuerst Custom-Repository-Weg, Default-Store später.
- Unsere `hacs.json` ist gültig, enthält aber `render_readme` (im Schema erlaubt, im Code wirkungslos) und `content_in_root: false` (Default, überflüssig) [G/A].

## 3. Befunde

### 3.1 Repo-Struktur (Frage 1)

- Genau **eine** Integration pro Repo; liegen mehrere Unterordner in `custom_components/`, verwaltet HACS nur den ersten. Alle zum Laufen nötigen Dateien liegen in `custom_components/<name>/`. Ausnahme: `content_in_root: true` erlaubt Root-Layout. [G] https://www.hacs.xyz/docs/publish/integration/
- `hacs.json` liegt im Repo-Root [G] https://www.hacs.xyz/docs/publish/start/
- Im Root darf zusätzlich liegen, was man will (README, LICENSE, `.github/`, `tests/`, `docs/`, `hacs.json`) [A]: HACS lädt nur den Integrationsordner (bzw. bei `zip_release` das Zip-Asset) [A, aus der Doku-Struktur abgeleitet].
- `content_in_root` und `zip_release`: siehe 3.2. Für uns ist beides nicht nötig [A].
- Die Vorlagen-Repos `blueprint` und `cookiecutter-homeassistant-custom-component` werden von HACS als Ausgangspunkt empfohlen [G] (Integrations-Seite).

### 3.2 hacs.json (Frage 2)

Zulässige Schlüssel laut Doku (https://www.hacs.xyz/docs/publish/start/) und HACS-Schema im Quellcode
(`custom_components/hacs/utils/validate.py`, `extra=PREVENT_EXTRA`, d. h. **unbekannte Schlüssel werden abgelehnt**) [G]:

| Schlüssel | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `name` | string | **ja** | Anzeigename in HACS |
| `content_in_root` | bool | nein | Inhalt liegt im Repo-Root statt in `custom_components/` (Default false) |
| `zip_release` | bool | nein | Inhalt kommt als Zip-Asset am GitHub-Release; nur Integrationen; verlangt `filename` |
| `filename` | string | nein | Dateiname für Einzeldatei-Typen bzw. das Zip bei `zip_release` |
| `hide_default_branch` | bool | nein | Default-Branch nicht zum Download anbieten (nur Releases) |
| `country` | string oder Liste | nein | ISO-3166-1-alpha-2-Code(s) |
| `homeassistant` | string | nein | Minimale HA-Version; Suffix `b0` erlaubt Betas |
| `hacs` | string | nein | Minimale HACS-Version |
| `persistent_directory` | string | nein | Relativer Pfad im Integrationsordner, bleibt beim Update erhalten (nur Integrationen) |
| `render_readme` | bool | nein | Im Schema vorhanden, **in der Doku nicht beschrieben**; im aktuellen `base.py` wird der Wert nicht zur Auswahl der Info-Datei gelesen, HACS rendert immer die README (`README.md`, Varianten) [G für Code-Stand, U ob künftig relevant] |

Quellen: https://www.hacs.xyz/docs/publish/start/ · https://raw.githubusercontent.com/hacs/integration/main/custom_components/hacs/utils/validate.py · https://raw.githubusercontent.com/hacs/integration/main/custom_components/hacs/repositories/base.py

Bewertung unserer Datei `{"name","content_in_root":false,"render_readme":true,"homeassistant":"2026.1.0"}`:
- Gültig (alle Schlüssel im Schema) [G].
- `render_readme`: wirkungslos und undokumentiert → **entfernen** [A].
- `content_in_root: false`: ist der Default → kann entfallen, schadet nicht [A].
- `homeassistant: "2026.1.0"`: sinnvoll, **muss zu den tatsächlich genutzten HA-APIs passen**. Wichtig: Brand-Bilder im Integrationsordner werden von HA erst ab **2026.3** angezeigt (3.5). Wer das Icon in HA sehen will, sollte `2026.3.0` verlangen [A].
- Empfohlen: `{"name": "FF Agent", "homeassistant": "2026.3.0"}` (Mindestversion final vom Architekten/Entwickler festlegen).

### 3.3 manifest.json (Frage 3)

Quelle HA: https://contributors.home-assistant.io/core/integrations/manifest/ (früher developers.home-assistant.io/docs/creating_integration_manifest/, per 301 weitergeleitet) [G]

- Reihenfolge: `domain`, `name`, dann alle weiteren Schlüssel **alphabetisch** (hassfest prüft das) [G].
- Von HACS geprüft (`INTEGRATION_MANIFEST_JSON_SCHEMA`, unbekannte Keys erlaubt): `domain`, `name`, `version`, `codeowners` (Liste), `documentation` (URL), `issue_tracker` (URL) – alle Pflicht [G] (Quellcode `validate.py`; Doku-Seite https://www.hacs.xyz/docs/publish/integration/ nennt dieselben sechs).
- Von HA verlangt: `domain` (Kleinbuchstaben/Ziffern/Unterstrich, = Ordnername), `name`, `codeowners`, `documentation` (für Custom: eigene HTTPS-Doku), `iot_class` (`local_polling`, `local_push`, `cloud_polling`, `cloud_push`, `assumed_state`, `calculated`) [G].
- `config_flow: true`, wenn `config_flow.py` existiert; `integration_type` (`hub`, `service`, `device` …) ist für Core-Integrationen mit Config-Flow Pflicht, fehlt es, gilt `hub`; trotzdem setzen [G].
- Optional: `requirements` (exakt gepinnt, `pkg==x.y.z`; nur Pakete, die HA nicht schon mitbringt), `dependencies`, `after_dependencies`, `loggers`, `single_config_entry`, `import_executor`, `quality_scale` [G].
- `version` (nur Custom, Pflicht): von AwesomeVersion parsebar, z. B. SemVer `1.2.0` oder CalVer `2026.10.1` [G].
- `issue_tracker` (nur Custom): URL für Fehlermeldungen [G].
- `quality_scale`: Core-Regel („neue Integrationen mindestens bronze"); Werte `custom` sind für interne Nutzung reserviert. Für Custom-Integrationen **nicht verpflichtend** [G für Werte, A für „nicht verpflichtend"; eine ausdrückliche Aussage für Custom wurde nicht gefunden, die Quality-Scale-Detailseiten lieferten 404] → [U].
- Welche Checks hassfest für Custom genau macht, ist nicht sauber dokumentiert (Blogartikel nennt nur das Ziel „gültige Daten"). Beobachtbar sind u. a.: Manifest-Schema/Sortierung, Translations-Format, `services.yaml`, Dependencies [U/A].

### 3.4 Versionierung & Releases (Frage 4)

- Mit Releases: HACS nutzt den **Tag-Namen des neuesten GitHub-Releases** als Version. „Just publishing tags is not enough." Ohne Tags: erste 7 Zeichen des letzten Commits. Bei Releases bietet HACS die 5 neuesten Releases plus Default-Branch an. [G] https://www.hacs.xyz/docs/publish/start/ , https://www.hacs.xyz/docs/publish/integration/
- Tag-Format muss AwesomeVersion-kompatibel sein (`v1.2.3` und `1.2.3` üblich) [G, Doku empfiehlt den AwesomeVersion-Demo-Validator].
- Zusammenspiel mit `manifest.json`: HACS nimmt die Versionsangabe für Anzeige/Updates aus dem Release-Tag; HA zeigt `manifest.version`. Beides muss synchron gehalten werden [A]. Empfehlung: Tag `vX.Y.Z` == `manifest.version` `X.Y.Z`, Release-Workflow soll das prüfen/setzen [A].
- Pre-Releases: GitHub-Releases mit Pre-Release-Flag werden von HACS nur Nutzern angeboten, die „Show beta versions" aktiviert haben; Standard-Download ist das neueste stabile Release (`base.py`) [G für Code-Stand]. Drafts werden ignoriert [G]. Die Doku-Seiten zu Pre-Release-Schaltern in HACS 2.x wurden nicht eindeutig gefunden (nur Sekundärquellen, Switch-Entity pro Repo) [U].
- Default-Store: mindestens ein Release **nach** erfolgreichem Lauf der Actions [G].
- `zip_release`: nur nötig, wenn gebaute Artefakte ausgeliefert werden; erfordert `filename` [G]. Für uns nicht nötig [A].

### 3.5 Brands/Icons (Frage 5)

- **Seit Home Assistant 2026.3** können Custom-Integrationen Bilder im Ordner `brand/` neben `manifest.json` ausliefern: `icon.png`, `dark_icon.png`, `logo.png`, `dark_logo.png` plus `@2x`-Varianten. Lokale Bilder haben Vorrang vor dem Brands-CDN. Ausgeliefert über die neue `brands`-Proxy-API. [G] https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/
- `home-assistant/brands`-Ordner `custom_integrations` ist „legacy"; Custom-Integrationen sollen eigene Bilder im `brand`-Ordner führen. Regeln: keine HA-Markenbilder verwenden, keine Symlinks. [G] https://github.com/home-assistant/brands
- HACS-Check `brands`: Datei `<content-path>/brand/icon.png` im Repo-Tree (bei `content_in_root`: `brand/icon.png`); fehlt sie, wird geprüft, ob die Domain in der `custom`-Liste von home-assistant/brands steht, sonst Fehler. [G] https://github.com/hacs/integration/blob/main/custom_components/hacs/validate/brands.py . Für uns also `custom_components/ff_agent/brand/icon.png` [A aus `content.path.remote`; Auflösung nicht im Code gezeigt → leichte Restunsicherheit U]. Die HACS-Doku sagt nur „brand directory in your repository" ohne Pfad [G].
- Bildanforderungen (Größe, Transparenz; üblich 256x256 icon, 512x512 `@2x`) sind im gelesenen Blogartikel nicht genannt [U]. Siehe Brands-README zur Prüfung vor dem Erstellen.
- Wichtig: Nutzung des Feuerwehr-/FF-Agent-Logos braucht Rechteklärung beim Hersteller [A, → offene Punkte].

### 3.6 GitHub-Repo-Anforderungen (Frage 6)

- **Öffentlich** (Pflicht): „Only public repositories on GitHub will work with HACS." [G] https://www.hacs.xyz/docs/publish/start/
- Private Repos: „can not be used with HACS at all"; HACS sieht nur öffentliche Informationen. Der GitHub-Token in HACS (OAuth ohne Scopes bzw. PAT ohne Scopes) dient nur dem Rate-Limit. [G] https://hacs.xyz/docs/faq/private_repositories/ (Fetch bestätigt) und Websuche. Drittanbieter-Workaround „Private HACS" (github.com/pestevez/private-hacs) existiert, ist nicht Teil von HACS, nicht geprüft [U].
- Beschreibung (Pflicht für Default-Store, Action-Check `description`), Topics (Check `topics`), Issues aktiviert (Check `issues`), nicht archiviert (Check `archived`) [G] https://www.hacs.xyz/docs/publish/action/ , https://www.hacs.xyz/docs/publish/include/
- README muss vorhanden sein (Check `information`) [G].
- Repo-Einstellungen (Sichtbarkeit, Topics usw.) ändern nur nach Bestätigung des Nutzers (CLAUDE.md-Regel) [Projektregel].

### 3.7 Validierung/CI (Frage 7)

**hacs/action** [G] https://www.hacs.xyz/docs/publish/action/
- Inputs: `category` (`integration`, `plugin`, `template`, `theme`, `appdaemon`, `python_script`), `ignore` (Leerzeichen-getrennt).
- Ignorierbare Checks: `archived`, `brands`, `description`, `hacsjson`, `images`, `information`, `issues`, `topics`.
- Prüft zusätzlich die Struktur/Manifest wie HACS selbst (hacs-validation, Manifest).
- Aktuelle Version: GitHub zeigt als neuestes Release `22.5.0` (Datum/Jahr nicht lesbar) [G/U]. Doku nutzt `hacs/action@main`; Pinning auf Tag/SHA plus Dependabot wird empfohlen [G].
- Läuft gegen das neueste Release, ohne Release gegen den Default-Branch [G].

**hassfest** [G] https://github.com/home-assistant/actions , https://contributors.home-assistant.io/blog/2020/04/16/hassfest/
- `uses: home-assistant/actions/hassfest@master`, mit `actions/checkout` davor; Trigger push, pull_request, nächtlicher Cron. Die Beschreibung: validiert „standalone integration repositories". Das HA-Repo weist die Hilfsactions als „internal … will change without warning" aus (nicht speziell hassfest) → Pinning-Empfehlung gibt es nicht [G].
- Der nächtliche Lauf zeigt Inkompatibilitäten mit neuen HA-Anforderungen früh [G].

Beispiel-Workflows siehe Abschnitt 4.4.

### 3.8 Zwei Wege (Frage 8)

**(a) Custom Repository** [G] https://www.hacs.xyz/docs/faq/custom_repositories/
- In HACS: Menü oben rechts → Custom repositories → URL, Typ „Integration" → Add. Best-Effort; das Repo braucht die bekannte Struktur.
- Mindestanforderung: öffentlich, `custom_components/<domain>/manifest.json` mit den 6 HACS-Pflichtfeldern, `hacs.json` mit `name`. Brand-Check, Releases, Topics usw. sind für den Custom-Weg nicht zwingend, werden aber von der Action geprüft [A].

**(b) Default-Store** [G] https://www.hacs.xyz/docs/publish/include/
- Nur Owner oder Hauptmitwirkender darf den PR stellen; nicht akzeptiert werden Test-Integrationen für Core-Betas oder Integrationen, die Core-Integrationen überschreiben.
- Voraussetzungen: als Custom Repository hinzufügbar, öffentlich, HACS-Action ohne Fehler **und ohne Ignores**, hassfest bestanden, **vollständiges GitHub-Release** nach den bestandenen Actions.
- Ablauf: `hacs/default` forken, Branch von `master`, Eintrag **alphabetisch** in der Datei `integration`, PR aus persönlichem Account (nicht Organisation), PR-Template vollständig und wahrheitsgemäß ausfüllen, Link zum erfolgreichen Action-Lauf angeben, PR von Draft auf „ready for review".
- Automatische Checks: Brands, Manifest, hacs-validation, HACS manifest (`name`), Archived, Releases (mind. 1), Owner, Repository (Beschreibung, Issues, Topics), lint jq (gültiges JSON), lint sorted.
- Wartezeit: kein fester Termin; „still take months" [G]. Nach Merge: nächster geplanter Scan.
- PR-Template-Checkliste [G] https://github.com/hacs/default/blob/master/.github/PULL_REQUEST_TEMPLATE.md : Doku gelesen; HACS-Action hinzugefügt; hassfest hinzugefügt; Actions ohne deaktivierte Checks; Link zum Action-Lauf; neues Release nach erfolgreichen Actions.

### 3.9 Weitere Dateien (Frage 9)

- `info.md`: in den aktuellen Docs und im aktuellen `base.py` nicht mehr vorgesehen; HACS rendert die `README.md` (Varianten `readme.md`, `README` …) [G für Code]. `info.md` gilt damit als veraltet [A]; nicht anlegen.
- README-Rendering: SVG-Tags werden ersetzt (`<svg` → `<disabled`) [G, `base.py`] → keine inline-SVGs, Bilder als Dateien/Links einbinden.
- `translations/en.json`: Für Custom-Integrationen **von Hand** pflegen (flaches Englisch, ohne `[%key:...%]`-Platzhalter); `strings.json` ist ein Core-Build-Feature, sonst werden rohe Schlüssel angezeigt. Weitere Sprachen `translations/de.json` usw. [G laut Zusammenfassung der Seite https://developers.home-assistant.io/docs/internationalization/custom_integration ; die Seite selbst wurde nicht direkt abgerufen, nur über Suchzusammenfassung → mittlere Sicherheit].
- `services.yaml`, `icons.json`: HA-Standardmechanismen; Details nicht neu recherchiert [U]; hassfest prüft sie [A].
- `requirements` im Manifest: exakt pinnen; HA installiert sie beim Laden [G]. Pakete, die HA ohnehin liefert, nicht auflisten [G].
- Quality Scale: für Custom nicht verpflichtend, aber als Qualitätsleitfaden (Tests, Config-Flow, Diagnostics) nützlich [A/U].

### 3.10 Typische Fehler/Stolperfallen (Frage 10)

1. Repo privat → HACS findet nichts (Hauptrisiko für uns).
2. Nur Tag, kein GitHub-Release → HACS zeigt Commit-Hash als Version [G].
3. Tag nicht AwesomeVersion-konform oder nicht synchron zu `manifest.version` [A].
4. `manifest.json` ohne `version`, `issue_tracker` oder `documentation` → HACS-Validierung schlägt fehl [G].
5. Falsche Schlüsselreihenfolge im Manifest → hassfest-Fehler [G].
6. `brand/icon.png` fehlt → HACS-Check `brands` schlägt fehl (außer Domain bei brands gelistet) [G].
7. Mehrere Ordner in `custom_components/` [G].
8. Unbekannter Schlüssel in `hacs.json` → Schema-Fehler (`PREVENT_EXTRA`) [G].
9. `strings.json` mit `[%key:…%]` statt handgeschriebener `translations/en.json` [G laut Suche].
10. Checks per `ignore` umgehen → Default-Store lehnt ab [G].
11. Release erstellt, bevor die Actions grün sind → PR-Voraussetzung nicht erfüllt [G].
12. Windows/OneDrive: Dateien mit BOM oder CRLF (JSON/YAML) – `.gitattributes` vorhanden, trotzdem prüfen [A, Projekt-Fallstrick].
13. `requirements` nicht gepinnt oder schwere Bibliotheken → Installationsfehler beim Laden [G].

## 4. Beispiele (Code englisch)

### 4.1 Verzeichnisbaum `ff_agent`

```text
ha-ff-agent/
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       ├── validate.yml        # HACS action + hassfest
│       └── release.yml         # optional, 4.5
├── custom_components/
│   └── ff_agent/
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── sensor.py / binary_sensor.py / ...
│       ├── services.yaml        # only if services exist
│       ├── icons.json           # optional
│       ├── brand/
│       │   ├── icon.png
│       │   ├── icon@2x.png      # optional
│       │   ├── dark_icon.png    # optional
│       │   └── logo.png         # optional
│       └── translations/
│           ├── en.json
│           └── de.json
├── tests/
├── docs/ ai/ .claude/           # project internals, ignored by HACS
├── hacs.json
├── README.md
└── LICENSE
```

### 4.2 hacs.json

```json
{
  "name": "FF Agent",
  "homeassistant": "2026.3.0"
}
```

### 4.3 manifest.json (Beispiel, Werte vom Architekten festzulegen)

```json
{
  "domain": "ff_agent",
  "name": "FF Agent",
  "codeowners": ["@rauchstefan"],
  "config_flow": true,
  "documentation": "https://github.com/rauchstefan/ha-ff-agent",
  "integration_type": "hub",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/rauchstefan/ha-ff-agent/issues",
  "loggers": ["custom_components.ff_agent"],
  "requirements": [],
  "version": "0.1.0"
}
```
Hinweis: `iot_class` hängt von der tatsächlichen FF-Agent-Schnittstelle ab (Polling/Push/Webhook) [U]. `loggers` bezieht sich laut Doku auf Logger-Namen der verwendeten Bibliothek; bei reinem Eigencode kann der Eintrag entfallen [A].

### 4.4 Workflows

`.github/workflows/validate.yml`:

```yaml
name: Validate

on:
  push:
  pull_request:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:

permissions: {}

jobs:
  hacs:
    name: HACS validation
    runs-on: ubuntu-latest
    steps:
      - uses: hacs/action@main   # pin to a release tag/SHA later, see .github/dependabot.yml
        with:
          category: integration

  hassfest:
    name: Hassfest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master
```

Hinweis: Die HACS-Action braucht kein Checkout (laut Doku-Beispiel). `permissions: {}` ist im Doku-Beispiel so; ob hassfest damit läuft, ist ungetestet [U]. Aktuelle Major-Version von `actions/checkout` vor Einsatz prüfen (Doku-Beispiele zeigen v3/v4).

### 4.5 Optionaler Release-Workflow (Skizze, nur nach Freigabe sinnvoll)

```yaml
name: Release
on:
  release:
    types: [published]
permissions:
  contents: write
jobs:
  check-version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Tag must equal manifest version
        run: |
          v=$(jq -r .version custom_components/ff_agent/manifest.json)
          test "v$v" = "${GITHUB_REF_NAME}" || test "$v" = "${GITHUB_REF_NAME}"
```

## 5. Checklisten

### 5.1 Custom Repository

- [ ] Repo öffentlich (Freigabe des Nutzers nötig)
- [ ] Beschreibung und Topics (z. B. `home-assistant`, `hacs`, `integration`, `feuerwehr`) gesetzt, Issues aktiv
- [ ] `custom_components/ff_agent/` mit `manifest.json` (6 HACS-Pflichtfelder + `iot_class`, `config_flow`, `integration_type`)
- [ ] `hacs.json` mit `name` (unbekannte Keys vermeiden)
- [ ] `brand/icon.png` im Integrationsordner (sonst Action-Fehler)
- [ ] `translations/en.json` handgeschrieben
- [ ] `validate.yml` grün (HACS + hassfest)
- [ ] GitHub-Release mit Tag = Manifest-Version (empfohlen; sonst Commit-Hash als Version)
- [ ] README mit Installation (My-Link `hacs_repository`), Konfiguration, Haftungs-/Datenschutzhinweis
- [ ] Test in einer HA-Testinstanz (Freigabe des Nutzers)

### 5.2 Default-Store (zusätzlich)

- [ ] Actions **ohne `ignore`** grün; Link zum Lauf bereit
- [ ] Release nach grünem Lauf erstellt (vollständiges Release, nicht nur Tag)
- [ ] Brand-Check erfüllt (`brand/icon.png`)
- [ ] Nicht archiviert, Beschreibung, Issues, Topics
- [ ] Owner stellt den PR aus persönlichem Account (`rauchstefan`)
- [ ] Fork `hacs/default`, Branch von `master`, Eintrag alphabetisch in Datei `integration`, JSON sortiert/valide
- [ ] PR-Template vollständig, wahrheitsgemäß, Ready for review
- [ ] Wartezeit einplanen (Monate)
- [ ] Hersteller-/Markenfragen zu FF Agent geklärt (Logo, Name)

## 6. Abgleich mit unserem Repo

Ist-Stand (geprüft 2026-10-16): vorhanden `hacs.json`, `README.md`, `LICENSE` (MIT), `.gitattributes`, `.gitignore`, Doku/`ai/`/`.claude/`. Fehlt: `custom_components/`, CI.

| Punkt | Ist | Soll / Aktion |
|---|---|---|
| Sichtbarkeit | privat | öffentlich (Nutzerfreigabe, siehe CLAUDE.md „Repo-Einstellungen") |
| `hacs.json` | enthält `render_readme`, `content_in_root:false` | auf `name` + `homeassistant` reduzieren; Mindestversion prüfen (2026.3.0 wegen Brands) |
| `custom_components/ff_agent/manifest.json` | fehlt | anlegen (4.3) |
| `brand/icon.png` | fehlt | Icon erstellen/Rechte klären |
| `translations/en.json` | fehlt | handschriftlich |
| `.github/workflows/validate.yml` | fehlt | anlegen (4.4); `dependabot.yml` für Action-Pins |
| Release | keines | nach grüner CI Release `v0.1.0` (Nutzerfreigabe nötig) |
| Beschreibung/Topics/Issues | unbekannt (nur per GitHub einsehbar) | prüfen/setzen |
| README | vorhanden (Inhalt nicht geprüft) | Installationsanleitung + My-Link ergänzen |
| `info.md` | nicht vorhanden | nicht anlegen |

## 7. Offene/unsichere Punkte

1. Genauer Umfang der hassfest-Prüfungen für Custom-Integrationen (kein Dokumentationstext gefunden).
2. Quality Scale für Custom: keine ausdrückliche Aussage gefunden (Detailseiten 404).
3. Auflösung von `content.path.remote` im HACS-Brands-Check (vermutlich `custom_components/ff_agent`).
4. Bildspezifikation (Pixelmaße) für `brand/*.png` nicht aus gelesener Quelle belegt.
5. Pre-Release-Verhalten in HACS 2.x: Code-Stand (`show_beta`) gelesen; Doku zu 2.x-Schaltern nur sekundär.
6. Translations-Regeln: nur über Suchzusammenfassung der HA-Seite belegt (Direktabruf scheiterte mit 404 wegen Umzug auf contributors.home-assistant.io).
7. Aktuelle empfohlene Versionen/Pins von `hacs/action` (neuestes Release 22.5.0, Datum unklar) und `actions/checkout`.
8. `iot_class` und `integration_type` hängen von der FF-Agent-Schnittstelle ab (Architektur offen).
9. Nur der Nutzer kann klären: Repo öffentlich machen; ob FF-Agent-Logo/Name verwendet werden darf (Hersteller); ob Default-Store gewünscht ist.
10. `render_readme`: möglicherweise in älteren HACS-Versionen relevant; ob Nutzer mit älterem HACS betroffen sind, unbekannt (entfernen ist trotzdem risikoarm, da Default `False` und README immer gerendert wird).

## 8. Empfehlung

1. Nutzerfreigabe zum Öffentlichmachen des Repos einholen (Voraussetzung für jeden HACS-Test).
2. Zuerst Weg (a) Custom Repository; Gerüst (Ordner, Manifest, `hacs.json`, Brand, `validate.yml`) in einem ersten Entwickler-Auftrag anlegen, CI grün bekommen.
3. `hacs.json` bereinigen (3.2); Mindest-HA-Version mit Architekt abstimmen.
4. Release-Konvention festlegen (Tag `vX.Y.Z` == manifest `X.Y.Z`), Releases nur nach Nutzerfreigabe.
5. Default-Store erst nach stabiler Version und Klärung der Markenrechte; ohne `ignore`-Einträge arbeiten, damit die Aufnahme jederzeit möglich bleibt.

## 9. Quellenverzeichnis (abgerufen 2026-10-16)

- HACS Integration publishing: https://www.hacs.xyz/docs/publish/integration/
- HACS General publishing / hacs.json: https://www.hacs.xyz/docs/publish/start/
- HACS Default inclusion: https://www.hacs.xyz/docs/publish/include/
- HACS Action: https://www.hacs.xyz/docs/publish/action/
- HACS Custom repositories: https://www.hacs.xyz/docs/faq/custom_repositories/
- HACS Private repositories: https://hacs.xyz/docs/faq/private_repositories/
- HACS Configuration options: https://hacs.xyz/docs/use/configuration/options/
- HACS Quellcode: https://github.com/hacs/integration/blob/main/custom_components/hacs/validate/brands.py , https://raw.githubusercontent.com/hacs/integration/main/custom_components/hacs/utils/validate.py , https://raw.githubusercontent.com/hacs/integration/main/custom_components/hacs/repositories/base.py
- hacs/action: https://github.com/hacs/action , https://github.com/hacs/action/releases
- hacs/default PR-Template: https://github.com/hacs/default/blob/master/.github/PULL_REQUEST_TEMPLATE.md
- HA Manifest: https://contributors.home-assistant.io/core/integrations/manifest/
- HA Brands Proxy API (2026-02-24): https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/
- home-assistant/brands: https://github.com/home-assistant/brands
- hassfest (Blog 2020): https://contributors.home-assistant.io/blog/2020/04/16/hassfest/
- home-assistant/actions: https://github.com/home-assistant/actions
- HA Translations Custom Integration (nur via Suche): https://developers.home-assistant.io/docs/internationalization/custom_integration
- Private HACS (Drittanbieter, ungeprüft): https://github.com/pestevez/private-hacs
- Pre-Release-Hinweise (sekundär): https://experimental.hacs.xyz/docs/faq/beta/
