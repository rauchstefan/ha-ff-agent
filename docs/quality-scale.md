# Quality Scale (Integration Quality Scale von Home Assistant)

Stand 2026-10-17, PR 6 (`261017-mvp-6-doku-qualitaet`).

**Quelle der Regelliste:** <https://contributors.home-assistant.io/core/quality-scale/rules/>,
abgerufen am 2026-10-17 und vom Projektleiter geprüft. Die Liste umfasst 54 Regeln (Bronze
20, Silber 10, Gold 21, Platin 3). Ziel laut ADR 0002: **Bronze** mit begründeten
Ausnahmen, dazu ausgewählte Regeln aus Silber und Gold.

Es gibt bewusst keine `quality_scale.yaml` im Integrationsordner, weil das Verhalten von
hassfest bei Custom-Integrationen ungeklärt ist. Diese Datei ersetzt sie.

Status: `done` (erfüllt, mit Beleg), `exempt` (nicht zutreffend, mit Begründung), `todo`
(offen).

## Bronze (20)

| Regel | Status | Beleg bzw. Begründung |
|---|---|---|
| `action-setup` | done | Actions werden in `async_setup` registriert: `custom_components/ff_agent/__init__.py`, `services.py`; Test `tests/test_services.py` (`accept`, `reject`, `reset_alarm`) |
| `appropriate-polling` | exempt | Kein Polling, `iot_class: cloud_push` (`manifest.json`). Es gibt keinen Coordinator. |
| `brands` | done | `custom_components/ff_agent/brand/icon.png` und `icon@2x.png`. Ob Name und Logo des Herstellers verwendet werden dürfen, ist offen (TODO `261016-repo-oeffentlich`). |
| `common-modules` | done | Basisklasse in `entity.py`; die Regel kennt keine Ausnahmen. Konstanten in `const.py`. |
| `config-flow` | done | `config_flow.py` mit UI-Flow, Felder in `translations/*.json` mit `data_description`; `tests/test_config_flow.py` |
| `config-flow-test-coverage` | done | `tests/test_config_flow.py`, `tests/test_options_flow.py`, `tests/test_reconfigure.py` (Erfolg, Fehler, Recovery, doppelte Einträge); `config_flow.py` ist durch das Abdeckungs-Gate (siehe `test-coverage`) abgedeckt |
| `dependency-transparency` | exempt | `requirements: []` in `manifest.json`, es gibt keine externen Bibliotheken |
| `docs-actions` | done | README, Abschnitt „Actions“ (`accept`, `reject`, `reset_alarm`) |
| `docs-conditions` | exempt | Die Integration hat keine eigenen Conditions. |
| `docs-high-level-description` | done | README, Abschnitt „Was die Integration tut und was nicht“ |
| `docs-installation-instructions` | done | README, Abschnitte „Voraussetzungen“ und „Installation“ |
| `docs-removal-instructions` | done | README, Abschnitt „Entfernen“ |
| `docs-triggers` | exempt | Keine eigenen Trigger. Ein State-Trigger auf die Event-Entität ist kein Trigger der Integration. |
| `entity-event-setup` | done | Dispatcher-Anmeldung in `async_added_to_hass` mit `async_on_remove`: `binary_sensor.py`, `event.py`, `sensor.py`; `tests/test_entities.py` |
| `entity-unique-id` | done | `entity.py`: `unique_id = "{entry_id}_{key}"`; `tests/test_entities.py` (keine Rückmelde-UUID in der `unique_id`) |
| `has-entity-name` | done | `entity.py`: `_attr_has_entity_name = True` |
| `runtime-data` | done | `ConfigEntry.runtime_data` mit `FFAgentData` (`models.py`, `__init__.py`) |
| `test-before-configure` | exempt | Projektbezogene Ausnahme: Offiziell nennt die Regel nur Helper und Discovery. Jeder Verbindungstest wäre eine echte Zu- oder Absage an FF Agent; die Erreichbarkeit des Webhooks lässt sich aus HA nicht prüfen. Das URL-Format wird offline in `reply_url.py` geprüft. ADR 0002, Abschnitt 3. |
| `test-before-setup` | exempt | Passt zur offiziellen Ausnahme „cannot check its configuration during setup“: Beim Setup gibt es keinen Verbindungsaufbau, der Webhook wartet passiv. |
| `unique-config-entry` | done | `unique_id` des Eintrags ist `sha256(reply_id)` gekürzt (`reply_url.py`); Abbruch `already_configured`; `tests/test_config_flow.py` |

## Silber (10)

| Regel | Status | Beleg bzw. Begründung |
|---|---|---|
| `action-exceptions` | done | Fehler der Rückmeldung werden zu `HomeAssistantError` mit Übersetzung (`reply.py`); Tests `tests/test_reply.py`, `tests/test_button.py`. Den Fehler für einen falschen oder nicht geladenen Eintrag wirft `service.async_get_config_entry` (HA Core), Test `tests/test_services.py`. |
| `config-entry-unloading` | done | `async_unload_entry` und `async_remove_entry` in `__init__.py`, Webhook wird über `async_on_unload` abgemeldet; `tests/test_init.py`, `tests/test_webhook.py` (Aufruf nach Unload wirkungslos) |
| `docs-configuration-parameters` | done | README, Abschnitte „Optionen“ und „Neu konfigurieren“ |
| `docs-installation-parameters` | done | README, Abschnitte „Einrichtung Schritt für Schritt“ und „Optionale Token-Absicherung“ |
| `entity-unavailable` | exempt | Offiziell gilt die Ausnahme nur für Integrationen ohne Entitäten. Inhaltlich trägt sie trotzdem: Die Daten kommen per Push, es gibt keine Verbindung, deren Abbruch man erkennen könnte. Fehler der Buttons sind Action-Fehler, keine Nichtverfügbarkeit. |
| `integration-owner` | done | `codeowners` in `manifest.json` |
| `log-when-unavailable` | exempt | Gleiche Begründung wie `entity-unavailable`: Push, keine Verbindung. |
| `parallel-updates` | done | `PARALLEL_UPDATES = 0` in `binary_sensor.py`, `event.py`, `sensor.py`; `= 1` in `button.py` |
| `reauthentication-flow` | todo | Zurückgestellt, bis bekannt ist, wie FF Agent eine ungültige UUID beantwortet (Annahme A7, ADR 0002). Bis dahin ersetzt *Neu konfigurieren* den Ablauf. |
| `test-coverage` | done | Gate `--cov-fail-under=95` in `pyproject.toml`, Stand 2026-10-17: 100 % |

## Gold (21)

| Regel | Status | Beleg bzw. Begründung |
|---|---|---|
| `devices` | done | `entity.py`: ein Gerät je Eintrag, `DeviceEntryType.SERVICE`; `tests/test_entities.py` |
| `diagnostics` | done | `diagnostics.py`, redigiert über `TO_REDACT` (`const.py`), mit `alarm_source` und ntfy-Block (Thema, Entity-UUID und `entity_id` redigiert); `tests/test_diagnostics.py`, `tests/test_privacy.py`, `tests/test_privacy_lifecycle.py` |
| `discovery` | exempt | Cloud-Dienst, nichts zu entdecken |
| `discovery-update-info` | exempt | Cloud-Dienst, nichts zu entdecken |
| `docs-data-update` | done | README, Abschnitt „Was die Integration tut und was nicht“ (Push-Datenfluss) |
| `docs-examples` | done | README, Abschnitt „Beispiel-Automationen“ |
| `docs-known-limitations` | done | README, Abschnitt „Bekannte Einschränkungen“ |
| `docs-supported-devices` | exempt | Dienst ohne Hardware |
| `docs-supported-functions` | done | README, Abschnitte „Entitäten“ und „Actions“ |
| `docs-troubleshooting` | done | README, Abschnitt „Fehlerbehebung“ |
| `docs-use-cases` | done | README, Abschnitt „Was die Integration tut und was nicht“ und Beispiele |
| `dynamic-devices` | exempt | Ein festes Gerät je Eintrag |
| `entity-category` | todo | Prüfen, ob „Letzte Rückmeldung“ als `diagnostic` eingestuft werden soll |
| `entity-device-class` | done | `sensor.py`: `TIMESTAMP` und `ENUM` |
| `entity-disabled-by-default` | exempt | Keine selten gebrauchten Entitäten |
| `entity-translations` | done | `translation_key` je Entität, `translations/de.json` und `en.json`; `tests/test_metadata.py` (gleiche Schlüssel) |
| `exception-translations` | done | Abschnitt `exceptions` in den Übersetzungen, genutzt in `reply.py` |
| `icon-translations` | done | `icons.json` |
| `reconfiguration-flow` | done | `async_step_reconfigure` in `config_flow.py`, inklusive Wechsel des Alarmwegs (Webhook/ntfy, ADR 0003); `tests/test_reconfigure.py` |
| `repair-issues` | done | Issue `webhook_token_rejected` in `webhook.py` und `ntfy_entity_missing` in `__init__.py` (ntfy-Entität fehlt, fremd oder deaktiviert), Übersetzungen unter `issues`; `tests/test_webhook.py`, `tests/test_ntfy_source.py` |
| `stale-devices` | exempt | Das Gerät ist an den Eintrag gebunden |

## Platin (3)

| Regel | Status | Beleg bzw. Begründung |
|---|---|---|
| `async-dependency` | exempt | Keine Abhängigkeiten |
| `inject-websession` | done | `reply.py` nutzt `async_get_clientsession` |
| `strict-typing` | todo | Kein mypy-strict-Gate |

## Offene `todo`s

- `reauthentication-flow` (Silber): nach Klärung von Annahme A7
- `entity-category` (Gold): Einstufung von „Letzte Rückmeldung“ prüfen
- `strict-typing` (Platin): mypy-strict-Gate einführen
