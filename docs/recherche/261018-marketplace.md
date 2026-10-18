# Recherche: Home-Assistant-Marketplace (Nachfolger von HACS) und was ha-ff-agent tun muss

Stand/Abruf der Quellen: 2026-10-18 · Autor: Researcher
Kennzeichnung: **[G]** belegt (Primärquelle gelesen), **[A]** abgeleitet, **[U]** unklar/unbekannt.

## 1. Fragestellung

Was ist der neue Home-Assistant-„Marketplace" (ab HA 2026.11), woher bezieht er seine Liste, was passiert mit
Custom-Repository-Installationen, welche Anforderungen gelten für Aufnahme/Installierbarkeit, erfüllt
`rauchstefan/ha-ff-agent` sie, und wie läuft die Aufnahme ab?

## 2. Kurzfazit

- **Der Marketplace ist HACS, in HA Core integriert** (Integration `marketplace`, Settings > Marketplace) [G]. Für Repo-Betreiber ändert sich fast nichts: „Getting into the catalog works as before, through hacs/default" [G].
- **Liste:** unverändert `hacs/default` über `data-v2.hacs.xyz` [G]. Das „generated integration domain registry" (hacs/integration#5512) war ein **nicht gemergter, geschlossener Fremd-Draft** für HA-Analytics und hat mit dem Marketplace nichts zu tun [G].
- **Custom Repositories bleiben möglich** (per Link, GitHub-Verbindung per Device Flow nötig) und werden bei der Migration **automatisch übernommen** [G]. Unsere bestehenden Nutzer müssen nichts tun.
- **Anforderungen** = die HACS-Anforderungen, plus einige strengere Installationsprüfungen (Domain-Zeichen, `manifest.version`, `hacs.json` im Root, Mindest-HA-Version) [G]. **ha-ff-agent erfüllt alles Geprüfte**; es fehlt für den Custom-Weg nichts. Der brand-Pfad stimmt (`custom_components/ff_agent/brand/`).
- **Icon-Anzeige im Marketplace** vor der Installation kommt aus dem `brand/`-Ordner des neuesten Releases (Hourly-Sync, Netlify) [G] — ein Brands-PR ist nicht nötig.
- **Aufnahme in die Standardliste:** weiterhin PR gegen `hacs/default`, Wartezeit „Monate", aktuell **kein Freeze** (Stand 2026-10-18 laufend neue PRs) [G].
- 2026.11 ist noch nicht erschienen (neuester Release-Post: 2026.10 vom 7.10.) [G]; der Marketplace-Code ist aber seit 2026-10-01 in `dev` gemergt [G].

## 3. Befunde

### 3.1 Was ist der Marketplace? (Frage 1)

- hacs/integration#5590 „HACS is moving to Home Assistant as Marketplace" (angelegt 2026-10-16, gelockt): HACS wird ab 2026.11 als Marketplace-Integration mitgeliefert; Entwicklung läuft in HA selbst; Feature-Wünsche in die Marketplace-Discussions, Bugs als Issues in home-assistant/core; „Repository submissions still go to hacs/default". [G] https://github.com/hacs/integration/issues/5590 (API-Abruf)
- home-assistant/core PR #183502 „Add Marketplace integration" (frenck, gemergt 2026-10-01, Label `integration: marketplace`): „brings HACS into Home Assistant as the Marketplace"; System-Integration, standardmäßig eingerichtet, Panel unter Einstellungen; Erst-Warnhinweis zu Community-Inhalten, Browsen ohne Annahme möglich; Installieren/Aktualisieren ohne GitHub-Konto; je Download eine Update-Entität; Überschreiben einer Core-Integration nur mit ausdrücklicher Bestätigung; keine Signaturen/Prüfsummen. [G] https://github.com/home-assistant/core/pull/183502
- Nachfolge-PRs (gemergt Oktober 2026): Brands-View für nicht installierte Marketplace-Einträge (#185001), Restart-Repair (#184718), Translations-Invalidierung (#184230), Theme-Entfernen (#186926). Offenes Folgethema: Kategorien (Core-Issues #186836, #186839, #186844 geschlossen; #186847 „Export categories in the Marketplace data" offen). [G] via GitHub-Suche https://api.github.com/search/issues?q=repo:home-assistant/core+marketplace
- Offizielle Doku: https://www.hacs.xyz/docs/marketplace/ („HACS and the Marketplace") und https://contributors.home-assistant.io/marketplace/ (How it works, Guides, Reference). Ein developers.home-assistant.io-Blogpost und ein 2026.11-Release-Post (Beta/Final) wurden **nicht gefunden**; der Release-Notes-Index zeigt als neuesten Eintrag 2026.10 (7. Okt.) [G/U]. 2026.11 ist daher noch nicht erschienen [A].
- Nutzersicht: nur auf HA ≥ 2026.11; HACS selbst kann dort nicht mehr installiert werden (Loader blockiert es). Auf ≤ 2026.10 bleibt HACS maßgeblich. [G] hacs.xyz/docs/marketplace

### 3.2 Listenquelle (Frage 2)

- Katalog = Dateien je Typ im Repo `hacs/default`, ausgeliefert über `data-v2.hacs.xyz` („the same source HACS uses"); enthält Version, Beschreibung, Sterne, plus Listen „Removed" (funktionieren, keine Updates) und „Critical" (sofortige Deinstallation + Neustart). Laden beim Start, Refresh alle 6 h. [G] https://contributors.home-assistant.io/marketplace/how-it-works/ und PR #183502
- hacs/default README erwähnt weiterhin nur HACS-Veröffentlichung; kein Hinweis auf neuen Prozess. [G]
- hacs/integration#5512 „Add generated integration domain registry" (Fremd-Draft von thomasgregg, **nie gemergt**, am 2026-10-16 von ludeeus geschlossen): eine kompakte `domains.json` der HACS-Default-Domains, gedacht für HA Analytics-Filter. **Kein Marketplace-Register.** [G] https://github.com/hacs/integration/pull/5512
- Custom Repositories bleiben: per Link hinzufügen, benötigt GitHub-Verbindung (Device Flow im Panel); gleiche Anforderungen wie Katalogeinträge; Core-Repo und Repos mit Apps (AppDaemon) werden abgelehnt. [G] how-it-works, PR #183502
- Versionen: neuester GitHub-Release-Tag; Pre-Releases nur mit aktivierter Option und nur wenn neuer; ohne Release letzter Commit des Default-Branches. Katalogversionen werden ohne GitHub-API installiert, andere Versionen/Custom Repos über die GitHub-API. [G] how-it-works

### 3.3 Übernahme bestehender Installationen (Frage 3)

- Migration „in place" beim ersten Start nach dem Update: Storage, Entitäten, Geräte, Dashboard-Ressourcen und **Custom Repositories** werden übernommen (Namen, Bereiche, Labels bleiben); Update-Entitäts-IDs bleiben, Automationen/Dashboards laufen weiter; die HACS-Integration wird entfernt; `/hacs` und `/hacsfiles` bleiben nutzbar (bzw. Weiterleitung auf Marketplace). Dashboard-Ressourcen wandern nach `/local/community/`. AppDaemon/Python-Scripts werden nicht mehr verwaltet. [G] PR #183502 und https://www.hacs.xyz/docs/marketplace/
- **Für ff_agent-Nutzer:** Wer `ff_agent` als Custom Repository installiert hat, behält Installation und Updates; es ist keine Aktion nötig. [G, daraus abgeleitet für ff_agent: A]
- Unklar: Verhalten bei einem Custom Repository, das später in `hacs/default` aufgenommen wird (Dopplung?) — nicht dokumentiert [U]. Details zur Migration von Custom Repos ohne GitHub-Token (Device Flow erforderlich?) [U].

### 3.4 Anforderungen (Frage 4)

Belegt [G] (https://contributors.home-assistant.io/marketplace/guides/integrations/, .../reference/validation/, .../reference/hacs-json/, https://www.hacs.xyz/docs/publish/include/):

| Anforderung | Quelle/Detail | Stand ha-ff-agent |
|---|---|---|
| Öffentliches GitHub-Repo, nicht archiviert | include | erfüllt (public, nicht archiviert) |
| Beschreibung, Topics, Issues aktiv | include | erfüllt (Topics u. a. `hacs`, `hacs-integration`, `home-assistant`) |
| README | include | vorhanden |
| OSI-Lizenz, von GitHub erkannt (Katalog; `NOASSERTION`/nicht-kommerziell scheitern) | include (neu gegenüber meiner Recherche 261016) | erfüllt (MIT, SPDX erkannt) |
| Genau ein Ordner `custom_components/<domain>/` | integrations-Guide | erfüllt |
| `hacs.json` im Root mit `name` | reference | erfüllt |
| `hide_default_branch`, `homeassistant`: dokumentierte Keys | hacs-json-Reference | erfüllt; unbekannte Keys werden sonst ignoriert |
| `manifest.json`: `version` (Pflicht, sonst Installation verweigert; soll Release-Tag entsprechen), `issue_tracker`, `documentation`, `codeowners` | integrations-Guide | erfüllt (0.4.0, Felder vorhanden) |
| Domain nur `a-z`, `0-9`, `_`, `-`; nicht Core-Domain; nicht doppelt | validation | erfüllt (`ff_agent`) |
| Vollständiges GitHub-Release (nur Tag reicht nicht) | catalog-Guide | erfüllt (v0.4.0, Latest) |
| Brand: `custom_components/<domain>/brand/icon.png` (oder Domain im brands-Repo) | validation, integrations-Guide | erfüllt (`icon.png`, `icon@2x.png`) |
| HACS-Action ohne `ignore` + hassfest, grün | catalog-Guide | `validate.yml` vorhanden (hassfest, hacs/action, nächtlicher Cron); `ignore`-Freiheit [A] nicht geprüft, Grep auf `ignore` zeigte keinen Treffer |
| Mindest-HA-Version via `hacs.json` `homeassistant` | reference | gesetzt (2026.3.0). Marketplace läuft nur auf ≥ 2026.11, also unkritisch |

- **Brands-Pfad:** `https://brands.home-assistant.io/marketplace/<domain>/<image>` wird **automatisch** befüllt: stündlicher Netlify-Job liest die Marketplace-Liste und prüft per HEAD auf `raw.githubusercontent.com`, welche der 8 Bildvarianten (`icon`, `logo`, `dark_icon`, `dark_logo`, je mit `@2x`) unter `custom_components/<domain>/brand/` im **neuesten Release-Tag** (Fallback: letzter Commit) vorhanden sind; Neuprüfung bei neuem Ref oder nach 7 Tagen. HA-intern: `/api/brands/marketplace/<domain>/<image>` (erst Integrationsordner, dann brands-Repo, dann Marketplace-Pfad, dann Platzhalter). Kein PR an home-assistant/brands nötig. [G] home-assistant/brands#11283 (gemergt 2026-10-08), core PR #185001. Beachte: Das Bild muss **im Release-Tag** liegen, nicht nur auf `main`. [A aus „latest release tag"] Das gilt für v0.4.0 nur, wenn `brand/` schon in diesem Tag war [U, per `git ls-tree v0.4.0` prüfbar].
- Kategorien: Core führt gerade eine Kategorisierung ein; für Custom-Manifeste soll hassfest ein **optionales** `categories` akzeptieren (unbekannter Slug nur Warnung). Issue #186844 geschlossen (2026-10-17), Marketplace-Export (#186847) offen. Format/Slugs: Design-Doc nicht öffentlich einsehbar. [G für Issue-Inhalt, U für Format] https://github.com/home-assistant/core/issues/186844
- Die Seite „Get into the catalog" nennt zusätzlich: Reviewchecks (Brand, Manifest, HACS-Validation, `hacs.json`-name, nicht archiviert, ≥ 1 Release, Owner, Beschreibung/Issues/Topics, JSON lint/sortiert). [G]
- Stärker als die HACS-Action (nur Marketplace) [G]: Domain-Zeichenregeln, Core-Ersetzung nur mit Bestätigung, Mindest-HA-Version, Dateiplatzierung, Größenlimit 100 MiB / 50 000 Dateien, Rollback bei fehlgeschlagener Nachprüfung (z. B. `manifest.version` ungültig).

**Fehlt konkret?** Aus dem Belegten nichts Blockierendes. Zu prüfen (kein Wissensstand): (a) liegt `brand/` im Tag v0.4.0, (b) `hacs/action` ohne `ignore` und aktuell grün, (c) Release-Tag == `manifest.version` (v0.4.0 == 0.4.0 erfüllt), (d) optional `categories` im Manifest, sobald das Format feststeht.

### 3.5 Aufnahmeprozess (Frage 5)

- PR gegen `hacs/default` (Fork, Branch von `master`, Eintrag `rauchstefan/ha-ff-agent` alphabetisch in der Datei `integration`, PR aus persönlichem Konto, PR-Template vollständig, Link zum Lauf ohne ignores, Link zum Release, hassfest-Lauf; Draft → „Ready for review"). Nur Owner/Hauptmitwirkender; Unvollständiges wird ohne Rückmeldung geschlossen. [G] https://contributors.home-assistant.io/marketplace/guides/catalog/ , https://www.hacs.xyz/docs/publish/include/
- Wartezeit: „months" [G]. Backlog: Stand 2026-10-18 sind 12 051 PRs in hacs/default aufgelistet (Suche, Zählung inkl. offener Rename-/Add-PRs; genaue Zahl offener PRs [U]), neue Add-PRs kommen noch am selben Tag. **Kein Freeze/keine Annahmesperre dokumentiert oder erkennbar.** [G/A]
- Nach Merge: nächster geplanter Scan, dann im Katalog [G].
- Bis zur Aufnahme: Nutzer fügen das Repo per „My link" (Custom Repository) hinzu [G] catalog-Guide.

## 4. Offene Punkte / nur der Nutzer kann klären

1. Ob der Standardkatalog-Eintrag (Monate Wartezeit, öffentlicher PR unter `rauchstefan`) gewünscht ist. Für bestehende Nutzer bringt er kaum Vorteil, für Auffindbarkeit schon.
2. Markenfragen zu FF Agent (Name/Logo) — Projektregel „kein Herstellername in Nutzertexten" gilt weiter [Projektregel].
3. Nicht auffindbar / unklar: eigener 2026.11-Release-Post (noch nicht erschienen), Format von `categories`, Verhalten bei Custom-Repo → später Katalog, Pflicht der GitHub-Verbindung für Custom Repos auf Bestandsnutzer.
4. Die Seiten reference/repository-structure und guides/releases wurden nicht gelesen.

## 5. Empfehlung und Checkliste „was ha-ff-agent tun muss"

Intern (reine Repo-Arbeit, ohne Freigabe-Pflichtschritt):
- [ ] Prüfen, ob `brand/icon.png` (und `@2x`) im Tag v0.4.0 liegen (`git ls-tree -r v0.4.0 --name-only | grep brand`); falls nicht, bei nächstem Release enthalten. (Release selbst nur nach Nutzerfreigabe.)
- [ ] `validate.yml`: bestätigen, dass `hacs/action` **ohne `ignore`** und hassfest zuletzt grün sind; Lauf-URLs für den PR notieren.
- [ ] README: Installationshinweis ergänzen, dass ab HA 2026.11 der Marketplace (Einstellungen > Marketplace) statt HACS genutzt wird; für ≤ 2026.10 weiter HACS-Custom-Repository. Dort keinen Herstellernamen nennen.
- [ ] `manifest.version` == Release-Tag bei jedem Release beibehalten.
- [ ] Optional später: `categories` im Manifest, sobald Format dokumentiert.
- [ ] Nach 2026.11-Release: Migration auf einer Testinstanz beobachten (nur mit Nutzerfreigabe, siehe CLAUDE.md „Freigaben").

Öffentliche Beiträge unter dem Konto `rauchstefan` (nur mit Nutzerfreigabe, ausdrücklich bestätigen):
- [ ] Fork von `hacs/default` und **Pull Request** mit Eintrag `rauchstefan/ha-ff-agent` in `integration` (öffentlich sichtbar, Konto des Nutzers, Review „Monate").
- [ ] Gegebenenfalls Kommentare/Antworten im PR (öffentlich).
- [ ] Neues GitHub-Release/Tag, falls `brand/` im v0.4.0 fehlt (Release = Freigabepunkt laut CLAUDE.md).
- Kein PR an `home-assistant/brands` und keiner an `hacs/integration` nötig [G].

Empfehlung: Der Custom-Repository-Weg funktioniert auch im Marketplace weiter und ist die gesicherte Mindestlösung. Den `hacs/default`-PR erst stellen, wenn der Nutzer das bestätigt; vorher Checkliste oben abarbeiten, damit der PR beim ersten Versuch vollständig ist.

## 6. Quellen (abgerufen 2026-10-18)

- https://github.com/hacs/integration/issues/5590 (API: api.github.com/repos/hacs/integration/issues/5590)
- https://github.com/hacs/integration/pull/5512
- https://github.com/home-assistant/core/pull/183502 sowie #185001, #184230, #184718, #186926; Issues #186836, #186844, #186847
- https://github.com/home-assistant/brands/pull/11283 und #11237
- https://www.hacs.xyz/docs/marketplace/ , https://www.hacs.xyz/docs/publish/include/
- https://contributors.home-assistant.io/marketplace/ , /how-it-works/ , /guides/catalog/ , /guides/integrations/ , /reference/validation/ , /reference/hacs-json/
- https://github.com/hacs/default (README, PR-Liste via GitHub-Suche)
- https://www.home-assistant.io/blog/categories/release-notes/
- GitHub-API-Abruf des eigenen Repos (Beschreibung, Topics, Lizenz)
