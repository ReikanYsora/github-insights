"""Tests for the GitHub Insights API client."""

from __future__ import annotations

from http import HTTPStatus

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.github_insights.api import (
    GitHubInsightsAuthError,
    GitHubInsightsClient,
    GitHubInsightsNotFoundError,
    GitHubInsightsRateLimitError,
    is_valid_repository,
)

from .conftest import REPOSITORY, TOKEN, mock_github_api


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("home-assistant/core", True),
        ("owner/repo.name-1", True),
        ("no-slash", False),
        ("too/many/slashes", False),
        ("", False),
    ],
)
def test_is_valid_repository(value: str, expected: bool) -> None:
    """The repository slug validator accepts only owner/name."""
    assert is_valid_repository(value) is expected


async def test_get_insights_aggregates_metrics(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The client aggregates every metric and ignores draft releases."""
    mock_github_api(aioclient_mock)
    client = GitHubInsightsClient(async_get_clientsession(hass), TOKEN)

    insights = await client.async_get_insights(REPOSITORY)

    assert insights.stargazers == 42000
    assert insights.followers == 1234
    assert insights.commits == 90000
    # The draft release is excluded from the count and the download totals.
    assert insights.releases == 2
    assert insights.latest_release_tag == "2024.1.0"
    assert insights.latest_release_name == "2024.1.0"
    assert insights.latest_release_downloads == 150
    assert insights.total_downloads == 350
    assert insights.open_issues == 500
    assert insights.closed_issues == 12000


async def test_invalid_token_raises_auth_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 401 response is surfaced as an auth error."""
    aioclient_mock.get(
        f"https://api.github.com/repos/{REPOSITORY}",
        status=HTTPStatus.UNAUTHORIZED,
    )
    client = GitHubInsightsClient(async_get_clientsession(hass), TOKEN)

    with pytest.raises(GitHubInsightsAuthError):
        await client.async_validate(REPOSITORY)


async def test_missing_repository_raises_not_found(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 404 response is surfaced as a not-found error."""
    aioclient_mock.get(
        f"https://api.github.com/repos/{REPOSITORY}",
        status=HTTPStatus.NOT_FOUND,
    )
    client = GitHubInsightsClient(async_get_clientsession(hass), TOKEN)

    with pytest.raises(GitHubInsightsNotFoundError):
        await client.async_validate(REPOSITORY)


async def test_rate_limit_raises_rate_limit_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 403 with no remaining quota is surfaced as a rate-limit error."""
    aioclient_mock.get(
        f"https://api.github.com/repos/{REPOSITORY}",
        status=HTTPStatus.FORBIDDEN,
        headers={"X-RateLimit-Remaining": "0"},
    )
    client = GitHubInsightsClient(async_get_clientsession(hass), TOKEN)

    with pytest.raises(GitHubInsightsRateLimitError):
        await client.async_validate(REPOSITORY)
