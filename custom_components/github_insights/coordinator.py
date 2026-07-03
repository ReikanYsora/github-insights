"""Data update coordinator for the GitHub Insights integration."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    GitHubInsightsAuthError,
    GitHubInsightsClient,
    GitHubInsightsError,
    RepositoryInsights,
)
from .const import (
    CONF_REPOSITORY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    LOGGER,
)

type GitHubInsightsConfigEntry = ConfigEntry[GitHubInsightsCoordinator]


class GitHubInsightsCoordinator(DataUpdateCoordinator[RepositoryInsights]):
    """Coordinate polling of a single GitHub repository."""

    config_entry: GitHubInsightsConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: GitHubInsightsConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.repository: str = config_entry.data[CONF_REPOSITORY]
        self.client = GitHubInsightsClient(
            async_get_clientsession(hass),
            config_entry.data[CONF_ACCESS_TOKEN],
        )
        minutes = config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=self.repository,
            update_interval=timedelta(minutes=minutes),
        )

    @override
    async def _async_update_data(self) -> RepositoryInsights:
        """Fetch the latest metrics from the GitHub API."""
        try:
            return await self.client.async_get_insights(self.repository)
        except GitHubInsightsAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except GitHubInsightsError as err:
            raise UpdateFailed(err) from err
