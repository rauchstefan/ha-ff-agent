"""Tests for determining the webhook URL."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.core_config import async_process_ha_core_config
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import CONF_CLOUDHOOK, CONF_CLOUDHOOK_URL, DOMAIN
from custom_components.ff_agent.webhook_url import (
    CloudhookUnavailable,
    UrlKind,
    async_create_webhook_url,
    async_get_webhook_url,
)

from .common import CloudNotAvailable, patch_cloud
from .const import CLOUDHOOK_URL, EXTERNAL_URL, INTERNAL_URL, WEBHOOK_ID

PATH = f"/api/webhook/{WEBHOOK_ID}"


@pytest.mark.usefixtures("external_url")
async def test_external_url(hass: HomeAssistant) -> None:
    """An external URL gives an absolute webhook URL."""
    assert await async_create_webhook_url(hass, WEBHOOK_ID) == (
        f"{EXTERNAL_URL}{PATH}",
        UrlKind.EXTERNAL,
        False,
    )


async def test_external_url_is_preferred_over_internal(hass: HomeAssistant) -> None:
    """With both URLs configured the external one wins."""
    await async_process_ha_core_config(
        hass, {"external_url": EXTERNAL_URL, "internal_url": INTERNAL_URL}
    )

    url, kind, cloudhook = await async_create_webhook_url(hass, WEBHOOK_ID)

    assert (url, kind, cloudhook) == (f"{EXTERNAL_URL}{PATH}", UrlKind.EXTERNAL, False)


async def test_internal_url_only(hass: HomeAssistant) -> None:
    """Without an external URL the internal URL is used and flagged as such."""
    await async_process_ha_core_config(hass, {"internal_url": INTERNAL_URL})

    assert await async_create_webhook_url(hass, WEBHOOK_ID) == (
        f"{INTERNAL_URL}{PATH}",
        UrlKind.INTERNAL,
        False,
    )


async def test_path_only(hass: HomeAssistant) -> None:
    """Without any URL only the path is returned."""
    assert await async_create_webhook_url(hass, WEBHOOK_ID) == (
        PATH,
        UrlKind.PATH_ONLY,
        False,
    )


async def test_cloud_creates_cloudhook(hass: HomeAssistant) -> None:
    """An active and connected cloud subscription yields a cloudhook."""
    with patch_cloud(hass) as cloud_mocks:
        result = await async_create_webhook_url(hass, WEBHOOK_ID)

    assert result == (CLOUDHOOK_URL, UrlKind.CLOUD, True)
    cloud_mocks["get_or_create"].assert_awaited_once_with(hass, WEBHOOK_ID)


@pytest.mark.usefixtures("external_url")
async def test_cloud_wins_over_external_url(hass: HomeAssistant) -> None:
    """The cloudhook is preferred over a configured external URL."""
    with patch_cloud(hass):
        _, kind, cloudhook = await async_create_webhook_url(hass, WEBHOOK_ID)

    assert (kind, cloudhook) == (UrlKind.CLOUD, True)


async def test_cloud_not_connected(hass: HomeAssistant) -> None:
    """A subscription without a connection raises and creates nothing."""
    with (
        patch_cloud(hass, connected=False) as cloud_mocks,
        pytest.raises(CloudhookUnavailable),
    ):
        await async_create_webhook_url(hass, WEBHOOK_ID)

    cloud_mocks["get_or_create"].assert_not_called()


@pytest.mark.parametrize("error", [CloudNotAvailable, TimeoutError, ValueError])
async def test_cloudhook_creation_failure_is_reported(
    hass: HomeAssistant, error: type[Exception]
) -> None:
    """Known errors while the cloudhook is created count as unavailable."""
    with patch_cloud(hass) as cloud_mocks:
        cloud_mocks["get_or_create"].side_effect = error
        with pytest.raises(CloudhookUnavailable):
            await async_create_webhook_url(hass, WEBHOOK_ID)


@pytest.mark.usefixtures("external_url")
async def test_cloud_without_subscription_falls_back(hass: HomeAssistant) -> None:
    """Without an active subscription the cloud is ignored."""
    with patch_cloud(hass, subscription=False) as cloud_mocks:
        result = await async_create_webhook_url(hass, WEBHOOK_ID)

    assert result == (f"{EXTERNAL_URL}{PATH}", UrlKind.EXTERNAL, False)
    cloud_mocks["get_or_create"].assert_not_called()
    cloud_mocks["is_connected"].assert_not_called()


@pytest.mark.parametrize(
    ("cloudhook", "cloudhook_url"),
    [(True, CLOUDHOOK_URL), (False, None)],
)
@pytest.mark.usefixtures("external_url")
async def test_get_webhook_url_of_entry(
    hass: HomeAssistant,
    entry_data: dict[str, Any],
    cloudhook: bool,
    cloudhook_url: str | None,
) -> None:
    """The stored cloudhook URL is returned as is, otherwise it is derived."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **entry_data,
            CONF_CLOUDHOOK: cloudhook,
            CONF_CLOUDHOOK_URL: cloudhook_url,
        },
    )

    url, kind = async_get_webhook_url(hass, entry)

    if cloudhook:
        assert (url, kind) == (CLOUDHOOK_URL, UrlKind.CLOUD)
    else:
        assert (url, kind) == (f"{EXTERNAL_URL}{PATH}", UrlKind.EXTERNAL)


async def test_get_webhook_url_of_entry_without_any_url(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Without a cloudhook and without a URL only the path is shown."""
    assert async_get_webhook_url(hass, mock_config_entry) == (
        PATH,
        UrlKind.PATH_ONLY,
    )


async def test_unexpected_cloudhook_error_is_not_swallowed(
    hass: HomeAssistant,
) -> None:
    """Errors that are not understood propagate to the caller."""
    with patch_cloud(hass) as cloud_mocks:
        cloud_mocks["get_or_create"].side_effect = RuntimeError
        with pytest.raises(RuntimeError):
            await async_create_webhook_url(hass, WEBHOOK_ID)
