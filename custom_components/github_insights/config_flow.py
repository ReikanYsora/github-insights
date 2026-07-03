"""Config flow for the GitHub Insights integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, override

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import (
    GitHubInsightsAuthError,
    GitHubInsightsClient,
    GitHubInsightsError,
    GitHubInsightsNotFoundError,
    GitHubInsightsRateLimitError,
    is_valid_repository,
)
from .const import (
    CONF_REPOSITORY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCESS_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_REPOSITORY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCESS_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


async def _async_validate(
    client: GitHubInsightsClient, repository: str
) -> dict[str, str]:
    """Validate the token against the repository and map errors to form keys."""
    if not is_valid_repository(repository):
        return {CONF_REPOSITORY: "invalid_repository"}
    try:
        await client.async_validate(repository)
    except GitHubInsightsAuthError:
        return {"base": "invalid_auth"}
    except GitHubInsightsNotFoundError:
        return {CONF_REPOSITORY: "repo_not_found"}
    except GitHubInsightsRateLimitError:
        return {"base": "rate_limit"}
    except GitHubInsightsError:
        return {"base": "cannot_connect"}
    return {}


class GitHubInsightsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GitHub Insights."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> GitHubInsightsOptionsFlow:
        """Return the options flow handler."""
        return GitHubInsightsOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            repository = user_input[CONF_REPOSITORY].strip()
            await self.async_set_unique_id(repository.lower())
            self._abort_if_unique_id_configured()

            client = GitHubInsightsClient(
                async_get_clientsession(self.hass),
                user_input[CONF_ACCESS_TOKEN],
            )
            errors = await _async_validate(client, repository)
            if not errors:
                return self.async_create_entry(
                    title=repository,
                    data={
                        CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN],
                        CONF_REPOSITORY: repository,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @override
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauthentication flow triggered by an invalid token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication with a new token."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        repository = reauth_entry.data[CONF_REPOSITORY]

        if user_input is not None:
            client = GitHubInsightsClient(
                async_get_clientsession(self.hass),
                user_input[CONF_ACCESS_TOKEN],
            )
            errors = await _async_validate(client, repository)
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            description_placeholders={CONF_REPOSITORY: repository},
            errors=errors,
        )


class GitHubInsightsOptionsFlow(OptionsFlow):
    """Handle the options flow for GitHub Insights."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the update interval."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL])}
            )

        current = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UPDATE_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL,
                            max=MAX_UPDATE_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="min",
                        )
                    ),
                }
            ),
        )
