"""Privacy test over the whole life cycle of a config entry.

One person runs through everything the integration offers, with DEBUG logging for
``custom_components.ff_agent``: config flow, webhook call with a JSON payload, the
token requirement, a wrong and the right token, the button, the action with
coordinates, HTTP failures, a reconfigure that creates a new webhook access, unload
and removal. It runs without and with a Nabu Casa cloudhook.

Afterwards none of the secrets may show up in:

- the log records of this integration (all levels, with tracebacks),
- all WARNING and ERROR records of any logger,
- the diagnostics (fetched while the entry is loaded),
- the states and attributes of all entities of the entry,
- the texts and tracebacks of the errors that reach the user.

Known exception: Home Assistant itself logs the webhook ID on DEBUG level (the webhook
component, and the service data of a call). That is not under the control of this
integration, so the log of other loggers is only checked from WARNING upwards. The
test never calls an unregistered webhook, because Home Assistant logs the ID on INFO
level in that case (and on WARNING for a method that is not allowed).
"""

from __future__ import annotations

import json
import logging
import traceback
from collections.abc import Mapping
from contextlib import ExitStack
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import call

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.aiohttp import MockRequest

from custom_components.ff_agent.const import (
    CONF_DEFAULT_TRANSPORT,
    CONF_HEADER_TOKEN,
    CONF_LOCATION_ENTITY,
    CONF_REGENERATE_WEBHOOK,
    CONF_REPLY_URL,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DOMAIN,
    ISSUE_TOKEN_REJECTED,
    TOKEN_HEADER,
)
from custom_components.ff_agent.diagnostics import async_get_config_entry_diagnostics

from .common import patch_cloud
from .const import (
    ACCEPT_URL,
    CLOUDHOOK_URL,
    LATITUDE,
    LOCATION_ENTITY,
    LONGITUDE,
    NEW_CLOUDHOOK_URL,
    OTHER_ACCEPT_URL,
    OTHER_REPLY_ID,
    OTHER_REPLY_URL,
    REJECT_URL,
    REPLY_ID,
    REPLY_URL,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

# Invented values that stand for the content of a real alarm.
PAYLOAD_SECRETS = {
    "payload keyword": "Payload-Keyword-Secret",
    "payload street": "Payload-Street-Secret 99",
    "payload city": "Payload-City-Secret",
    "payload unit": "Payload-Unit-Secret",
    "query value": "Query-Value-Secret",
    "header value": "Header-Value-Secret",
}
PAYLOAD = {
    "keyword": PAYLOAD_SECRETS["payload keyword"],
    "address": {
        "street": PAYLOAD_SECRETS["payload street"],
        "city": PAYLOAD_SECRETS["payload city"],
    },
    "units": [PAYLOAD_SECRETS["payload unit"]],
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
}
QUERY = f"key={PAYLOAD_SECRETS['query value']}"
WRONG_TOKEN = "wrong-token-placeholder-not-the-real-one"


def _render(record: logging.LogRecord) -> str:
    """Return the message of a record together with its traceback, if any."""
    text = record.getMessage()
    if record.exc_info and record.exc_info[1] is not None:
        text += "\n" + "".join(traceback.format_exception(record.exc_info[1]))
    return f"{text}\n{record.exc_text or ''}"


def _leaks(text: str, secrets: Mapping[str, str]) -> list[str]:
    """Return the labels of the secrets that occur in the text."""
    return sorted(label for label, value in secrets.items() if value in text)


async def _call_webhook(
    hass: HomeAssistant, webhook_id: str, token: str | None = None
) -> int:
    """Call the webhook like FF Agent does through a cloudhook; return the status."""
    headers = {
        "Content-Type": "application/json",
        "X-Custom-Header": PAYLOAD_SECRETS["header value"],
    }
    if token is not None:
        headers[TOKEN_HEADER] = token
    request = MockRequest(
        json.dumps(PAYLOAD).encode(),
        "test",
        method="POST",
        headers=headers,
        query_string=QUERY,
    )
    response = await webhook.async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()
    return response.status


@pytest.mark.usefixtures("external_url")
@pytest.mark.parametrize("with_cloud", [False, True], ids=["local", "cloudhook"])
async def test_whole_life_cycle_leaks_no_secret(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
    with_cloud: bool,
) -> None:
    """From the config flow to the removal, no secret leaves the places it belongs."""
    caplog.set_level(logging.DEBUG, logger="custom_components.ff_agent")
    # A fixed time, so that no timestamp can accidentally contain a coordinate.
    freezer.move_to("2026-10-17 12:00:00+00:00")
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )

    stack = ExitStack()
    cloud_mocks = stack.enter_context(patch_cloud(hass)) if with_cloud else None
    with stack:
        secrets: dict[str, str] = {
            "reply ID": REPLY_ID,
            "reply URL": REPLY_URL,
            "latitude": str(LATITUDE),
            "longitude": str(LONGITUDE),
            "latitude in a query": f"{LATITUDE:.6f}",
            "longitude in a query": f"{LONGITUDE:.6f}",
            "wrong token": WRONG_TOKEN,
            **PAYLOAD_SECRETS,
        }
        # Checked at the end, one text per look at diagnostics and states.
        artifacts: list[str] = []
        errors: list[HomeAssistantError] = []
        registry = er.async_get(hass)

        def entity_id(platform: str, key: str) -> str:
            found = registry.async_get_entity_id(
                platform, DOMAIN, f"{entry.entry_id}_{key}"
            )
            assert found is not None
            return found

        async def snapshot() -> None:
            """Look at diagnostics, issues and the states of all entities."""
            diagnostics = await async_get_config_entry_diagnostics(hass, entry)
            artifacts.append(json.dumps(diagnostics, default=str))
            for registry_entry in er.async_entries_for_config_entry(
                registry, entry.entry_id
            ):
                state = hass.states.get(registry_entry.entity_id)
                if state is not None:
                    artifacts.append(json.dumps(state.as_dict(), default=str))
            for (domain, _id), issue in ir.async_get(hass).issues.items():
                if domain == DOMAIN:
                    artifacts.append(repr(issue))

        async def attempt(domain: str, service: str, data: dict[str, Any]) -> None:
            """Call an action; what reaches the user as an error is collected."""
            try:
                await hass.services.async_call(domain, service, data, blocking=True)
            except HomeAssistantError as err:
                errors.append(err)

        # 1. Config flow.
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "Test Person", CONF_REPLY_URL: REPLY_URL}
        )
        await hass.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY
        entry = result["result"]
        assert entry.state is ConfigEntryState.LOADED
        webhook_id = entry.data[CONF_WEBHOOK_ID]
        secrets["webhook ID"] = webhook_id
        secrets["webhook URL"] = result["description_placeholders"]["webhook_url"]
        secrets["token"] = entry.data[CONF_HEADER_TOKEN]
        if with_cloud:
            assert secrets["webhook URL"] == CLOUDHOOK_URL
            secrets["cloudhook URL"] = CLOUDHOOK_URL
        await snapshot()

        # 2. A webhook call with a JSON payload.
        assert await _call_webhook(hass, webhook_id) == 200
        assert entry.runtime_data.alarm.calls_total == 1
        await snapshot()

        # 3. Require the token through the options flow, with a location for replies.
        options = await hass.config_entries.options.async_init(entry.entry_id)
        assert options["type"] is FlowResultType.FORM
        options = await hass.config_entries.options.async_configure(
            options["flow_id"],
            {
                CONF_REQUIRE_TOKEN: True,
                CONF_RESET_MINUTES: 30,
                CONF_DEFAULT_TRANSPORT: "car",
                CONF_LOCATION_ENTITY: LOCATION_ENTITY,
            },
        )
        await hass.async_block_till_done()
        assert options["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options[CONF_REQUIRE_TOKEN] is True

        # 4. A wrong token and no token are refused, the right one is let through.
        assert await _call_webhook(hass, webhook_id, WRONG_TOKEN) == 401
        assert await _call_webhook(hass, webhook_id) == 401
        assert entry.runtime_data.alarm.rejected_total == 2
        issue_id = ISSUE_TOKEN_REJECTED.format(entry_id=entry.entry_id)
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
        await snapshot()
        assert await _call_webhook(hass, webhook_id, secrets["token"]) == 200
        assert entry.runtime_data.alarm.calls_total == 1
        await snapshot()

        # 5. The button "accept" sends the location of the option.
        aioclient_mock.get(ACCEPT_URL, text=f"answer for {REPLY_ID}")
        aioclient_mock.get(REJECT_URL)
        await attempt("button", "press", {"entity_id": entity_id("button", "accept")})
        assert aioclient_mock.call_count == 1
        _method, url, _data, _headers = aioclient_mock.mock_calls[0]
        assert dict(url.query)["lat"] == f"{LATITUDE:.6f}"
        await snapshot()

        # 6. The action with coordinates (later than the repeat guard of the button).
        freezer.tick(timedelta(seconds=11))
        entry_data = {"config_entry_id": entry.entry_id}
        coordinates = {"latitude": LATITUDE, "longitude": LONGITUDE}
        accept_data = {**entry_data, "transport": "car", **coordinates}
        await attempt(DOMAIN, "accept", accept_data)
        assert aioclient_mock.call_count == 2
        await snapshot()

        # 7. HTTP failures. The text of aiohttp's errors contains the address.
        address = f"{ACCEPT_URL}?transport=CAR&lat={LATITUDE:.6f}&lng={LONGITUDE:.6f}"
        failures: list[tuple[str, str, dict[str, Any]]] = [
            ("accept", ACCEPT_URL, {"status": 500, "text": address}),
            (
                "accept",
                ACCEPT_URL,
                {"exc": aiohttp.ClientConnectionError(f"Cannot connect to {address}")},
            ),
            ("reject", REJECT_URL, {"exc": TimeoutError(REJECT_URL)}),
        ]
        action_data = {"accept": accept_data, "reject": entry_data}
        for action, mocked_url, failure in failures:
            freezer.tick(timedelta(seconds=11))
            aioclient_mock.clear_requests()
            aioclient_mock.get(mocked_url, **failure)
            await attempt(DOMAIN, action, action_data[action])
        await hass.async_block_till_done()
        assert len(errors) == 3
        await snapshot()

        # 8. Reconfigure: a new reply URL and a new webhook access.
        old_webhook_id = webhook_id
        old_token = secrets["token"]
        secrets["old webhook ID"] = old_webhook_id
        secrets["old token"] = old_token
        secrets["new reply ID"] = OTHER_REPLY_ID
        secrets["new reply URL"] = OTHER_REPLY_URL
        if cloud_mocks is not None:
            secrets["old cloudhook URL"] = CLOUDHOOK_URL
            cloud_mocks["get_or_create"].return_value = NEW_CLOUDHOOK_URL
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert result["step_id"] == "reconfigure"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_REPLY_URL: OTHER_REPLY_URL, CONF_REGENERATE_WEBHOOK: True},
        )
        await hass.async_block_till_done()
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful_new_webhook"
        new_webhook_id = entry.data[CONF_WEBHOOK_ID]
        new_token = entry.data[CONF_HEADER_TOKEN]
        assert new_webhook_id != old_webhook_id
        assert new_token != old_token
        # The closing dialog shows the new access once; that is its purpose.
        assert result["description_placeholders"]["token"] == new_token
        secrets["webhook ID"] = new_webhook_id
        secrets["token"] = new_token
        secrets["old webhook URL"] = secrets["webhook URL"]
        secrets["webhook URL"] = result["description_placeholders"]["webhook_url"]
        if cloud_mocks is not None:
            assert secrets["webhook URL"] == NEW_CLOUDHOOK_URL
            secrets["cloudhook URL"] = NEW_CLOUDHOOK_URL
        assert entry.state is ConfigEntryState.LOADED

        # The new access works, and the new reply URL is used.
        assert await _call_webhook(hass, new_webhook_id, new_token) == 200
        assert entry.runtime_data.alarm.calls_total == 1
        aioclient_mock.clear_requests()
        aioclient_mock.get(OTHER_ACCEPT_URL)
        freezer.tick(timedelta(seconds=11))
        await attempt("button", "press", {"entity_id": entity_id("button", "accept")})
        assert aioclient_mock.call_count == 1
        _method, url, _data, _headers = aioclient_mock.mock_calls[0]
        assert url.path.endswith(f"{OTHER_REPLY_ID}/accept")
        assert len(errors) == 3

        # 9. Diagnostics while the entry is loaded, then unload.
        await snapshot()
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
        await snapshot()

        # 10. Remove.
        entity_ids = [
            registry_entry.entity_id
            for registry_entry in er.async_entries_for_config_entry(
                registry, entry.entry_id
            )
        ]
        assert len(entity_ids) >= 5
        assert await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()
        assert all(hass.states.get(entity) is None for entity in entity_ids)
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
        if cloud_mocks is not None:
            # The old cloudhook went with the reconfigure, the new one with the removal.
            assert cloud_mocks["delete"].await_args_list == [
                call(hass, old_webhook_id),
                call(hass, new_webhook_id),
            ]

    # The log of this integration: all levels, all secrets, with tracebacks.
    ours = "\n".join(
        _render(record)
        for record in caplog.records
        if record.name.startswith("custom_components.ff_agent")
    )
    for expected in (
        "Received a webhook call",
        "Rejected a webhook call",
        "Sending reply",
        "Alarm recognized",
    ):
        assert expected in ours
    assert _leaks(ours, secrets) == []

    # Everything that was logged as WARNING or ERROR, whoever logged it.
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    serious = "\n".join(_render(record) for record in warnings)
    assert "HTTP status 500" in serious
    assert _leaks(serious, secrets) == []

    # Diagnostics, issues and states, at every look.
    assert len(artifacts) >= 10
    for artifact in artifacts:
        assert _leaks(artifact, secrets) == []

    # What reached the user as an error, including the traceback and the details.
    assert len(errors) == 3
    for error in errors:
        rendered = "\n".join(
            (
                str(error),
                repr(error),
                str(getattr(error, "translation_placeholders", None)),
                "".join(traceback.format_exception(error)),
            )
        )
        assert _leaks(rendered, secrets) == []
