"""Determine the URL that FF Agent has to call for a webhook.

Order of preference: Nabu Casa cloudhook, external URL, internal URL, bare path.
The returned URLs are secrets (they contain the webhook ID or the cloudhook ID) and
must never be logged.
"""

from __future__ import annotations

from contextlib import suppress
from enum import StrEnum

from homeassistant.components import webhook
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import NoURLAvailableError

from .const import CONF_CLOUDHOOK, CONF_CLOUDHOOK_URL
from .models import FFAgentConfigEntry


class UrlKind(StrEnum):
    """How the webhook URL was determined."""

    CLOUD = "cloud"
    EXTERNAL = "external"
    INTERNAL = "internal"
    PATH_ONLY = "path_only"


class CloudhookUnavailable(HomeAssistantError):
    """No cloudhook can be created: the cloud is not connected or failed.

    Deliberately not named like cloud.CloudNotConnected, which is a different class.
    """


@callback
def _async_local_webhook_url(
    hass: HomeAssistant, webhook_id: str
) -> tuple[str, UrlKind]:
    """Return the external, internal or path-only URL of a webhook."""
    try:
        return (
            webhook.async_generate_url(
                hass, webhook_id, allow_internal=False, prefer_external=True
            ),
            UrlKind.EXTERNAL,
        )
    except NoURLAvailableError:
        pass

    try:
        return (
            webhook.async_generate_url(hass, webhook_id, allow_external=False),
            UrlKind.INTERNAL,
        )
    except NoURLAvailableError:
        return webhook.async_generate_path(webhook_id), UrlKind.PATH_ONLY


async def async_create_webhook_url(
    hass: HomeAssistant, webhook_id: str
) -> tuple[str, UrlKind, bool]:
    """Return the webhook URL, its kind and whether a cloudhook was created.

    Raises CloudhookUnavailable if Nabu Casa Cloud has an active subscription but is
    not connected or the cloudhook cannot be created (cloud error, timeout). A
    cloudhook is only created in the cloud case.
    """
    if "cloud" in hass.config.components:
        # Lazy import: the cloud integration is only an optional (after) dependency.
        from homeassistant.components import cloud

        if cloud.async_active_subscription(hass):
            if not cloud.async_is_connected(hass):
                raise CloudhookUnavailable
            # A tuple variable: ruff would rewrite a literal tuple to the Python 3.14
            # form "except A, B:", which older interpreters reject.
            known_errors = (cloud.CloudNotAvailable, TimeoutError, ValueError)
            try:
                url = await cloud.async_get_or_create_cloudhook(hass, webhook_id)
            except known_errors:
                raise CloudhookUnavailable from None
            return url, UrlKind.CLOUD, True

    url, kind = _async_local_webhook_url(hass, webhook_id)
    return url, kind, False


@callback
def async_get_webhook_url(
    hass: HomeAssistant, entry: FFAgentConfigEntry
) -> tuple[str, UrlKind]:
    """Return the webhook URL of an existing entry without creating anything."""
    if entry.data[CONF_CLOUDHOOK] and (url := entry.data.get(CONF_CLOUDHOOK_URL)):
        return url, UrlKind.CLOUD
    return _async_local_webhook_url(hass, entry.data[CONF_WEBHOOK_ID])


async def async_delete_cloudhook(hass: HomeAssistant, webhook_id: str) -> None:
    """Delete the cloudhook of a webhook ID, if the cloud is loaded.

    A cloud that is gone or a cloudhook that does not exist anymore is no error: the
    result is the same, there is no cloudhook left.
    """
    if "cloud" not in hass.config.components:
        return
    # Lazy import: the cloud integration is only an optional (after) dependency.
    from homeassistant.components import cloud

    with suppress(cloud.CloudNotAvailable, ValueError):
        await cloud.async_delete_cloudhook(hass, webhook_id)
