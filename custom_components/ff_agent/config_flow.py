"""Config flow for the FF Agent integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN, NAME


class FFAgentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for FF Agent.

    Placeholder flow: a plain confirmation step without input fields. The
    credential fields follow once the FF Agent interface is known.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step started by the user."""
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})
        return self.async_show_form(step_id="user")
