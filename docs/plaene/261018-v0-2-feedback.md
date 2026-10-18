# Plan 261018: Rückmeldungen zu v0.2.0 (sieben Punkte, ein PR)

> **Entscheidungen des Nutzers (2026-10-18), siehe „Offene Fragen“:** Punkt 6 entfällt, die
> Button-Namen bleiben „Zusagen“/„Absagen“. Der Reset-Button heißt „Alarm zurücksetzen“ und
> darf auf der Geräteseite zuerst stehen. Der Standort im Einrichtungsschritt bleibt wie in
> den Optionen (Person und Geräte-Tracker), keine Zonen. Umgesetzt sind damit die Punkte 1–5
> und 7.

- **Branch/PR:** `feat/261018-v0-2-feedback`, ein PR, Squash-Merge nach Gate.
- **TODOs:** 261018-leere-dialogtexte, -reconfig-alarmquelle-text, -ntfy-abschluss-redundant,
  -geraet-ohne-link, -einrichtung-zusage-optionen, -reihenfolge-zusage, -alarm-reset.
- **Quality Scale:** Ziel bleibt **Bronze** mit den ausgewählten Silber/Gold-Regeln
  (`docs/quality-scale.md`). Betroffen: `action-setup`, `action-exceptions`,
  `docs-actions`, `config-flow` (jedes neue Feld bekommt `data_description`),
  `entity-translations`, `icon-translations`. Kein Rückschritt.
- **Kein Versionssprung** in `manifest.json`; CHANGELOG nur unter `[Unreleased]`.

## Nicht-Ziele

- Keine feste Adresse als Text und keine festen Koordinaten in den Optionen (siehe offene
  Frage 2, Zone).
- Kein neuer Diagnose-Zähler für manuelle Rücksetzungen.
- Keine Änderung an Entity-IDs, Unique-IDs, `VERSION`/`MINOR_VERSION` des Config-Eintrags.
- Die Aktionsnamen `ff_agent.accept`/`ff_agent.reject` und ihre Übersetzungen
  („Zusagen“/„Absagen“) bleiben unverändert.
- Kein Refactoring von `config_flow.py` (eigenes TODO 261018-configflow-aufteilen).

## Randbedingungen für alle Punkte

- Übersetzungen: Es gibt nur `translations/de.json` und `translations/en.json`, kein
  `strings.json`. hassfest prüft bei Custom-Integrationen `en.json` (Schema, keine URLs,
  Schlüssel klein mit Unterstrich). Dass de und en **dieselben Schlüssel** haben, verlangt
  nur unser Test `test_translations_en_de_have_same_keys`. Also jeden Schlüssel immer in
  beiden Dateien anlegen oder entfernen.
- Keine URL in Übersetzungen (hassfest und `test_translations_contain_no_urls`), kein
  `€`/`$`/`eur ` (`test_texts_name_no_vendor_and_no_price`), kein Firmenname.
- Neue Platzhalter in `config.*` müssen in `test_every_step_text_has_its_placeholders_in_the_flow`
  (Menge `delivered`) enthalten sein. Dieser Plan führt keinen neuen Platzhalter ein.
- Lokal gibt es kein Python. Tests, ruff und hassfest laufen nur in GitHub Actions; nach
  jedem Push den Lauf prüfen.

---

## 1. Kein Link in der Geräte-Info (261018-geraet-ohne-link)

**Wichtiger Fallstrick:** Lässt man `configuration_url` in `DeviceInfo` einfach weg, behalten
**bestehende** Geräte den gespeicherten Link. `DeviceRegistry.async_get_or_create` hat für
`configuration_url` den Standard `UNDEFINED` und übernimmt nur Werte, die nicht `UNDEFINED`
sind (`homeassistant/helpers/device_registry.py`, `_async_update_device`:
`if value is not UNDEFINED and value != getattr(old, attr_name)`). `DeviceInfo.as_dict()`
lässt nur `UNDEFINED`-Felder weg, ein explizites `None` wird übertragen und löscht den Wert.

**Änderungen**
- `entity.py`: In `DeviceInfo(...)` `configuration_url=None` setzen, mit Kommentar
  „explicit None clears the link of devices created by earlier versions“. Import
  `CONFIGURATION_URL` entfernen.
- `const.py`: `CONFIGURATION_URL` löschen (wird sonst nirgends genutzt).

**Tests** (`tests/test_entities.py`)
- `test_entities_belong_to_one_service_device`: `assert device.configuration_url is None`.
- Neu `test_an_old_configuration_url_is_removed`: Vor dem Setup das Gerät der Entry mit
  `dr.async_get(hass).async_get_or_create(config_entry_id=..., identifiers={(DOMAIN, entry_id)},
  configuration_url="https://www.ff-agent.com")` anlegen. Nach dem Setup ist
  `configuration_url is None`.

**Risiko:** gering.

---

## 2. Alarmquelle in der Neukonfiguration als Frage (261018-reconfig-alarmquelle-text)

**Verwendung des Selectors geprüft:** `selector.alarm_source` wird nur von
`ALARM_SOURCE_SELECTOR` genutzt, und der kommt nur in `_reconfigure_schema` vor. Die
Einrichtung nutzt Menüs mit eigenen Texten (`menu_options`). Die neuen Optionstexte wirken
also nur in der Neukonfiguration. Sie müssen weiter „(empfohlen)“/„(recommended)“ enthalten
(`test_cloud_is_recommended_in_the_first_question`).

**Änderungen nur in `translations/*.json`**

| Schlüssel | de | en |
|---|---|---|
| `config.step.reconfigure.data.alarm_source` | `Wie bekommt Home Assistant den Alarm?` | `How does Home Assistant receive the alarm?` |
| `config.step.reconfigure.data_description.alarm_source` | `Wechselst du den Weg, führt dich die Einrichtung Schritt für Schritt durch alles Nötige. Den alten Webhook in FF Agent löschst du danach.` | `If you switch, the setup guides you step by step. Afterwards delete the old webhook in FF Agent.` |
| `selector.alarm_source.options.webhook` | `Über Home Assistant Cloud oder eine eigene Internetadresse (empfohlen). Voraussetzung: ein Abo für Home Assistant Cloud oder eine aus dem Internet erreichbare Adresse deines Home Assistant (IP-Adresse oder Domain).` | `Through Home Assistant Cloud or your own internet address (recommended). Requires a Home Assistant Cloud subscription or an address of your Home Assistant that is reachable from the internet (IP address or domain).` |
| `selector.alarm_source.options.ntfy` | `Über den kostenlosen Dienst ntfy. Kein Abo nötig, Home Assistant muss nicht aus dem Internet erreichbar sein.` | `Through the free service ntfy. No subscription needed, Home Assistant does not have to be reachable from the internet.` |

**Tests** (`tests/test_metadata.py`)
- Neu `test_reconfigure_asks_how_the_alarm_arrives` (de/en parametrisiert): Label endet mit
  `?`; Option `webhook` enthält `Abo`/`subscription` und `Domain`/`domain`; Option `ntfy`
  enthält `kostenlos`/`free`.

**README:** Abschnitt „Neu konfigurieren“, Aufzählungspunkt „Weg für den Alarm“ in
„Wie bekommt Home Assistant den Alarm?“ umbenennen und die Voraussetzung nennen.

**Risiko:** gering. Lange Optionstexte brechen im Radio-Layout um, das ist gewollt.

---

## 3. ntfy-Abschluss ohne Wiederholung (261018-ntfy-abschluss-redundant)

**Entscheidung:** Der Hinweis „Gut zu wissen“ bleibt im Abschluss. Der Dialog `ntfy` ist schon
lang, und der Hinweis gehört zu „was nach der Einrichtung gilt“. Kriterium für den kurzen
Text: Die URL für FF Agent ist **genau die, die zuletzt im Dialog `ntfy` bzw. `ntfy_select`
angezeigt wurde.** Thema und Server werden also gemeinsam verglichen. So fällt auch der
Sonderfall auf, dass der Nutzer in Schritt 1 ntfy mit eigenem Server einrichtet, nachdem der
Dialog `ntfy.sh` angezeigt hat.

**Änderungen `config_flow.py`**
- `__init__`: `self._shown_ntfy_url: str | None = None`.
- `_ntfy_placeholders()`: Vor dem `return` den berechneten Wert
  `ntfy_publish_url(server, topic)` in `self._shown_ntfy_url` merken. Nur
  `async_step_ntfy` und `_async_show_ntfy_select` rufen die Methode auf, beide zeigen den
  Wert an. Docstring ergänzen.
- `_async_finish_ntfy`: Textauswahl ersetzen durch

  ```python
  placeholders = _link_placeholders()
  if not topic:
      text = "ntfy_topic_unknown"
  elif (url := ntfy_publish_url(server, topic)) == self._shown_ntfy_url:
      text = SOURCE_NTFY  # short text: the guide showed exactly this URL
  else:
      text = NTFY_OTHER_ADDRESS
      placeholders[NTFY_PUBLISH_URL] = url
  ```

  `NTFY_OTHER_ADDRESS = "ntfy_other_address"` als Modulkonstante in `config_flow.py`. Der
  geheime URL-Platzhalter wird im kurzen Fall **nicht** mehr übergeben. Der Reconfigure-Zweig
  nutzt weiter `reason=f"reconfigure_successful_{text}"`, ergibt also
  `reconfigure_successful_ntfy` (kurz) bzw. `reconfigure_successful_ntfy_other_address`.

**Übersetzungen**

`config.create_entry.ntfy` (kurz, neu)
- de: `Geschafft: Die ntfy-Entität ist gefunden, die Einrichtung ist abgeschlossen.\n\nHast du den Webhook in FF Agent wie im vorigen Dialog angelegt (Schritt 3), ist nichts weiter zu tun. Prüfe die Kette mit einem Testalarm: In Home Assistant springt „Alarm aktiv“ an. Die Werte für FF Agent findest du jederzeit unter „Konfigurieren“.\n\n**Gut zu wissen:** Der Dienst ntfy sieht, wann du alarmiert wirst, aber keine Einsatzdaten. Ist Home Assistant oder die Internetverbindung beim Alarm gerade weg, geht der Alarm verloren, denn ntfy liefert ihn nicht nach.`
- en: `Done: The ntfy entity has been found, the setup is complete.\n\nIf you created the webhook in FF Agent as shown in the previous dialog (step 3), there is nothing left to do. Check the chain with a test alarm: \"Alarm active\" turns on in Home Assistant. You can look up the values for FF Agent at any time under \"Configure\".\n\n**Good to know:** The ntfy service sees when you are alerted, but no mission data. If Home Assistant or the internet connection is down when an alarm comes in, the alarm is lost, because ntfy does not deliver it later.`

`config.create_entry.ntfy_other_address` (neu, volle Werte)
- de: Der bisherige Text von `create_entry.ntfy`, jedoch mit diesem ersten Absatz und
  diesem zweiten Absatz statt „Prüfe, ob …“:
  `Geschafft: Die ntfy-Entität ist gewählt, die Einrichtung ist abgeschlossen.\n\n**Achtung: Die Adresse für FF Agent ist eine andere als im vorigen Dialog**, weil die gewählte Entität ein anderes Thema oder einen anderen ntfy-Server nutzt. Lege den Webhook in FF Agent (Web-UI > Automatisierung > Persönliche Webhooks) mit diesen Werten an bzw. korrigiere ihn:`
  Danach die bisherige Liste (Type … leer), der Satz zum geheimen Thema, neu
  `Prüfe danach mit einem Testalarm, ob „Alarm aktiv“ anspringt.` und der unveränderte
  Absatz „Gut zu wissen“.
- en: analog: `Done: The ntfy entity has been chosen, the setup is complete.\n\n**Note: The address for FF Agent differs from the previous dialog**, because the chosen entity uses another topic or another ntfy server. Create or correct the webhook in FF Agent (web UI > Automation > Personal webhooks) with these values:`, Liste, Geheimnis-Satz, `Then check with a test alarm that \"Alarm active\" turns on.`, „Good to know“.

`config.abort.reconfigure_successful_ntfy` (kurz, ersetzt den bisherigen)
- de: `Der Alarm kommt jetzt über ntfy. Hast du den Webhook in FF Agent wie im vorigen Dialog angelegt (Schritt 3), ist nichts weiter zu tun; prüfe es mit einem Testalarm.\n\nEinen bisherigen Webhook mit einer älteren Adresse (direkt auf Home Assistant oder ein altes ntfy-Thema) löschst du in FF Agent; er funktioniert nicht mehr.\n\nDie Integration wird neu geladen; ein gerade aktiver Alarm wird dabei zurückgesetzt.`
- en: `The alarm now comes through ntfy. If you created the webhook in FF Agent as shown in the previous dialog (step 3), there is nothing left to do; check it with a test alarm.\n\nDelete a previous webhook with an older address (directly to Home Assistant or an old ntfy topic) in FF Agent; it no longer works.\n\nThe integration is reloaded; an alarm that is active at that moment is reset.`

`config.abort.reconfigure_successful_ntfy_other_address` (neu)
- de: `Der Alarm kommt jetzt über ntfy. **Achtung: Die Adresse ist eine andere als im vorigen Dialog**, weil die gewählte Entität ein anderes Thema oder einen anderen ntfy-Server nutzt. Trage in FF Agent (Web-UI > Automatisierung > Persönliche Webhooks) diese Adresse ein: Methode GET, URL `{ntfy_publish_url}`, Basis-Authentifizierung, Header, Inhalt und Query-Parameter leer.` + die drei letzten Absätze des **bisherigen** `reconfigure_successful_ntfy` (alter Webhook löschen, Geheimnis, Reload).
- en: analog mit `**Note: The address differs from the previous dialog**, because the chosen entity uses another topic or another ntfy server. Enter this address in FF Agent (...)`.

`ntfy_topic_unknown` und `reconfigure_successful_ntfy_topic_unknown` bleiben unverändert.

**Tests**
- `tests/test_metadata.py`
  - `test_translations_cover_the_config_flow`: `config.create_entry.ntfy_other_address` und
    `config.abort.reconfigure_successful_ntfy_other_address` ergänzen.
  - `test_ntfy_texts_show_the_url_for_ff_agent`: Statt `create_entry.ntfy` und
    `abort.reconfigure_successful_ntfy` die beiden `*_other_address`-Texte prüfen.
  - Neu `test_short_ntfy_closing_texts_repeat_no_values` (de/en): `create_entry.ntfy` und
    `abort.reconfigure_successful_ntfy` enthalten keinen Platzhalter, kein `GET`, aber
    `Testalarm`/`test alarm`; `create_entry.ntfy` enthält „Gut zu wissen“/„Good to know“.
- `tests/test_config_flow.py`
  - `test_ntfy_find_creates_the_entry`: `description_placeholders == LINKS` (ohne URL).
  - `test_ntfy_select_takes_an_existing_subscription`: zusätzlich
    `result["description"] == "ntfy_other_address"`.
  - Neu `test_ntfy_other_server_with_the_same_topic_shows_the_full_values`: Dialog `ntfy`
    ohne ntfy-Eintrag anzeigen (zeigt `ntfy.sh`), dann `add_ntfy_entry(hass, {sub: topic},
    url=OWN_NTFY_SERVER)` und Entität anlegen, `ntfy_find` → `ntfy_other_address`, URL mit
    `OWN_NTFY_SERVER` im Platzhalter, `_assert_placeholders`.
- `tests/test_reconfigure.py`
  - `test_webhook_to_ntfy`: `description_placeholders == LINKS`.
  - `test_ntfy_own_entity_is_not_in_use`: `reason == "reconfigure_successful_ntfy_other_address"`,
    Platzhalter `ntfy_publish_url == NTFY_PUBLISH_URL` bleibt.
  - Übrige Prüfungen auf `reconfigure_successful_ntfy` bleiben gültig (Thema wie angezeigt).
- `tests/test_privacy_lifecycle.py` (Schritt 4): `reason == "reconfigure_successful_ntfy"`
  bleibt; statt `new_topic in ...["ntfy_publish_url"]` jetzt
  `"ntfy_publish_url" not in result["description_placeholders"]`.

**README:** Weg B, Schritt 4: Satz „Der Abschlussdialog zeigt die Werte … noch einmal“
ersetzen durch „Der Abschlussdialog wiederholt die Werte nur, wenn die gewählte Entität eine
andere Adresse hat als angezeigt.“

**Risiken:** Ein Test, der den alten Platzhalter erwartet, wird übersehen; CI fängt das.
Ein Nutzer, der Schritt 3 übersprungen hat, sieht die URL im Abschluss nicht mehr; der kurze
Text verweist deshalb auf „Konfigurieren“, wo die Optionen die URL zeigen.

---

## 4. Verkehrsmittel und Standort schon bei der Einrichtung (261018-einrichtung-zusage-optionen)

**Design**
- Neuer Formularschritt `reply_settings` **direkt nach** `user` und **vor** der Frage zur
  Alarmquelle. Begründung: Er gehört inhaltlich zur Rückmelde-URL, und alle sieben Endpfade
  (cloud, external, internal, path_only, webhook_anyway, ntfy, ntfy_topic_unknown bzw.
  ntfy_other_address) liegen danach. So kennt jeder Endpfad die Werte, ohne Sonderfall.
- Felder und Selektoren wie in den Optionen: `CONF_DEFAULT_TRANSPORT` (Pflicht, Standard
  `DEFAULT_TRANSPORT`, `TRANSPORT_SELECTOR`) und `CONF_LOCATION_ENTITY` (optional,
  `LOCATION_SELECTOR`, ohne Vorbelegung). „Adresse“ = Standort-Entität (`person`,
  `device_tracker`), siehe offene Frage 2.
- Die Werte landen beim Anlegen in `entry.options`. Die Integration speichert weiter keine URL;
  `reply.py` hängt `transport`, `lat`, `lng` wie bisher bei jeder Zusage an. `reply.py`
  bleibt unverändert.
- Es gibt nur **zwei** `async_create_entry`-Aufrufe (`_async_finish_webhook`,
  `_async_finish_ntfy`); alle Endpfade laufen durch sie. Reconfigure und Options Flow sind
  nicht betroffen.

**Änderungen `config_flow.py`**
- Modulkonstante `REPLY_SETTINGS_SCHEMA` **nicht** nötig; Schema in der Methode bauen:

  ```python
  vol.Schema({
      vol.Required(CONF_DEFAULT_TRANSPORT, default=DEFAULT_TRANSPORT): TRANSPORT_SELECTOR,
      vol.Optional(CONF_LOCATION_ENTITY): LOCATION_SELECTOR,
  })
  ```
- `__init__`: `self._reply_options: dict[str, Any] = {}`.
- `async_step_user`: nach dem Erzeugen von Webhook-ID und Token
  `return await self.async_step_reply_settings()` statt `async_step_alarm_source()`.
- Neu `async_step_reply_settings(user_input)`: Ohne Eingabe Formular `step_id="reply_settings"`.
  Mit Eingabe `self._reply_options = {CONF_DEFAULT_TRANSPORT: user_input[CONF_DEFAULT_TRANSPORT]}`
  und, nur wenn gesetzt, `CONF_LOCATION_ENTITY`; dann `return await self.async_step_alarm_source()`.
  Nichts loggen (Standort-Entität ist personenbezogen).
- Neue Methode `_new_entry_options(self) -> dict[str, Any]`:
  `return {**_default_options(), **self._reply_options}`. Beide `options=_default_options()`
  in `async_create_entry` durch `options=self._new_entry_options()` ersetzen.
  `_default_options()` bleibt als Modulfunktion bestehen.
- Modul-Docstring: neuen Schritt erwähnen.

**Übersetzungen** (Schritt `config.step.reply_settings`, in der JSON direkt nach `user`)

| Schlüssel | de | en |
|---|---|---|
| `title` | `Zusage: Verkehrsmittel und Standort` | `Accepting: transport and location` |
| `description` | `Diese Angaben schickt Home Assistant bei jeder Zusage an FF Agent mit, über den Button und über die Action. Die Rückmelde-URL aus dem vorigen Schritt bleibt dabei unverändert; die Werte werden bei jeder Zusage angehängt. Jetzt wird nichts gesendet. Du kannst beides später unter „Konfigurieren“ ändern.` | `Home Assistant sends these values to FF Agent with every acceptance, through the button and the action. The mission reply URL from the previous step stays as it is; the values are added to each acceptance. Nothing is sent now. You can change both later under \"Configure\".` |
| `data.default_transport` | `Standard-Verkehrsmittel` | `Default transport` |
| `data.location_entity` | `Standort-Entität` | `Location entity` |
| `data_description.default_transport` | `Wird bei jeder Zusage mitgesendet, wenn die Action kein Verkehrsmittel angibt.` | `Sent with every acceptance if the action does not name a transport.` |
| `data_description.location_entity` | `Optional: eine Person oder ein Gerät-Tracker, dessen aktueller Standort bei jeder Zusage mitgesendet wird. Leer lassen, um keinen Standort zu senden.` | `Optional: a person or device tracker whose current location is sent with every acceptance. Leave empty to send no location.` |

Außerdem `config.step.user.description` anpassen:
- de: `Eine Einrichtung gehört zu genau einer Person. Es wird nichts an FF Agent gesendet. Danach legst du fest, was beim Zusagen mitgesendet wird, und wählst, wie der Alarm bei Home Assistant ankommt.`
- en: `One entry belongs to exactly one person. Nothing is sent to FF Agent. Next you choose what is sent with an acceptance and how the alarm reaches Home Assistant.`

**Tests** (`tests/test_config_flow.py`)
- Helfer `_submit(..., settings: dict[str, Any] | None = DEFAULT_SETTINGS)`: Nach dem
  User-Schritt, **wenn** das Ergebnis ein Formular mit `step_id == "reply_settings"` ist und
  `settings is not None`, die Einstellungen absenden und deren Ergebnis zurückgeben.
  `DEFAULT_SETTINGS = {CONF_DEFAULT_TRANSPORT: "car"}`. Damit bleiben Duplikat-, Fehler- und
  „already_in_progress“-Tests unverändert (sie enden vorher).
- `tests/test_privacy_lifecycle.py`, Schritt 1: nach dem User-Schritt
  `async_configure(flow_id, {CONF_DEFAULT_TRANSPORT: "car"})` einfügen.
- Neu `test_reply_settings_follow_the_reply_url`: `_submit(..., settings=None)` →
  Formular `reply_settings`, Schema-Schlüssel genau `{default_transport, location_entity}`,
  Standard `car`, noch kein Eintrag.
- Neu `test_reply_settings_land_in_the_options` (parametrisiert über Endpfade
  `cloud`/external, `webhook_anyway`, `ntfy`): Mit `{default_transport: "bicycle",
  location_entity: "person.test"}` ist `entry.options == {reset_minutes: 30,
  default_transport: "bicycle", require_token: False, location_entity: "person.test"}`.
- Neu `test_reply_settings_without_a_location`: Ohne Standort fehlt `location_entity` in
  den Optionen ganz (nicht `None`).
- Neu `test_reply_settings_reach_the_accept_button` (in `tests/test_button.py` oder
  `test_config_flow.py`): Eintrag über den Flow mit `feet` anlegen, Button drücken, Query
  `transport=FEET`.
- `test_user_flow_creates_entry_with_external_url`: erwartete Optionen bleiben (Standard
  `car` über `DEFAULT_SETTINGS`).
- `tests/test_metadata.py`, `test_translations_cover_the_config_flow`: die sechs neuen
  Schlüssel von `reply_settings` ergänzen.

**README:** „Einrichtung Schritt für Schritt“: neuer Schritt zwischen 2 und 3 („Zusage:
Verkehrsmittel und Standort“), Schritt 3 wird 4. Hinweis, dass die URL nicht gespeichert,
sondern die Werte bei jeder Zusage angehängt werden.

**Risiken:** Mittel. Viele Flow-Tests laufen über `_submit`; der Helfer fängt das ab. Wer
einen Test mit direktem `async_configure` übersieht, bekommt in CI ein rotes
`step_id == "alarm_source"`. Option `location_entity` wird in der Diagnose schon redigiert
(`TO_REDACT`).

---

## 5. „Alarm aktiv“ von Hand zurücksetzen (261018-alarm-reset)

**Verhalten**
- Button „Alarm zurücksetzen“ (eigene Entität, Key `reset_alarm`) und Aktion
  `ff_agent.reset_alarm` mit Pflichtfeld `config_entry_id` (wie accept/reject).
- Schaltet „Alarm aktiv“ sofort aus und stoppt den Rücksetz-Timer. `last_alarm` bleibt,
  damit „Letzter Alarm“ und das 30-s-Fenster gegen Doppelalarme unverändert bleiben: Eine
  Wiederholung desselben Alarms schaltet „Alarm aktiv“ nicht wieder ein, ein neuer Alarm
  nach dem Fenster schon.
- Ohne aktiven Alarm passiert nichts (kein Signal, kein Log außer DEBUG).
- Eine Absage setzt nicht zurück (unverändert, nur Test).
- FF Agent erfährt nichts davon; kein Netzwerkaufruf.

**Änderungen**
- `const.py`: `SERVICE_RESET_ALARM: Final = "reset_alarm"`.
- `alarm.py`, neue Methode in `AlarmManager`:

  ```python
  @callback
  def async_reset(self) -> bool:
      """Switch "alarm active" off by hand; return False if nothing was active."""
      if self._closed or not self.active:
          return False
      self._async_cancel_reset()
      self.active = False
      self.active_until = None
      _LOGGER.debug("Alarm reset by hand")
      async_dispatcher_send(self._hass, self._signal_state)
      return True
  ```
- `button.py`: Klasse `ResetAlarmButton(FFAgentEntity, ButtonEntity)` mit Key
  `SERVICE_RESET_ALARM`; `async_press` ruft `self._manager.async_reset()`.
  `async_add_entities([accept, reject, reset])` in dieser Reihenfolge. Modul-Docstring
  anpassen. `PARALLEL_UPDATES = 1` bleibt.
- `services.py`: `RESET_ALARM_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string})`;
  Handler `_async_reset_alarm(call)` holt den Eintrag mit `service.async_get_config_entry`
  (wirft bei unbekanntem/nicht geladenem Eintrag `ServiceValidationError`) und ruft
  `entry.runtime_data.alarm.async_reset()`. Registrierung in `async_setup_services` mit
  `SupportsResponse.NONE`. Docstring anpassen.
- `services.yaml`: Block `reset_alarm` mit `config_entry_id` (required, Selector
  `config_entry: {integration: ff_agent}`), wie `reject`.
- `icons.json`: `entity.button.reset_alarm.default = "mdi:alarm-light-off"`,
  `services.reset_alarm.service = "mdi:alarm-light-off"`.

**Übersetzungen**

| Schlüssel | de | en |
|---|---|---|
| `entity.button.reset_alarm.name` | `Alarm zurücksetzen` | `Reset alarm` |
| `services.reset_alarm.name` | `Alarm zurücksetzen` | `Reset alarm` |
| `services.reset_alarm.description` | `Schaltet „Alarm aktiv“ einer Person sofort aus und beendet die Rücksetzzeit. „Letzter Alarm“ bleibt. Ohne aktiven Alarm passiert nichts. An FF Agent wird nichts gesendet.` | `Turns \"Alarm active\" of one person off right away and stops the reset time. \"Last alarm\" stays. Nothing happens without an active alarm. Nothing is sent to FF Agent.` |
| `services.reset_alarm.fields.config_entry_id.name` | `Eintrag` | `Entry` |
| `services.reset_alarm.fields.config_entry_id.description` | `Der FF-Agent-Eintrag der Person, deren Alarm zurückgesetzt wird.` | `The FF Agent entry of the person whose alarm is reset.` |

**Tests**
- `tests/test_alarm.py`
  - `test_reset_by_hand_ends_the_alarm`: Alarm, `async_reset()` → `True`, `active False`,
    `active_until None`, `last_alarm` unverändert, ein zusätzliches State-Signal; nach Ablauf
    der Rücksetzzeit kein weiteres Signal (Timer gestoppt).
  - `test_reset_without_an_alarm_does_nothing`: `False`, kein Signal.
  - `test_reset_after_shutdown_does_nothing`.
  - `test_repetition_after_a_reset_does_not_reactivate` (10 s später → dedupliziert,
    bleibt aus) und `test_new_alarm_after_a_reset_activates_again` (31 s später → an).
- `tests/test_button.py`
  - `test_reset_button_switches_the_alarm_off`: Webhook-Aufruf, Binary-Sensor `on`,
    Button drücken, `off`; „Letzter Alarm“ unverändert; `aioclient_mock.call_count == 0`.
  - `test_reset_button_without_an_alarm_does_nothing`.
  - `test_reject_does_not_reset_the_alarm`: Alarm, Absagen drücken, Binary-Sensor bleibt `on`.
  - `test_buttons_and_sensor_exist_and_belong_to_the_device` und
    `test_unloading_makes_the_entities_unavailable`: `reset_alarm` ergänzen.
  - `test_button_names_are_translated`: dritter Name, en `FF Agent Test Reset alarm`,
    de `FF Agent Test Alarm zurücksetzen`.
- `tests/test_services.py`
  - `test_actions_exist_even_without_an_entry`/`..._registered_...`: `reset_alarm`.
  - Neu `test_reset_alarm_switches_the_alarm_off` und `test_reset_alarm_without_an_alarm_does_nothing`.
  - `reset_alarm` in die Parametrisierung von `test_an_unknown_entry_is_refused`,
    `test_an_entry_of_another_integration_is_refused`, `test_an_entry_that_is_not_loaded_is_refused`,
    `test_the_entry_is_required` aufnehmen (bei `reset_alarm` gilt `call_count == 0` ohnehin).
- `tests/test_entities.py`, `test_unique_ids_contain_the_entry_id_but_no_secret`:
  `f"{entry_id}_reset_alarm"` ergänzen, `len(entries) == 7`.
- `tests/test_metadata.py`
  - `test_icons_cover_the_reply_entities_and_actions`: Button und Service `reset_alarm`.
  - `test_translations_cover_replies_actions_and_exceptions`: Schleife um `reset_alarm`
    erweitern, Felder `{"config_entry_id"}`, `entity.button.reset_alarm.name` vorhanden.
  - `test_services_yaml_matches_the_translations_and_the_schemas`: Menge der Services
    `{"accept", "reject", "reset_alarm"}`, Felder von `reset_alarm` `{"config_entry_id"}`.

**README:** Tabelle „Entitäten“ (neue Zeile, Hinweis zum 30-s-Fenster), Abschnitt „Actions“
(`ff_agent.reset_alarm`), Datenschutz/Recorder „sechs Entitäten … zwei Buttons“ → „sieben
… drei Buttons“, Fehlerbehebung „Alarm aktiv ging unerwartet aus“ um den Button ergänzen,
Bekannte Einschränkungen unverändert. English summary: Reset-Aktion nennen.

**Risiken:** gering. Ein Nutzer könnte erwarten, dass Reset auch das Doppelalarm-Fenster
öffnet; README sagt es ausdrücklich.

---

## 6. „Zusagen“ vor „Absagen“ (261018-reihenfolge-zusage) – ENTFÄLLT

**Entfällt (Entscheidung des Nutzers, 2026-10-18).** Die Button-Namen bleiben „Zusagen“ und
„Absagen“ (englisch „Accept“ und „Decline“), nichts wird umbenannt. Der Rest dieses
Abschnitts bleibt als Recherche erhalten; die Erkenntnis zur Sortierung steht als Fallstrick
in `docs/architektur.md`.

**Recherche (Frontend-Quellcode, Branch `dev`, abgerufen 2026-10-18)**
- Die Geräteseite `src/panels/config/devices/ha-config-device-page.ts` sortiert alle
  Entitäten des Geräts in `_entities` mit `stringCompare(ent1.stateName || "zzz"+entity_id, …,
  this.hass.locale.language)`. `stateName` kommt aus `computeEntityEntryName(entity)`
  (`src/common/entity/compute_entity_name_display.ts`) und ist `entry.name ?? entry.original_name`.
  Danach gruppiert `_entitiesByCategory` nur (Steuerelemente, Sensoren, …), ohne neu zu
  sortieren; `device-detail/ha-device-entities-card.ts` behält die Reihenfolge bei.
- `stringCompare` (`src/common/string/compare.ts`) nutzt `new Intl.Collator(language, { numeric: true })`.
- `original_name` ist der übersetzte Name in der **Systemsprache** von Home Assistant
  (`entity_platform.py` übergibt `original_name=entity.name`). Ein vom Nutzer vergebener
  Name (`entry.name`) hat Vorrang.
- **Ergebnis:** Sortiert wird alphabetisch nach Anzeigenamen. Reihenfolge der
  Registrierung, Reihenfolge in `button.py` oder Entity-ID spielen keine Rolle. Ohne
  Umbenennung gibt es keine Stellschraube. Englisch passt schon („Accept“ < „Decline“),
  das Problem besteht nur auf Deutsch („Absagen“ < „Zusagen“).
- Quellen:
  https://github.com/home-assistant/frontend/blob/dev/src/panels/config/devices/ha-config-device-page.ts,
  https://github.com/home-assistant/frontend/blob/dev/src/common/entity/compute_entity_name_display.ts,
  https://github.com/home-assistant/frontend/blob/dev/src/panels/config/devices/device-detail/ha-device-entities-card.ts,
  https://github.com/home-assistant/frontend/blob/dev/src/common/string/compare.ts,
  https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity_platform.py

**Lösung:** Nur die **deutschen Anzeigenamen** der Buttons ändern, englische bleiben.

| Key | bisher de | neu de (Vorschlag) | en (unverändert) |
|---|---|---|---|
| `entity.button.accept.name` | Zusagen | **Komme** | Accept |
| `entity.button.reject.name` | Absagen | **Komme nicht** | Decline |
| `entity.button.reset_alarm.name` | – | Alarm zurücksetzen | Reset alarm |

Sortierung auf der Geräteseite (Steuerelemente), de: „Alarm zurücksetzen“, „Komme“,
„Komme nicht“; en: „Accept“, „Decline“, „Reset alarm“. „Komme“ steht vor „Komme nicht“,
weil ein Präfix immer zuerst sortiert, unabhängig vom Collator.

Alternativen, falls der Nutzer „Komme“ nicht mag (alle sortieren richtig):
„Ich komme“/„Ich komme nicht“, „Zusage: ja“/„Zusage: nein“. Nicht geeignet:
„Einsatz zusagen“/„Einsatz absagen“ oder „Rückmeldung: Zusage/Absage“ (gleiches Problem).

**Nebenwirkungen**
- Bestehende Installationen: Entity-IDs bleiben (Registry über `unique_id`), nur der
  Anzeigename ändert sich, sobald die Integration neu geladen ist. Dashboards, die den
  Standardnamen anzeigen, zeigen den neuen Namen. Vom Nutzer umbenannte Entitäten bleiben,
  wie sie sind.
- Neuinstallationen auf Deutsch: Home Assistant bildet Entity-IDs für Deutsch aus dem
  deutschen Namen (`de` steht in `NATIVE_ENTITY_IDS`), also z. B.
  `button.<name>_komme` und `button.<name>_komme_nicht` statt `..._zusagen`/`..._absagen`.
  Die README nennt keine Button-IDs; Beispiele nutzen die Aktionen.
- Wortwahl gemischt: Aktionen heißen weiter „Zusagen“/„Absagen“, der Sensor zeigt
  „Zugesagt“/„Abgesagt“. Das ist vertretbar; Aktionen erscheinen nicht auf der Geräteseite.
- Die Sortierung folgt der Systemsprache, nicht der Profilsprache des Nutzers.

**Tests**
- `tests/test_button.py`, `test_button_names_are_translated`: de
  `["FF Agent Test Komme", "FF Agent Test Komme nicht", "FF Agent Test Alarm zurücksetzen"]`.
- Neu `tests/test_metadata.py::test_accept_sorts_before_reject_on_the_device_page` (de/en):
  `names = texts["entity"]["button"]`; `sorted([accept, reject], key=str.casefold)[0] == accept`.
  Docstring verweist auf die Sortierung im Frontend.
- Neu `tests/test_button.py::test_renamed_buttons_keep_their_entity_ids`: Vor dem Setup
  Registry-Einträge für `accept`/`reject` mit `suggested_object_id="ff_agent_test_zusagen"`
  bzw. `"..._absagen"` anlegen (Muster `_register_last_alarm_sensor` in `test_entities.py`),
  `hass.config.language = "de"`, Setup; Entity-IDs unverändert, `friendly_name` neu.

**README:** Tabelle „Entitäten“ (Namen), Hinweis: „Home Assistant sortiert Entitäten auf der
Geräteseite alphabetisch nach Namen.“ CHANGELOG nennt die Umbenennung unter „Geändert“
mit dem Hinweis, dass bestehende Entity-IDs bleiben.

**Risiko:** gering technisch, aber Geschmacksfrage (offene Frage 1).

---

## 7. Hinweis Browser-Cache (261018-leere-dialogtexte)

- `README.md`, Abschnitt „Installation“, nach Schritt 2 (HACS) und Schritt 2 (manuell):
  „Nach jedem Update: Home Assistant neu starten und die Seite im Browser hart neu laden
  (Strg+F5, am Mac Cmd+Umschalt+R). In der Companion-App die App neu starten bzw. den
  Frontend-Cache in den App-Einstellungen leeren.“
- `README.md`, „Fehlerbehebung“, neuer Absatz **„Dialoge ohne Text oder mit alten Texten“**:
  Ursache ist meist der Browser-Cache; Neustart allein reicht nicht, harter Reload (wie oben).
- `CHANGELOG.md` `[Unreleased]`: Abschnitt „Update“ mit demselben Hinweis.
- Kein Code.

---

## Gemeinsame Doku-Schritte

- `CHANGELOG.md` `[Unreleased]`:
  - **Neu:** Button und Aktion „Alarm zurücksetzen“ (`ff_agent.reset_alarm`); Einrichtung
    fragt Standard-Verkehrsmittel und Standort-Entität ab.
  - **Geändert:** Frage „Wie bekommt Home Assistant den Alarm?“ mit Voraussetzungen in der
    Neukonfiguration; kürzerer ntfy-Abschluss; (deutsche Button-Namen „Komme“/„Komme nicht“
    entfallen mit Punkt 6)
    (bestehende Entity-IDs bleiben).
  - **Entfernt:** Link „Besuchen“ in der Geräte-Info.
  - **Update:** Neustart plus harter Browser-Reload.
- `docs/architektur.md`: Modulliste (`button.py`: accept, reject, reset_alarm;
  `services.py`: + reset_alarm), Entitäten-Tabelle (neue Zeile, deutsche Namen), Actions-Absatz,
  Optionen („auch im Einrichtungsschritt `reply_settings`“), Flows (`user` → `reply_settings`
  → Frage zur Alarmquelle), neuer Fallstrick: „Geräteseite sortiert nach Anzeigename
  (`entry.name ?? original_name`, Systemsprache); Reihenfolge im Code wirkt nicht“ und
  „`configuration_url` muss explizit `None` sein, um einen gespeicherten Link zu löschen“.
- `docs/quality-scale.md`: Nachweise bei `action-setup`, `docs-actions` um `reset_alarm`
  ergänzen.

## Empfohlene Commit-Reihenfolge

Jeder Commit hält die Tests grün; nach jedem Push CI prüfen.

1. `fix: drop the product link from the device info` (Punkt 1)
2. `feat: ask how the alarm arrives in the reconfigure flow` (Punkt 2)
3. `feat: shorten the ntfy closing dialog when the address was shown` (Punkt 3)
4. `feat: ask for transport and location during setup` (Punkt 4)
5. `feat: add button and action to reset the alarm` (Punkt 5)
6. ~~`feat: name the reply buttons so that accepting comes first` (Punkt 6)~~ entfällt
7. `docs: update README, CHANGELOG and architecture for the v0.2.0 feedback` (Punkt 7 und
   gemeinsame Doku; README-Teile der Punkte 2–6 dürfen auch in deren Commits)

## Definition of Done (gesamt)

- [ ] Alle Punkte außer dem entfallenen Punkt 6 umgesetzt wie oben, de und en mit identischen Schlüsseln.
- [ ] CI grün: pytest, ruff, hassfest, HACS-Validierung.
- [ ] Neue/angepasste Tests aus allen Abschnitten vorhanden; keine Prüfung auf alte Texte
      oder Platzhalter übrig.
- [ ] Keine Secrets, keine URL in Übersetzungen, kein Firmenname, kein Versionssprung.
- [ ] README, CHANGELOG `[Unreleased]`, `docs/architektur.md`, `docs/quality-scale.md`
      aktualisiert.
- [ ] `tester` PASS, `reviewer` „freigegeben“.
- [ ] Gegenprobe durch den Nutzer nach dem nächsten Release: Neukonfiguration zeigt die
      Frage, ntfy-Abschluss ist kurz, Geräte-Info ohne „Besuchen“, Einrichtung fragt
      Verkehrsmittel/Standort, „Komme“ steht vor „Komme nicht“, Reset funktioniert.

## Offene Fragen an den Nutzer (entschieden am 2026-10-18)

**Entscheidungen:**

1. **Button-Namen:** Punkt 6 entfällt. Die Namen bleiben „Zusagen“/„Absagen“ (en wie bisher).
2. **Feste Adresse:** Es bleibt bei der Standort-Entität (Person und Geräte-Tracker) wie in
   den Optionen, keine Zonen.
3. **Reset-Button:** Name „Alarm zurücksetzen“ (en „Reset alarm“). Er darf auf der
   Geräteseite zuerst stehen.

Ursprüngliche Fragen:

1. **Button-Namen:** Einverstanden mit „Komme“/„Komme nicht“? Alternativen:
   „Ich komme“/„Ich komme nicht“ oder „Zusage: ja“/„Zusage: nein“. Ohne Antwort setzt der
   Entwickler „Komme“/„Komme nicht“ um.
2. **Feste Adresse:** Reicht die Standort-Entität (Person/Gerät-Tracker)? Mit wenig Aufwand
   ließe sich zusätzlich eine **Zone** (z. B. „Zuhause“) wählen; dann ginge immer deren
   feste Position mit. Ohne Antwort bleibt es bei Person/Gerät-Tracker.
3. **Position des Reset-Buttons:** Auf Deutsch steht „Alarm zurücksetzen“ alphabetisch vor
   „Komme“. Passt das, oder soll er ans Ende (dann etwa „Zurücksetzen: Alarm aktiv“)?
