"""Privacy test for the replies (the whole life cycle: test_privacy_lifecycle.py).

All flows run with DEBUG logging. The reply ID, the webhook ID and the coordinates
must not show up in the log, in an error message, in a traceback, in the diagnostics
or in a state.
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import Mock

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import DOMAIN
from custom_components.ff_agent.diagnostics import async_get_config_entry_diagnostics

from .common import async_setup_entry
from .const import (
    ACCEPT_URL,
    LATITUDE,
    LOCATION_ENTITY,
    LONGITUDE,
    REJECT_URL,
    REPLY_ID,
    WEBHOOK_ID,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

COORDINATES = (str(LATITUDE), str(LONGITUDE), "1.234500", "6.789000")


def _our_log(caplog: pytest.LogCaptureFixture) -> str:
    """Return the log messages of this integration, with tracebacks."""
    return "\n".join(
        f"{record.getMessage()}\n{record.exc_text or ''}"
        for record in caplog.records
        if record.name.startswith("custom_components.ff_agent")
    )


async def _call(
    hass: HomeAssistant, domain: str, service: str, data: dict[str, object]
) -> None:
    await hass.services.async_call(domain, service, data, blocking=True)


async def test_replies_leave_no_secret_anywhere(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    location_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Buttons, actions, success and every kind of failure leak nothing."""
    caplog.set_level(logging.DEBUG)
    # A fixed time, so that no timestamp can accidentally contain a coordinate.
    freezer.move_to("2026-10-17 12:00:00+00:00")
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )
    await async_setup_entry(hass, location_entry)
    registry = er.async_get(hass)

    def entity_id(platform: str, key: str) -> str:
        found = registry.async_get_entity_id(
            platform, DOMAIN, f"{location_entry.entry_id}_{key}"
        )
        assert found is not None
        return found

    entry = {"config_entry_id": location_entry.entry_id}
    errors: list[BaseException] = []

    async def attempt(domain: str, service: str, data: dict[str, object]) -> None:
        try:
            await _call(hass, domain, service, data)
        except HomeAssistantError as err:
            errors.append(err)

    # Success: button with the location of the option, then the actions.
    aioclient_mock.get(ACCEPT_URL, text=f"answer for {REPLY_ID}")
    aioclient_mock.get(REJECT_URL)
    press = {"entity_id": entity_id("button", "accept")}
    await attempt("button", "press", press)
    await attempt(DOMAIN, "reject", entry)
    await attempt(
        DOMAIN,
        "accept",
        {**entry, "transport": "car", "latitude": LATITUDE, "longitude": LONGITUDE},
    )

    # Failures, each with an error text that contains the address like aiohttp's do.
    failures: list[dict[str, object]] = [
        {"exc": aiohttp.ClientConnectionError(f"Cannot connect to {ACCEPT_URL}")},
        {
            "exc": aiohttp.ClientResponseError(
                Mock(real_url=ACCEPT_URL), (), status=500, message=ACCEPT_URL
            )
        },
        {"exc": TimeoutError(ACCEPT_URL)},
        {"status": 404},
    ]
    for failure in failures:
        # Later than the repeat guard of the successful rejection above.
        freezer.tick(timedelta(seconds=11))
        aioclient_mock.clear_requests()
        aioclient_mock.get(REJECT_URL, **failure)
        await attempt(DOMAIN, "reject", entry)
    await hass.async_block_till_done()

    assert len(errors) == 4
    secrets = (REPLY_ID, WEBHOOK_ID, *COORDINATES)

    # Our own log contains neither the ID nor a coordinate; the whole log not the ID.
    assert REPLY_ID not in caplog.text
    ours = _our_log(caplog)
    assert "Sending reply" in ours
    for secret in secrets:
        assert secret not in ours

    # Errors shown to the user, including their tracebacks.
    for error in errors:
        rendered = f"{error}\n{''.join(traceback.format_exception(error))}"
        for secret in secrets:
            assert secret not in rendered

    # Diagnostics.
    result = await async_get_config_entry_diagnostics(hass, location_entry)
    diagnostics = json.dumps(result)
    for secret in (REPLY_ID, *COORDINATES):
        assert secret not in diagnostics

    # States and attributes of all entities of the entry.
    for registry_entry in er.async_entries_for_config_entry(
        registry, location_entry.entry_id
    ):
        state = hass.states.get(registry_entry.entity_id)
        assert state is not None
        dumped = json.dumps(state.as_dict(), default=str)
        for secret in (REPLY_ID, *COORDINATES):
            assert secret not in dumped
