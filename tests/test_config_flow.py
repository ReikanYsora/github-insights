"""Tests for the GitHub Insights config flow."""

from __future__ import annotations

from http import HTTPStatus

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.github_insights.const import CONF_REPOSITORY, DOMAIN

from .conftest import API, REPOSITORY, TOKEN, mock_github_api


async def test_user_flow_success(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A valid token and repository create a config entry."""
    mock_github_api(aioclient_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_TOKEN: TOKEN, CONF_REPOSITORY: REPOSITORY},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == REPOSITORY
    assert result["data"] == {
        CONF_ACCESS_TOKEN: TOKEN,
        CONF_REPOSITORY: REPOSITORY,
    }
    assert result["result"].unique_id == REPOSITORY.lower()


@pytest.mark.parametrize(
    ("status", "extra", "field", "error"),
    [
        (HTTPStatus.UNAUTHORIZED, {}, "base", "invalid_auth"),
        (HTTPStatus.NOT_FOUND, {}, CONF_REPOSITORY, "repo_not_found"),
        (
            HTTPStatus.FORBIDDEN,
            {"headers": {"X-RateLimit-Remaining": "0"}},
            "base",
            "rate_limit",
        ),
    ],
)
async def test_user_flow_errors_recover(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    status: HTTPStatus,
    extra: dict,
    field: str,
    error: str,
) -> None:
    """API errors are surfaced and the flow recovers on a retry."""
    aioclient_mock.get(f"{API}/repos/{REPOSITORY}", status=status, **extra)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_TOKEN: TOKEN, CONF_REPOSITORY: REPOSITORY},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {field: error}

    aioclient_mock.clear_requests()
    mock_github_api(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_TOKEN: TOKEN, CONF_REPOSITORY: REPOSITORY},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_invalid_repository(hass: HomeAssistant) -> None:
    """A malformed repository slug is rejected without any API call."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_TOKEN: TOKEN, CONF_REPOSITORY: "not-a-slug"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_REPOSITORY: "invalid_repository"}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Configuring the same repository twice aborts the flow."""
    mock_config_entry.add_to_hass(hass)
    mock_github_api(aioclient_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_TOKEN: TOKEN, CONF_REPOSITORY: REPOSITORY},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A reauth flow updates the stored token."""
    mock_config_entry.add_to_hass(hass)
    mock_github_api(aioclient_mock)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_TOKEN: "ghp_newtoken"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_ACCESS_TOKEN] == "ghp_newtoken"
