# Recherche: Wie wird Home Assistant für den FF-Agent-Webhook erreichbar? Gibt es kostenlose Relays?

TODO-ID: `261017-erreichbarkeit-recherche` · Abruf der Quellen: 2026-10-17 · Autor: Researcher

Kennzeichnung wie in den bestehenden Recherchen: **[G]** gesichert (Quelle gelesen),
**[A]** abgeleitet (eigene Schlussfolgerung), **[U]** unbekannt oder nicht belegt.

Randbedingungen eingehalten: keine Konten, keine Formulare, nichts installiert oder
ausgeführt. Gelesen wurden nur öffentliche Webseiten und öffentlicher Quellcode. Das Abruf-Tool
fasst Seiten zusammen; wo eine Seite abgeschnitten war oder nicht erreichbar (403/404), steht
das dabei. Es kommen keine echten Webhook-IDs oder Adressen vor.

## 1. Fragestellung

Normale Einsatzkräfte betreiben Home Assistant (HA) oft als HA OS auf einem Raspberry Pi,
ohne Netzwerkwissen. FF Agent (Cloud) muss bei einem Alarm einen Webhook von HA aufrufen
(GET oder POST, Timeout 5 s, optional eigene Header). Ohne Nabu Casa und ohne externe URL
zeigt der Config Flow nur eine interne Adresse, die FF Agent nicht erreicht.

1. Nabu Casa: Preis, Test, Cloudhooks ohne Remote-UI, My-Link, Laien-Anleitung.
2. Alternativen mit eingehender Verbindung (Cloudflare, Tailscale, ngrok, DuckDNS, MyFRITZ,
   DS-Lite/CGNAT).
3. Kostenlose Relays, bei denen HA abholt statt angerufen zu werden.
4. Folgerungen für Config Flow, README, ADR 0002 und Datenschutz; Textvorschlag.

## 2. Kurzfazit

- **Standardweg: Nabu Casa.** 7,50 EUR/Monat oder 75 EUR/Jahr (netto), **31 Tage kostenlos ohne
  Karte** [G]. Die Integration erzeugt den Cloudhook selbst, der Nutzer muss nichts an Router,
  Domain oder Zertifikaten tun. Cloudhook-Erzeugung hängt im HA-Code nicht an „Remote-Steuerung“ [G].
- **Den My-Link gibt es:** `https://my.home-assistant.io/redirect/cloud/` („Home Assistant Cloud“,
  seit Core 2021.3) [G]. Er öffnet die Cloud-Seite der **eigenen** Instanz. Achtung: Der Dienst
  wird laut Nabu Casa am **2. Dezember (2026)** in **„Home Assistant Link“** umbenannt [G]; der Dialog sollte
  beide Namen nennen.
- **Bester kostenloser Weg für Laien: ntfy als Relay** (FF Agent ruft per GET/POST ein geheimes
  ntfy-Thema auf, HA hört über die **Core-Integration `ntfy`**, seit 2025.5, per Event-Entität zu,
  ausgehende Verbindung genügt) [G]. Aber: nur Zeitpunkte, Thema ist nur ein „Passwort“, ntfy.sh nennt
  weder Serverstandort noch DSGVO, Alarme während einer Trennung gehen verloren, und alle
  FF-Agent-Aufrufe teilen sich vermutlich eine Absender-IP und damit das Ratenlimit [A].
- Eigene Tunnel (Cloudflare, Tailscale Funnel, ngrok) sind kostenlos oder günstig, aber für
  Laien zu aufwendig. DuckDNS plus Portfreigabe scheitert bei DS-Lite/CGNAT und öffnet HA zum
  Internet; **nicht empfohlen** für die Zielgruppe.
- Webhook Relay, Hookdeck, smee.io, IFTTT, Pushover, Telegram: **nicht geeignet** (Abschnitt 3.3).
- Das Zusatz-Token (Header) kommt über ntfy **nicht** an [A]. Über Nabu Casa bleibt es offen (A12).
- **Empfehlung für die Integration:** README und Dialog nennen Nabu Casa zuerst, ntfy als
  Ausweichweg. Eine eingebaute Relay-Unterstützung lohnt nur in der schlanken Form
  „vorhandene ntfy-Event-Entität als Alarmquelle wählen“ (Abschnitt 5), nicht als eigener
  ntfy-Client.

## 3. Befunde

### 3.1 Nabu Casa / Home Assistant Cloud

- **Preis und Test:** 7,50 EUR/Monat, 75 EUR/Jahr („ein Jahr zum Preis von 10 Monaten“), jeweils
  zuzüglich Steuer; **31 Tage kostenlos, keine Kartendaten nötig** [G]
  https://www.nabucasa.com/pricing/ , https://www.nabucasa.com/link/ (beide 2026-10-17).
- **Umbenennung:** Die Seite sagt „On December 2nd, Home Assistant Cloud becomes Home Assistant
  Link“ (Jahr dort nicht genannt, die HA-Seite nennt den 2. Dezember 2026) [G]
  https://www.nabucasa.com/link/ , https://www.home-assistant.io/cloud/ . Funktionen laut Seite:
  Fernzugriff, Offsite-Backups, Sprachsteuerung, Sprachverarbeitung; Webhooks sind dort **nicht**
  aufgeführt [G]. Die HA-Doku nennt Nabu Casa als einfachsten und sichersten Weg: keine
  Router-Änderung, ein Schalter [G] https://www.home-assistant.io/docs/configuration/remote/ .
- **Cloudhooks:** Die Webhook-Doku nennt „Nabu Casa Cloud webhooks“ als zweiten erlaubten Zugang
  neben dem lokalen Netz [G] https://www.home-assistant.io/docs/automation/trigger/ . Das Nabu-Casa-Support-
  Dokument (https://support.nabucasa.com/hc/en-us/articles/25619382358685) liefert beim Abruf 403; über
  eine Suche belegt: Der Nutzer schaltet am Webhook-Trigger „nur aus dem lokalen Netz erreichbar“
  aus, öffnet unter Einstellungen > Cloud die Webhook-Karte und bekommt dort eine eindeutige URL
  (`hooks.nabu.casa`, genaue Schreibung dort [U]) [G, Suchzusammenfassung]. **Für unsere Integration entfällt das:**
  Sie erzeugt den Cloudhook über `cloud.async_get_or_create_cloudhook` (ADR 0002).
- **Remote-UI nötig?** Im HA-Core-Code (`cloud/http_api.py`) prüft die Cloudhook-Erzeugung nur
  Admin-Recht und Cloud-Anmeldung, **nicht** „Remote“ [G]
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/cloud/http_api.py .
  Die Bibliothek `hass_nabucasa`, die den eigentlichen Aufruf macht, wurde nicht gelesen. Ob
  der Nabu-Casa-Server Cloudhooks bei abgeschalteter Remote-Steuerung ausliefert, ist daher
  **[U]**; ein Forenbeitrag deutet an, dass Alexa/Google-Anbindung auch bei abgeschalteter
  Fernsteuerung lief [G, nur Indiz, anderer Dienst]. Beim ersten echten Test mit
  Cloudhook ausdrücklich prüfen.
- **Nachteile:** kostenpflichtig nach dem Test; die Einsatzkraft braucht Admin-Rechte in HA
  (Anmeldung am Cloud-Konto) [A]. Ein Forenbeitrag berichtet von verschwundenen Cloud-Webhooks
  ohne Support-Antwort [G, Einzelfall] https://community.home-assistant.io/t/webhooks-api-or-nabu-casa/88776 (nur über die Suche gesehen).
- **Datenschutz:** Der Alarm läuft über Server von Nabu Casa (Aufrufzeitpunkt, Quell-IP). Nabu
  Casa ist der Betreiber von HA und bietet den Dienst vertraglich an; Hosting-Ort und
  Auftragsverarbeitung nicht geprüft **[U]**.

**My-Home-Assistant-Link:** `https://my.home-assistant.io/redirect/cloud/` existiert, Titel
„Home Assistant Cloud“, Zweck „Show your Home Assistant Cloud configuration in Home Assistant“, ohne
Parameter, eingeführt in Core 2021.3 [G] https://my.home-assistant.io/redirect/cloud/ und
https://my.home-assistant.io/faq/ . Der Nutzer wird gefragt, welche HA-Adresse er hat, und landet
auf der Cloud-Seite seiner Instanz. Es ist die **einzige** Weiterleitung mit „cloud“ im Namen [G,
Zusammenfassung des Abruf-Tools; die Redirect-Liste selbst wurde nicht Zeile für Zeile gelesen]. Dazu
passt `https://my.home-assistant.io/redirect/network/` („Link to Network“, Netzwerk-Einstellungen)
[G], nützlich für den Hinweis „externe Adresse“. Ob die Umbenennung zu Link den Redirect-Namen
ändert, ist **[U]**.

**Anleitung für Laien (Vorschlag, [A]):** Link `.../redirect/cloud/` öffnen, Konto anlegen
(Test starten, 31 Tage, ohne Karte), danach in HA unter *Einstellungen > Home Assistant Cloud*
anmelden. Danach den Dialog der Integration erneut starten. Der Anmeldeschritt selbst wurde nicht
nachvollzogen (kein Konto anlegen erlaubt).

### 3.2 Alternativen mit eingehender Verbindung

| Weg | Kosten | Aufwand für Laien | Zuverlässigkeit / Sicherheit | Befund |
|---|---|---|---|---|
| Cloudflare Tunnel (Add-on `cloudflared`) | Tunnel kostenlos; **eigene Domain** nötig (laufende Kosten, einige EUR/Jahr [A]) | hoch: Cloudflare-Konto, Domain, DNS umziehen | Ausgehende Verbindung, kein offener Port; läuft über Cloudflare. Add-on „Maintenance: yes (2026)“ | [G] https://github.com/brenner-tobias/addon-cloudflared (Domain-Pflicht dort belegt; Kostenaussage nur aus Blogs, [A]). Cloudflare-Doku: nur ausgehend [G] https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/ . Ob Cloudflare-Schutzfunktionen FF-Agent-Aufrufe blocken, [U] |
| Tailscale Funnel | Free-Plan nutzbar, Funnel „beta“ [G] | hoch: Kommandozeile `tailscale funnel`, MagicDNS, HTTPS, Policy-Attribut | Adresse unter `*.ts.net`, nur Ports 443/8443/10000, Bandbreite begrenzt, TLS endet auf dem Gerät [G] https://tailscale.com/kb/1223/funnel . Ein HA-Add-on mit Funnel-Unterstützung nicht geprüft **[U]** | nur etwas für Technikaffine |
| ngrok | Free: 1 Entwicklungs-Domain, 20 000 Anfragen/Monat, 1 GB; Zwischenseite im Browser; ab 10 USD/Monat ohne [G] https://ngrok.com/pricing | mittel bis hoch (Konto, Agent muss laufen) | Dienst für Entwickler; kein Betriebsversprechen für Alarmierung [A] | nicht empfohlen |
| DuckDNS + Let's Encrypt + Portfreigabe | kostenlos | hoch: Add-ons, Router-Freigabe, Zertifikat | HA hängt direkt im Internet; HA-Doku: „Just putting a port up is not secure“; Dynamische IP und CG-NAT als Stolpersteine [G] https://www.home-assistant.io/docs/configuration/remote/ . DuckDNS-FAQ-Seite war nicht abrufbar (404), Dienst-Zuverlässigkeit **[U]** | nicht für die Zielgruppe |
| Router-Funktion (z. B. FRITZ!Box MyFRITZ) | kostenlos [A, nicht belegt: Seite 404] | mittel: Portfreigabe plus MyFRITZ-Konto | Nur mit passender FRITZ!Box; gleiche Risiken wie Portfreigabe | Herstellerseite zu MyFRITZ nicht abrufbar (404) **[U]**; Forum erwähnt MyFRITZ per IPv6 [G, Suche] https://www.computerbase.de/forum/threads/ds-lite-myfritz.1925757/ |
| DS-Lite / CGNAT | – | – | Klassische IPv4-Portfreigabe **geht nicht** (geteilte IPv4) [G, Suche]; nur IPv6-Freigabe. FF Agent müsste die IPv6-Adresse erreichen können: **[U]** (Server-Seite unbekannt). Das IPv6-Präfix wechselt häufig, DynDNS (AAAA) nötig, Stolpersteine in der FRITZ!Box [G, Suche] https://blog.lohr.dev/ipv6-port-sharing-using-fritzbox | Für Laien faktisch nicht lösbar; hier helfen nur Nabu Casa oder ein Relay (ausgehend) |

Fazit [A]: Alles außer Nabu Casa braucht Konto, Domain oder Router-Eingriff; für Einsatzkräfte ohne
Netzwerkwissen unrealistisch. Wer es kann, braucht keine Anleitung von uns, nur den Hinweis auf
„externe URL“.

### 3.3 Relays (HA holt ab, kein Zugang von außen)

**Bewertungsrahmen:** FF Agent ruft eine URL im Internet auf, HA hält eine **ausgehende**
Verbindung zum Relay. Der Dienst darf nur Alarmzeitpunkte kennen (der Aufruf trägt vermutlich
keine Einsatzdaten, ADR 0002 A2).

#### ntfy (ntfy.sh oder selbst gehostet)

- **Veröffentlichen per GET oder POST:** `/<thema>/trigger`, `/publish` und `/send` akzeptieren GET;
  ein leerer Aufruf sendet „triggered“. Parameter lassen sich in die URL schreiben [G]
  https://docs.ntfy.sh/publish/ . Das passt zu FF Agent, das GET und POST beherrscht, mit
  https und 5 s Timeout [G, ADR]. Dass FF Agent diese URL akzeptiert und ntfy innerhalb 5 s
  antwortet, ist [A], nicht getestet.
- **Abonnieren:** JSON-Stream, SSE, Raw, **WebSocket** (`/<thema>/ws`); geschützte Themen per Basic-Auth
  oder `auth`-Parameter [G] https://docs.ntfy.sh/subscribe/api/ .
- **HA kann es mit Bordmitteln:** Die Core-Integration `ntfy` (seit HA 2025.5, `iot_class: cloud_push`,
  Qualitätsstufe Platin) bietet je Thema eine **Event-Entität**, die das Thema abonniert und
  Meldungen in Echtzeit als Automations-Trigger liefert; Filter nach Priorität, Tags, Titel,
  Inhalt. Dienstadresse standardmäßig `https://ntfy.sh` oder eigene Instanz; Benutzername und
  Passwort sind optional, anonym also möglich [G, aus optionalen Feldern abgeleitet]
  https://www.home-assistant.io/integrations/ntfy/ ,
  https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/ntfy/manifest.json .
- **Verbindungsverhalten (Quellcode `ntfy/event.py`, dev):** WebSocket-Hintergrundtask, bei Fehlern
  Wiederverbindung alle 10 s, Entität „nicht verfügbar“ währenddessen; es wird **kein `since`**
  übergeben, verpasste Meldungen werden also nicht ausdrücklich nachgeholt. Die Bibliothek
  `aiontfy` wurde nicht gelesen [G] https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/ntfy/event.py .
  Folge [A]: Fällt die Verbindung (HA-Neustart, Internetausfall, ntfy.sh-Störung) während eines
  Alarms aus, geht der Alarm verloren. Das gilt für Nabu Casa ähnlich (HA offline = kein Alarm),
  aber ntfy.sh ist ein weiterer Ausfallpunkt.
- **Kostenlose Grenzen (ntfy.sh):** 250 Nachrichten/Tag, Nachrichten bis 4096 Byte, Nachrichten werden
  **12 h** zwischengespeichert; Serverstandard: 60 Anfragen Burst, danach 1 je 5 s je Besucher
  (= je IP), 30 offene Verbindungen je Besucher, Verstöße können zu einer IP-Sperre führen [G]
  https://docs.ntfy.sh/publish/ , https://docs.ntfy.sh/config/ .
  **Risiko [A]:** Wenn alle FF-Agent-Aufrufe aus wenigen Server-IPs kommen, teilen sich alle
  Einsatzkräfte das Limit „je Besucher“. Bei Großalarmen wären 429-Fehler möglich. Nicht prüfbar **[U]**.
  Eine Wiederholung bei Fehler durch FF Agent ist ebenfalls [U].
- **Selbst hosten:** ja, Open Source; der Datenschutztext empfiehlt es für volle Kontrolle [G]
  https://docs.ntfy.sh/privacy/ . Für Laien nicht machbar und nützt nichts, solange der eigene
  Server selbst erreichbar sein muss; der Verein/Kreisverband könnte einen Server betreiben [A].
- **Latenz:** WebSocket-Push, vermutlich unter 1–2 s [A], nicht gemessen.
- **Datenschutz:**
  - Das Thema ist laut Doku „essentially a password“, Namen aus Buchstaben, Ziffern, `_`, `-`,
    bis 64 Zeichen [G]. Wer das Thema kennt, sieht **Alarmzeitpunkte** der Person und kann
    **falsche Alarme einspielen** [A]. Ein langes Zufallsthema (HA kann eines erzeugen [G]) ist wie eine Webhook-ID
    zu behandeln.
  - ntfy.sh speichert Nachrichten 12 h, IP-Adressen werden für das Ratenlimit genutzt und können für
    Debugging geloggt werden; **Serverstandort und DSGVO werden in der Datenschutzerklärung nicht
    genannt** [G] https://docs.ntfy.sh/privacy/ . Weitergabe möglich an Firebase, Twilio, Amazon
    SES, Stripe [G].
  - Alarmzeitpunkte einer Einsatzkraft sind personenbezogen (Funktionsbezug Feuerwehr/Hilfsorganisation).
    Ob das Gesundheits- oder Einsatzbezug im Sinne von Art. 9 DSGVO ist, ist eine **Rechtsfrage, die
    nur der Nutzer bzw. seine Organisation klären kann [U]**. Ein Zeitpunkt „Alarm, Person X“ ist auch
    ohne Einsatzinhalt aussagekräftig (Anwesenheit, Einsatzbereitschaft).
  - Zugriffsschutz: Geschützte Themen mit Benutzer/Passwort oder Token sind möglich, brauchen aber
    Zugriffssteuerung am Server; ob auf ntfy.sh ein Thema ohne Bezahlkonto reserviert werden kann, wurde
    nicht belegt **[U]**. FF Agent könnte Basic-Auth senden [G, Dialog], daher wäre ein geschütztes Thema
    technisch denkbar.
- **Zusatz-Token-Header:** ntfy wertet bestimmte Header aus (`Title`, `Priority`, `Tags`, `Actions`,
  …) [G]. Eigene Header kommen beim Abonnenten nicht an, nur Nachricht, Titel, Tags
  [A]. Das Token ist über ntfy **nicht prüfbar**. Ersatz: Das lange Zufallsthema (und optional
  ein Tag/Titel-Filter in der Event-Entität).
- **Bewertung:** machbar, kostenlos, nur für Laien mit ~6 Klicks; aber Dritter sieht Zeitpunkte, Verfügbarkeit
  ohne Zusage, Limit-Risiko.

#### Webhook Relay (webhookrelay.com)

Free: 150 Webhooks/Monat, 1 Eingang, 2 Ausgänge, **0 Tunnel**; bei Überschreitung werden die
Buckets gesperrt. Interne Ziele brauchen einen Relay-Agenten; Selbst-Hosting nicht genannt [G]
https://webhookrelay.com/pricing/ . Ein HA-Tutorial existiert laut Doku-Verzeichnis, Inhalt nicht gelesen **[U]**
https://webhookrelay.com/docs/ . Für Laien zu aufwendig (Agent/Add-on, Konto), Limit durch Testalarme schnell erreicht [A]. **Nicht empfohlen.**

#### Hookdeck

Free-Plan: 10 000 Ereignisse/Monat, 3 Tage Aufbewahrung, 1 Nutzer; bei Überschreitung sperrt das
Dashboard [G] https://hookdeck.com/pricing . Lieferung an ein lokales HA braucht vermutlich die CLI
(läuft nicht auf HA OS ohne Zusatz) [A]. **Nicht für Laien.**

#### smee.io

Leitet Webhooks per SSE an einen lokalen Client weiter; Zweck laut Seite Entwicklung (Probot/GitHub); keine
Zusagen zu Verfügbarkeit, Speicherung oder Sicherheit [G] https://smee.io/ . Kein Betrieb für Alarme. **Nicht geeignet.**

#### Pipedream

Nicht geprüft **[U]**. Aufwand (Konto, Workflow) und Abholung durch HA unklar; nicht weiterverfolgt.

#### MQTT mit HTTP-Eingang

Nicht im Detail geprüft **[U]**. Ein öffentlicher MQTT-Broker bräuchte einen HTTP→MQTT-Eingang; für Laien wäre
das Konto, Bridge und Sicherheitskonzept in einem. Ein Hinweis [A]: Ein Dienst mit HTTP-Eingang und MQTT-Abo ist
funktional ntfy ähnlich, aber teurer im Aufbau. Nicht empfohlen.

#### Pushover, Gotify, Telegram

- Diese Kanäle sind für Nachrichten **an Menschen** gedacht. FF Agent kann zwar deren HTTP-API
  als „Generischen Webhook“ aufrufen [A], aber HA hat keine Bordmittel, die eigene Nachricht
  zurückzulesen: Ein Telegram-Bot erhält Nachrichten, die er selbst sendet, nicht als Update [A,
  Bekanntes Telegram-Verhalten, nicht neu belegt]; Pushover und Gotify hat HA nur als Sendeweg [A]. **Nicht geeignet.**

#### FF-Agent-Typen „IFTTT Maker“ und „Homee Webhook“

- **IFTTT:** Die HA-Integration `ifttt` braucht selbst eine externe URL oder die Nabu-Casa-Webhook-URL, und der
  Webhooks-Dienst von IFTTT verlangt den **Pro-Plan** [G] https://www.home-assistant.io/integrations/ifttt/ . Das löst
  das Problem nicht (IFTTT würde HA ja von außen aufrufen).
- **Homee:** Der Typ ruft vermutlich ein Homee-Gerät/den Homee-Cloud-Dienst auf; für HA ohne Nutzen **[U]**. Kein Weg.

### 3.4 Vergleichstabelle aller Wege

Bewertung für die Zielgruppe „keine Netzwerkkenntnisse“. Zuverlässigkeit und Latenz sind
überwiegend [A], da nicht gemessen.

| Weg | Kosten | Aufwand Laie | Zuverlässigkeit | Latenz | Datenschutz | Voraussetzungen |
|---|---|---|---|---|---|---|
| **Nabu Casa / Link** | 7,50 EUR/Monat oder 75 EUR/Jahr, 31 Tage gratis [G] | **niedrig** (Konto, Anmelden) | hoch (Betreiber ist HA-Hersteller) [A]; Einzelfälle verschwundener Cloudhooks [G Forum] | gering, <1–2 s [A] | Nabu Casa sieht Aufrufzeitpunkte [A]; Token-Header evtl. durchgereicht (A12 [U]) | Cloud-Konto, Admin-Zugang in HA |
| **ntfy.sh + HA-Integration `ntfy`** | 0 EUR | **niedrig bis mittel** (Thema anlegen, in FF Agent eintragen) | mittel [A]: Verlust bei Trennung (kein `since`), geteiltes Ratenlimit möglich | gering [A] | Dritter sieht Zeitpunkte, Thema = Passwort, DSGVO/Standort unklar [G]; Token-Header kommt nicht an | HA ab 2025.5, ausgehendes Internet |
| ntfy selbst gehostet | Servermiete/eigene Hardware | hoch | abhängig vom Betreiber | gering | volle Kontrolle | eigener erreichbarer Server (z. B. Verein) |
| Cloudflare Tunnel | Tunnel gratis, Domain kostet [G/A] | hoch | hoch [A] | gering | Cloudflare sieht den Verkehr; HA nicht offen | Domain, Cloudflare-Konto, Add-on |
| Tailscale Funnel | gratis (Beta) [G] | hoch | mittel (Beta) | gering | Relay sieht Verkehr nicht (TLS auf dem Gerät) [G] | Tailscale-Konto, CLI |
| ngrok Free | 0 EUR (20 000 Anfragen/Monat) [G] | mittel bis hoch | mittel [A] | gering | ngrok sieht Verkehr [A] | Agent muss laufen |
| DuckDNS + Portfreigabe | 0 EUR | **sehr hoch** | mittel (dynamische IP, Zertifikat) | gering | HA direkt im Internet; Risiko [G] | echte IPv4, Router-Zugriff |
| FRITZ!Box MyFRITZ | gratis [A] | mittel bis hoch | mittel | gering | HA offen [A] | FRITZ!Box, Portfreigabe [U] |
| DS-Lite/CGNAT | – | – | Portfreigabe unmöglich [G] | – | – | nur ausgehende Wege (Nabu Casa, Relay) oder IPv6 [U] |
| Webhook Relay / Hookdeck / smee.io / Pipedream / MQTT | 0 EUR mit Limits | hoch (Agent/CLI) | siehe 3.3 | – | Dritter sieht Zeitpunkte | nicht empfohlen |
| Pushover / Gotify / Telegram | – | – | – | – | – | HA kann nicht abonnieren [A] |
| IFTTT / Homee | IFTTT Pro nötig [G] | – | – | – | – | löst das Problem nicht |

## 4. Bewertung und Empfehlung

**Standardweg: Nabu Casa.** Es ist der einzige Weg, bei dem die Einsatzkraft weder Router, Domain noch
Drittdienst anfassen muss, und er ist in der Integration schon umgesetzt (Cloudhook). Der Test ist
kostenlos, die Kosten sind klein gegen den Nutzen. Die Einsatzkraft bleibt in der Hand eines einzigen,
bekannten Betreibers.

**Alternative für Nutzer ohne Nabu Casa: ntfy.sh mit der HA-Integration `ntfy`**, mit klaren Auflagen:

- langes Zufallsthema (HA kann es erzeugen), nie öffentlich teilen;
- Datenschutz-Hinweis in der Anleitung (Dritter sieht die Alarmzeitpunkte, Standort/DSGVO nicht dokumentiert);
- Ehrlicher Hinweis: Kein Zusatz-Token möglich, keine Garantie bei Ausfall;
- FF-Agent-Seite per Testalarm prüfen.

**Für Technikaffine:** eine eigene externe HTTPS-Adresse (Cloudflare Tunnel oder Reverse Proxy); der
Config Flow erkennt sie ohnehin als `external`.

**Nicht empfohlen:** DuckDNS mit Portfreigabe (Sicherheitsrisiko, DS-Lite), ngrok, Webhook Relay,
Hookdeck, smee.io, Pushover/Telegram/IFTTT.

## 5. Folgerungen für die Integration (Vorschlag, keine Umsetzung)

### 5.1 Reihenfolge im Config Flow und README

1. Nabu Casa aktiv: Cloudhook (wie ADR 0002).
2. Externe HTTPS-URL: wie bisher.
3. Weder noch: **neuer Hinweis** mit Nabu-Casa-Link (My-Link) und, nachrangig, dem ntfy-Weg.
4. Interne Adresse nur als letzte Information („erreicht FF Agent nicht“).

README: Abschnitt „Erreichbarkeit“ mit den drei Wegen in der Reihenfolge Nabu Casa, ntfy, eigene
Adresse; Tabelle aus 3.4 in verkürzter Form, ein klarer Satz zu DS-Lite („Portfreigabe nicht
möglich, nehmen Sie Nabu Casa“).

### 5.2 Lohnt sich eingebaute Relay-Unterstützung?

- **Eigener ntfy-Client in der Integration (Abo per WebSocket/SSE): nein, vorerst nicht.** Er bräuchte
  einen eigenen Verbindungsmanager mit Wiederverbindung, Nachhol-Logik (`since`), Auth, Tests und
  Datenschutz-Verantwortung für ein Drittsystem. Die Core-Integration `ntfy` leistet das schon, mit
  Platin-Qualität [G]. Außerdem verlöre ADR 0002 seine Aussage „der Alarm kommt per Webhook“; das Zusatz-Token
  und das Prüfen der Form gäbe es nicht.
- **Schlanke Variante, die sich lohnt (Vorschlag, [A]):** Eine Option „Alarmquelle: vorhandene
  Event-Entität (z. B. ntfy)“ im Options Flow. Die Integration hört auf `state_changed` dieser Entität
  (`async_track_state_change_event`) und leitet jeden neuen Zeitstempel in den bestehenden
  `AlarmManager`. Vorteile:
  - Entitäten, Dedup, Rücksetz-Timer und Doku bleiben gleich.
  - Keine neue Netzwerklogik, `iot_class` bleibt `cloud_push`.
  - Gleicher Filter-Fallstrick wie bei der eigenen Event-Entität (`unavailable`/`unknown` ignorieren, siehe `docs/architektur.md`).
- **Auswirkung auf ADR 0002:** Ergänzung „Alternative Alarmquelle über eine vorhandene Event-Entität“; die
  Webhook-Registrierung bleibt (auch ohne externe Adresse nutzbar). Der Config Flow zeigt dann zusätzlich
  den ntfy-Weg. Die ADR-Aussage „Von HA aus wird nie ein Alarm ausgelöst“ bleibt gültig.
- **Auswirkung auf Datenschutz:** Der Abschnitt „Datenschutz“ in ADR/Architektur bekommt einen Zusatz: Bei
  ntfy kennt ein Dritter (der ntfy-Betreiber) die Alarmzeitpunkte; das Thema ist ein Geheimnis wie die
  Webhook-ID und gehört in dieselbe Redaction in Diagnostics. Mit der schlanken Variante speichert die
  Integration nur die `entity_id`.
- **Nicht vergessen:** Hinweis, dass die Zusatz-Token-Option beim ntfy-Weg wirkungslos ist.

Ob das gebaut werden soll, entscheiden Nutzer und Architekt (DSGVO-Frage zuerst, Abschnitt 6).

### 5.3 Textvorschlag für den Dialog „keine externe Adresse“

Aufbau nach dem ADR-Schlüssel `internal`/`path_only`. HA rendert Markdown in Dialogbeschreibungen,
die Links sind daher anklickbar [A]. Platzhalter in `{}` füllt die Integration.

```text
Dein Home Assistant ist von außen noch nicht erreichbar.

FF Agent sitzt im Internet und muss deinen Home Assistant bei einem Alarm "anrufen"
können. Dafür braucht er eine Adresse, die auch von außerhalb deines Heimnetzes
funktioniert. Die Adresse, die ich gerade sehe ({url}), funktioniert nur zuhause.
Ohne eine solche Adresse kommt kein Alarm an. Zusagen und Absagen funktionieren trotzdem.

Der einfachste Weg ist Home Assistant Cloud (Nabu Casa, ab Dezember 2026 "Home Assistant Link"):

1. [Hier klicken, um Home Assistant Cloud einzurichten](https://my.home-assistant.io/redirect/cloud/)
2. Konto anlegen und einloggen. Die ersten 31 Tage sind kostenlos, eine Zahlkarte
   brauchst du dafür nicht. Danach kostet es 7,50 € im Monat oder 75 € im Jahr.
3. Danach diese Einrichtung noch einmal starten. Du bekommst dann eine passende Adresse.

Du willst nichts bezahlen? Dann geht es auch mit dem kostenlosen Dienst ntfy. Das ist
etwas komplizierter, und die Betreiber des Dienstes können sehen, wann du alarmiert wurdest.
Eine Anleitung steht in der README unter "Ohne Nabu Casa".
```

Hinweise zum Text [A]:
- Die Dialogtexte sind in HA nicht beliebig lang; im Dialog nur Kurzform, Details in die README.
- Der Preis steht im Dialog nicht dauerhaft richtig; besser „Preis siehe Nabu Casa“ oder den Betrag
  weglassen. Preise ändern sich (siehe 6).
- „Home Assistant Link“ gleich mit aufnehmen, weil die Umbenennung am 2. Dezember ansteht.

## 6. Offene Punkte / was nur der Nutzer klären kann

1. **Cloudhook ohne Remote-Steuerung (U):** Funktioniert der Cloudhook, wenn „Remote-Steuerung“
   abgeschaltet ist? Beim ersten echten Test prüfen. Gleiches Test für das Zusatz-Token (A12).
2. **Header-Durchreichung bei Nabu Casa (U)** und **Nabu-Casa-Umbenennung:** Bleiben `redirect/cloud/` und Cloudhook-
   Namen nach dem 2. Dezember stabil? Nach dem Stichtag prüfen.
3. **DSGVO-Bewertung für ntfy.sh (U):** Darf ein Dritter ohne dokumentierten Serverstandort die Alarmzeitpunkte kennen?
   Das kann nur der Nutzer bzw. die Organisation klären. Bis dahin ntfy nur als „freiwillig,
   auf eigene Verantwortung“ führen.
4. **Absende-IP und Ratenlimit (U):** Von welchen IPs ruft FF Agent auf; teilen sich alle Nutzer ein Limit bei ntfy.sh?
   Frage an den Hersteller; die Anfrage läuft bereits.
5. **Wiederholt FF Agent bei Fehler, wertet es die Antwort aus, kann es IPv6? (U)**
6. **FF Agent und ntfy:** Ob FF Agent die URL `https://ntfy.sh/<Thema>/trigger` mit GET akzeptiert und
   die Antwort in 5 s erhält, kann nur ein Test mit einem echten Testalarm klären (Freigabe nötig, siehe CLAUDE.md).
7. **Nicht geprüft:** MyFRITZ (Seite 404), DuckDNS-FAQ (404), Pipedream, MQTT mit HTTP-Eingang, Tailscale-Add-on
   für HA, Nabu-Casa-Support-Artikel (403, nur über Suchzusammenfassung).
8. **Geheimes Thema auf ntfy.sh ohne Bezahlkonto reservierbar? (U)** Entscheidet, ob Zugriffsschutz möglich ist.
9. **Preise** sind Stand 2026-10-17 und ändern sich; nicht fest in Dialogtexte schreiben.

## 7. Empfehlung für das weitere Vorgehen

1. README und Dialog nach 5.1/5.3 überarbeiten (Doku-Auftrag, kein Code-Risiko): Nabu Casa zuerst, mit My-Link.
2. Beim ersten echten Test mit Cloudhook die Punkte 1 und 2 aus Abschnitt 6 abhaken.
3. Entscheidung des Nutzers über den ntfy-Weg einholen (DSGVO, Abschnitt 6 Punkt 3). Erst danach den ntfy-Abschnitt
   in die README schreiben.
4. Falls ja: Architekt bewertet die schlanke Variante „Alarmquelle = vorhandene Event-Entität“ und ergänzt
   ADR 0002; ein eigener ntfy-Client wird nicht gebaut.
5. Hersteller-Anfrage um die Fragen 4 und 5 ergänzen (Absende-IP, Wiederholung).

## 8. Quellen (Abruf 2026-10-17)

- https://www.nabucasa.com/pricing/ · https://www.nabucasa.com/link/ (Preis, Test, Umbenennung)
- https://www.home-assistant.io/cloud/ · https://www.home-assistant.io/docs/configuration/remote/
- https://my.home-assistant.io/redirect/cloud/ · https://my.home-assistant.io/redirect/network/ · https://my.home-assistant.io/faq/
- https://www.home-assistant.io/docs/automation/trigger/ (Webhook-Trigger) · https://www.home-assistant.io/integrations/webhook/
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/cloud/http_api.py
- https://support.nabucasa.com/hc/en-us/articles/25619382358685 (403; nur Suchzusammenfassung)
- https://www.home-assistant.io/integrations/ntfy/ · https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/ntfy/event.py · .../ntfy/manifest.json
- https://docs.ntfy.sh/publish/ · https://docs.ntfy.sh/subscribe/api/ · https://docs.ntfy.sh/config/ · https://docs.ntfy.sh/privacy/
- https://webhookrelay.com/pricing/ · https://webhookrelay.com/docs/ · https://hookdeck.com/pricing · https://smee.io/
- https://github.com/brenner-tobias/addon-cloudflared · https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- https://tailscale.com/kb/1223/funnel · https://ngrok.com/pricing
- https://www.home-assistant.io/integrations/ifttt/
- https://blog.lohr.dev/ipv6-port-sharing-using-fritzbox · https://www.computerbase.de/forum/threads/ds-lite-myfritz.1925757/ (nur Suchzusammenfassung)
- https://community.home-assistant.io/t/webhooks-api-or-nabu-casa/88776 (nur Suchzusammenfassung)
- Repo: `docs/adr/0002-integrationsweg-webhook-und-rueckmelde-url.md`, `docs/architektur.md`
