"""Diagnostics support for the GitHub Insights integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from .const import CONF_REPOSITORY
from .coordinator import GitHubInsightsConfigEntry

TO_REDACT = {CONF_ACCESS_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GitHubInsightsConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            CONF_REPOSITORY: entry.data[CONF_REPOSITORY],
            **async_redact_data(entry.data, TO_REDACT),
        },
        "data": asdict(coordinator.data) if coordinator.data else None,
    }
