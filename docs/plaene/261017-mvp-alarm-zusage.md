# Umsetzungsplan: MVP Alarm-Eingang und Zusage/Absage

- **Datum:** 2026-10-17 · **Autor:** Architekt
- **Grundlage:** ADR `docs/adr/0002-integrationsweg-webhook-und-rueckmelde-url.md`
- **Vorschlag für TODOs (der Projektleiter legt sie an):** je PR eine TODO-ID, Branch
  `feat/<todo-id>`.

| PR | TODO-ID (Vorschlag) | Inhalt |
|---|---|---|
| 1 | `261017-mvp-1-config-flow` | Manifest, Rückmelde-URL-Parser, Webhook-URL-Ermittlung, Config Flow (`user`), Entfernen |
| 2 | `261017-mvp-2-webhook` | Webhook-Empfang, optionale Token-Prüfung mit Repair-Issue, Erfassung der Aufruf-Form, Diagnostics mit Redaction |
| 3 | `261017-mvp-3-alarm-entitaeten` | AlarmManager, Binary-Sensor, Event, Sensor „letzter Alarm“, Gerät, Icons |
| 4 | `261017-mvp-4-rueckmeldung` | ReplyClient, Buttons, Actions, Sensor „letzte Rückmeldung“ |
| 5 | `261017-mvp-5-options-reconfigure` | Options Flow, Reconfigure |
| 6 | `261017-mvp-6-doku-qualitaet` | README, Quality-Scale-Checkliste, Datenschutztest über alles |

Die Reihenfolge ist Absicht: Nach PR 2 kann der erste echte Webhook-Test stattfinden
(Annahmen A2 bis A5, A12, A13), bevor Entitäten und Rückmeldung darauf aufbauen. Mit
„auch für Testalarme“ in FF Agent lässt sich dieser Test über einen Testalarm fahren. Ein Test in der
echten HA-Instanz braucht die Freigabe des Nutzers.

## Ziel

Eine Einsatzkraft ohne Admin-Rechte richtet die Integration für sich ein. Sie bekommt in HA:

- einen Trigger bei jedem Alarm (Event-Entität),
- einen Zustand „Alarm aktiv“ mit Rücksetzzeit,
- den Zeitpunkt des letzten Alarms,
- Buttons und Actions für Zusage und Absage.

Die Integration ist datensparsam: keine Geheimnisse in Logs oder Diagnostics, keine
Einsatzinhalte im Recorder.

**Quality Scale:** Bronze mit begründeten Ausnahmen, dazu ausgewählte Regeln aus Silber und
Gold (siehe ADR, Abschnitt „Qualitätsziel“, und PR 6).

## Nicht-Ziele

- Einsatzdetails abrufen (iCal, Widget-API, App-Endpunkte). Der Erweiterungspunkt wird nur
  vorbereitet, siehe „Erweiterungspunkt Einsatzdetails“.
- Parsen eines Webhook-Payloads (A2 ungeklärt)
- Reauth-Flow (A7 ungeklärt)
- Verfügbarkeit setzen, Alarm auslösen, WebAPI
- Release, Versionssprung, Installation in der echten HA-Instanz. Das braucht jeweils die
  Freigabe des Nutzers.
- Wiederherstellen von „Alarm aktiv“ nach einem HA-Neustart

## Betroffene Dateien (Endstand)

```text
custom_components/ff_agent/
  __init__.py        setup/unload/remove, Webhook-Registrierung, Actions in async_setup
  manifest.json      cloud_push, service, dependencies webhook, after_dependencies cloud
  const.py           Konstanten, Optionen, Grenzwerte, TRANSPORTS
  models.py          Dataclasses: WebhookCall, AlarmEvent, ReplyResult, FFAgentData
  reply_url.py       Parser für die Rückmelde-URL (rein, ohne hass)
  webhook_url.py     Ermittlung der Webhook-URL (Cloudhook/extern/intern/Pfad)
  webhook.py         Webhook-Handler, Erfassung der Form
  alarm.py           AlarmManager (Dedup, Rücksetz-Timer, Dispatcher)
  reply.py           ReplyClient (HTTP, Lock, Doppelklick-Schutz)
  services.py        Registrierung der Actions accept/reject
  services.yaml
  entity.py          Basisentität mit DeviceInfo
  binary_sensor.py   alarm
  event.py           alarm
  sensor.py          last_alarm, last_reply
  button.py          accept, reject
  diagnostics.py
  config_flow.py     user, reconfigure, Options Flow
  icons.json
  translations/de.json, translations/en.json
tests/
  conftest.py        Fixtures (Platzhalter-IDs, MockConfigEntry, Setup-Helfer)
  test_reply_url.py  test_webhook_url.py  test_config_flow.py  test_init.py
  test_webhook.py    test_diagnostics.py  test_alarm.py  test_entities.py
  test_reply.py      test_button.py  test_services.py  test_privacy.py
  test_metadata.py   (anpassen)
README.md            Doku (PR 6)
```

## Verbindliche Vorgaben für alle PRs

**Platzhalter in Tests und Doku**, keine echten Kennungen und keine echten Koordinaten:

| Platzhalter | Wert |
|---|---|
| `REPLY_ID` | `00000000-0000-4000-8000-000000000000` |
| `OTHER_REPLY_ID` | `00000000-0000-4000-8000-000000000001` |
| Rückmelde-URL | `https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept?transport=CAR` |
| `WEBHOOK_ID` | `test-webhook-id-placeholder` |
| Cloudhook-URL | `https://hooks.nabu.casa/test-placeholder` |
| Externe URL | `https://example.com` |
| Koordinaten | `latitude=1.2345`, `longitude=6.789` |

**HA-APIs** (geprüft gegen HA 2026.3.0 und `dev`, Stand 2026-10-17):

- `from homeassistant.components import webhook`:
  - `webhook.async_register(hass, DOMAIN, name, webhook_id, handler, local_only=False, allowed_methods=...)`
  - `webhook.async_unregister(hass, webhook_id)`
  - `webhook.async_generate_id()`
  - `webhook.async_generate_url(hass, webhook_id, allow_internal=..., allow_external=..., prefer_external=...)`
  - `webhook.async_generate_path(webhook_id)`
  - `async_register` wirft `ValueError`, wenn die ID schon registriert ist.
- Cloud **nur lazy importieren** (`from homeassistant.components import cloud` innerhalb der
  Funktion) und nur, wenn `"cloud" in hass.config.components` gilt. Verfügbar sind
  `cloud.async_active_subscription(hass)`, `cloud.async_is_connected(hass)`,
  `await cloud.async_get_or_create_cloudhook(hass, webhook_id)`,
  `await cloud.async_delete_cloudhook(hass, webhook_id)`, `cloud.CloudNotAvailable` und
  `cloud.CloudNotConnected`.
- `from homeassistant.helpers.network import NoURLAvailableError`
- Config Flow:
  - `ConfigFlow.async_create_entry(title=, data=, description=, description_placeholders=, options=)`
  - `self._get_reconfigure_entry()`
  - `self.async_update_reload_and_abort(entry, unique_id=, data_updates=, ...)`
  - `OptionsFlowWithReload`, `self.config_entry` im Options Flow (nicht im `__init__` setzen)
- Actions:
  - Registrierung in `async_setup` mit
    `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`
  - Eintrag auflösen mit
    `homeassistant.helpers.service.async_get_config_entry(hass, DOMAIN, entry_id)`. Die
    Funktion wirft `ServiceValidationError`, wenn der Eintrag fehlt oder nicht geladen ist.
    In 2026.3 ist `entry_id: str` Pflicht.
- Event-Entität: `_attr_event_types`; nach `self._trigger_event("alarm")` selbst
  `self.async_write_ha_state()` aufrufen.
- Repair-Issues: `import homeassistant.helpers.issue_registry as ir`,
  `ir.async_create_issue(...)` und `ir.async_delete_issue(hass, DOMAIN, issue_id)`;
  Übersetzungen unter `issues.<translation_key>`.
- Cloudhook-Header: `cloud/client.py` (`async_webhook_message`) übergibt Header, Methode
  und Query der Cloud-Nachricht ungefiltert an `MockRequest` [G]. Was der Nabu-Casa-Server
  davor durchlässt, ist A12.
- `ConfigEntry.runtime_data` mit typisiertem Alias
  `type FFAgentConfigEntry = ConfigEntry[FFAgentData]`
- **Cloudhook-Aufrufe** kommen als `homeassistant.util.aiohttp.MockRequest`. Erlaubt sind
  `await request.text()`, `request.query`, `request.headers` und `request.method`.
  **`request.read()` nicht verwenden**, `MockRequest` hat diese Methode nicht.

**Logging- und Datenschutzregeln:**

- Nie loggen: Rückmelde-URL, `reply_id`, Webhook-URL, `webhook_id`, Query-Werte, Body-Werte,
  Koordinaten, `str(err)` von aiohttp-Exceptions (sie enthalten die URL).
- Erlaubt: Methode, Längen, Statuscode, Exception-Typname (`type(err).__name__`), Zähler.

**Weitere Regeln:**

- Translations von Hand in `translations/en.json` und `de.json` mit identischen Keys.
  `test_metadata.py` prüft das. Kein `strings.json`.
- Basisentität: `_attr_has_entity_name = True` und `_attr_should_poll = False`.
- `PARALLEL_UPDATES = 0` für `binary_sensor`, `event` und `sensor`, `PARALLEL_UPDATES = 1`
  für `button`.
- Commits auf Englisch, Conventional Commits. Nach jedem PR: `ruff check .`,
  `ruff format --check .` und `pytest` grün.

## Konstanten (`const.py`, Endstand)

```python
DOMAIN: Final = "ff_agent"
NAME: Final = "FF Agent"

CONF_REPLY_ID: Final = "reply_id"
CONF_REPLY_HOST: Final = "reply_host"
CONF_CLOUDHOOK: Final = "cloudhook"  # bool
CONF_CLOUDHOOK_URL: Final = "cloudhook_url"  # str | None, secret
CONF_HEADER_TOKEN: Final = "header_token"  # str, secret, always generated
# CONF_WEBHOOK_ID and CONF_NAME come from homeassistant.const

CONF_REPLY_URL: Final = "reply_url"  # flow field only, never stored
CONF_REGENERATE_WEBHOOK: Final = "regenerate_webhook"

CONF_RESET_MINUTES: Final = "reset_minutes"
CONF_DEFAULT_TRANSPORT: Final = "default_transport"
CONF_LOCATION_ENTITY: Final = "location_entity"
CONF_REQUIRE_TOKEN: Final = "require_token"  # bool, default False (ADR 0002, 5.)

TOKEN_HEADER: Final = "X-FF-Agent-Token"
ISSUE_TOKEN_REJECTED: Final = "webhook_token_rejected_{entry_id}"

DEFAULT_RESET_MINUTES: Final = 30
MIN_RESET_MINUTES: Final = 1
MAX_RESET_MINUTES: Final = 1440
DEFAULT_TRANSPORT: Final = "CAR"
TRANSPORTS: Final = ("CAR",)  # only verified values, extend after check (A9)

DEDUP_SECONDS: Final = 30
REPLY_TIMEOUT_SECONDS: Final = 10
REPLY_REPEAT_GUARD_SECONDS: Final = 10
MAX_BODY_ANALYSIS_CHARS: Final = 65536
MAX_SHAPE_DEPTH: Final = 5
MAX_SHAPE_KEYS: Final = 50
MAX_NAME_CHARS: Final = 64  # header, query and JSON key names
MAX_USER_AGENT_CHARS: Final = 120

DEFAULT_REPLY_HOST: Final = "www.ff-agent.com"
REPLY_PATH: Final = "/app2/missionreplies/{reply_id}/{action}"
WEBHOOK_ALLOWED_METHODS: Final = ("GET", "POST")  # exactly what FF Agent offers [G]

SIGNAL_ALARM: Final = "ff_agent_alarm_{entry_id}"  # payload AlarmEvent
SIGNAL_ALARM_STATE: Final = "ff_agent_alarm_state_{entry_id}"
SIGNAL_REPLY: Final = "ff_agent_reply_{entry_id}"  # payload ReplyResult

TO_REDACT: Final = {
    CONF_REPLY_ID,
    "webhook_id",
    CONF_CLOUDHOOK_URL,
    "webhook_url",
    CONF_HEADER_TOKEN,
    "unique_id",
    "title",
    CONF_LOCATION_ENTITY,
}
```

## Empfohlene Feldwerte in FF Agent

Verbindlich für den Abschlussdialog (PR 1), den Options-Text (PR 5) und das README (PR 6).
Quelle und Begründung: ADR 0002, Abschnitt 5a. Pfad in der Web-UI: Automatisierung >
Persönliche Webhooks > Webhook hinzufügen.

| Feld | Wert |
|---|---|
| Type | Alarm |
| Webhooktyp | Generischer Webhook |
| Name | frei, z. B. „Home Assistant“ |
| Aktiv | an |
| auch für Testalarme | an (zum Testen; Automationen laufen dann auch bei Testalarmen) |
| auch für Infoalarme | aus |
| auch für stille Einsätze | nach Wunsch, Vorschlag an |
| Zeitplan aktiviert | aus |
| Methode | POST |
| URL | angezeigte Webhook-URL mit `https://` |
| Basis-Authentifizierung | leer |
| Header | nur bei eingeschalteter Option: `X-FF-Agent-Token` = angezeigtes Token |
| Inhalt / Query-Parameter | leer |

---

## PR 1: Grundlage und Config Flow (`261017-mvp-1-config-flow`)

### Schritte

1. **`manifest.json`** anpassen. Die Schlüssel stehen nach `domain` und `name` alphabetisch.
   - neu: `"after_dependencies": ["cloud"]`, `"dependencies": ["webhook"]`
   - geändert: `"iot_class": "cloud_push"`, `"integration_type": "service"`
   - entfernt: `single_config_entry`
   - `version` bleibt `0.1.0`; der Versionssprung kommt erst mit dem Release.
2. **`const.py`** mit den Konstanten oben, soweit PR 1 sie braucht. Die übrigen kommen mit
   den späteren PRs.
3. **`reply_url.py`**: `parse_reply_input(value: str) -> ReplyTarget` (Dataclass mit `host`
   und `reply_id`, `frozen=True`). Ungültige Eingaben werfen `InvalidReplyUrl` (eigene
   Exception).
   - Vor der Prüfung Leerzeichen am Rand entfernen (`strip()`).
   - Ist die Eingabe eine UUID (`uuid.UUID(value)` gelingt), gilt
     `host = DEFAULT_REPLY_HOST`.
   - Sonst mit `yarl.URL(value)` parsen. Gefordert sind:
     - `scheme == "https"`
     - `host` (in Kleinbuchstaben) ist `ff-agent.com` oder endet auf `.ff-agent.com`
     - die Pfadteile sind genau `["/", "app2", "missionreplies", <uuid>, "accept"|"reject"]`
       (ein abschließender Slash ist erlaubt)
     - Query und Fragment werden ignoriert.
   - `reply_id = str(uuid.UUID(part))`, also normalisiert und in Kleinbuchstaben.
   - `def reply_unique_id(reply_id: str) -> str` gibt die ersten 16 Zeichen von
     `hashlib.sha256(reply_id.encode()).hexdigest()` zurück.
4. **`webhook_url.py`**:
   - `class UrlKind(StrEnum)` mit den Werten `CLOUD`, `EXTERNAL`, `INTERNAL` und
     `PATH_ONLY`.
   - `async def async_create_webhook_url(hass, webhook_id) -> tuple[str, UrlKind, bool]`.
     Das dritte Element sagt, ob ein Cloudhook angelegt wurde. Ablauf:
     1. Gilt `"cloud" in hass.config.components` und ist ein Abo aktiv
        (`cloud.async_active_subscription`), wirft die Funktion bei fehlender Verbindung
        (`not cloud.async_is_connected`) `CloudNotConnected`. Sonst gibt sie
        `(await cloud.async_get_or_create_cloudhook(...), CLOUD, True)` zurück.
     2. Sonst `async_generate_url(hass, id, allow_internal=False, prefer_external=True)`
        mit Ergebnis `EXTERNAL`.
     3. Bei `NoURLAvailableError` `async_generate_url(hass, id, allow_external=False)`
        mit Ergebnis `INTERNAL`.
     4. Bei erneutem `NoURLAvailableError` `async_generate_path(id)` mit Ergebnis
        `PATH_ONLY`.
   - `def async_get_webhook_url(hass, entry) -> tuple[str, UrlKind]` (`@callback`) für die
     Anzeige im Options Flow (PR 5). Bei `entry.data[CONF_CLOUDHOOK]` liefert sie die
     gespeicherte `cloudhook_url`, sonst die Schritte 2 bis 4 ohne neue Anlage.
5. **`config_flow.py`**, Schritt `user`:
   - Schema: `vol.Required(CONF_NAME, default=NAME): str` und
     `vol.Required(CONF_REPLY_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL))`
   - Ablauf:
     1. `parse_reply_input` aufrufen; bei `InvalidReplyUrl` den Fehler `invalid_reply_url`
        am Feld `reply_url` setzen.
     2. `await self.async_set_unique_id(reply_unique_id(...))` und
        `self._abort_if_unique_id_configured()` (Abbruch `already_configured`).
     3. `webhook_id = webhook.async_generate_id()` und
        `header_token = secrets.token_urlsafe(32)`.
     4. `async_create_webhook_url` aufrufen. Bei `CloudNotConnected` den Formularfehler
        `cloud_not_connected` (Basis) setzen.
     5. Eintrag anlegen: `async_create_entry` mit `title=name` und
        `data={reply_id, reply_host, webhook_id, cloudhook, cloudhook_url|None, header_token}`,
        dazu `options={reset_minutes: 30, default_transport: "CAR", require_token: False}`,
        `description=url_kind` und `description_placeholders={"webhook_url": url}`. Das
        Token erscheint hier noch nicht, um die Ersteinrichtung einfach zu halten; es steht
        im Options Flow.
   - **Kein HTTP-Aufruf** an FF Agent.
6. **`__init__.py`**:
   - `async_setup_entry` und `async_unload_entry` bleiben vorerst ohne Plattformen.
   - Neu ist `async_remove_entry(hass, entry)`. Gilt `entry.data.get(CONF_CLOUDHOOK)` und
     `"cloud" in hass.config.components`, ruft es lazy `cloud.async_delete_cloudhook` auf.
     `CloudNotAvailable` und `ValueError` werden mit `contextlib.suppress` ignoriert.
7. **Translations** (de/en):
   - `config.step.user`: Titel, Beschreibung und Feldtexte. `data_description` erklärt, wo
     die URL in FF Agent steht: Web-UI > Automatisierung > Einsatzrückmeldungen, die
     Zusage-URL kopieren. Hinweis: Die URL ist ein Geheimnis.
   - `config.error`: `invalid_reply_url`, `cloud_not_connected`
   - `config.abort`: `already_configured`
   - `config.create_entry.cloud|external|internal|path_only`:
     - Text mit `{webhook_url}` und einer Kurzanleitung nach der Tabelle „Empfohlene
       Feldwerte in FF Agent“ (Type Alarm, Generischer Webhook, Methode POST, URL,
       Testalarme an, Infoalarme aus, Zeitplan aus). Markdown-Liste, kurz halten.
     - `internal` warnt deutlich: FF Agent erreicht diese Adresse nicht.
     - `path_only` erklärt, dass eine externe URL oder Nabu Casa nötig ist.
   - Den alten Schlüssel `single_instance_allowed` entfernen.

### Tests (PR 1)

- `test_reply_url.py`, parametrisiert:
  - gültig: Zusage-URL mit Query, Absage-URL, UUID in Großbuchstaben, blanke UUID,
    Leerzeichen am Rand, abschließender Slash, Subdomain `free.ff-agent.com`
  - ungültig: `http://`, Host `ff-agent.com.example.org`, Host `example.com`, falscher Pfad,
    fehlende Aktion, kaputte UUID, leere Eingabe
  - `reply_unique_id` ist deterministisch, 16 Zeichen lang und enthält die UUID nicht.
- `test_webhook_url.py`:
  - externe URL über `await async_process_ha_core_config(hass, {"external_url": "https://example.com"})`
  - nur intern (`internal_url`)
  - keine URL ergibt `PATH_ONLY`
  - Cloud aktiv: `hass.config.components.add("cloud")`, dazu `patch` auf
    `homeassistant.components.cloud.async_active_subscription` (True),
    `async_is_connected` (True) und `async_get_or_create_cloudhook` (Platzhalter-URL)
  - Cloud aktiv, aber nicht verbunden: wirft `CloudNotConnected`
- `test_config_flow.py` (ersetzt die bisherigen Tests):
  - Formular anzeigen
  - Erfolg mit externer URL: Daten, Optionen, `description == "external"`, Placeholder
    enthält die URL, `unique_id` ist der Hash
  - Erfolg mit Cloud (`cloudhook=True`, `cloudhook_url` gesetzt)
  - `invalid_reply_url`, danach Korrektur und Erfolg (Error-Recovery)
  - `cloud_not_connected`, danach Erfolg
  - doppelte Person führt zu `already_configured`
  - zwei verschiedene Personen ergeben zwei Einträge (`single_config_entry` ist weg)
  - der Flow speichert nie die volle URL: `CONF_REPLY_URL not in entry.data`
  - `header_token` ist gesetzt (mindestens 40 Zeichen) und je Eintrag verschieden;
    `require_token` ist `False`
- `test_init.py`: Setup, Unload und Reload wie bisher, aber mit `MockConfigEntry`-Daten aus
  der Fixture. `async_remove_entry` mit Cloudhook ruft `async_delete_cloudhook` auf (Patch);
  ohne Cloudhook wird nichts aufgerufen; `CloudNotAvailable` wird geschluckt.
- `test_metadata.py`: prüft zusätzlich `iot_class == "cloud_push"`, `"webhook"` in
  `dependencies` und das Fehlen von `single_config_entry`.

**DoD PR 1:**

- CI grün (ruff, pytest, hassfest)
- Config-Flow-Abdeckung 100 % (`config-flow-test-coverage`)
- Kein Platzhalter-Geheimnis in `caplog.text`, als Assert im Erfolgstest

---

## PR 2: Webhook-Empfang und Diagnostics (`261017-mvp-2-webhook`)

### Schritte

1. **`models.py`**:
   - `WebhookCall` (frozen dataclass) mit den Feldern:
     - `received_at: datetime`
     - `method: str`
     - `content_type: str | None`
     - `body_length: int`
     - `header_names: tuple[str, ...]`, sortiert und in Kleinbuchstaben
     - `user_agent: str | None`, gekürzt auf 120 Zeichen
     - `query_keys: tuple[str, ...]`
     - `body_kind: Literal["empty", "json", "form", "text", "binary"]`
     - `body_shape: Any`
   - `def as_diagnostics(self) -> dict[str, Any]`
   - `FFAgentData` (dataclass): im ersten Schritt nur `webhook_stats`, ab PR 3 mit
     `alarm`, ab PR 4 mit `reply`.
2. **`webhook.py`**:
   - `async def async_capture_call(request) -> WebhookCall`:
     - Body über `await request.text()` lesen. `UnicodeDecodeError` ergibt
       `body_kind="binary"` mit `body_length` aus `request.headers.get("Content-Length")`.
       Danach den Text auf `MAX_BODY_ANALYSIS_CHARS` kürzen.
     - JSON erkennen: Content-Type enthält `json` oder der Text beginnt mit `{` bzw. `[`.
       Dann `json_loads` aus `homeassistant.util.json` anwenden. Gelingt das, gilt
       `body_kind="json"` und `body_shape = _shape(obj)`.
     - Formular erkennen: Content-Type `application/x-www-form-urlencoded`. Dann
       `urllib.parse.parse_qs(text, keep_blank_values=True)`; `body_shape` ist die
       sortierte Liste der Schlüssel.
     - Sonst `text` (Shape = `None`) oder `empty`.
     - `_shape(obj, depth)`: Ein dict wird zu `{key: _shape(v)}` mit höchstens
       `MAX_SHAPE_KEYS` Schlüsseln, eine Liste zu `[_shape(erstes Element)]` plus Länge.
       Skalare werden zum Typnamen (`"str(12)"` mit Länge, `"int"`, `"float"`, `"bool"`,
       `"null"`). Ab `MAX_SHAPE_DEPTH` steht dort `"..."`. **Werte werden nie übernommen.**
     - Darf nie werfen. Jede Exception beim Parsen ergibt `body_kind="text"`.
   - `def async_build_handler(entry_id) -> Handler` (`hass, webhook_id, request`):
     1. **Token-Prüfung**, nur wenn `entry.options.get(CONF_REQUIRE_TOKEN)` gilt:
        `presented = request.headers.get(TOKEN_HEADER, "")`. Ist
        `hmac.compare_digest(presented.encode(), entry.data[CONF_HEADER_TOKEN].encode())`
        falsch, passiert Folgendes, und dann ist Schluss:
        - `rejected_total += 1`
        - Debug-Log ohne Header-Wert
        - Repair-Issue anlegen:
          `ir.async_create_issue(hass, DOMAIN, ISSUE_TOKEN_REJECTED.format(entry_id=...), is_fixable=False, severity=ir.IssueSeverity.WARNING, translation_key="webhook_token_rejected", translation_placeholders={"title": entry.title})`
        - `return web.Response(status=HTTPStatus.UNAUTHORIZED)`

        Header-Namen sind in `request.headers` (CIMultiDict, auch bei `MockRequest`)
        unabhängig von Groß- und Kleinschreibung.
     2. Bei gültigem Token bzw. ausgeschalteter Option: ein evtl. bestehendes Issue mit
        `ir.async_delete_issue` entfernen. Der Aufruf ist idempotent.
     3. `call = await async_capture_call(request)`. `header_names` enthält den Token-Header
        nur als Namen, nie mit Wert.
     4. Debug-Log nur mit Methode und Länge
     5. weiterreichen an `entry.runtime_data`. In PR 2 heißt das nur: Statistik zählen und
        `last_call` setzen.
     6. `return None`, HA antwortet dann mit 200.

     Laufzeit: Bis auf `request.text()` wird nichts awaitet. FF Agent bricht nach 5 s ab;
     der Handler muss weit darunter bleiben.
   - **Translations** `issues.webhook_token_rejected` (title, description): Ein Aufruf ohne
     gültigen Header `X-FF-Agent-Token` wurde abgelehnt. Prüfen, ob der Header in FF Agent
     eingetragen ist. Bei Nabu Casa: Option ausschalten, falls der Header nicht ankommt.
3. **`__init__.py`**:
   - In `async_setup_entry` die Runtime-Daten anlegen und registrieren:
     `webhook.async_register(hass, DOMAIN, entry.title, entry.data[CONF_WEBHOOK_ID], handler, local_only=False, allowed_methods=list(WEBHOOK_ALLOWED_METHODS))`
   - Danach `entry.async_on_unload(lambda: webhook.async_unregister(hass, webhook_id))`.
4. **`diagnostics.py`**: `async_get_config_entry_diagnostics(hass, entry)` gibt zurück:
   - `entry`: `async_redact_data(entry.as_dict(), TO_REDACT)`
   - `webhook`: `{url_kind, allowed_methods, require_token}`; `url_kind` kommt aus
     `async_get_webhook_url`, die URL selbst nicht
   - `stats`: `{calls_total, rejected_total, last_call: call.as_diagnostics() | None}`.
     `last_call.header_names` zeigt beim ersten Test, ob `x-ff-agent-token` über den
     Cloudhook ankommt (A12).

   Ab PR 3 und PR 4 kommen weitere Abschnitte dazu (`alarm`, `reply`).

### Tests (PR 2)

`test_webhook.py`, mit `hass_client_no_auth` und einem eingerichteten Eintrag:

- GET (mit Query `a=1`) und POST liefern 200 und zählen hoch; `query_keys == ("a",)`.
- HEAD liefert 200 und zählt nicht (HA beantwortet HEAD ohne Handler).
- `PUT` liefert 405.
- Token-Option an (`MockConfigEntry(options={..., "require_token": True})`):
  - ohne Header: 401, Zähler `rejected_total == 1`, `calls_total == 0`, Repair-Issue im
    `issue_registry` vorhanden
  - falscher Header: 401
  - richtiger Header, Name in Kleinbuchstaben geschrieben: 200, Issue gelöscht
  - Token-Wert steht nicht in `caplog`, nicht in der Diagnose, nicht in `last_call`
- Token-Option aus: Aufruf ohne Header liefert 200.
- Cloudhook-Pfad mit Header: `MockRequest(..., headers={"X-FF-Agent-Token": <token>})` wird
  angenommen.
- POST mit JSON `{"keyword": "B3", "lat": 1.2345}`:
  - `body_kind == "json"`, Shape `{"keyword": "str(2)", "lat": "float"}`
  - der Wert `"B3"` steht nirgends in `entry.runtime_data`, in der Diagnose oder in
    `caplog`
- Formular-POST: Shape ist die Schlüsselliste.
- Ungültiges JSON mit Content-Type json ergibt `text`.
- Ungültiges UTF-8 ergibt `binary`.
- Leerer Body ergibt `empty`.
- Cloudhook-Pfad:
  `await webhook.async_handle_webhook(hass, WEBHOOK_ID, MockRequest(content=b'{"a":1}', mock_source="test", method="POST", headers={"Content-Type": "application/json"}))`
  läuft ohne `AttributeError` und liefert Shape `{"a": "int"}`.
- Nach dem Unload bleibt ein Aufruf ohne Wirkung (der Zähler bleibt gleich).

`test_diagnostics.py`, mit `get_diagnostics_for_config_entry` aus
`pytest_homeassistant_custom_component.components.diagnostics` (falls in der Version nicht
vorhanden: Funktion direkt aufrufen):

- `json.dumps(result)` enthält weder `REPLY_ID` noch `WEBHOOK_ID` noch die Cloudhook-URL
  noch den Titel.
- `url_kind` ist vorhanden.

**DoD PR 2:**

- Ein GET- oder POST-Aufruf mit beliebigem Body liefert 200 (bei aktiver Token-Pflicht
  nur mit gültigem Token) und erzeugt nie eine Exception im Log.
- Die Diagnose zeigt die Form des letzten Aufrufs.
- **Messpunkt für den ersten echten Test** (A2 bis A5, A12, A13; nur nach Freigabe des
  Nutzers):
  1. Eintrag einrichten.
  2. In FF Agent einen Generischen Webhook nach der Tabelle oben anlegen, zusätzlich den
     Header `X-FF-Agent-Token` eintragen (Option in HA dabei noch **aus**).
  3. Einen Testalarm auslösen lassen (Testalarme an).
  4. Diagnose herunterladen. Prüfen: Methode, `header_names` (kommt der Token-Header an?),
     `query_keys`, `body_kind`, Anzahl Aufrufe je Alarm.
  5. Erst danach die Token-Option testweise einschalten und einen zweiten Testalarm prüfen.

  Der Projektleiter bewertet das Ergebnis vor PR 3.

---

## PR 3: Alarm-Logik und Entitäten (`261017-mvp-3-alarm-entitaeten`)

### Schritte

1. **`models.py`**: `AlarmEvent` (frozen dataclass) mit `received_at: datetime`. Das Feld
   `details` kommt erst später, siehe Erweiterungspunkt.
2. **`alarm.py`**: `class AlarmManager`:
   - `__init__(hass, entry_id, reset_minutes)`
   - Attribute:
     - `active: bool`
     - `last_alarm: datetime | None`
     - `active_until: datetime | None`
     - Zähler `calls_total`, `alarms_total`, `deduplicated_total`
     - `last_call: WebhookCall | None`
   - `@callback def async_handle_call(self, call: WebhookCall) -> None`:
     1. `calls_total += 1`; `last_call = call`
     2. Liegt der letzte Alarm weniger als `DEDUP_SECONDS` zurück, `deduplicated_total += 1`
        und Ende.
     3. Sonst `last_alarm = call.received_at`; `alarms_total += 1`; `active = True`;
        `active_until = now + reset`.
     4. Den laufenden Timer abbrechen und mit `async_call_later(hass, reset_seconds, self._async_reset)`
        neu starten.
     5. `async_dispatcher_send(hass, SIGNAL_ALARM.format(...), AlarmEvent(...))` und
        `async_dispatcher_send(hass, SIGNAL_ALARM_STATE.format(...))`
   - `@callback def _async_reset(self, _now)`: `active = False`, `active_until = None`,
     Zustandssignal senden.
   - `@callback def async_shutdown(self)`: Timer abbrechen. Registrierung über
     `entry.async_on_unload`.
   - `reset_minutes` kommt aus `entry.options.get(CONF_RESET_MINUTES, DEFAULT_RESET_MINUTES)`.
   - Uhrzeit immer über `dt_util.utcnow()`.
3. Der Webhook-Handler ruft künftig `entry.runtime_data.alarm.async_handle_call(call)` auf.
   Die Statistik aus PR 2 wandert in den Manager; die Diagnose bekommt den Abschnitt
   `alarm`.
4. **`entity.py`**: `FFAgentEntity(Entity)` setzt `_attr_has_entity_name = True`,
   `_attr_should_poll = False`, `_attr_unique_id = f"{entry.entry_id}_{key}"` und
   `_attr_translation_key = key`. `_attr_device_info` ist eine `DeviceInfo` mit:
   - `identifiers={(DOMAIN, entry.entry_id)}`
   - `name=entry.title`
   - `manufacturer="mackoy consulting"`
   - `model="FF Agent"`
   - `entry_type=DeviceEntryType.SERVICE`
   - `configuration_url="https://www.ff-agent.com"`
5. **`binary_sensor.py`**: `alarm`. `is_on` liefert `manager.active`. In
   `async_added_to_hass` mit `self.async_on_remove(async_dispatcher_connect(... SIGNAL_ALARM_STATE ..., self.async_write_ha_state))`
   anmelden (`entity-event-setup`). Keine Device-Class, keine Attribute.
6. **`event.py`**: `alarm` mit `_attr_event_types = ["alarm"]`. Auf `SIGNAL_ALARM`
   reagieren: `self._trigger_event("alarm")` und danach `self.async_write_ha_state()`.
   Keine Event-Attribute.
7. **`sensor.py`**: `last_alarm` als `RestoreSensor` mit
   `device_class=SensorDeviceClass.TIMESTAMP`.
   - In `async_added_to_hass` wird `await self.async_get_last_sensor_data()` gelesen. Ist der
     Wert gesetzt und `manager.last_alarm is None`, wird er als `native_value` angezeigt. In
     den Manager wird er **nicht** übernommen, das Dedup-Fenster bleibt also flüchtig.
   - Bei `SIGNAL_ALARM` wird `native_value = event.received_at` gesetzt.
8. **`__init__.py`**: `PLATFORMS = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]`.
9. **`icons.json`**:
   - `binary_sensor.alarm`: `default` ist `mdi:alarm-light-outline`, `state.on` ist
     `mdi:alarm-light`
   - `event.alarm`: `mdi:fire-truck`
   - `sensor.last_alarm`: `mdi:clock-alert-outline`
10. **Translations**, `entity`-Abschnitt:
    - `binary_sensor.alarm.name`: „Alarm aktiv“ bzw. „Alarm active“
    - `event.alarm.name`: „Alarm“, dazu `state_attributes.event_type.state.alarm`
    - `sensor.last_alarm.name`: „Letzter Alarm“ bzw. „Last alarm“

### Tests (PR 3)

- `test_alarm.py`, Unit-Tests des Managers mit `freezer` (pytest-freezer ist in phcc
  enthalten; sonst `async_fire_time_changed` mit Patch von `dt_util.utcnow`):
  - erster Aufruf aktiviert und dispatcht
  - zweiter Aufruf nach 10 s wird dedupliziert und dispatcht nicht
  - Aufruf nach 31 s ergibt einen neuen Alarm, der Timer startet neu
  - nach Ablauf der Rücksetzzeit ist `active` falsch
  - `async_shutdown` bricht den Timer ab
- `test_entities.py`, End-to-End über `hass_client_no_auth`:
  - nach dem POST ist `binary_sensor.<name>_alarm_aktiv` an, `event` hat einen
    Zeitstempel-State und `event_type == "alarm"`, `sensor.<name>_letzter_alarm` ist gesetzt
  - nach `freezer.tick(timedelta(minutes=31))` und `async_fire_time_changed` ist der
    Binary-Sensor aus
  - Gerät im Device-Registry mit `entry_type` SERVICE
  - `unique_id`s enthalten die `entry_id`, aber nicht `REPLY_ID`
  - Restore: `mock_restore_cache_with_extra_data` stellt `last_alarm` nach dem Setup wieder
    her
  - Entity-IDs nicht hart codieren, sondern über
    `er.async_get_entity_id(platform, DOMAIN, unique_id)` holen

**DoD PR 3:**

- Alle Entitäten sind übersetzt (de/en) und gehören zum Gerät.
- Event-Trigger und Binary-Sensor verhalten sich wie beschrieben.
- Die Diagnose zeigt die Zähler.

---

## PR 4: Rückmeldung (`261017-mvp-4-rueckmeldung`)

### Schritte

1. **`models.py`**:
   - `class ReplyAction(StrEnum)`: `ACCEPT = "accept"`, `REJECT = "reject"`
   - `ReplyResult` (dataclass): `action`, `at`, `success: bool`, `status: int | None`,
     `content_type: str | None`, `error_type: str | None`, `skipped: bool`
2. **`reply.py`**: `class ReplyClient`:
   - `__init__(hass, entry_id, host, reply_id)`; dazu `self._lock = asyncio.Lock()` und
     `self.last_result: ReplyResult | None`.
   - `async def async_send(self, action, *, transport: str | None, location: tuple[float, float] | None) -> ReplyResult`. Ablauf:
     1. `async with self._lock:`
     2. Gab es für dieselbe `action` einen Erfolg vor weniger als
        `REPLY_REPEAT_GUARD_SECONDS`, wird `ReplyResult(skipped=True, success=True)` ohne
        HTTP-Aufruf zurückgegeben.
     3. URL `f"https://{host}" + REPLY_PATH.format(reply_id=..., action=action)`.
        Parameter: bei `accept` `transport` (falls gesetzt), dazu `lat`/`lng` mit
        `f"{value:.6f}"`, falls ein Standort da ist. Bei `reject` keine Parameter.
     4. Aufruf:
        ```python
        session = async_get_clientsession(self._hass)
        async with session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=REPLY_TIMEOUT_SECONDS),
            allow_redirects=True,
        ) as resp:
            status = resp.status
            content_type = resp.content_type
        ```
        Den Body nicht auswerten und nicht loggen.
     5. Bei `TimeoutError` oder `aiohttp.ClientError` wird ein Ergebnis mit
        `success=False, error_type=type(err).__name__` gespeichert. Dann wird
        `ReplyConnectionError` geworfen, **ohne `from err`-Nachricht** in Logs.
        `raise ... from None` ist ausdrücklich gewollt, weil die verkettete Exception die URL
        enthält und in Tracebacks landen würde.
     6. Bei Status außerhalb von 200 bis 299 wird das Ergebnis gespeichert und
        `ReplyHttpError(status)` geworfen.
     7. Nach jedem echten Versuch (nicht bei `skipped`) wird `self.last_result` gesetzt und
        `SIGNAL_REPLY` dispatcht.
   - Eigene Exceptions in `reply.py`: `ReplyError`, `ReplyConnectionError(ReplyError)`,
     `ReplyHttpError(ReplyError)` mit `.status`.
   - `def resolve_location(hass, entity_id) -> tuple[float, float] | None`: liest die
     Attribute `latitude`/`longitude` des States. Fehlen sie, gibt es `None` und ein
     Debug-Log ohne Werte.
3. **Fehlerabbildung** in einer gemeinsamen Funktion, z. B.
   `async def async_send_reply(hass, entry, action, transport=None, location=None)` in
   `reply.py`:
   - Werte ergänzen: `transport` aus den Optionen, `location` über `resolve_location` aus der
     Option `location_entity`. Explizite Werte haben Vorrang.
   - `ReplyConnectionError` wird zu
     `HomeAssistantError(translation_domain=DOMAIN, translation_key="reply_connection_error")`.
   - `ReplyHttpError` wird zu `HomeAssistantError(..., translation_key="reply_http_error", translation_placeholders={"status": str(err.status)})`.
4. **`button.py`**: `accept` und `reject`, `PARALLEL_UPDATES = 1`. `async_press` ruft
   `async_send_reply` auf.
5. **`services.py`**: `@callback def async_setup_services(hass)`. Aufgerufen wird sie aus
   `async_setup` in `__init__.py`; dort steht auch das `CONFIG_SCHEMA`. Schemata:
   ```python
   ACCEPT_SCHEMA = vol.Schema(
       {
           vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
           vol.Optional("transport"): vol.In(TRANSPORTS),
           vol.Inclusive("latitude", "location"): cv.latitude,
           vol.Inclusive("longitude", "location"): cv.longitude,
       }
   )
   REJECT_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string})
   ```
   - Den Eintrag mit `service.async_get_config_entry(call.hass, DOMAIN, call.data[ATTR_CONFIG_ENTRY_ID])`
     auflösen.
   - Danach `async_send_reply` aufrufen.
   - `SupportsResponse.NONE`
6. **`services.yaml`**: Felder mit Selektoren:
   - `config_entry_id`: `config_entry: {integration: ff_agent}`
   - `transport`: `select` mit `options: [CAR]` und `translation_key: transport`
   - `latitude`/`longitude`: `number` mit `mode: box`, `step: any`, Bereich ±90 bzw. ±180
7. **`sensor.py`**: `last_reply` mit `SensorDeviceClass.ENUM` und den Optionen
   `["accepted", "rejected", "failed"]`. Reagiert auf `SIGNAL_REPLY`:
   - Erfolg ergibt `accepted` bzw. `rejected`.
   - Misserfolg ergibt `failed`.
   - Keine Attribute, kein Restore.
8. **Translations:**
   - `services.accept` und `services.reject` mit Name, Beschreibung und Feldern
   - `selector.transport.options.CAR`: „Auto“ bzw. „Car“
   - `exceptions.reply_connection_error`, `exceptions.reply_http_error` (mit `{status}`)
   - `entity.button.accept|reject`
   - `entity.sensor.last_reply` mit den States
9. **`icons.json`**:
   - `button.accept`: `mdi:check-circle`; `button.reject`: `mdi:close-circle`
   - `sensor.last_reply`: `mdi:message-reply-text`
   - `services.accept`: `mdi:check-circle`; `services.reject`: `mdi:close-circle`
10. Die Diagnose bekommt den Abschnitt `reply`: `last_result` ohne URL, mit `action`, `at`,
    `success`, `status`, `content_type`, `error_type`.

### Tests (PR 4)

Alle HTTP-Aufrufe laufen über `aioclient_mock`. Ein echter Zugriff auf ff-agent.com findet
nie statt.

- `test_reply.py`:
  - Zusage mit `CAR` und Koordinaten: Methode GET, Pfad, Query `transport=CAR`,
    `lat=1.234500`, `lng=6.789000`. Prüfen über `aioclient_mock.mock_calls[-1]`.
  - Absage ohne Query
  - 200 ergibt `success`
  - 404 ergibt `ReplyHttpError(404)`
  - `exc=TimeoutError()` und `exc=aiohttp.ClientError()` ergeben `ReplyConnectionError`
  - Doppelklick-Schutz: zweimal `accept` direkt nacheinander ergibt genau einen HTTP-Aufruf
  - `accept`, dann `reject` ergibt zwei Aufrufe
  - nach 11 s (freezer) ist erneutes `accept` wieder möglich
  - Standort-Entität vorhanden bzw. ohne Koordinaten
- `test_button.py`: Druck auf `accept`/`reject` löst den richtigen Aufruf aus. Ein Fehler
  wird zu `HomeAssistantError` mit `translation_key`. `sensor.last_reply` wechselt zu
  `accepted` bzw. `failed`.
- `test_services.py`:
  - beide Actions mit gültigem Eintrag
  - unbekannte `config_entry_id` ergibt `ServiceValidationError`
  - nur `latitude` ohne `longitude` ergibt `vol.Invalid` bzw. `MultipleInvalid`
  - unbekanntes `transport` wird abgelehnt
  - zwei Einträge: die richtige UUID wird verwendet
- `test_privacy.py` (Grundstock, Ausbau in PR 6): Alle obigen Abläufe laufen unter
  `caplog.set_level(logging.DEBUG)`. `REPLY_ID`, `WEBHOOK_ID` und die Koordinatenwerte
  stehen nicht in `caplog.text`.

**DoD PR 4:**

- Zusage und Absage funktionieren über Button und Action.
- Fehler erscheinen übersetzt.
- In keinem Log und keiner Diagnose steht die UUID.

---

## PR 5: Options Flow und Reconfigure (`261017-mvp-5-options-reconfigure`)

### Schritte

1. **Options Flow** (`class FFAgentOptionsFlow(OptionsFlowWithReload)`, über
   `@staticmethod @callback async_get_options_flow(config_entry)` am ConfigFlow), Schritt
   `init`:
   - `description_placeholders={"webhook_url": url, "url_kind": kind, "token_header": TOKEN_HEADER, "token": entry.data[CONF_HEADER_TOKEN]}`.
     URL und Art kommen aus `async_get_webhook_url`. Die Beschreibung erklärt die Art der
     URL; für `internal` und `path_only` ist der Text derselbe wie im Abschlussdialog. Sie
     enthält die Feldwerte-Tabelle in Kurzform und den Hinweis zum Header.
   - Felder:
     - `require_token`: `BooleanSelector`, Standard `False`. `data_description`: „Erst
       einschalten, wenn der Header in FF Agent eingetragen ist und ein Testalarm in der
       Diagnose `x-ff-agent-token` unter `header_names` zeigt. Empfohlen, wenn Automationen
       Tore oder Türen steuern.“
     - `reset_minutes`: `NumberSelector(min=1, max=1440, step=1, mode=BOX, unit_of_measurement="min")`
     - `default_transport`: `SelectSelector(options=list(TRANSPORTS), translation_key="transport")`
     - `location_entity`: optional, `EntitySelector(EntitySelectorConfig(domain=["person", "device_tracker"]))`
   - Das Leeren von `location_entity` muss möglich sein. Dafür `vol.Optional` mit
     `description={"suggested_value": ...}` statt `default` verwenden.
   - Die Werte setzt das ConfigEntry; der Reload passiert automatisch.
2. **Reconfigure** (`async_step_reconfigure`):
   - Felder: `reply_url` (optional, leer bedeutet unverändert, **nie vorbelegt**, weil es ein
     Geheimnis ist) und `regenerate_webhook` (bool, Standard `False`).
   - Ablauf:
     1. Ist `reply_url` gesetzt, wird sie geparst (Fehler `invalid_reply_url`). Danach
        `new_uid = reply_unique_id(...)`.
     2. Ist `new_uid != entry.unique_id` und hat ein **anderer** Eintrag diese `unique_id`,
        bricht der Flow mit `already_configured` ab. Dafür
        `self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, new_uid)`
        verwenden.
     3. Bei `regenerate_webhook` („Webhook-Zugang neu erzeugen“, erneuert URL und Token):
        - Hatte der alte Eintrag einen Cloudhook, ihn nach erfolgreicher Neuanlage löschen
          (suppress `CloudNotAvailable` und `ValueError`).
        - Neue ID mit `webhook.async_generate_id()` und neues
          `header_token = secrets.token_urlsafe(32)`, danach `async_create_webhook_url`
          aufrufen. `CloudNotConnected` ergibt den Formularfehler.
        - Den neuen Cloudhook erst anlegen, dann den alten löschen. So bleibt bei einem
          Fehler der alte Zugang erhalten.
     4. Ohne Neuerzeugung, aber mit Änderung der Rückmelde-URL:
        `return self.async_update_reload_and_abort(entry, unique_id=new_uid, data_updates={reply_id, reply_host})`
        mit Abbruchgrund `reconfigure_successful`.
     5. Mit Neuerzeugung: `self.hass.config_entries.async_update_entry(entry, unique_id=..., data={...})`,
        dann `self.hass.config_entries.async_schedule_reload(entry.entry_id)` und
        `return self.async_abort(reason="reconfigure_successful_new_webhook", description_placeholders={"webhook_url": url, "token_header": TOKEN_HEADER, "token": new_token})`.
        So bekommt der Nutzer die neue URL und das neue Token zu sehen;
        `async_update_reload_and_abort` kennt keine Placeholder.
     6. Ohne Änderung: Abbruch mit `reconfigure_successful`.
3. **Translations:** `options.step.init` (Beschreibung mit `{webhook_url}`, Felder,
   `data_description`), `config.step.reconfigure` und
   `config.abort.reconfigure_successful` bzw. `reconfigure_successful_new_webhook`.
   `reconfigure_successful_new_webhook` erinnert daran, URL und (falls genutzt) Header in
   FF Agent zu ersetzen. Bei aktiver Token-Pflicht werden Alarme bis dahin abgelehnt; der
   Text sagt das.

### Tests (PR 5)

- Options:
  - Formular zeigt die Webhook-URL im Placeholder (extern)
  - Speichern ändert `entry.options`, der Reload greift die neue Rücksetzzeit auf
  - `location_entity` lässt sich leeren
  - Placeholder enthält Token-Header und Token; `require_token` an, danach lehnt der
    Webhook Aufrufe ohne Header mit 401 ab
- Reconfigure:
  - nur neue Rückmelde-URL: Daten und `unique_id` neu, die Webhook-ID bleibt
  - gleiche URL: `reconfigure_successful`, keine Änderung
  - URL einer anderen bestehenden Person: `already_configured`
  - ungültige URL: Fehler und Recovery
  - Webhook neu erzeugen ohne Cloud: neue ID und neues Token, der alte Webhook ist
    abgemeldet (Aufruf an die alte ID ändert nichts), der neue funktioniert
  - Webhook neu erzeugen mit Cloud: `async_delete_cloudhook` wird mit der alten ID
    aufgerufen, `async_get_or_create_cloudhook` mit der neuen
  - Cloud nicht verbunden: Formularfehler

**DoD PR 5:**

- Die Webhook-URL ist jederzeit über „Konfigurieren“ abrufbar.
- Die UUID und der Webhook lassen sich ohne Entfernen der Integration erneuern.

---

## PR 6: Doku und Qualitätsabschluss (`261017-mvp-6-doku-qualitaet`)

### Schritte

1. **README.md** (Deutsch, englische Kurzfassung optional). Zu jedem Abschnitt steht die
   zugehörige Regel der Quality Scale.
   - Was die Integration tut und was nicht (`docs-high-level-description`). Ausdrücklich:
     keine Alarmauslösung, keine Einsatzdetails im MVP.
   - Voraussetzungen: FF-Agent-Konto, Zugriff auf „Automatisierung“, HA von außen
     erreichbar (Nabu Casa oder externe URL mit HTTPS)
   - Installation über HACS (Custom Repository) und manuell
     (`docs-installation-instructions`)
   - Einrichtung Schritt für Schritt (`docs-installation-parameters`):
     1. In FF Agent unter Automatisierung > Einsatzrückmeldungen die Zusage-URL kopieren.
     2. In HA die Integration hinzufügen, Name und Zusage-URL eintragen.
     3. Die angezeigte Webhook-URL kopieren.
     4. In FF Agent unter Automatisierung > Persönliche Webhooks > „Webhook hinzufügen“
        **jedes Feld nach der Tabelle „Empfohlene Feldwerte in FF Agent“** ausfüllen. Die
        Tabelle steht vollständig im README, mit Begründung je Feld (Testalarme,
        Infoalarme, stille Einsätze, Zeitplan, Methode POST).
     5. Einen Testalarm auslösen lassen und prüfen, ob „Alarm“ in HA auslöst.
     6. Optional, empfohlen bei Toren und Türen: Header `X-FF-Agent-Token` mit dem Token aus
        „Konfigurieren“ in FF Agent eintragen, Testalarm, in der Diagnose prüfen, dann in HA
        „Zusatz-Token verlangen“ einschalten.
   - Optionen (`docs-configuration-parameters`) und Reconfigure, inklusive Token-Pflicht
     und Repair-Hinweis bei abgelehnten Aufrufen
   - Entitäten und Event-Trigger (`docs-triggers`), Actions (`docs-actions`)
   - Beispiel-Automationen (`docs-examples`): Licht an bei Event `alarm`; Benachrichtigung
     mit Actionable Buttons, die `ff_agent.accept` aufrufen
   - Datenschutz:
     - Webhook-URL und Rückmelde-URL sind Geheimnisse.
     - Der Recorder speichert Alarmzeitpunkte; Beispiel für `recorder: exclude` mit
       `entity_globs`.
     - Diagnostics sind redigiert.
     - Wer die Webhook-URL kennt, kann ohne Token-Pflicht „Alarm aktiv“ auslösen. Dann
       den Zugang neu erzeugen und die Token-Pflicht einschalten.
   - Bekannte Einschränkungen (`docs-known-limitations`):
     - Webhook ohne Inhalt; Testalarm, stiller Einsatz und echter Alarm sind in HA nicht
       unterscheidbar
     - Filter und Zeitplan liegen in FF Agent
     - Token-Prüfung über Nabu Casa erst nach Bestätigung, dass der Header ankommt
     - Neustart setzt „Alarm aktiv“ zurück
     - nur `CAR` als Verkehrsmittel belegt
     - Rückmeldung gilt für den aktiven Einsatz
     - Erfolg heißt „HTTP 2xx“, nicht unbedingt „von FF Agent verbucht“
   - Optional: iCal über die Core-Integration „Remote Calendar“, mit Recorder-Hinweis
   - Entfernen (`docs-removal-instructions`): Integration löschen, persönlichen Webhook in
     FF Agent löschen, bei Bedarf die Rückmelde-URL in FF Agent neu erzeugen
   - Fehlerbehebung (`docs-troubleshooting`): Diagnose herunterladen; „Alarm kommt nicht an“
     (URL-Art, Webhook „Aktiv“, Auslöse-Filter, Zeitplan, HTTPS, Token-Pflicht und
     Repair-Hinweis, `rejected_total` in der Diagnose)
2. **`docs/quality-scale.md`**: Tabelle aller Bronze-Regeln mit Status `done` oder `exempt`
   und Begründung, dazu die zusätzlich erfüllten Silber- und Gold-Regeln. Keine
   `quality_scale.yaml` im Integrationsordner, weil das Verhalten von hassfest bei
   Custom-Integrationen ungeklärt ist.
3. **`test_privacy.py`** ausbauen: ein Test, der den ganzen Lebenszyklus mit DEBUG-Logging
   durchläuft. Er prüft am Ende, dass keines der Geheimnisse in `caplog.text`, in der
   Diagnose oder in den State-Attributen aller `ff_agent`-Entitäten steht. Lebenszyklus:
   1. Flow
   2. Webhook mit JSON-Payload, dann mit Token-Pflicht (richtiges und falsches Token)
   3. Button
   4. Action mit Koordinaten
   5. HTTP-Fehler
   6. Reconfigure mit Neuerzeugung
   7. Unload
   8. Remove
4. Abdeckung messen (`pytest --cov=custom_components.ff_agent`, falls `pytest-cov` über
   phcc vorhanden ist). Ziel: mindestens 95 % je Modul (`test-coverage`).

**DoD PR 6:**

- README deckt alle `docs-*`-Regeln der Bronze-Stufe ab.
- Die Quality-Scale-Tabelle ist vollständig.
- Abdeckung mindestens 95 %.
- `test_privacy.py` ist grün.

---

## Erweiterungspunkt Einsatzdetails (nicht bauen, nur freihalten)

- Der Handler gibt den Aufruf als `WebhookCall` an den Manager. Der rohe Text wird dabei
  **nicht** in `WebhookCall` gespeichert. Wird später ein Payload-Parser gebraucht, bekommt
  der Manager den Rohtext als zusätzliches flüchtiges Argument und `AlarmEvent` ein
  optionales Feld `details: MissionDetails | None`.
- Spätere Detail-Entitäten (z. B. `sensor.keyword`, `sensor.location`) setzen
  `_unrecorded_attributes` für alle Inhaltsattribute. Sie werden bei
  `entity-disabled-by-default` geprüft.
- Kandidat Nummer eins sind Platzhalter in den Query-Parametern oder Headern des
  Generischen Webhooks (A13). Der Parser würde dann nur bekannte, vom Nutzer gesetzte
  Schlüssel lesen (z. B. `keyword`, `location`, `alarm_type`). Damit ließen sich auch
  Testalarme von echten Alarmen unterscheiden.
- Achtung: Die Event-Entität speichert ihre Event-Attribute über `RestoreEntity` in
  `.storage/core.restore_state`. Einsatzinhalte gehören deshalb **nicht** in die
  Event-Attribute, sondern in eigene Sensoren.
- Eine Abrufquelle (Hersteller-API, iCal) wird als eigene Klasse `DetailsSource`
  angeschlossen. Sie wird durch den Alarm angestoßen und pollt nicht dauerhaft; `iot_class`
  bleibt `cloud_push`.

## Teststrategie (Überblick)

| Ebene | Werkzeug | Umfang |
|---|---|---|
| Reine Funktionen | pytest parametrisiert | `reply_url`, `_shape`, Location-Auflösung |
| Config Flow | `hass.config_entries.flow` / `.options.flow`, Patches für `cloud` | alle Pfade inklusive Fehlern und Recovery |
| Webhook | `hass_client_no_auth`, `webhook.async_handle_webhook` mit `MockRequest` | Methoden, Bodies, Cloud-Pfad, Unload |
| Zeitlogik | `freezer`, `async_fire_time_changed` | Dedup, Rücksetzzeit, Doppelklick-Schutz |
| HTTP nach außen | `aioclient_mock` | Erfolg, 4xx/5xx, Timeout, ClientError, Query-Parameter |
| Entitäten | Entity- und Device-Registry, `mock_restore_cache_with_extra_data` | Namen, `unique_id`s, Gerät, Restore |
| Datenschutz | `caplog` auf DEBUG, Diagnose, State-Attribute | keine Geheimnisse und keine Payload-Werte |

## Risiken

| Risiko | Wirkung | Gegenmaßnahme |
|---|---|---|
| Webhook-Verhalten anders als angenommen (A2 bis A5) | Fehl- oder Doppelalarme | PR 2 als Messpunkt vor PR 3; Dedup; Diagnose der Form |
| Nabu Casa reicht den Token-Header nicht durch (A12) | Bei aktiver Token-Pflicht werden alle Alarme verworfen | Option standardmäßig aus; Einschalten erst nach Diagnose-Nachweis; 401 plus Repair-Issue macht Ablehnungen sichtbar |
| Nutzer schaltet Testalarme ab und kann nicht testen | Einrichtung ungeprüft | Feldwerte-Tabelle empfiehlt Testalarme an |
| HA-Warnung bei falscher Methode (z. B. PUT) enthält die Webhook-ID | Geheimnis im Log | nur GET/POST bewerben; Privacy-Test ohne PUT-Fall; Restrisiko liegt in HA Core |
| Rückmeldung per GET klappt nicht, oder die Antwort ist immer 200 (A6, A7) | falsches Erfolgsgefühl | „Erfolg“ in der Doku definieren; Methode als Konstante; Test während eines Testalarms nach Freigabe |
| `REPLY_ID` gilt je Einsatz (A8) | Rückmeldung unbrauchbar | früh beim ersten Test prüfen; dann Plan anpassen |
| Webhook-URL gelangt an Dritte | falsche Alarme in HA | optionale Token-Pflicht; Neuerzeugung über Reconfigure; Doku |
| aiohttp-Exceptions mit URL landen im Traceback | UUID im Log | `raise ... from None`; Privacy-Test |
| hassfest bemängelt den Cloud-Import | CI rot | `after_dependencies: ["cloud"]`, lazy Import |
| Echte Zusage bei Tests | Einsatzplanung gestört | nur `aioclient_mock`; echter Test nur nach Freigabe und nur während eines Testalarms |

## Definition of Done (MVP gesamt)

- PR 1 bis 6 sind gemergt, jeweils mit CI grün, `tester` PASS und `reviewer` freigegeben.
- `manifest.json`: `cloud_push`, `service`, `dependencies: ["webhook"]`,
  `after_dependencies: ["cloud"]`, ohne `single_config_entry`.
- Mehrere Einträge sind möglich; die Einrichtung zeigt eine passende Webhook-URL mit
  Erklärung.
- Event, Binary-Sensor, die beiden Sensoren, die Buttons und die Actions funktionieren und
  sind de/en übersetzt.
- Diagnostics sind redigiert; der Privacy-Test ist grün; die Abdeckung liegt bei mindestens
  95 %.
- Die Bronze-Checkliste ist erfüllt bzw. die Ausnahmen sind begründet.
- Die Ergebnisse des ersten echten Tests (A2 bis A10, A12, A13) stehen in
  `docs/architektur.md`.
  Abweichungen sind als Folge-TODO erfasst.
