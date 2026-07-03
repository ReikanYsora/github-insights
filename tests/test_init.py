"""Tests for the GitHub Insights setup and sensors."""

from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import API, REPOSITORY, mock_github_api


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add the entry to hass and run setup."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_and_sensors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The integration sets up and creates the expected sensor states."""
    mock_github_api(aioclient_mock)
    await _setup(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data.update_interval == timedelta(minutes=5)

    assert hass.states.get("sensor.home_assistant_core_commits").state == "90000"
    assert hass.states.get("sensor.home_assistant_core_releases").state == "2"
    assert (
        hass.states.get("sensor.home_assistant_core_latest_release").state == "2024.1.0"
    )
    assert (
        hass.states.get("sensor.home_assistant_core_latest_release_downloads").state
        == "150"
    )
    assert hass.states.get("sensor.home_assistant_core_total_downloads").state == "350"
    assert hass.states.get("sensor.home_assistant_core_stars").state == "42000"
    assert hass.states.get("sensor.home_assistant_core_followers").state == "1234"
    assert hass.states.get("sensor.home_assistant_core_open_issues").state == "500"
    assert hass.states.get("sensor.home_assistant_core_closed_issues").state == "12000"

    latest = hass.states.get("sensor.home_assistant_core_latest_release")
    assert latest.attributes["name"] == "2024.1.0"
    assert latest.attributes["url"].endswith("/releases/2024.1.0")


async def test_setup_auth_failure_triggers_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An invalid token during setup puts the entry into the reauth state."""
    aioclient_mock.get(f"{API}/repos/{REPOSITORY}", status=HTTPStatus.UNAUTHORIZED)
    await _setup(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_diagnostics_redacts_token(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Diagnostics expose the metrics but redact the access token."""
    from custom_components.github_insights.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    mock_github_api(aioclient_mock)
    await _setup(hass, mock_config_entry)

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["entry"]["access_token"] == "**REDACTED**"
    assert diagnostics["entry"]["repository"] == REPOSITORY
    assert diagnostics["data"]["commits"] == 90000
    assert diagnostics["data"]["total_downloads"] == 350


async def test_unload_entry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The integration unloads cleanly."""
    mock_github_api(aioclient_mock)
    await _setup(hass, mock_config_entry)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
