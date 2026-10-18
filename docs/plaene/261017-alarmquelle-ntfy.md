# Umsetzungsplan: Alarmquelle wählbar (Webhook oder ntfy), verständliche Erreichbarkeits-Texte

- **Datum:** 2026-10-17 · **Autor:** Architekt
- **TODO:** `261017-ux-erreichbarkeit` · **Branch:** `feat/261017-ux-erreichbarkeit`
- **Grundlage:** ADR `docs/adr/0003-alarmquelle-webhook-oder-ntfy.md`, ADR 0002,
  Recherche `docs/recherche/261017-erreichbarkeit.md`
- **Baut auf:** PR rauchstefan/ha-ff-agent#4 (`fix/261017-fundort-transport`: Fundort der
  Rückmelde-URL, Verkehrsmittel `car`/`feet`/`bicycle`)
- **Quality Scale:** Bronze bleibt erfüllt, die schon erfüllten Silber- und Gold-Regeln
  bleiben erfüllt. Neu berührt: `repair-issues`, `reconfiguration-flow`, `diagnostics`,
  `config-flow`, `test-coverage`.
- **Stand:** ADR 0003 angenommen (Nutzer, 2026-10-17). Der Einstieg ist nach seiner
  Entscheidung überarbeitet: erst die Frage nach Home Assistant Cloud, dann je Pfad ein
  Einrichtungsdialog mit nummerierten Schritten.

## Ziel

1. Bei der Einrichtung fragt die Integration: „Nutzt du Home Assistant Cloud (Nabu
   Casa)?“
   - **Ja (empfohlen)** → Cloud-Pfad: Webhook über Home Assistant Cloud oder, falls
     vorhanden, über die externe URL.
   - **Nein** → kurzer Hinweis auf ntfy als kostenlose Alternative, dann der ntfy-Pfad. HA
     muss dabei nicht von außen erreichbar sein.
   - Nichts wird erzwungen; der Wechsel zum anderen Pfad ist jederzeit möglich.
2. Je Pfad gibt es einen Einrichtungsdialog mit nummerierten Schritten und My-Links. Im
   Cloud-Pfad gibt es keine Sackgasse: „Erneut prüfen“, „Stattdessen ntfy“, „Trotzdem
   fortfahren“.
3. Im ntfy-Modus speist die Event-Entität der Core-Integration `ntfy` den bestehenden
   `AlarmManager`. Die Filterregel aus ADR 0003, Abschnitt 3, verhindert Fehlalarme bei
   Restore und verliert keine echten Alarme.
4. Die Quelle lässt sich über Reconfigure wechseln. Bestehende Einträge werden migriert
   (1.1 → 1.2) und bleiben Webhook-Einträge.
5. Thema und ntfy-`entity_id` stehen in keinem Log und keiner Diagnose.
   Datenschutzhinweis in Dialog und README.

## Nicht-Ziele

- Eigener ntfy-Client, Nachholen verpasster Meldungen (`since`)
- Programmatisches Anlegen des ntfy-Abos bzw. des ntfy-Eintrags (ADR 0003, Alternativen)
- Allgemeine „beliebige Event-Entität als Quelle“. Der Listener wird aber so gebaut, dass das
  später billig ist.
- Diagnose-Binärsensor „Alarmweg verbunden“ (Folge-TODO)
- Änderungen an Rückmeldung, Verkehrsmitteln, Gerät/Hersteller (TODO
  `261017-geraeteinfo-hersteller` bleibt separat)
- Release, Versionssprung in `manifest.json`, Installation in der echten HA-Instanz, echter
  Testalarm über ntfy. Das braucht jeweils die Freigabe des Nutzers.

## Voraussetzungen und Branching

- **PR #4 zuerst mergen**, dann `feat/261017-ux-erreichbarkeit` von `main` abzweigen. Ist
  #4 beim Start noch offen, von `fix/261017-fundort-transport` abzweigen und nach dem Merge
  von #4 auf `main` rebasen. Konfliktträchtig sind `translations/*.json`, `README.md`,
  `docs/architektur.md` und `tests/test_metadata.py`.
- Merge erst nach dem Okay des Nutzers (sein Test läuft noch, siehe TODO).
- Ein PR. Wird er zu groß für den Review, ist die Schnittlinie nach Schritt 7: PR a mit
  Migration, Menüs und Webhook-Texten, PR b mit ntfy.

## Betroffene Dateien

```text
custom_components/ff_agent/
  const.py           neue Schlüssel, Quellen, ntfy-Konstanten, My-Links, Issue-ID, TO_REDACT
  models.py          FFAgentData.source; NtfySubscription; NtfyEventShape
  alarm.py           async_handle_alarm() aus async_handle_call() herausgelöst
  webhook_url.py     Reachability + async_probe_reachability()
  ntfy_source.py     NEU: Suche/Beschreibung des Abos, NtfyAlarmSource (Listener)
  __init__.py        async_migrate_entry, Setup je Quelle, Issues, Remove
  config_flow.py     MINOR_VERSION 2, Menüs, Webhook-Pfad, ntfy-Pfad, Reconfigure, Options
  diagnostics.py     alarm_source, ntfy-Block
  translations/de.json, translations/en.json
tests/
  conftest.py, const.py, common.py     Fixtures für ntfy (Platzhalter)
  test_ntfy_source.py                  NEU
  test_ntfy_contract.py                NEU
  test_migration.py                    NEU (oder in test_init.py)
  test_config_flow.py, test_reconfigure.py, test_options_flow.py, test_init.py,
  test_diagnostics.py, test_privacy.py, test_privacy_lifecycle.py, test_alarm.py,
  test_metadata.py, test_webhook_url.py                       anpassen/ergänzen
README.md, CHANGELOG.md
docs/architektur.md, docs/quality-scale.md, docs/adr/0002-...md (Verweis auf 0003)
```

`manifest.json` bleibt unverändert: kein Versionssprung und kein `ntfy` in
`after_dependencies` (Begründung ADR 0003, 1.).

## Schritte

### Schritt 1: `const.py`

```python
CONF_ALARM_SOURCE: Final = "alarm_source"
SOURCE_WEBHOOK: Final = "webhook"
SOURCE_NTFY: Final = "ntfy"
ALARM_SOURCES: Final = (SOURCE_WEBHOOK, SOURCE_NTFY)   # Auswahl im Reconfigure

# Menüs der Einrichtung (Optionen = Step-IDs, Reihenfolge = Anzeigereihenfolge)
MENU_ALARM_SOURCE: Final = ["cloud", "no_cloud"]           # "Ja (empfohlen)", "Nein"
MENU_NO_CLOUD: Final = ["ntfy", "cloud", "own_address"]
MENU_CLOUD_SETUP: Final = ["cloud", "ntfy", "webhook_anyway"]
MENU_CLOUD_NOT_CONNECTED: Final = ["cloud", "ntfy"]
MENU_NTFY: Final = ["ntfy_find", "cloud"]

CONF_NTFY_ENTITY_UUID: Final = "ntfy_entity_uuid"  # Registry-UUID, data
CONF_NTFY_TOPIC: Final = "ntfy_topic"              # secret, data
CONF_NTFY_SERVER: Final = "ntfy_server"            # nur Anzeige, data
CONF_NTFY_ENTITY: Final = "ntfy_entity"            # nur Flow-Feld (entity_id), nie gespeichert

# Schlüssel der Core-Integration ntfy. Nicht importieren: homeassistant.components.ntfy
# importiert aiontfy. Abgesichert durch tests/test_ntfy_contract.py.
NTFY_DOMAIN: Final = "ntfy"
NTFY_SUBENTRY_TYPE: Final = "topic"
NTFY_CONF_TOPIC: Final = "topic"
NTFY_CONF_URL: Final = "url"
NTFY_DEFAULT_SERVER: Final = "https://ntfy.sh/"
NTFY_TOPIC_BYTES: Final = 16          # secrets.token_hex -> 32 Zeichen
NTFY_MAX_EVENT_AGE_SECONDS: Final = 60

ISSUE_NTFY_ENTITY_MISSING: Final = "ntfy_entity_missing_{entry_id}"

# My-Home-Assistant-Links. Übersetzungen dürfen keine URLs enthalten (hassfest),
# deshalb kommen sie als description_placeholders.
MY_CLOUD_URL: Final = "https://my.home-assistant.io/redirect/cloud/"
MY_NETWORK_URL: Final = "https://my.home-assistant.io/redirect/network/"
MY_NTFY_SETUP_URL: Final = "https://my.home-assistant.io/redirect/config_flow_start/?domain=ntfy"
MY_NTFY_INTEGRATION_URL: Final = "https://my.home-assistant.io/redirect/integration/?domain=ntfy"
```

`TO_REDACT` ergänzen um `CONF_NTFY_TOPIC`, `CONF_NTFY_ENTITY_UUID`, `CONF_NTFY_ENTITY`,
`"ntfy_publish_url"` und `"entity_id"`.

### Schritt 2: Migration und Versionen

- `FFAgentConfigFlow.MINOR_VERSION = 2` (`VERSION` bleibt 1).
- In `__init__.py`:

```python
async def async_migrate_entry(hass, entry) -> bool:
    if entry.version > 1:
        return False  # Downgrade von einer künftigen Hauptversion
    if entry.minor_version < 2:
        hass.config_entries.async_update_entry(
            entry,
            data={
                CONF_ALARM_SOURCE: SOURCE_WEBHOOK,
                CONF_NTFY_ENTITY_UUID: None,
                CONF_NTFY_TOPIC: None,
                CONF_NTFY_SERVER: None,
                **entry.data,  # vorhandene Werte gewinnen
            },
            minor_version=2,
        )
    return True
```

- `async_migrate_entry` loggt höchstens die Versionen, keine Daten.
- Neue Einträge legen alle Schlüssel an, beide Modi:
  - `webhook_id`, `header_token`: immer erzeugt
  - im ntfy-Modus `cloudhook=False` und `cloudhook_url=None`

### Schritt 3: `alarm.py`

Den Kern aus `async_handle_call` als eigene Methode herauslösen:

```python
@callback
def async_handle_call(self, call: WebhookCall) -> None:
    if self._closed:
        return
    self.calls_total += 1
    self.last_call = call
    self.async_handle_alarm(call.received_at)

@callback
def async_handle_alarm(self, received_at: datetime) -> bool:
    """Neuer Alarm oder Wiederholung; True bei neuem Alarm. Für alle Quellen."""
    if self._closed:
        return False
    # bisheriger Rumpf ab der Dedup-Prüfung, unverändert;
    # Log-Text neutral ("Alarm counted as a repetition of the last alarm")
```

Das Verhalten im Webhook-Modus bleibt bitgleich. Die bestehenden Tests in
`test_alarm.py`/`test_alarm_scenarios.py` müssen ohne inhaltliche Änderung grün bleiben.

### Schritt 4: `models.py`

```python
@dataclass(frozen=True, slots=True)
class NtfySubscription:
    """Ein ntfy-Abo, wie es die Integration aus Registry und ntfy-Eintrag liest."""
    entity_id: str
    entity_uuid: str
    topic: str | None    # None, wenn nicht lesbar
    server: str | None   # None, wenn nicht lesbar

@dataclass(frozen=True, slots=True)
class NtfyEventShape:
    """Form einer akzeptierten ntfy-Meldung, ohne Werte."""
    received_at: datetime
    age_seconds: float
    message_length: int | None
    has_title: bool
    tags_count: int | None
    def as_diagnostics(self) -> dict[str, Any]: ...
```

Dazu `FFAgentData.source: NtfyAlarmSource | None = None` (Import unter `TYPE_CHECKING`).

### Schritt 5: `webhook_url.py`, Erreichbarkeit ohne Nebenwirkung

```python
class Reachability(StrEnum):
    CLOUD = "cloud"        # Cloud-Abo aktiv (verbunden oder nicht)
    EXTERNAL = "external"  # externe URL vorhanden
    NONE = "none"

@callback
def async_probe_reachability(hass: HomeAssistant) -> Reachability:
    """Erzeugt nichts. CLOUD, wenn cloud geladen und async_active_subscription."""
```

- Für EXTERNAL dieselbe Logik wie `_async_local_webhook_url`, aber nur der Teil „extern“:
  `webhook.async_generate_url(..., allow_internal=False, prefer_external=True)` mit einer
  Dummy-ID, oder `network.get_url(hass, allow_internal=False, prefer_external=True)`. Fängt
  `NoURLAvailableError`.
- `cloud` weiter lazy importieren, vorher `"cloud" in hass.config.components` prüfen.
- `async_create_webhook_url` bleibt unverändert.
- Zwei Aufrufer:
  - die Einstiegsfrage: nur Textvariante `alarm_source_cloud`, keine Auswahl
  - der Cloud-Pfad: entscheidet zwischen Abschluss, `cloud_setup` und
    `cloud_not_connected`

### Schritt 6: `ntfy_source.py` (neu)

Öffentliche Funktionen (alle `@callback`, ohne I/O):

```python
def async_generate_topic() -> str                        # secrets.token_hex(NTFY_TOPIC_BYTES)
def async_describe_entity(hass, entity_id_or_uuid) -> NtfySubscription | None
def async_find_subscription_by_topic(hass, topic) -> NtfySubscription | None
def ntfy_publish_url(server: str | None, topic: str) -> str
    # f"{(server or NTFY_DEFAULT_SERVER).rstrip('/')}/{topic}/trigger"
```

- `async_describe_entity`:
  - `er.async_resolve_entity_id` und Registry-Eintrag
  - `None`, wenn es den Eintrag nicht gibt oder er `platform != "ntfy"`,
    `domain != "event"` oder `disabled` ist
  - Thema und Server lesen:
    - `hass.config_entries.async_get_entry(reg.config_entry_id)`
    - `.subentries.get(reg.config_subentry_id)`
    - `subentry_type == NTFY_SUBENTRY_TYPE`, dann `data.get(NTFY_CONF_TOPIC)` und
      `entry.data.get(NTFY_CONF_URL)`
  - Jede fehlende Stufe ergibt `None` im jeweiligen Feld, **keine Exception**.
- `async_find_subscription_by_topic`:
  - über `hass.config_entries.async_entries(NTFY_DOMAIN)` und deren `subentries`
  - Treffer bei `subentry_type == "topic"` und `data.get("topic") == topic`
  - dann `er.async_entries_for_config_entry(registry, entry_id)` mit passender
    `config_subentry_id` und `domain == "event"`
  - Ergebnis über `async_describe_entity`, damit dieselben Regeln gelten (z. B.
    deaktiviert = nicht gefunden)
- Keine Funktion loggt Thema oder `entity_id`.

Listener:

```python
class NtfyAlarmSource:
    def __init__(self, hass, alarm: AlarmManager, entity_id: str) -> None
    @callback
    def async_start(self) -> None:
        # Basiswert: aktueller State, falls gültiger Zeitstempel (nicht unavailable/unknown)
        # unsub_state = async_track_state_change_event(hass, [entity_id], self._handle)
    @callback
    def async_stop(self) -> None
    @callback
    def _handle(self, event: Event[EventStateChangedData]) -> None:
        # Regeln 1–6 aus ADR 0003, Abschnitt 3, in genau dieser Reihenfolge.
        # Zähler: events_total, accepted_total, ignored_restored_total,
        #         ignored_stale_total, ignored_duplicate_total
        # Bei Annahme: self._alarm.async_handle_alarm(ts); last_event = NtfyEventShape(...)
        # Form aus new_state.attributes: message (len), title (bool), tags (len).
        # Fehlende oder anders typisierte Attribute -> None/False, keine Exception.
    def as_diagnostics(self) -> dict[str, Any]
```

- Zeitstempel lesen mit `dt_util.parse_datetime(state.state)`. `None` bedeutet ungültig
  (Regel 2).
- Regel 3:
  - `old_state is None or old_state.attributes.get(ATTR_RESTORED)`
  - `ATTR_RESTORED` kommt aus `homeassistant.const`
- Regel 5:
  - `age = dt_util.utcnow() - ts`
  - `age > timedelta(seconds=NTFY_MAX_EVENT_AGE_SECONDS)` → ignorieren
  - negatives Alter gilt als frisch
- Debug-Logs nur mit dem Grund, z. B. `"ntfy event ignored: restored"`.

### Schritt 7: `__init__.py`, Setup je Quelle

```python
source = entry.data[CONF_ALARM_SOURCE]
token_issue = ISSUE_TOKEN_REJECTED.format(entry_id=entry.entry_id)
ntfy_issue = ISSUE_NTFY_ENTITY_MISSING.format(entry_id=entry.entry_id)
if source != SOURCE_WEBHOOK or not entry.options.get(CONF_REQUIRE_TOKEN):
    ir.async_delete_issue(hass, DOMAIN, token_issue)
if source == SOURCE_WEBHOOK:
    ir.async_delete_issue(hass, DOMAIN, ntfy_issue)
    # Webhook-Registrierung wie bisher
else:
    _async_setup_ntfy(hass, entry)   # siehe unten
await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
```

`_async_setup_ntfy(hass, entry)`:

1. `uuid = entry.data.get(CONF_NTFY_ENTITY_UUID)`. `entity_id` über
   `er.async_resolve_entity_id`; `reg` = Registry-Eintrag oder `None`.
2. Ist `reg` vorhanden, immer
   `async_track_entity_registry_updated_event(hass, [reg.entity_id], cb)` registrieren
   (`entry.async_on_unload`).
   - `cb` bei `action == "remove"`: Issue anlegen, Listener stoppen.
   - `cb` bei `action == "update"` und `"entity_id"` oder `"disabled_by"` in `changes`:
     `hass.config_entries.async_schedule_reload(entry.entry_id)`.
   - Andere Updates ignorieren, z. B. `capabilities`: Die ntfy-Entität ändert ihre
     `event_types` mit jeder Meldung.
3. `sub = async_describe_entity(hass, uuid)` (falls `uuid`).
   - `None`: Issue anlegen (`is_fixable=False`, `is_persistent=False`,
     `severity=ir.IssueSeverity.ERROR`, `translation_key="ntfy_entity_missing"`,
     Platzhalter `title`). Setup läuft weiter.
   - Sonst: Issue löschen, `NtfyAlarmSource(hass, alarm, sub.entity_id)` starten,
     `entry.async_on_unload(source.async_stop)`, `entry.runtime_data.source = source`.

`async_remove_entry`: zusätzlich `ntfy_issue` löschen. Den Cloudhook wie bisher nur bei
`cloudhook=True` löschen.

### Schritt 8: `config_flow.py`

Gemeinsame Hilfen:

```python
def _link_placeholders() -> dict[str, str]:
    return {"cloud_url": MY_CLOUD_URL, "network_url": MY_NETWORK_URL,
            "ntfy_setup_url": MY_NTFY_SETUP_URL,
            "ntfy_integration_url": MY_NTFY_INTEGRATION_URL}
```

Jeder `async_show_menu`/`async_show_form`/`async_create_entry`/`async_abort`, dessen Text
Platzhalter enthält, bekommt sie vollständig mit. Sonst zeigt das Frontend `{cloud_url}`
roh an.

Flow-Zustand in `self`:

- `_name`, `_reply` (geparstes Ziel), `_unique_id`, `_reply_updates`
- `_webhook_id`, `_header_token`, `_regenerate`
- `_ntfy_topic`
- `_cloud_attempts: int` (erfolglose Prüfungen im Cloud-Pfad)

Menüoptionen sind Step-IDs: Wählt der Nutzer z. B. „Erneut prüfen“ (Option `cloud`),
ruft HA `async_step_cloud(None)` auf. Menüs haben keine Vorauswahl [G]. „(empfohlen)“
steht deshalb im Optionstext, und die Reihenfolge der Liste ist die Anzeigereihenfolge
(`sort=False`).

**Einrichtung (`SOURCE_USER`):**

| Schritt | Art | Verhalten |
|---|---|---|
| `user` | Formular (wie bisher) | Prüft die Rückmelde-URL, setzt `unique_id`, `_abort_if_unique_id_configured()`. Erzeugt `_webhook_id`/`_header_token` einmalig. → `async_step_alarm_source()` |
| `alarm_source` | Menü `["cloud", "no_cloud"]` | Einstiegsfrage. Erscheint, wenn `async_probe_reachability` **nicht** `CLOUD` liefert. |
| `alarm_source_cloud` | Menü `["cloud", "no_cloud"]` | Dieselbe Frage mit angepasstem Text, wenn ein Cloud-Abo erkannt ist. Kein automatisches Weiterspringen. |
| `no_cloud` | Menü `["ntfy", "cloud", "own_address"]` | Kurzer Hinweis: ntfy ist die kostenlose Alternative. „Doch Cloud“ und „eigene Adresse“ bleiben möglich. |
| `cloud` | ohne eigene Anzeige | Cloud-Pfad, siehe unten |
| `own_address` | ohne eigene Anzeige | Ruft denselben Cloud-Pfad auf. Erkannt wird ohnehin zuerst die Cloud, sonst die externe URL. |
| `cloud_not_connected` | Menü `["cloud", "ntfy"]` | Cloud-Abo aktiv, aber nicht verbunden |
| `cloud_setup` | Menü `["cloud", "ntfy", "webhook_anyway"]` | **Einrichtungsdialog Cloud** mit nummerierten Schritten; erster erfolgloser Versuch |
| `cloud_setup_retry` | Menü `["cloud", "ntfy", "webhook_anyway"]` | Ab dem zweiten erfolglosen Versuch, mit Prüfhinweisen |
| `webhook_anyway` | ohne eigene Anzeige | Lokale URL (`internal`/`path_only`), Abschluss. Nur Zu- und Absage. |
| `ntfy` | Menü `["ntfy_find", "cloud"]` | **Einrichtungsdialog ntfy** mit nummerierten Schritten, Thema und FF-Agent-URL |
| `ntfy_find` | ohne eigene Anzeige | Sucht die Entität über das Thema; Treffer → Abschluss, sonst → `ntfy_select` mit Fehler |
| `ntfy_select` | Formular, Feld `ntfy_entity` (optional) | Erscheint nur, wenn die Suche nichts findet. Leer absenden sucht erneut, eine gewählte Entität wird geprüft. |

Schrittfolge für den Nutzer:

```text
user → alarm_source[_cloud]
  ├─ Ja (empfohlen) → cloud ─┬─ Cloud verbunden ......................→ Abschluss „cloud“
  │                          ├─ externe URL ...........................→ Abschluss „external“
  │                          ├─ Cloud nicht verbunden → cloud_not_connected (erneut | ntfy)
  │                          └─ nichts → cloud_setup (erneut | ntfy | trotzdem)
  │                                        └─ erneut, wieder nichts → cloud_setup_retry
  └─ Nein → no_cloud ─┬─ Weiter mit ntfy → ntfy (Einrichtungsdialog)
                      │       ├─ Erledigt → ntfy_find ─┬─ gefunden → Abschluss „ntfy“
                      │       │                        └─ nicht gefunden → ntfy_select → Abschluss „ntfy“
                      │       └─ Doch Home Assistant Cloud → cloud
                      ├─ Doch Home Assistant Cloud → cloud
                      └─ Eigene Internetadresse → own_address (= cloud-Pfad)
```

**Einstiegsfrage (`async_step_alarm_source`):**

- `reach = async_probe_reachability(hass)`.
- Bei `CLOUD`: `async_show_menu(step_id="alarm_source_cloud", ...)`, sonst
  `step_id="alarm_source"`. Beide haben `menu_options=["cloud", "no_cloud"]`.
- Eine Methode, zwei Step-IDs. Die Variante `alarm_source_cloud` braucht keinen eigenen
  Handler, weil Menüs nur die Optionen aufrufen.
- Das Ergebnis der Erkennung steuert nur den Text, nie die Auswahl.

**Cloud-Pfad (`async_step_cloud`, `async_step_own_address` ruft ihn auf):**

1. `reach = async_probe_reachability(hass)`.
2. `NONE`: `_cloud_attempts += 1`. Beim ersten Mal das Menü `cloud_setup` zeigen, sonst
   `cloud_setup_retry`.
3. Sonst `async_create_webhook_url(hass, self._webhook_id)`:
   - `CloudhookUnavailable` → Menü `cloud_not_connected`
   - andere Exception → nur den Typ loggen, `async_abort(reason="unknown")`. Der bisherige
     Fehler `unknown` wird damit zum Abort-Grund; den Text übernehmen.
   - Erfolg → `_async_finish_webhook(url, kind, cloudhook)`, Abschluss `cloud` bzw.
     `external`

`async_step_webhook_anyway`: `_async_local_webhook_url` (keine Cloud), dann
`_async_finish_webhook(url, kind, False)` mit `internal` bzw. `path_only`.

**ntfy-Pfad:**

- `async_step_ntfy` (Menü `ntfy`):
  - `_ntfy_topic` einmalig erzeugen.
    - Reconfigure, aktuelle Quelle ntfy und kein `_regenerate`: das gespeicherte Thema
      übernehmen.
  - Server für die Anzeige:
    - genau ein ntfy-Eintrag vorhanden: dessen `data["url"]`
    - sonst `NTFY_DEFAULT_SERVER`
  - Platzhalter: `ntfy_topic`, `ntfy_publish_url` (`ntfy_publish_url(server, topic)`) und
    die Link-Platzhalter.
- `async_step_ntfy_find` (ohne Anzeige):
  1. Kein Eintrag für `ntfy` vorhanden: → `ntfy_select` mit `errors["base"] =
     "ntfy_not_set_up"`.
  2. Sonst `sub = async_find_subscription_by_topic(hass, _ntfy_topic)`. Bei `None`: →
     `ntfy_select` mit `errors["base"] = "ntfy_entity_not_found"`.
  3. `sub.entity_uuid` hängt schon an einem **anderen** `ff_agent`-Eintrag: →
     `ntfy_select` mit `errors["base"] = "ntfy_entity_in_use"`.
  4. Sonst `_async_finish_ntfy(sub)`.
- `async_step_ntfy_select(user_input)`:
  - Feld `vol.Optional(CONF_NTFY_ENTITY)` mit
    `EntitySelector(EntitySelectorConfig(integration="ntfy", domain="event"))`. Im
    Reconfigure ist die aktuelle Entität als `suggested_value` vorbelegt (UUID →
    `entity_id`).
  - Leer abgesendet: dieselbe Suche wie `ntfy_find`, Fehler im selben Formular.
  - Entität angegeben:
    - `sub = async_describe_entity(...)`, bei `None` Fehler
      `errors[CONF_NTFY_ENTITY] = "ntfy_entity_invalid"`
    - dann Prüfung „in use“ wie oben
    - dann `_async_finish_ntfy(sub)`
  - Platzhalter wie im Menü `ntfy`. Die Beschreibung wiederholt das Thema kurz.
  - Ein Formular kann keinen Pfadwechsel anbieten. Wer hier doch die Cloud will, schließt
    den Dialog und startet neu. Das ist vertretbar, weil der Wechsel im Menü `ntfy` direkt
    davor möglich war.

**Abschluss je nach Kontext** (`self.source == SOURCE_RECONFIGURE`?):

- `_async_finish_webhook(url, kind, cloudhook)`:
  - **Einrichtung:**
    - `async_create_entry(title, data=..., options=Default-Optionen, description=kind)`
    - `data` enthält `alarm_source="webhook"`, die Webhook-Felder und die ntfy-Felder mit
      `None`
    - Platzhalter `webhook_url` plus Link-Platzhalter
  - **Reconfigure:** Muster aus dem heutigen `_async_regenerate`:
    1. `async_update_entry(data={**entry.data, **_reply_updates, alarm_source="webhook", webhook_id, header_token, cloudhook, cloudhook_url})`
       und `unique_id`.
    2. `async_schedule_reload`.
    3. Bei neuem Token das Issue `webhook_token_rejected` löschen.
    4. War die alte Webhook-ID eine andere und hatte einen Cloudhook: diesen löschen
       (Fehler nur als Typ loggen).
    5. `async_abort(reason="reconfigure_successful_new_webhook", description_placeholders={webhook_url, token_header, token, ...links})`.
- `_async_finish_ntfy(sub)`:
  - `topic = sub.topic or _ntfy_topic`, `server = sub.server or NTFY_DEFAULT_SERVER`,
    `publish_url = ntfy_publish_url(server, topic)`.
  - **Einrichtung:**
    - `async_create_entry(..., data={..., alarm_source="ntfy", ntfy_entity_uuid=sub.entity_uuid, ntfy_topic=topic, ntfy_server=server, cloudhook=False, cloudhook_url=None}, description="ntfy")`
    - Platzhalter `ntfy_publish_url`
  - **Reconfigure:**
    1. `data` analog aktualisieren.
    2. `async_schedule_reload`.
    3. Die Issues `webhook_token_rejected` und `ntfy_entity_missing` löschen.
    4. Hatte der Eintrag einen Cloudhook: ihn löschen (nach dem Update, Fehler nur als Typ
       loggen).
    5. `async_abort(reason="reconfigure_successful_ntfy", description_placeholders={"ntfy_publish_url": ...})`.
    - Hat sich nichts geändert (gleiche Quelle, gleiche UUID, gleiches Thema, keine
      Rückmelde-Änderung): `async_abort(reason="reconfigure_successful")` **ohne** Reload.

**Reconfigure (`async_step_reconfigure`):**

- Das Schema wird dynamisch gebaut:
  - `reply_url` (optional, wie bisher)
  - `alarm_source`: `SelectSelector(options=ALARM_SOURCES, translation_key="alarm_source")`,
    `default` = aktuelle Quelle
  - `regenerate_webhook` (bool): Bedeutung neu „neue geheime Adresse erzeugen“, für beide
    Quellen
- Nach Prüfung der Rückmelde-URL und der `unique_id` (wie heute) in `self` merken.
- Danach:
  - Ziel `ntfy` → `async_step_ntfy()` (Einrichtungsdialog). Mit `_regenerate` gibt es ein
    neues Thema.
  - Ziel `webhook`, und eine der Bedingungen gilt:
    - alte Quelle `ntfy`
    - `_regenerate` (neue ID und Token in `self`)
    - die aktuelle URL ist `internal`/`path_only`

    → `async_step_cloud()`. Die Einstiegsfrage entfällt im Reconfigure; das Feld
    `alarm_source` ersetzt sie.
  - Sonst wie heute: keine Änderung → Abort ohne Reload. Nur die Rückmelde-URL geändert →
    `async_update_reload_and_abort`.
- Der bisherige Fehler `cloud_not_connected` im Reconfigure-Formular entfällt (jetzt Menü).
  Der Schlüssel `config.error.cloud_not_connected` fällt weg.

**Options Flow:**

- `async_step_init`: Bei `alarm_source == "ntfy"` → `return await self.async_step_ntfy()`.
  Sonst das bisherige Formular.
  - Neu ist der Platzhalter `cloud_url` für den überarbeiteten Hinweis auf nicht erreichbare
    Adressen.
- `async_step_ntfy`:
  - Felder `reset_minutes`, `default_transport`, `location_entity`, **ohne**
    `require_token`
  - Beim Speichern bleibt ein vorhandenes `require_token` erhalten (`{**user_input,
    CONF_REQUIRE_TOKEN: options.get(CONF_REQUIRE_TOKEN, False)}`), damit es nach einem
    Wechsel zurück wieder gilt.
  - Platzhalter: `ntfy_entity` (aktuelle `entity_id` oder `–`) und `ntfy_publish_url`
    (aus `data`)

### Schritt 9: `diagnostics.py`

```python
{
  "entry": async_redact_data(entry.as_dict(), TO_REDACT),
  "alarm_source": source,
  "webhook": {...wie bisher...} if source == "webhook" else None,
  "ntfy": {
      "entity_found": bool, "entity_platform_ok": bool, "entity_disabled": bool | None,
      "entity_available": bool | None,   # State != unavailable
      "server": entry.data.get(CONF_NTFY_SERVER),
      **(runtime_data.source.as_diagnostics() if source läuft else {}),
  } if source == "ntfy" else None,
  "stats": ..., "alarm": ..., "reply": ...,
}
```

Nie enthalten: Thema, `entity_id`, UUID, Attributwerte. `entry.as_dict()` enthält die ntfy-
Schlüssel; sie werden über `TO_REDACT` redigiert.

### Schritt 10: Übersetzungen

Texte siehe Abschnitt „Texte“. Regeln:

- de und en mit identischen Schlüsseln (`test_translations_en_de_have_same_keys`)
- keine URLs (hassfest und `test_translations_contain_no_urls`), kein HTML, kein
  führendes/abschließendes Leerzeichen, keine Platzhalter in einfachen Anführungszeichen
- Keine Hersteller- oder Firmennamen von FF Agent. „Home Assistant Cloud“,
  „Home Assistant Link“ und „ntfy“ sind erlaubt.
- Preis nie nennen; nur „kostenpflichtig, zunächst kostenlos testbar“

### Schritt 11: Tests

Siehe „Teststrategie“. Das Abdeckungs-Gate (95 %) muss halten, Ziel bleibt 100 %.

### Schritt 12: Doku

- **README** (Aufbau siehe unten), **CHANGELOG** (Unreleased: „Alarm über ntfy“,
  „verständliche Hilfe, wenn Home Assistant nicht erreichbar ist“).
- **ADR 0002:** In der Statuszeile „ergänzt durch ADR 0003 (Alarmquelle)“. Abschnitt 3 und
  „Konsequenzen“ bekommen je einen Satz mit Verweis.
- **`docs/architektur.md`:**
  - Integrationsweg: zwei Quellen
  - Struktur: `ntfy_source.py`
  - Datenfluss: zweiter Eingang
  - Config-Eintrag: neue Schlüssel, `MINOR_VERSION` 2
  - Datenschutz: Thema und `entity_id`
  - HA-Fallstricke:
    - Semantik der ntfy-Event-Entität und Filterregel
    - Platzhalter-State `restored: true`
    - hassfest verbietet URLs in Übersetzungen
    - `async_show_menu` hat keine Vorauswahl
- **`docs/quality-scale.md`:** `repair-issues`, `reconfiguration-flow` und `diagnostics`
  um ntfy ergänzen.

README-Abschnitte:

1. **„Wie kommt der Alarm an?“** Empfehlung: Home Assistant Cloud, wenn vorhanden.
   Kostenlose Alternative: ntfy. Kurze Gegenüberstellung:

   | Weg | Kosten | Von außen erreichbar | Zusatz-Token | Dritter sieht Alarmzeitpunkte |
   |---|---|---|---|---|
   | Direkt (Webhook) | Home Assistant Cloud: Abo; eigene Adresse: eigener Aufwand | ja | ja | Home Assistant Cloud (bei Cloud-Nutzung) |
   | ntfy | kostenlos | nein | nein | ntfy.sh |

2. **„Weg A: Home Assistant Cloud oder eigene Adresse“**
   - My-Link, Anmeldung, „Erneut prüfen“
   - Hinweis auf die Umbenennung in „Home Assistant Link“
   - eigene Adresse unter Einstellungen > System > Netzwerk
   - DS-Lite-Satz aus der Recherche („Portfreigabe nicht möglich“)
3. **„Weg B: ntfy (kostenlos)“**, Schritt für Schritt:
   1. Integration ntfy hinzufügen: Dienstadresse unverändert, keine Anmeldung.
   2. „Thema hinzufügen“ → „Thema eingeben“, das angezeigte Thema einfügen, Anzeigename
      „FF Agent Alarm“.
   3. In FF Agent einen Generischen Webhook anlegen: Methode GET, URL
      `https://ntfy.sh/<thema>/trigger`, alles andere leer.
   4. In der FF-Agent-Einrichtung „Erledigt“ wählen. Die Integration sucht die Entität;
      nur wenn sie nichts findet, wählst du sie selbst aus.
   5. Mit einem Testalarm prüfen.

   Die Reihenfolge entspricht dem Einrichtungsdialog `ntfy`.
4. **„Datenschutz bei ntfy“:** der Text unten (README-Fassung), dazu ein Beispiel
   `recorder: exclude` für die ntfy-Entität (Platzhalter `event.ff_agent_alarm`).
5. **„Grenzen von ntfy“:**
   - Ein Alarm während einer Unterbrechung geht verloren, ntfy holt nichts nach.
   - ntfy.sh ist ein zusätzlicher Ausfallpunkt.
   - Bei sehr vielen gleichzeitigen Alarmen ist ein Ratenlimit möglich [U].
   - Kein Zusatz-Token: Wer Tore oder Türen schaltet, nimmt Weg A mit Token.
6. **Fehlerbehebung:** Repair „ntfy-Abo fehlt“, Entität „nicht verfügbar“, Wechsel des Wegs
   über „Neu konfigurieren“. Nach dem Wechsel den alten Webhook in FF Agent löschen.
7. **English summary** ergänzen (2–4 Sätze).

## Texte (Deutsch; Englisch sinngemäß)

Schreibweise in JSON: Zeilenumbrüche als `\n`. Platzhalter in `{}` füllt der Code. Links
nur als `[Text]({platzhalter})`. Wo unten nur „wie bisher“ steht, bleibt der Text.

### `config.step.user.description`

> Eine Einrichtung gehört zu genau einer Person. Es wird nichts an FF Agent gesendet. Im
> nächsten Schritt wählst du, wie der Alarm bei Home Assistant ankommt.

EN: One setup belongs to exactly one person. Nothing is sent to FF Agent. In the next step
you choose how the alarm reaches Home Assistant.

### `config.step.alarm_source` (Menü, kein Cloud-Abo erkannt)

- **title:** Nutzt du Home Assistant Cloud?
- **description:**

> Bei einem Alarm muss FF Agent deinem Home Assistant Bescheid geben. Am einfachsten geht
> das mit **Home Assistant Cloud** von Nabu Casa (neuer Name ab Dezember 2026: Home
> Assistant Link). Das ist ein kostenpflichtiges Abo, das du zunächst kostenlos testen
> kannst. Wähle „Ja“ auch, wenn du es jetzt einrichten möchtest. Die Einrichtung zeigt dir
> die Schritte.
>
> Ohne Home Assistant Cloud geht es kostenlos über den Dienst **ntfy**.
>
> Den Weg kannst du später unter „Neu konfigurieren“ wechseln.

- **menu_options.cloud:** Ja (empfohlen)
- **menu_options.no_cloud:** Nein

EN: title „Do you use Home Assistant Cloud?“; description: „When an alarm comes in, FF
Agent has to notify your Home Assistant. The easiest way is **Home Assistant Cloud** by
Nabu Casa (called Home Assistant Link from December 2026). It is a paid subscription that
you can try for free first. Choose ‚Yes‘ also if you want to set it up now; you will be
guided step by step. Without Home Assistant Cloud you can use the free service **ntfy**.
You can switch later under ‚Reconfigure‘.“; options „Yes (recommended)“, „No“.

### `config.step.alarm_source_cloud` (Menü, Cloud-Abo erkannt)

- **title:** Nutzt du Home Assistant Cloud?
- **description:**

> Home Assistant Cloud ist bei dir bereits aktiv. Wähle „Ja“, dann bekommst du sofort die
> Adresse für FF Agent.
>
> Möchtest du Home Assistant Cloud dafür nicht nutzen, wähle „Nein“. Dann geht es kostenlos
> über den Dienst ntfy.

- **menu_options.cloud:** Ja (empfohlen)
- **menu_options.no_cloud:** Nein

EN: „Home Assistant Cloud is already active on your system. Choose ‚Yes‘ to get the
address for FF Agent right away. If you don't want to use it for this, choose ‚No‘ to use
the free service ntfy.“

### `config.step.no_cloud` (Menü)

- **title:** Kostenlose Alternative: ntfy
- **description:**

> Kein Problem. Ohne Home Assistant Cloud kommt der Alarm über den kostenlosen Dienst
> **ntfy**: FF Agent schickt den Alarm dorthin, und Home Assistant holt ihn ab. Home
> Assistant muss dafür nicht von außen erreichbar sein. Du brauchst zusätzlich die
> Integration ntfy; die Einrichtung zeigt dir jeden Schritt.
>
> Der Dienst ntfy sieht, wann du alarmiert wirst, aber keine Einsatzdaten.
>
> Hast du eine eigene Internetadresse für Home Assistant (für Fortgeschrittene), kannst du
> stattdessen diese nutzen.

- **menu_options.ntfy:** Weiter mit ntfy (kostenlos)
- **menu_options.cloud:** Doch Home Assistant Cloud nutzen
- **menu_options.own_address:** Ich habe eine eigene Internetadresse (für Fortgeschrittene)

EN: title „Free alternative: ntfy“; options „Continue with ntfy (free)“, „Use Home
Assistant Cloud after all“, „I have my own internet address (advanced)“; description
analog.

### `config.step.cloud_setup` (Menü, Einrichtungsdialog Cloud)

- **title:** Home Assistant Cloud einrichten
- **description:**

> Dein Home Assistant ist von außen noch nicht erreichbar. FF Agent kann ihn bei einem
> Alarm deshalb noch nicht erreichen. So richtest du Home Assistant Cloud ein (neuer Name
> ab Dezember 2026: Home Assistant Link):
>
> 1. [Home Assistant Cloud öffnen]({cloud_url}). Der Link öffnet die Cloud-Seite deines
>    Home Assistant.
> 2. Ein Konto anlegen oder dich anmelden. Das Abo ist kostenpflichtig, du kannst es aber
>    zunächst kostenlos testen.
> 3. Warten, bis dort „Verbunden“ steht. Das kann ein bis zwei Minuten dauern.
> 4. Zurück in dieses Fenster und „Erneut prüfen“ wählen. Danach bekommst du die Adresse
>    und die Einstellungen für FF Agent.
>
> **Eigene Internetadresse?** Trage sie unter [Einstellungen > System > Netzwerk]({network_url})
> ein und wähle dann „Erneut prüfen“.
>
> Ohne Home Assistant Cloud geht es auch kostenlos über ntfy. Mit „Trotzdem fortfahren“
> funktionieren nur Zusagen und Absagen; den Alarm kannst du später unter „Neu
> konfigurieren“ nachrüsten.

- **menu_options.cloud:** Erneut prüfen
- **menu_options.ntfy:** Stattdessen ntfy nutzen (kostenlos)
- **menu_options.webhook_anyway:** Trotzdem fortfahren (nur Zusagen und Absagen, Alarm
  später nachrüsten)

EN: title „Set up Home Assistant Cloud“; Schritte „Open Home Assistant Cloud“, „Create an
account or sign in; paid subscription, free trial first“, „Wait until it says Connected
(may take a minute or two)“, „Come back and choose ‚Check again‘“; options „Check again“,
„Use ntfy instead (free)“, „Continue anyway (accept/decline only, add the alarm later)“.

### `config.step.cloud_setup_retry` (Menü)

- **title:** Noch nicht erreichbar
- **description:**

> Home Assistant ist weiterhin nur in deinem Heimnetz erreichbar. Prüfe bitte:
>
> 1. Bist du in [Home Assistant Cloud]({cloud_url}) angemeldet, und ist das Abo oder der
>    Test aktiv?
> 2. Steht dort „Verbunden“? Nach dem Anmelden kann das ein bis zwei Minuten dauern.
> 3. Oder, bei eigener Adresse: Steht unter [Netzwerk]({network_url}) eine Internetadresse,
>    die mit https beginnt?
>
> Danach „Erneut prüfen“ wählen. Du kannst auch den kostenlosen Weg über ntfy nehmen.

- **menu_options:** wie `cloud_setup`

### `config.step.cloud_not_connected` (Menü)

- **title:** Home Assistant Cloud ist nicht verbunden
- **description:**

> Home Assistant Cloud ist eingerichtet, aber gerade nicht verbunden.
>
> 1. [Home Assistant Cloud öffnen]({cloud_url}).
> 2. Prüfen, ob du angemeldet bist und dort „Verbunden“ steht.
> 3. Zurück in dieses Fenster und „Erneut versuchen“ wählen.

- **menu_options.cloud:** Erneut versuchen
- **menu_options.ntfy:** Stattdessen ntfy nutzen (kostenlos)

### `config.step.ntfy` (Menü, Einrichtungsdialog ntfy)

- **title:** Alarm über ntfy einrichten
- **description:**

> So kommt der Alarm über ntfy an. Öffne die Links am besten in einem neuen Tab und lass
> dieses Fenster offen.
>
> **1. Integration ntfy hinzufügen:** [ntfy hinzufügen]({ntfy_setup_url}). Die Dienstadresse
> lässt du unverändert, Benutzername und Passwort bleiben leer. Ist ntfy schon
> eingerichtet, öffne stattdessen [die Integration ntfy]({ntfy_integration_url}) und wähle
> „Thema hinzufügen“.
>
> **2. Dieses Thema abonnieren:** Wähle „Thema eingeben“ und trage ein:
>
> - Thema: `{ntfy_topic}`
> - Anzeigename: `FF Agent Alarm` (sonst erscheint das geheime Thema als Name)
>
> **3. In FF Agent eintragen:** Web-UI > Automatisierung > Persönliche Webhooks > Webhook
> hinzufügen:
>
> - Type: Alarm, Webhooktyp: Generischer Webhook
> - Methode: GET
> - URL: `{ntfy_publish_url}`
> - Aktiv: an; auch für Testalarme: an (zum Testen); auch für Infoalarme: aus; Zeitplan:
>   aus
> - Basis-Authentifizierung, Header, Inhalt und Query-Parameter: leer
>
> **4. Hier „Erledigt“ wählen.** Die Integration sucht dann die neue ntfy-Entität.
>
> Das Thema ist geheim wie ein Passwort. Wer es kennt, sieht deine Alarmzeitpunkte und kann
> falsche Alarme auslösen. Trage es nur in der Integration ntfy und in FF Agent ein.

- **menu_options.ntfy_find:** Erledigt, Entität suchen
- **menu_options.cloud:** Doch Home Assistant Cloud nutzen

EN: title „Set up the alarm through ntfy“; Schritte „Add the ntfy integration (keep the
service URL, leave username and password empty; if ntfy is already set up, open it and
choose ‚Add topic‘)“, „Subscribe to this topic: ‚Enter topic‘, Topic `{ntfy_topic}`,
Display name `FF Agent Alarm`“, „Enter in FF Agent: … Method GET, URL
`{ntfy_publish_url}` …“, „Choose ‚Done‘ here“; options „Done, find the entity“, „Use Home
Assistant Cloud after all“; Geheimnis-Satz analog.

### `config.step.ntfy_select` (Formular)

- **title:** ntfy-Entität auswählen
- **description:**

> Die Integration hat das ntfy-Abo für das Thema `{ntfy_topic}` noch nicht gefunden.
>
> 1. Prüfe in der [Integration ntfy]({ntfy_integration_url}), ob das Thema abonniert ist
>    (Schritt 2 im vorigen Dialog).
> 2. Warte ein paar Sekunden und wähle „Absenden“ mit leerem Feld. Die Integration sucht
>    dann erneut.
> 3. Oder wähle die Entität unten selbst aus, zum Beispiel ein Thema, das du schon
>    abonniert hast.

- **data.ntfy_entity:** ntfy-Entität
- **data_description.ntfy_entity:** Die Event-Entität des abonnierten Themas. Leer lassen,
  damit die Integration erneut über das Thema sucht.

EN: title „Choose the ntfy entity“; description analog; field „ntfy entity“, help „The
event entity of the subscribed topic. Leave empty to search again by topic.“

Anmerkung: Die deutschen Beschriftungen der ntfy-Integration („Thema hinzufügen“, „Thema
eingeben“, „Anzeigename“) sind aus den englischen Strings abgeleitet [A]. Der tester
gleicht sie mit der deutschen Übersetzung von HA 2026.3 ab und passt den Text an.

### `config.step.reconfigure`

- **description:**

> Hier kannst du die Rückmelde-URL ersetzen (zum Beispiel nach dem Neuerzeugen in FF Agent),
> den Weg für den Alarm wechseln oder eine neue geheime Adresse erzeugen. Lässt du alles
> unverändert, passiert nichts. Es wird nichts an FF Agent gesendet.
>
> Speichern lädt die Integration neu; ein gerade aktiver Alarm wird dabei zurückgesetzt.

- **data.alarm_source:** Weg für den Alarm
- **data_description.alarm_source:** Home Assistant Cloud bzw. eigene Internetadresse
  (empfohlen) oder der kostenlose Dienst ntfy. Beim Wechsel führt dich die Einrichtung
  Schritt für Schritt durch alles Nötige.
- **data.regenerate_webhook:** Neue geheime Adresse erzeugen
- **data_description.regenerate_webhook:** Erzeugt eine neue Adresse für FF Agent: beim
  direkten Weg eine neue Webhook-Adresse und ein neues Token, bei ntfy ein neues Thema. Die
  alte Adresse funktioniert danach nicht mehr; die neue musst du in FF Agent eintragen.
  Sinnvoll, wenn die Adresse bekannt geworden ist.

### `selector.alarm_source.options`

- **webhook:** Home Assistant Cloud oder eigene Internetadresse (empfohlen)
- **ntfy:** Kostenloser Dienst ntfy

(Die gespeicherten Werte bleiben `webhook` und `ntfy`. Nur die Beschriftung folgt der
neuen Einstiegsfrage.)

### `config.error` (neu)

- **ntfy_not_set_up:** Die Integration ntfy ist noch nicht eingerichtet. Richte sie zuerst
  ein (Schritt 1 im vorigen Dialog) und versuche es dann erneut.
- **ntfy_entity_not_found:** Kein ntfy-Abo mit diesem Thema gefunden. Prüfe Schritt 2 und
  versuche es nach einigen Sekunden erneut, oder wähle die Entität selbst aus.
- **ntfy_entity_invalid:** Diese Entität ist keine aktive Event-Entität der Integration ntfy.
  Wähle die Entität eines ntfy-Themas.
- **ntfy_entity_in_use:** Diese ntfy-Entität nutzt schon eine andere FF-Agent-Einrichtung.
  Jede Person braucht ein eigenes Thema.

`cloud_not_connected` entfällt. `unknown` wandert nach `config.abort.unknown` (Text wie
bisher).

### `config.create_entry`

- **cloud** (geändert: nummerierte Schritte):

> Geschafft: Home Assistant ist über Home Assistant Cloud erreichbar. Jetzt nur noch FF
> Agent einrichten:
>
> 1. FF Agent im Browser öffnen: Web-UI > Automatisierung > Persönliche Webhooks > Webhook
>    hinzufügen.
> 2. Type: Alarm, Webhooktyp: Generischer Webhook.
> 3. Methode: POST.
> 4. URL: `{webhook_url}`
> 5. Aktiv: an; auch für Testalarme: an (zum Testen; Automationen laufen dann auch bei
>    Testalarmen); auch für Infoalarme: aus; Zeitplan aktiviert: aus.
> 6. Basis-Authentifizierung, Inhalt und Query-Parameter leer lassen, speichern.
> 7. Mit einem Testalarm prüfen: In Home Assistant springt „Alarm aktiv“ an.
>
> Die URL ist ein Geheimnis. Trage sie nur in FF Agent ein.

- **external:** wie `cloud`, erster Satz: „Geschafft: Home Assistant ist über deine eigene
  Internetadresse erreichbar. Jetzt nur noch FF Agent einrichten:“
- **internal** (Abschluss nach „Trotzdem fortfahren“):

> **Gespeichert. Zusagen und Absagen funktionieren, Alarme kommen aber noch nicht an.**
> Dein Home Assistant ist nur in deinem Heimnetz erreichbar (`{webhook_url}`), FF Agent
> sitzt im Internet.
>
> So rüstest du den Alarm später nach:
>
> 1. [Home Assistant Cloud]({cloud_url}) einrichten (neuer Name ab Dezember 2026: Home
>    Assistant Link) oder eine eigene Internetadresse eintragen.
> 2. Bei dieser Einrichtung „Neu konfigurieren“ öffnen und speichern. Du bekommst dann die
>    Adresse und die Einstellungen für FF Agent.
>
> Oder wähle unter „Neu konfigurieren“ den kostenlosen Weg über ntfy.
>
> Lege den Webhook in FF Agent erst an, wenn du die neue Adresse hast.

- **path_only:** wie `internal`, erster Absatz: „**Gespeichert. Zusagen und Absagen
  funktionieren, Alarme kommen aber noch nicht an.** Home Assistant kennt noch keine
  eigene Adresse, nur den Pfad `{webhook_url}`. …“
- **ntfy** (neu): Die FF-Agent-Werte standen schon im Einrichtungsdialog. Der Abschluss
  bestätigt sie mit der Server-Adresse des tatsächlichen Abos.

> Geschafft: Die ntfy-Entität ist gefunden, die Einrichtung ist abgeschlossen.
>
> Prüfe, ob der Webhook in FF Agent (Web-UI > Automatisierung > Persönliche Webhooks) genau
> diese Werte hat, und lege ihn sonst jetzt an:
>
> - Type: Alarm
> - Webhooktyp: Generischer Webhook
> - Methode: GET
> - URL: `{ntfy_publish_url}`
> - Aktiv: an
> - auch für Testalarme: an (zum Testen; Automationen laufen dann auch bei Testalarmen)
> - auch für Infoalarme: aus
> - Zeitplan aktiviert: aus
> - Basis-Authentifizierung, Header, Inhalt und Query-Parameter: leer
>
> Die URL enthält dein geheimes Thema. Trage sie nur in FF Agent ein.
>
> **Gut zu wissen:** Der Dienst ntfy sieht, wann du alarmiert wirst, aber keine
> Einsatzdaten. Ist Home Assistant oder die Internetverbindung beim Alarm gerade weg, geht
> der Alarm verloren, denn ntfy liefert ihn nicht nach.

### `config.abort` (neu bzw. geändert)

- **reconfigure_successful_ntfy:**

> Der Alarm kommt jetzt über ntfy. Trage in FF Agent (Web-UI > Automatisierung > Persönliche
> Webhooks) diese Adresse ein: Methode GET, URL `{ntfy_publish_url}`, Basis-Authentifizierung,
> Header, Inhalt und Query-Parameter leer.
>
> Einen bisherigen Webhook, der direkt auf Home Assistant zeigt, löschst du in FF Agent; er
> funktioniert nicht mehr.
>
> Die Integration wird neu geladen; ein gerade aktiver Alarm wird dabei zurückgesetzt.

- **reconfigure_successful_new_webhook:** Der erste Satz lautet „Der Alarm kommt direkt über
  das Internet.“, dann der bisherige Text. Der vorletzte Absatz („Ist die Adresse nur eine
  interne …“) wird ersetzt durch:

> Hast du vorher ntfy genutzt, lösche in FF Agent den Webhook mit der ntfy-Adresse.

- **unknown:** Text des bisherigen `config.error.unknown`.

### `options.step.init.description` (Webhook)

Den Absatz „Ist die Art `internal` oder `path_only` …“ ersetzen durch:

> Steht oben bei der Art `internal` oder `path_only`, erreicht FF Agent die Adresse nicht.
> Richte [Home Assistant Cloud]({cloud_url}) ein und öffne dann „Neu konfigurieren“, oder
> wechsle dort zum kostenlosen Weg über ntfy.

### `options.step.ntfy` (neu)

- **title:** FF Agent: Optionen
- **description:**

> **Alarm über ntfy**
>
> - Entität: `{ntfy_entity}`
> - Adresse für FF Agent: `{ntfy_publish_url}` (Methode GET)
>
> In FF Agent (Web-UI > Automatisierung > Persönliche Webhooks) gelten diese Werte: Type
> Alarm, Webhooktyp Generischer Webhook, Methode GET, die Adresse von oben, Aktiv an,
> Zeitplan aus, Basis-Authentifizierung, Header, Inhalt und Query-Parameter leer.
>
> Ein Zusatz-Token gibt es bei ntfy nicht. Das Thema in der Adresse ist der einzige Schutz:
> Gib es niemandem weiter und teile keine Screenshots dieser Seite. Weg, Entität oder Thema
> änderst du unter „Neu konfigurieren“.
>
> **Speichern lädt die Integration neu; ein gerade aktiver Alarm wird dabei zurückgesetzt.**

- **data/data_description:** `reset_minutes`, `default_transport` und `location_entity`
  wie in `init`.

### `issues.ntfy_entity_missing` (neu)

- **title:** FF Agent: ntfy-Abo für den Alarm fehlt
- **description:**

> Die Einrichtung „{title}“ empfängt Alarme über ntfy, findet aber die ntfy-Entität nicht
> mehr, oder sie ist deaktiviert. Solange kommen keine Alarme an; Zusagen und Absagen
> funktionieren weiter.
>
> Abonniere das Thema in der Integration ntfy erneut, oder wähle unter „Neu konfigurieren“
> dieser Einrichtung eine vorhandene ntfy-Entität bzw. den direkten Weg über das Internet.
>
> Der Hinweis verschwindet, sobald die Einrichtung wieder eine gültige Entität hat.

### README: Datenschutz bei ntfy (Vorschlag)

> **Datenschutz bei ntfy.** Jeder Alarm läuft über den Dienst ntfy.sh. Dessen Betreiber
> sieht, wann ein Alarm kommt, und speichert die Meldung bis zu 12 Stunden. Einsatzdaten
> werden nicht übertragen, solange in FF Agent unter „Inhalt“ und „Query-Parameter“ nichts
> eingetragen ist. Das Thema wirkt wie ein Passwort: Wer es kennt, sieht deine
> Alarmzeitpunkte und kann falsche Alarme auslösen. Halte es geheim und teile keine
> Screenshots der Einrichtung. Die Integration ntfy speichert Thema und Meldung im Verlauf
> von Home Assistant und damit auch in Backups. Wer das nicht möchte, schließt ihre Entität
> vom Recorder aus.

## Teststrategie

Grundsatz: **keine echte ntfy-Verbindung.** Die ntfy-Integration wird in Tests nie geladen.
Simuliert werden ihr Config-Eintrag samt Subentry, ihr Registry-Eintrag und ihr State.

Fixtures in `tests/conftest.py` bzw. `tests/common.py` (nur Platzhalter):

- `NTFY_TOPIC = "0123456789abcdef0123456789abcdef"`, `NTFY_ENTITY_ID = "event.ff_agent_alarm"`
  in `tests/const.py`
- `ntfy_config_entry`:
  - `MockConfigEntry(domain="ntfy", data={"url": "https://ntfy.sh/"}, subentries_data=[ConfigSubentryData(subentry_type="topic", data={"topic": NTFY_TOPIC}, title="FF Agent Alarm", unique_id=NTFY_TOPIC, subentry_id="<platzhalter>")])`
  - mit `add_to_hass`, **ohne** Setup
- `ntfy_entity`: `er.async_get(hass).async_get_or_create("event", "ntfy", "<uid>", config_entry=ntfy_config_entry, config_subentry_id="<platzhalter>", suggested_object_id="ff_agent_alarm")`
- `ntfy_entry`: FF-Agent-Eintrag mit `alarm_source="ntfy"` und `ntfy_entity_uuid` der
  Fixture
- Helfer `fire_ntfy(hass, ts=None, attrs=None)`:
  - `hass.states.async_set(NTFY_ENTITY_ID, ts.isoformat(timespec="milliseconds"), {"event_type": "triggered", "message": "triggered", "topic": NTFY_TOPIC, **attrs})`
  - Zeit über `freezer`

**`test_ntfy_source.py`** (Listener, je ein Test):

| Fall | Erwartung |
|---|---|
| `ts1` → `ts2` (frisch) | genau 1 Alarm; Event-Entität und `binary_sensor` an |
| `None` → `ts_alt` (hinzugefügt) | kein Alarm, Basiswert gesetzt |
| Platzhalter `unavailable` + `restored: true` → `ts_alt` | kein Alarm |
| Platzhalter `restored: true` → `ts_frisch` (Restore direkt nach Alarm) | kein Alarm |
| `ts1` → `unavailable` → `ts1` | kein Alarm (`ignored_duplicate`) |
| `ts1` → `unavailable` → `ts_neu` frisch (10-s-Fenster) | 1 Alarm |
| `unknown` → `ts` frisch (erstes Abo) | 1 Alarm |
| `unavailable` → `ts_alt` (> 60 s) ohne Basiswert | kein Alarm (`ignored_stale`) |
| `unavailable` → `ts` 30 s alt ohne Basiswert | 1 Alarm (festgeschriebenes Rest-Risiko) |
| State gleich, nur Attribute geändert | kein Alarm |
| ungültiger State (`"abc"`) | kein Alarm, keine Exception |
| Zeitstempel in der Zukunft | 1 Alarm |
| zwei Meldungen innerhalb von 30 s | 1 Alarm, 1 dedupliziert (AlarmManager) |
| Start mit gültigem State, dann gleicher State erneut geschrieben | kein Alarm |
| Unload: danach `fire_ntfy` | kein Alarm, kein Listener übrig |
| Registry `remove` | Issue `ntfy_entity_missing` angelegt, kein Alarm mehr |
| Registry `update` `entity_id` (Umbenennung) | Reload geplant; danach Alarm über die neue `entity_id` |
| Registry `update` nur `capabilities` | kein Reload |
| Setup mit unbekannter UUID / falscher Plattform / deaktiviert | Issue, Setup `LOADED`, Buttons funktionieren |
| Setup danach mit gültiger Entität | Issue gelöscht |
| ntfy-Modus | `webhook.async_register` nicht aufgerufen; POST auf `/api/webhook/<id>` erzeugt keinen Alarm |
| Fehlende/anders typisierte Attribute (`message` als Zahl, `tags` fehlt) | Form `None`/`False`, keine Exception |

**`test_ntfy_source.py`** (Suche):

- `async_find_subscription_by_topic` findet über Subentry und Registry.
- kein ntfy-Eintrag, anderes Thema, falscher Subentry-Typ, Entität deaktiviert →
  jeweils `None`
- `async_describe_entity` liest Thema und Server
- fehlende Subentry → `topic=None`, keine Exception
- `ntfy_publish_url` mit und ohne abschließenden Schrägstrich, `None` → ntfy.sh

**`test_ntfy_contract.py`:** Prüft den installierten Core-Quellcode per `ast`, ohne ihn zu
importieren (Muster `test_cloud_contract.py`).

- `components/ntfy/const.py`:
  - `DOMAIN == "ntfy"`, `SUBENTRY_TYPE_TOPIC == "topic"`, `CONF_TOPIC == "topic"`
  - `DEFAULT_URL` beginnt mit `https://ntfy.sh`
- `components/ntfy/event.py`:
  - Klasse mit Basis `EventEntity`
  - `async_setup_entry` übergibt `config_subentry_id`
  - `RECONNECT_INTERVAL` existiert
- `components/ntfy/config_flow.py` speichert `CONF_URL`.
- `helpers/entity_registry.py`: `async_resolve_entity_id` existiert.
- `ATTR_RESTORED == "restored"` in `homeassistant.const`.

**`test_config_flow.py`** (neu bzw. angepasst):

- Einstiegsfrage:
  - ohne Cloud-Abo: `user` → Menü `alarm_source` (`FlowResultType.MENU`), Optionen genau
    `["cloud", "no_cloud"]` in dieser Reihenfolge
  - mit Cloud-Abo (`patch_cloud`): Menü `alarm_source_cloud`, gleiche Optionen. Es wird
    **kein** Cloudhook erzeugt, solange der Nutzer nichts gewählt hat (kein automatisches
    Weiterspringen).
- `no_cloud` → Menü `no_cloud` mit `["ntfy", "cloud", "own_address"]`. Jede Option führt in
  den erwarteten Schritt.
- Cloud-Pfad (`cloud`, ebenso `own_address`):
  - mit Cloud → `create_entry` `cloud`, `data.alarm_source == "webhook"`, ntfy-Felder `None`
  - mit externer URL → `external`. Das gilt auch über `own_address`, und auch bei „Ja“ ohne
    Cloud-Abo.
  - Cloud-Abo aktiv, nicht verbunden → Menü `cloud_not_connected` → nach Verbinden „Erneut
    versuchen“ (`cloud`) → `cloud`
  - unerreichbar → Menü `cloud_setup`, zweites Prüfen → `cloud_setup_retry`, nach
    `external_url` → `external`
  - `webhook_anyway` → `internal` bzw. `path_only`
  - aus `cloud_setup` die Option `ntfy` → Menü `ntfy`
  - unerwartete Exception → Abort `unknown`, Log nur mit Typname
- ntfy-Pfad:
  - Menü `ntfy` mit `["ntfy_find", "cloud"]`
    - Platzhalter: 32-stelliges Hex-Thema und `ntfy_publish_url ==
      "https://ntfy.sh/<thema>/trigger"`
    - mit genau einem ntfy-Eintrag mit eigener `url`: Publish-URL mit diesem Server
  - erneutes Anzeigen (z. B. `ntfy` → `cloud` → `cloud_setup` → `ntfy`) behält das Thema
  - `cloud` aus dem Menü `ntfy` → Cloud-Pfad
  - `ntfy_find`:
    - ohne ntfy-Eintrag → Formular `ntfy_select` mit `ntfy_not_set_up`
    - Eintrag ohne Treffer → `ntfy_select` mit `ntfy_entity_not_found`
    - Treffer → `create_entry` `ntfy`
  - `ntfy_select`:
    - leer abgesendet, inzwischen gibt es das Abo → `create_entry` `ntfy`
    - leer, weiter nichts → derselbe Fehler, gleiches Thema
    - fremde Domain oder Plattform → `ntfy_entity_invalid`
    - anderes, vorhandenes Thema → gespeichertes Thema = das der Entität
  - Entität schon bei anderem Eintrag → `ntfy_entity_in_use`, sowohl über `ntfy_find` als
    auch über `ntfy_select`
  - kein Cloudhook erzeugt (`patch_cloud`-Mock nicht aufgerufen)
- Wechsel: `no_cloud` → `ntfy` → `cloud` → `cloud_setup` → `ntfy` → `ntfy_find` → Eintrag
  (beide Richtungen in einem Flow)
- Alle Menüs und Formulare liefern die benötigten `description_placeholders`. Der Test
  vergleicht die Platzhalter im Text mit den gelieferten Schlüsseln, für jede Step-ID.
- doppelte Rückmelde-URL → Abort vor dem Menü

**`test_reconfigure.py`:**

- Webhook → ntfy:
  - Daten umgestellt
  - Cloudhook gelöscht (Mock)
  - Token-Issue gelöscht
  - Abort `reconfigure_successful_ntfy` mit URL
  - Reload
- ntfy → Webhook:
  - mit Cloud → Abort `reconfigure_successful_new_webhook`; `webhook_id` unverändert ohne
    `regenerate`, neu mit `regenerate`
  - unerreichbar → Menüs `cloud_setup`/`cloud_setup_retry` wie bei der Einrichtung, ohne
    Einstiegsfrage
- ntfy → ntfy ohne Änderung → `reconfigure_successful` ohne Reload; mit
  `regenerate_webhook` → neues Thema im Menü `ntfy`
- Webhook `internal` → Webhook nach Einrichten der Cloud (ohne `regenerate`) → Cloudhook
  für die bestehende ID
- Bestehende Tests (Rückmelde-URL, `already_configured`, Regenerate) bleiben grün und
  werden auf das neue Feld `alarm_source` angepasst.

**`test_options_flow.py`:**

- Im ntfy-Modus zeigt `init` den Schritt `ntfy` ohne `require_token`.
- Speichern erhält ein gesetztes `require_token`.
- Platzhalter `ntfy_entity` und `ntfy_publish_url` sind vorhanden; Entität fehlt → `–`.
- Webhook-Modus unverändert plus `cloud_url`.

**Migration** (`test_migration.py`):

- 1.1-Eintrag → nach Setup `minor_version == 2`, `alarm_source == "webhook"`, ntfy-Felder
  `None`, sonst unverändert, Webhook registriert
- `version=2` → Setup `MIGRATION_ERROR`
- 1.2-Eintrag bleibt unverändert

**`test_diagnostics.py`:**

- ntfy-Modus:
  - `alarm_source == "ntfy"`, `webhook is None`
  - `ntfy`-Block mit Zählern und `last_event`-Form
  - Thema, `entity_id` und UUID nicht im JSON (String-Suche über das ganze Ergebnis)
- Webhook-Modus: `ntfy is None`

**`test_privacy.py` / `test_privacy_lifecycle.py`:** Den ganzen Lebenszyklus im ntfy-Modus
durchlaufen: Setup, Meldung, Reload, Reconfigure, Diagnose, Remove. Prüfen:

- Thema und `NTFY_ENTITY_ID` nicht in `caplog` (Level DEBUG)
- nicht in Attributen der eigenen Entitäten
- nicht in Issue-Platzhaltern

**`test_metadata.py`:**

- erwartete Schlüssel um die neuen Steps, Menüs, Fehler, Aborts, `create_entry.ntfy`,
  `selector.alarm_source` und `issues.ntfy_entity_missing` erweitern
- `config.error.cloud_not_connected` aus der Erwartung nehmen
- `create_entry.ntfy` und `config.step.ntfy.description` enthalten `{ntfy_publish_url}`;
  `internal`/`path_only` enthalten `{cloud_url}` und „Neu konfigurieren“
- `config.step.alarm_source.menu_options.cloud` und `alarm_source_cloud.menu_options.cloud`
  enthalten „(empfohlen)“ bzw. „(recommended)“
- `cloud_setup.description` und `ntfy.description` enthalten nummerierte Schritte (Zeilen
  mit `1.`, `2.` bzw. `**1.`)
- Platzhalter-Vollständigkeit als Tabelle im Test: Step-ID → erwartete Platzhalter. Jeder
  `{name}` im Text muss in der Liste stehen, die der Flow liefert.
- Kein Text enthält den Firmennamen des Herstellers (Prüfung in `tests/test_metadata.py`).

**`test_alarm.py`:** Für `async_handle_alarm` direkt: Rückgabewert, Verhalten nach
`async_shutdown`. Die bestehenden Webhook-Tests unverändert.

**`test_webhook_url.py`:** `async_probe_reachability` für Cloud aktiv (verbunden und nicht
verbunden), extern, keins, Cloud nicht geladen. Erzeugt nichts (Mock nicht aufgerufen).

## Risiken

| Risiko | Wirkung | Gegenmaßnahme |
|---|---|---|
| Verlorene Alarme im ntfy-Modus bei Verbindungsabbruch oder Neustart (kein `since`) | Alarm kommt nicht an | README ehrlich; Webhook-Weg als zuverlässigere Wahl; Folge-TODO Diagnose-Sensor „Alarmweg verbunden“; eigener Client nur, wenn es in der Praxis auftritt |
| Kopplung an Interna der ntfy-Integration (Subentry-Schlüssel, Event-Semantik) | Suche oder Filter bricht nach einem HA-Update | Vertragstest; die manuelle Auswahl bleibt als Rückfall; Filter hängt nur an `EventEntity`-Semantik |
| Ratenlimit von ntfy.sh bei geteilten Absender-IPs (N3, [U]) | 429, Alarm geht verloren | README; Frage an den Hersteller; eigener ntfy-Server möglich (Server wird aus dem ntfy-Eintrag gelesen) |
| Viele Verzweigungen in Flow und Reconfigure | Fehler in seltenen Pfaden | gemeinsame Schritte und Finish-Helfer; Testmatrix oben; Review-Fokus auf `self.source`-Zweige und Platzhalter |
| Konflikte mit PR #4 | Mehraufwand beim Rebase | #4 zuerst mergen; Übersetzungen am Ende des PR einmal komplett gegen `main` abgleichen |
| hassfest lehnt URLs in Übersetzungen ab | CI rot | nur Platzhalter; bestehender Test `test_translations_contain_no_urls` |
| My-Link-Parameter `?domain=ntfy` (N6) oder Verhalten der Links im Dialog (N7) anders als angenommen | Nutzer findet die ntfy-Einrichtung nicht | Text nennt zusätzlich den Weg über Einstellungen; im ersten echten Test prüfen |
| Thema in `entity_id`/Gerätename, wenn der Nutzer keinen Anzeigenamen setzt | Geheimnis in UI, Logs anderer Integrationen, Screenshots | Anleitung verlangt Anzeigenamen; unsere Logs und Diagnose nennen die `entity_id` nie |
| Platzhalter `restored: true` beim Entladen ist nur [A] | Doppelalarm nach ntfy-Reload innerhalb 60 s | Regel 5 fängt ältere Werte ab; Rest-Risiko dokumentiert und per Test festgeschrieben |
| Mehr Dialoge bis zum Ziel (Frage, ggf. `no_cloud`, Einrichtungsdialog, Abschluss) | Laien brechen ab | Jeder Dialog hat eine Aufgabe und nummerierte Schritte; der Cloud-Pfad mit aktivem Abo braucht nur Frage und Abschluss |
| Nutzer antwortet „Ja“, hat aber weder Cloud noch Lust auf ein Abo | Landet im Einrichtungsdialog Cloud | Dort ist „Stattdessen ntfy nutzen“ direkt erreichbar |
| Technikaffine mit eigener Adresse antworten „Nein“ | Würden ungewollt zu ntfy geschickt | Option „eigene Internetadresse“ in `no_cloud`; zudem erkennt „Ja“ eine externe URL ohne Abo |
| Der Nutzer trägt die ntfy-URL in FF Agent ein, bevor das Abo existiert | Testalarm geht ins Leere, ntfy holt nichts nach | Reihenfolge im Dialog (erst abonnieren, dann FF Agent); Testalarm erst nach „Geschafft“ |
| Im Formular `ntfy_select` gibt es keinen Pfadwechsel | Nutzer steckt fest, wenn er doch Cloud will | Wechsel ist im Menü `ntfy` direkt davor möglich; Dialog schließen und neu starten |
| Server im Einrichtungsdialog weicht vom späteren Abo ab (eigener ntfy-Server, mehrere ntfy-Einträge) | Falsche URL in FF Agent | Der Abschluss `ntfy` zeigt die URL des tatsächlichen Abos und bittet um Abgleich |
| Nutzer wechselt die Quelle, lässt aber den alten Webhook in FF Agent | Unnötige Aufrufe; HA loggt WARNING mit Webhook-ID für unregistrierte Webhooks; ntfy sieht weiter Zeitpunkte | Abschlusstexte fordern zum Löschen auf |

## Definition of Done

- [ ] Alle Schritte 1–12 umgesetzt, auf PR #4 aufbauend, Branch `feat/261017-ux-erreichbarkeit`.
- [ ] Einrichtung: Nach der Rückmelde-URL kommt die Frage „Nutzt du Home Assistant Cloud?“
      mit „Ja (empfohlen)“ und „Nein“. Ein erkanntes Abo ändert nur den Text.
      - „Nein“ führt über den ntfy-Hinweis (`no_cloud`) in den ntfy-Pfad; „Doch Cloud“
        und „eigene Adresse“ bleiben wählbar.
      - Cloud-Pfad ohne Sackgasse: Einrichtungsdialog mit nummerierten Schritten und
        My-Link, „Erneut prüfen“, „Stattdessen ntfy“, „Trotzdem fortfahren“. Die externe
        URL wird erkannt.
      - ntfy-Pfad: Einrichtungsdialog mit nummerierten Schritten, erzeugtem Thema und
        FF-Agent-URL (GET `/trigger`), dann Suche und bei Bedarf manuelle Auswahl.
      - Wechsel zwischen den Pfaden in beide Richtungen möglich.
- [ ] Reconfigure wechselt die Quelle in beide Richtungen. Cloudhook und Issues werden
      aufgeräumt.
- [ ] Options-Dialog je Quelle; im ntfy-Modus kein Token-Schalter.
- [ ] Laufzeit: Filterregel 1–6 aus ADR 0003; Dedup über den `AlarmManager`; kein Webhook
      im ntfy-Modus; Repair-Issue `ntfy_entity_missing`; Registry-Listener.
- [ ] Migration 1.1 → 1.2 getestet. `manifest.json` unverändert (Version, Abhängigkeiten).
- [ ] Diagnostics mit `alarm_source` und ntfy-Block. Thema, `entity_id` und UUID nicht
      enthalten (Test).
- [ ] Texte de/en nach Abschnitt „Texte“. Keine URL in Übersetzungen, kein Preis, kein
      Hersteller- oder Firmenname von FF Agent.
- [ ] Tests nach „Teststrategie“; CI grün (ruff, pytest, hassfest, HACS); Abdeckung ≥ 95 %,
      Ziel 100 %.
- [ ] README (Abschnitte 1–7), CHANGELOG, ADR 0002 (Verweis), `docs/architektur.md` und
      `docs/quality-scale.md` aktualisiert.
- [ ] tester PASS, reviewer „freigegeben“, **Merge erst nach dem Okay des Nutzers**.

## Folge-TODOs (Vorschlag für den Projektleiter)

- `ntfy-verbindungssensor`: Diagnose-Binärsensor „Alarmweg verbunden“ (Connectivity,
  `entity_category: diagnostic`). Im ntfy-Modus spiegelt er die Verfügbarkeit der
  ntfy-Entität, im Webhook-Modus bei Cloud `cloud.async_is_connected`. Optional mit
  Repair-Issue nach X Minuten ohne Verbindung.
- `ntfy-echter-test` (braucht die Freigabe des Nutzers): Annahmen N1–N3, N6, N7 und N10
  aus ADR 0003 prüfen. Dazu GET an ntfy.sh aus FF Agent, Laufzeit, Diagnoseform der Meldung
  und die deutschen Labels der ntfy-Integration.
- `link-umbenennung`: Nach dem 2. Dezember 2026 prüfen, ob `redirect/cloud/` und die Texte
  zu „Home Assistant Link“ noch stimmen (N8).
- Bei Bedarf `ntfy-komfort`: Abo programmatisch anlegen (ADR 0003, Alternativen). Nur auf
  Wunsch des Nutzers.
