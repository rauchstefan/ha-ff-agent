"""Static checks for the HACS and Home Assistant metadata files."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import pytest
from homeassistant.util import yaml as yaml_util

from custom_components.ff_agent.const import (
    DOMAIN,
    MENU_ALARM_SOURCE,
    MENU_CLOUD_NOT_CONNECTED,
    MENU_CLOUD_SETUP,
    MENU_NO_CLOUD,
    MENU_NTFY,
    TRANSPORT_API_VALUES,
    TRANSPORTS,
)

ROOT = Path(__file__).parent.parent
INTEGRATION = ROOT / "custom_components" / DOMAIN
# Menus of the config flow: step ID -> options.
MENUS = {
    "alarm_source": MENU_ALARM_SOURCE,
    "alarm_source_cloud": MENU_ALARM_SOURCE,
    "no_cloud": MENU_NO_CLOUD,
    "cloud_setup": MENU_CLOUD_SETUP,
    "cloud_setup_retry": MENU_CLOUD_SETUP,
    "cloud_not_connected": MENU_CLOUD_NOT_CONNECTED,
    "ntfy": MENU_NTFY,
}
HACS_REQUIRED_MANIFEST_KEYS = {
    "domain",
    "documentation",
    "issue_tracker",
    "codeowners",
    "name",
    "version",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict):
            keys |= _flatten(value, f"{full}.")
        else:
            keys.add(full)
    return keys


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_hacs_json_has_only_name_and_homeassistant() -> None:
    """hacs.json holds exactly the agreed keys."""
    assert _load(ROOT / "hacs.json") == {
        "name": "FF Agent",
        "homeassistant": "2026.3.0",
    }


def test_manifest_has_hacs_required_keys() -> None:
    """The manifest contains all keys HACS requires and the domain matches."""
    manifest = _load(INTEGRATION / "manifest.json")
    assert HACS_REQUIRED_MANIFEST_KEYS <= manifest.keys()
    assert manifest["domain"] == DOMAIN
    assert {"iot_class", "config_flow", "integration_type"} <= manifest.keys()


def test_manifest_describes_a_push_service() -> None:
    """FF Agent pushes alarms to a webhook; there is one entry per person."""
    manifest = _load(INTEGRATION / "manifest.json")
    assert manifest["iot_class"] == "cloud_push"
    assert manifest["integration_type"] == "service"
    assert "webhook" in manifest["dependencies"]
    assert manifest["after_dependencies"] == ["cloud"]
    assert "single_config_entry" not in manifest


def test_manifest_version_matches_the_latest_changelog_release() -> None:
    """The manifest version is the newest released version in the CHANGELOG."""
    changelog = (ROOT / "CHANGELOG.md").read_text("utf-8")
    latest = re.search(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.MULTILINE)
    assert latest is not None
    assert _load(INTEGRATION / "manifest.json")["version"] == latest.group(1)


def test_manifest_key_order() -> None:
    """Hassfest order: domain, name, then the remaining keys alphabetically."""
    keys = list(_load(INTEGRATION / "manifest.json"))
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def test_translations_en_de_have_same_keys() -> None:
    """German and English translations cover the same keys."""
    en = _flatten(_load(INTEGRATION / "translations" / "en.json"))
    de = _flatten(_load(INTEGRATION / "translations" / "de.json"))
    assert en == de


@pytest.mark.parametrize("language", ["en", "de"])
def test_translations_cover_the_config_flow(language: str) -> None:
    """The user step, its errors and all four closing dialogs are translated."""
    keys = _flatten(_load(INTEGRATION / "translations" / f"{language}.json"))
    expected = {
        "config.step.user.title",
        "config.step.user.description",
        "config.step.user.data.name",
        "config.step.user.data.reply_url",
        "config.step.user.data_description.reply_url",
        "config.step.reply_settings.title",
        "config.step.reply_settings.description",
        "config.step.reply_settings.data.default_transport",
        "config.step.reply_settings.data.location_entity",
        "config.step.reply_settings.data_description.default_transport",
        "config.step.reply_settings.data_description.location_entity",
        "config.error.invalid_reply_url",
        "config.error.ntfy_not_set_up",
        "config.error.ntfy_entity_not_found",
        "config.error.ntfy_entity_invalid",
        "config.error.ntfy_entity_in_use",
        "config.abort.already_in_progress",
        "config.abort.already_configured",
        "config.abort.unknown",
        "config.abort.reconfigure_successful_ntfy",
        "config.abort.reconfigure_successful_ntfy_other_address",
        "config.abort.reconfigure_successful_ntfy_topic_unknown",
        "config.abort.reconfigure_successful_local",
        "config.create_entry.ntfy_topic_unknown",
        "config.create_entry.cloud",
        "config.create_entry.external",
        "config.create_entry.internal",
        "config.create_entry.path_only",
        "config.create_entry.ntfy",
        "config.create_entry.ntfy_other_address",
        "config.step.ntfy_select.title",
        "config.step.ntfy_select.description",
        "config.step.ntfy_select.data.ntfy_entity",
        "config.step.ntfy_select.data_description.ntfy_entity",
        "selector.alarm_source.options.webhook",
        "selector.alarm_source.options.ntfy",
        "issues.ntfy_entity_missing.title",
        "issues.ntfy_entity_missing.description",
    }
    for step, options in MENUS.items():
        expected |= {f"config.step.{step}.title", f"config.step.{step}.description"}
        expected |= {f"config.step.{step}.menu_options.{option}" for option in options}
    assert expected <= keys
    assert "config.abort.single_instance_allowed" not in keys
    # The connection error is a menu now, the unexpected error an abort.
    assert "config.error.cloud_not_connected" not in keys
    assert "config.error.unknown" not in keys


@pytest.mark.parametrize("language", ["en", "de"])
def test_translations_cover_the_repair_issue(language: str) -> None:
    """The repair issue for a rejected webhook call has a title and a description."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    issue = texts["issues"]["webhook_token_rejected"]
    assert issue["title"]
    assert "{title}" in issue["description"]
    assert "X-FF-Agent-Token" in issue["description"]


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("kind", ["cloud", "external", "internal", "path_only"])
def test_closing_dialogs_show_the_webhook_url(language: str, kind: str) -> None:
    """Every closing dialog contains the webhook URL placeholder."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    assert "{webhook_url}" in texts["config"]["create_entry"][kind]


@pytest.mark.parametrize(
    ("name", "size"),
    [("icon.png", (256, 256)), ("icon@2x.png", (512, 512))],
)
def test_brand_icon_dimensions(name: str, size: tuple[int, int]) -> None:
    """Brand icons have the sizes required for local brand images."""
    assert _png_size(INTEGRATION / "brand" / name) == size


@pytest.mark.parametrize("language", ["en", "de"])
def test_translations_contain_no_urls(language: str) -> None:
    """hassfest rejects URLs in translations, so they must live in placeholders."""
    values = _load(INTEGRATION / "translations" / f"{language}.json")
    assert "http://" not in json.dumps(values)
    assert "https://" not in json.dumps(values)


def test_icons_cover_the_entities() -> None:
    """Every entity has an icon translation; the alarm lamp lights up when active."""
    icons = _load(INTEGRATION / "icons.json")["entity"]
    assert icons["binary_sensor"]["alarm"] == {
        "default": "mdi:alarm-light-outline",
        "state": {"on": "mdi:alarm-light"},
    }
    assert icons["event"]["alarm"] == {"default": "mdi:fire-truck"}
    assert icons["sensor"]["last_alarm"] == {"default": "mdi:clock-alert-outline"}


@pytest.mark.parametrize(
    ("language", "names"),
    [
        ("en", ("Alarm active", "Alarm", "Last alarm")),
        ("de", ("Alarm aktiv", "Alarm", "Letzter Alarm")),
    ],
)
def test_translations_name_the_alarm_entities(
    language: str, names: tuple[str, str, str]
) -> None:
    """The entity names are translated, the event type has a label."""
    entities = _load(INTEGRATION / "translations" / f"{language}.json")["entity"]
    assert entities["binary_sensor"]["alarm"]["name"] == names[0]
    assert entities["event"]["alarm"]["name"] == names[1]
    assert entities["sensor"]["last_alarm"]["name"] == names[2]
    event_type = entities["event"]["alarm"]["state_attributes"]["event_type"]
    assert event_type["state"]["alarm"] == "Alarm"


def test_icons_cover_the_reply_entities_and_actions() -> None:
    """The buttons, the sensor and both actions have an icon."""
    icons = _load(INTEGRATION / "icons.json")
    assert icons["entity"]["button"]["accept"] == {"default": "mdi:check-circle"}
    assert icons["entity"]["button"]["reject"] == {"default": "mdi:close-circle"}
    assert icons["entity"]["sensor"]["last_reply"] == {
        "default": "mdi:message-reply-text"
    }
    assert icons["services"] == {
        "accept": {"service": "mdi:check-circle"},
        "reject": {"service": "mdi:close-circle"},
    }


@pytest.mark.parametrize("language", ["en", "de"])
def test_translations_cover_replies_actions_and_exceptions(language: str) -> None:
    """Buttons, sensor states, actions and errors are translated."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    entity = texts["entity"]
    assert entity["button"]["accept"]["name"]
    assert entity["button"]["reject"]["name"]
    last_reply = entity["sensor"]["last_reply"]
    assert last_reply["name"]
    assert set(last_reply["state"]) == {"accepted", "rejected", "failed"}
    assert "{status}" in texts["exceptions"]["reply_http_error"]["message"]
    assert "{transport}" in texts["exceptions"]["invalid_transport"]["message"]
    assert set(texts["selector"]["transport"]["options"]) == set(TRANSPORTS)
    for label in texts["selector"]["transport"]["options"].values():
        assert label
    assert texts["exceptions"]["reply_connection_error"]["message"]
    for service in ("accept", "reject"):
        assert texts["services"][service]["name"]
        assert texts["services"][service]["description"]
    fields = texts["services"]["accept"]["fields"]
    assert set(fields) == {"config_entry_id", "transport", "latitude", "longitude"}
    assert set(texts["services"]["reject"]["fields"]) == {"config_entry_id"}
    for field in fields.values():
        assert field["name"]
        assert field["description"]


@pytest.mark.parametrize("language", ["en", "de"])
def test_error_messages_do_not_contain_addresses(language: str) -> None:
    """The translated errors name no URL and no ID."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    for error in texts["exceptions"].values():
        assert "http://" not in error["message"].lower()
        assert "https://" not in error["message"].lower()
        assert "uuid" not in error["message"].lower()


def test_services_yaml_matches_the_translations_and_the_schemas() -> None:
    """Every field of services.yaml is translated and the transport list matches."""
    services = yaml_util.load_yaml(str(INTEGRATION / "services.yaml"))
    assert set(services) == {"accept", "reject"}
    assert set(services["accept"]["fields"]) == {
        "config_entry_id",
        "transport",
        "latitude",
        "longitude",
    }
    assert set(services["reject"]["fields"]) == {"config_entry_id"}
    for service in services.values():
        entry = service["fields"]["config_entry_id"]
        assert entry["required"] is True
        assert entry["selector"] == {"config_entry": {"integration": DOMAIN}}
    transport = services["accept"]["fields"]["transport"]["selector"]["select"]
    assert transport["options"] == list(TRANSPORTS)
    assert transport["translation_key"] == "transport"
    assert list(TRANSPORTS) == ["car", "feet", "bicycle"]
    assert dict(TRANSPORT_API_VALUES) == {
        "car": "CAR",
        "feet": "FEET",
        "bicycle": "BICYCLE",
    }
    for key in ("latitude", "longitude"):
        assert services["accept"]["fields"][key]["selector"]["number"]["step"] == "any"


@pytest.mark.parametrize("language", ["en", "de"])
def test_translations_cover_the_options_and_the_reconfigure_flow(
    language: str,
) -> None:
    """Both flows, their fields, errors and closing dialogs are translated."""
    keys = _flatten(_load(INTEGRATION / "translations" / f"{language}.json"))
    expected = {
        "config.step.reconfigure.title",
        "config.step.reconfigure.description",
        "config.step.reconfigure.data.reply_url",
        "config.step.reconfigure.data.alarm_source",
        "config.step.reconfigure.data.regenerate_webhook",
        "config.step.reconfigure.data_description.reply_url",
        "config.step.reconfigure.data_description.alarm_source",
        "config.step.reconfigure.data_description.regenerate_webhook",
        "config.abort.reconfigure_successful",
        "config.abort.reconfigure_successful_new_webhook",
        "options.step.init.title",
        "options.step.init.description",
    }
    for field in (
        "require_token",
        "reset_minutes",
        "default_transport",
        "location_entity",
    ):
        expected.add(f"options.step.init.data.{field}")
        expected.add(f"options.step.init.data_description.{field}")
    assert expected <= keys


@pytest.mark.parametrize("language", ["en", "de"])
def test_options_form_shows_the_access_and_warns_about_the_reload(
    language: str,
) -> None:
    """The description names URL, header and token and the reset of a running alarm."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    step = texts["options"]["step"]["init"]
    for placeholder in ("webhook_url", "url_kind", "token_header", "token"):
        assert f"{{{placeholder}}}" in step["description"]
    reload_hint = {
        "en": "Saving reloads the integration; an alarm that is active at that "
        "moment is reset.",
        "de": "Speichern lädt die Integration neu; ein gerade aktiver Alarm wird "
        "dabei zurückgesetzt.",
    }[language]
    assert reload_hint in step["description"]
    token_hint = step["data_description"]["require_token"]
    assert "x-ff-agent-token" in token_hint
    assert "header_names" in token_hint
    reconfigure = texts["config"]["step"]["reconfigure"]["description"]
    assert reload_hint in reconfigure


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("kind", ["internal", "path_only"])
def test_unreachable_url_dialogs_point_to_reconfigure(language: str, kind: str) -> None:
    """Saved without alarm: the way out is the cloud link and the reconfigure flow."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    text = texts["config"]["create_entry"][kind]
    assert "{cloud_url}" in text
    assert {"en": "Reconfigure", "de": "Neu konfigurieren"}[language] in text
    assert "ntfy" in text
    for outdated in ("remove this entry", "lege sie neu an", "Entferne danach"):
        assert outdated not in text


@pytest.mark.parametrize("language", ["en", "de"])
def test_new_webhook_dialog_shows_the_access_once(language: str) -> None:
    """The closing dialog after a new access shows URL, header name and token."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    text = texts["config"]["abort"]["reconfigure_successful_new_webhook"]
    for placeholder in ("webhook_url", "token_header", "token"):
        assert f"{{{placeholder}}}" in text


@pytest.mark.parametrize("language", ["en", "de"])
def test_reply_url_help_names_the_place_in_the_person_settings(language: str) -> None:
    """The help of the field points to the personal settings of the person."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    step = texts["config"]["step"]["user"]
    text = step["data_description"]["reply_url"]
    assert "Weblinks für Einsatzmeldung" in text
    assert "Übung/Einsatz" in text
    for outdated in ("Einsatzrückmeldungen", "Mission replies"):
        assert outdated not in text
    # hassfest does not allow URLs in translations.
    assert "http://" not in text
    assert "https://" not in text


# --- The alarm source (ADR 0003) -----------------------


@pytest.mark.parametrize("language", ["en", "de"])
def test_menus_have_exactly_their_options(language: str) -> None:
    """Every menu option of the flow has a label, and no label is left over."""
    steps = _load(INTEGRATION / "translations" / f"{language}.json")["config"]["step"]
    for step, options in MENUS.items():
        assert list(steps[step]["menu_options"]) == options


@pytest.mark.parametrize(
    ("language", "word"), [("en", "(recommended)"), ("de", "(empfohlen)")]
)
def test_cloud_is_recommended_in_the_first_question(language: str, word: str) -> None:
    """Menus have no preselection, so the recommendation is in the label."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    steps = texts["config"]["step"]
    for step in ("alarm_source", "alarm_source_cloud"):
        assert word in steps[step]["menu_options"]["cloud"]
        assert word not in steps[step]["menu_options"]["no_cloud"]
    assert word in texts["selector"]["alarm_source"]["options"]["webhook"]


@pytest.mark.parametrize("language", ["en", "de"])
def test_guides_have_numbered_steps(language: str) -> None:
    """The guides for the cloud and for ntfy are numbered step by step."""
    steps = _load(INTEGRATION / "translations" / f"{language}.json")["config"]["step"]
    for step in ("cloud_setup", "cloud_setup_retry", "cloud_not_connected"):
        lines = steps[step]["description"].split("\n")
        assert {"1.", "2.", "3."} <= {line[:2] for line in lines}
    ntfy = steps["ntfy"]["description"]
    for number in ("**1.", "**2.", "**3.", "**4."):
        assert number in ntfy


@pytest.mark.parametrize("language", ["en", "de"])
def test_ntfy_texts_show_the_url_for_ff_agent(language: str) -> None:
    """The guide, the closing dialogs and the options show the GET URL."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    config = texts["config"]
    for text in (
        config["step"]["ntfy"]["description"],
        config["create_entry"]["ntfy_other_address"],
        config["abort"]["reconfigure_successful_ntfy_other_address"],
        texts["options"]["step"]["ntfy"]["description"],
    ):
        assert "{ntfy_publish_url}" in text
        assert "GET" in text
    guide = config["step"]["ntfy"]["description"]
    for placeholder in ("ntfy_topic", "ntfy_setup_url", "ntfy_integration_url"):
        assert f"{{{placeholder}}}" in guide
    cloud_guide = config["step"]["cloud_setup"]["description"]
    assert "{cloud_url}" in cloud_guide
    assert "{network_url}" in cloud_guide
    assert "{cloud_url}" in texts["options"]["step"]["init"]["description"]


@pytest.mark.parametrize("language", ["en", "de"])
def test_short_ntfy_closing_texts_repeat_no_values(language: str) -> None:
    """If the guide showed the URL, the closing text only points to a test alarm."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    config = texts["config"]
    test_alarm = {"en": "test alarm", "de": "Testalarm"}[language]
    good_to_know = {"en": "Good to know", "de": "Gut zu wissen"}[language]
    for text in (
        config["create_entry"]["ntfy"],
        config["abort"]["reconfigure_successful_ntfy"],
    ):
        assert not re.findall(r"\{\w+\}", text)
        assert "GET" not in text
        assert test_alarm in text
    assert good_to_know in config["create_entry"]["ntfy"]


@pytest.mark.parametrize("language", ["en", "de"])
def test_ntfy_issue_names_the_entry(language: str) -> None:
    """The repair issue names the entry and nothing secret."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    issue = texts["issues"]["ntfy_entity_missing"]
    assert issue["title"]
    assert set(re.findall(r"\{(\w+)\}", issue["description"])) == {"title"}


@pytest.mark.parametrize("language", ["en", "de"])
def test_texts_name_no_vendor_and_no_price(language: str) -> None:
    """No company name of FF Agent and no price in the texts."""
    text = (INTEGRATION / "translations" / f"{language}.json").read_text("utf-8")
    for forbidden in ("mackoy", "consulting", "€", "eur ", "$"):
        assert forbidden not in text.lower()
    assert "Home Assistant Link" in text


def test_no_vendor_name_in_code_and_user_docs() -> None:
    """No company name of FF Agent in the code, README or CHANGELOG.

    This is an unofficial community project; the device info shows a neutral
    manufacturer and no text names the vendor or operator of FF Agent.
    """
    files = [
        path
        for path in INTEGRATION.rglob("*")
        if path.is_file() and path.suffix in {".py", ".json", ".yaml", ".yml"}
    ]
    files += [ROOT / "README.md", ROOT / "CHANGELOG.md"]
    assert len(files) > 10
    for path in files:
        text = path.read_text("utf-8").lower()
        for forbidden in ("mackoy", "consulting"):
            assert forbidden not in text, f"{forbidden!r} found in {path.name}"


def test_manifest_does_not_depend_on_ntfy() -> None:
    """ntfy stays optional: no dependency, no after_dependency (ADR 0003, 1.)."""
    manifest = _load(INTEGRATION / "manifest.json")
    assert "ntfy" not in manifest.get("dependencies", [])
    assert "ntfy" not in manifest.get("after_dependencies", [])


@pytest.mark.parametrize(
    ("language", "reconfigure", "service_url"),
    [("en", "Reconfigure", "service URL"), ("de", "Neu konfigurieren", "Dienst-URL")],
)
def test_ntfy_texts_use_the_terms_of_the_ui(
    language: str, reconfigure: str, service_url: str
) -> None:
    """The issue names the fallback; the guide uses the field name of ntfy."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    issue = texts["issues"]["ntfy_entity_missing"]["description"]
    assert reconfigure in issue.split("\n\n")[-1]
    assert service_url in texts["config"]["step"]["ntfy"]["description"]
    assert "Dienstadresse" not in json.dumps(texts, ensure_ascii=False)
    aborts = texts["config"]["abort"]
    assert "{webhook_url}" in aborts["reconfigure_successful_local"]
    assert "GET" in aborts["reconfigure_successful_ntfy_topic_unknown"]


@pytest.mark.parametrize(
    ("language", "subscription", "domain", "free"),
    [("en", "subscription", "domain", "free"), ("de", "Abo", "Domain", "kostenlos")],
)
def test_reconfigure_asks_how_the_alarm_arrives(
    language: str, subscription: str, domain: str, free: str
) -> None:
    """The field is a question and each option names what it requires."""
    texts = _load(INTEGRATION / "translations" / f"{language}.json")
    label = texts["config"]["step"]["reconfigure"]["data"]["alarm_source"]
    assert label.endswith("?")
    options = texts["selector"]["alarm_source"]["options"]
    assert subscription in options["webhook"]
    assert domain in options["webhook"]
    assert free in options["ntfy"]
