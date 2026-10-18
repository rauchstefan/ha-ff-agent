# Recherche: HACS-Update-Dialog (Commit-Hashes, fehlendes Bild)

Stand: 2026-10-18. Alle URLs am 2026-10-18 abgerufen.

> **Nachtrag 2026-10-18:** v0.4.0 ist seit 2026-10-18 ein reguläres Release. Die Nutzer-Schritte mit dem Beta-Schalter (Abschnitt 2) und Abschnitt 3.2 sind damit überholt. Die deutsche HACS-Bezeichnung lautet „Erneut herunterladen“ (EN „Redownload“), der Beta-Schalter „Beta-Versionen anzeigen“.

## 1. Fragestellung

1. Warum zeigt HACS für `ff_agent` Commit-Hashes (7192103 / 36c857e) statt 0.4.0? Rolle von
   „Beta-Versionen anzeigen“ / `show_beta` / Pre-Release-Switch. Was muss der Nutzer tun, was kann das Repo tun?
2. Woher kommt das Bild der HACS-Update-Entität („icon not available“)? Reicht der lokale `brand/`-Ordner?

## 2. Kurzfazit

- Problem 1: HACS kennt als „stabile“ Version nur Nicht-Pre-Release-Releases. Ohne `show_beta` und ohne
  reguläres Release fällt HACS auf den Default-Branch zurück und zeigt den 7-stelligen Commit-Hash. Das ist
  erwartetes Verhalten, kein Fehler. Die Installation von `7192103` kam von `main`, nicht von einem Tag.
- Nutzer: Beta-Anzeige für das Repo aktivieren, dann „Neu herunterladen“ und gezielt Version 0.4.0 wählen
  (nicht den Default-Branch), danach HA neu starten.
- Repo: Dauerhafte Lösung ist ein reguläres (kein Pre-Release) GitHub-Release, sobald vertretbar. Zusätzlich
  `hide_default_branch: true`. `zip_release` ist nicht nötig.
- Problem 2: Die HACS-Update-Entität baut die Bild-URL fest als
  `https://brands.home-assistant.io/_/ff_agent/icon.png`. Der lokale `brand/`-Ordner wird dafür **nicht**
  verwendet (HACS-Code, abgeleitet; HA-Frontend-Verhalten dazu nicht belegt). Er wirkt für HA-Seiten, die
  den Brands-Proxy `/api/brands/integration/...` nutzen.
- Dateinamen und Größen in `brand/` (`icon.png` 256 px, `icon@2x.png` 512 px) passen zur Vorgabe.
- Ein PR an `home-assistant/brands` für Custom Integrations ist laut dessen README Legacy; ob er noch
  angenommen wird, ist nicht belegt. Den Ordner `custom_integrations/` also nicht mehr als Standardweg ansehen.

## 3. Befunde

### 3.1 Versionsanzeige (Commit-Hash)

Quelle: `https://raw.githubusercontent.com/hacs/integration/main/custom_components/hacs/repositories/base.py`
(Zusammenfassung des Codes, keine Zeilennummern erhoben).

Belegt:
- `common_update_data` holt bis zu 30 Releases inkl. Pre-Releases (`get_releases(prerelease=True, returnlimit=30)`).
  Das neueste Pre-Release-Tag landet in `data.prerelease`, das neueste **stabile** Tag in `data.last_version`.
- `display_available_version`: Ist `show_beta` gesetzt und `data.prerelease` vorhanden, wird das Pre-Release-Tag
  angezeigt. Sonst, wenn `last_version` gesetzt ist, dieses. Sonst `last_commit` (7 Zeichen).
- `display_installed_version`: `installed_version`, sonst `installed_commit`.
- `version_to_download`: `selected_tag`, sonst `last_version`, sonst `default_branch` bzw. `"main"`.
- Installation einer Default-Branch-Ref löscht `installed_version` und setzt `installed_commit = last_commit`.
- `pending_update` vergleicht bei Default-Branch-Installation die Commits.
- HACS-Doku `https://hacs.xyz/docs/publish/start/`: Nutzt das Repo GitHub-Releases, ist das neueste Release-Tag
  die Version; nur Tags reichen nicht. Ohne Releases dienen die ersten 7 Zeichen des letzten Commits. Zu
  Pre-Releases sagt diese Seite nichts.
- HACS-Doku `https://hacs.xyz/docs/use/entities/switch/`: Der Pre-Release-Switch bestimmt, ob die Update-Entität
  Pre-Releases berücksichtigt.

Abgeleitet (Ursache): `ff_agent` hat nur Pre-Releases, also `last_version = None`. Ohne `show_beta` zeigt
HACS `last_commit` (36c857e, aktueller `main`-Stand). Installiert wurde ursprünglich der Default-Branch
(`installed_commit` 7192103). Beide Anzeigen sind damit konsistent erklärt. Auch mit aktiviertem `show_beta`
bleibt die installierte Anzeige ein Commit-Hash, bis einmal ein Tag installiert wurde.

Nicht geprüft: die genaue Beschriftung der UI-Menüpunkte in der HACS-Version des Nutzers.

### 3.2 Schritte für den Nutzer (abgeleitet aus Code und README des Projekts)

1. HACS, Integrationen, „FF Agent“ öffnen. Beta-/Vorabversionen für dieses Repo aktivieren (Menü ⋮ des Repos,
   bzw. die Entität „FF Agent Pre-release“ unter dem HACS-Gerät, falls vorhanden). Das ist bei HACS pro Repo.
2. Im selben Menü „Neu herunterladen“ (Redownload) wählen. Im Versionsdialog **0.4.0** auswählen, nicht den
   Eintrag des Default-Branches/Commits.
3. Home Assistant neu starten (HACS meldet „Restart required“).
4. Danach sollten installiert und neueste Version 0.4.0 zeigen. Erscheint weiter ein Hash, wurde der
   Default-Branch gewählt: Schritt 2 wiederholen.

### 3.3 Optionen im Repo

| Option | Wirkung | Bewertung |
|---|---|---|
| Reguläres Release (Pre-Release-Haken entfernen) | `last_version` wird gesetzt; HACS zeigt Tag ohne Beta-Schalter | Beste Lösung, löst Problem für alle Nutzer. Release braucht laut Projektregeln Freigabe des Nutzers. Fachlich: „Vorabversion“ ist dann nicht mehr als solche markiert. |
| `hide_default_branch: true` in hacs.json | HACS soll den Default-Branch nicht anbieten (Doku: hacs.xyz/docs/publish/start/); laut Review in HACS 2.x im Code nicht ausgewertet | Empfohlen als Ergänzung. Verhindert versehentliche Hash-Installation. Wirkt sinnvoll erst mit mindestens einem Release; bei nur Pre-Releases ohne Beta-Schalter gäbe es sonst nichts zu installieren (abgeleitet, nicht getestet). |
| `zip_release` (+ `filename`) | Für Releases mit ZIP-Asset | Nicht nötig; Code liegt unter `custom_components/ff_agent/` im Repo. Zusätzlicher Pflegeaufwand. |
| Status quo (nur Pre-Release) | Nutzer müssen Beta-Schalter setzen | README erklärt das bereits; kein Dauerzustand. |

### 3.4 Bild der Update-Entität

Quelle: `https://raw.githubusercontent.com/hacs/integration/main/custom_components/hacs/update.py`.

Belegt: `entity_picture` liefert für Integrationen mit Domain
`https://brands.home-assistant.io/_/{domain}/icon.png`, sonst `None`. Es ist eine feste Absolut-URL zum
Brands-CDN, ohne Token und ohne lokalen Proxy.

Belegt (HA-Blog `https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/`, früher
developers.home-assistant.io): Seit HA 2026.3 liegen Custom-Integration-Bilder im Ordner `brand/` neben
`manifest.json` (`icon.png`, `logo.png`, `dark_`-Varianten, `@2x`). Lokale Bilder haben Vorrang vor dem CDN.
Ausgeliefert werden sie über den authentifizierten Proxy `/api/brands/integration/{domain}/{image}`, den das
Frontend (`brandsUrl()`) nutzt. Pixelgrößen nennt der Blog nicht.

Abgeleitet: Die HACS-Entität umgeht den Proxy und fragt `brands.home-assistant.io/_/ff_agent/icon.png` ab.
Gibt es dort kein Bild, bleibt der Platzhalter. Der lokale Ordner hilft daher für Integrationsseite/Geräte,
nicht für diese HACS-Entität. Nicht belegt: ob HA-Frontend die Entity-Picture-URL gezielt umschreibt; das
Ergebnis beim Nutzer (Platzhalter) spricht dagegen. Auch nicht belegt, ob HACS dies in einer neueren Version
ändert (geprüft wurde der `main`-Stand).

home-assistant/brands (`https://github.com/home-assistant/brands`): README nennt den Ordner
`custom_integrations` „Legacy“, mit Verweis auf `brand/` in der Integration seit HA 2026.3.0. Eine
ausdrückliche Annahmesperre steht dort nicht; ob PRs noch gemergt werden, ist **unbekannt**.

Vorgaben des Brands-Repos: PNG, optimiert, transparent bevorzugt; `icon.png` quadratisch 256x256,
`icon@2x.png` 512x512; Logo kürzeste Seite 128-256 px (`@2x` 256-512); Ordnername = Domain; keine HA-Marken.

Prüfung unseres Ordners `custom_components/ff_agent/brand/`: enthält `icon.png` (Ansicht 256x256, quadratisch,
rotes Haus-Symbol mit „FF“) und `icon@2x.png` (512x512). Namen und Größen entsprechen der Vorgabe. Es fehlt
`logo.png`/`logo@2x.png` (optional; ohne Logo wird laut Blog/CDN-Fallback nichts Eigenes gezeigt, Verhalten
nicht geprüft). Transparenz (abgerundete Ecken) und PNG-Optimierung nicht geprüft. Pixelmaße wurden visuell
aus der Bildansicht entnommen, nicht per Tool gemessen.

## 4. Offene Punkte

- Nutzer: Entscheidung, ob 0.4.0 als reguläres Release markiert werden darf (Freigabepflicht).
- Nutzer: Bestätigen, welche Menüpunkte HACS bei ihm bietet; Ergebnis nach Neuinstallation melden.
- Unbekannt: Nimmt `home-assistant/brands` aktuell noch Custom-Integration-PRs an? (Issues/PRs im Repo prüfen,
  Pull-Request-Template lesen.)
- Unbekannt: Plant HACS, die Entity-Picture über den lokalen Proxy zu laden? (HACS-Issues durchsuchen.)

## 5. Empfehlung

Problem 1: Nutzer führt die Schritte aus 3.2 aus. Repo veröffentlicht, sobald vertretbar, ein reguläres Release
(Freigabe nötig) und setzt danach `hide_default_branch: true`. `zip_release` nicht verwenden. README-Hinweis
beibehalten, bis ein reguläres Release existiert.

Problem 2: Lokaler `brand/`-Ordner beibehalten (korrekt). Für das HACS-Entity-Bild einen PR an
`home-assistant/brands` unter `custom_integrations/ff_agent/` (`icon.png` 256, `icon@2x.png` 512) stellen,
nachdem im Repo (README/Template/Issues) geprüft wurde, dass er noch angenommen wird. Alternativ als rein
kosmetisch akzeptieren und im Backlog vermerken. Kein funktionaler Schaden.

## Nachtrag 2026-10-18: Brands-PR und Marketplace

- Ein PR an `home-assistant/brands` ist nicht möglich. Die PR-Vorlage des Repos sagt,
  dass neue Custom-Integrationen nicht mehr angenommen werden. Verwiesen wird auf die
  Ankündigung zur Brands-Proxy-API
  (https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api).
- HACS zieht als Integration „Marketplace“ in Home Assistant (hacs/integration#5590).
- Die HACS-Betreuer haben das Problem „icon not available“ trotz lokalem `brand/`-Ordner
  geschlossen, mit dem Hinweis, es sei im Marketplace ab HA 2026.11 behoben. Fundstellen:
  hacs/integration#5402, hacs/integration#5179 und der geschlossene PR
  hacs/integration#5524 („Use the brands proxy for update entity pictures“).
- Für die Anzeige vor der Installation nennt das README des brands-Repos den Pfad
  `https://brands.home-assistant.io/marketplace/[domain]/icon.png`. Er wird aus dem
  `brand/`-Ordner der Custom-Integration bedient.
- Folge: Am Repo ist nichts zu tun. Nach HA 2026.11 prüfen.
