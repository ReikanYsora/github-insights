"""Common fixtures for the GitHub Insights tests."""

from __future__ import annotations

from collections.abc import Generator

from homeassistant.const import CONF_ACCESS_TOKEN
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.github_insights.const import CONF_REPOSITORY, DOMAIN

REPOSITORY = "home-assistant/core"
TOKEN = "ghp_testtoken"
API = "https://api.github.com"


@pytest.fixture(scope="session", autouse=True)
def _warm_dns_resolver_thread() -> Generator[None]:
    """Start aiohttp's async DNS resolver thread before any test runs.

    aiohttp resolves through pycares, which spawns a long-lived daemon thread on
    first use. Starting it once at session scope keeps the Home Assistant test
    harness cleanup check from flagging it as a lingering thread in whichever
    test happens to create the shared client session first.
    """
    try:
        import pycares

        pycares.Channel()
    except ImportError:
        pass
    yield


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=REPOSITORY,
        unique_id=REPOSITORY.lower(),
        data={CONF_ACCESS_TOKEN: TOKEN, CONF_REPOSITORY: REPOSITORY},
    )


def mock_github_api(aioclient_mock: AiohttpClientMocker) -> None:
    """Register a full, successful set of GitHub API responses."""
    aioclient_mock.get(
        f"{API}/repos/{REPOSITORY}",
        json={
            "stargazers_count": 42000,
            "default_branch": "dev",
            "owner": {"login": "home-assistant"},
        },
    )
    aioclient_mock.get(
        f"{API}/users/home-assistant",
        json={"followers": 1234},
    )
    aioclient_mock.get(
        f"{API}/repos/{REPOSITORY}/commits",
        json=[{"sha": "abc123"}],
        headers={
            "Link": (
                f'<{API}/repositories/1/commits?per_page=1&page=90000>; rel="last"'
            )
        },
    )
    aioclient_mock.get(
        f"{API}/repos/{REPOSITORY}/releases",
        json=[
            {
                "name": "2024.1.0",
                "tag_name": "2024.1.0",
                "html_url": f"https://github.com/{REPOSITORY}/releases/2024.1.0",
                "draft": False,
                "prerelease": False,
                "published_at": "2024-01-03T00:00:00Z",
                "assets": [{"download_count": 100}, {"download_count": 50}],
            },
            {
                "name": "2023.12.0",
                "tag_name": "2023.12.0",
                "html_url": f"https://github.com/{REPOSITORY}/releases/2023.12.0",
                "draft": False,
                "prerelease": False,
                "published_at": "2023-12-06T00:00:00Z",
                "assets": [{"download_count": 200}],
            },
            {
                "name": "draft",
                "tag_name": "draft",
                "html_url": f"https://github.com/{REPOSITORY}/releases/draft",
                "draft": True,
                "prerelease": False,
                "published_at": None,
                "assets": [{"download_count": 9999}],
            },
        ],
    )
    aioclient_mock.get(
        f"{API}/search/issues",
        params={"q": f"repo:{REPOSITORY} type:issue state:open", "per_page": "1"},
        json={"total_count": 500},
    )
    aioclient_mock.get(
        f"{API}/search/issues",
        params={"q": f"repo:{REPOSITORY} type:issue state:closed", "per_page": "1"},
        json={"total_count": 12000},
    )
