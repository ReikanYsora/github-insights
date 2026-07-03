"""Asynchronous GitHub REST API client for the GitHub Insights integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from http import HTTPStatus
import re
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession

from .const import API_BASE_URL, API_VERSION, REQUEST_TIMEOUT

# Matches the ``page=<n>`` value of the ``rel="last"`` entry in a ``Link`` header,
# used to derive a total count without downloading every page.
_LINK_LAST_PAGE = re.compile(r'[?&]page=(\d+)>;\s*rel="last"')

_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class GitHubInsightsError(Exception):
    """Base exception for the GitHub Insights API client."""


class GitHubInsightsAuthError(GitHubInsightsError):
    """Raised when the token is invalid or lacks the required scopes."""


class GitHubInsightsNotFoundError(GitHubInsightsError):
    """Raised when the requested repository does not exist."""


class GitHubInsightsRateLimitError(GitHubInsightsError):
    """Raised when the GitHub API rate limit is exhausted."""


@dataclass(slots=True)
class RepositoryInsights:
    """Aggregated metrics for a single GitHub repository."""

    stargazers: int
    followers: int
    commits: int
    releases: int
    latest_release_name: str | None
    latest_release_tag: str | None
    latest_release_url: str | None
    latest_release_downloads: int
    total_downloads: int
    open_issues: int
    closed_issues: int


def is_valid_repository(repository: str) -> bool:
    """Return whether the string looks like an ``owner/repo`` slug."""
    return bool(_REPOSITORY_PATTERN.match(repository))


class GitHubInsightsClient:
    """Thin asynchronous wrapper around the GitHub REST API."""

    def __init__(self, session: ClientSession, token: str) -> None:
        """Initialize the client with a shared session and an access token."""
        self._session = session
        self._headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "home-assistant-github-insights",
        }

    @staticmethod
    def _raise_for_status(response: ClientResponse) -> None:
        """Translate an HTTP status into a typed exception."""
        if response.status == HTTPStatus.UNAUTHORIZED:
            raise GitHubInsightsAuthError("Invalid GitHub token")
        if response.status == HTTPStatus.FORBIDDEN:
            if response.headers.get("X-RateLimit-Remaining") == "0":
                raise GitHubInsightsRateLimitError("GitHub API rate limit exhausted")
            raise GitHubInsightsAuthError("Access forbidden, check the token scopes")
        if response.status == HTTPStatus.NOT_FOUND:
            raise GitHubInsightsNotFoundError("Repository not found")
        if response.status != HTTPStatus.OK:
            raise GitHubInsightsError(
                f"Unexpected status {response.status} from GitHub"
            )

    async def _get(
        self, path: str, *, params: dict[str, str] | None = None
    ) -> tuple[Any, str | None]:
        """Perform a GET request and return the JSON body and ``Link`` header."""
        url = f"{API_BASE_URL}{path}"
        try:
            async with (
                asyncio.timeout(REQUEST_TIMEOUT),
                self._session.get(
                    url, headers=self._headers, params=params
                ) as response,
            ):
                self._raise_for_status(response)
                return await response.json(), response.headers.get("Link")
        except (ClientError, TimeoutError) as err:
            raise GitHubInsightsError(
                f"Error communicating with GitHub: {err}"
            ) from err

    async def _get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """Return the core repository payload."""
        data, _ = await self._get(f"/repos/{owner}/{repo}")
        return data

    async def _get_user(self, login: str) -> dict[str, Any]:
        """Return the account payload for a user or organization."""
        data, _ = await self._get(f"/users/{login}")
        return data

    async def _get_commit_count(self, owner: str, repo: str, sha: str | None) -> int:
        """Return the number of commits on the default branch.

        GitHub does not expose a commit count directly, so we request a single
        commit and read the ``rel="last"`` page number from the ``Link`` header.
        """
        params = {"per_page": "1"}
        if sha:
            params["sha"] = sha
        data, link = await self._get(f"/repos/{owner}/{repo}/commits", params=params)
        if link and (match := _LINK_LAST_PAGE.search(link)):
            return int(match.group(1))
        return len(data)

    async def _get_releases(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Return every release of the repository, following pagination."""
        releases: list[dict[str, Any]] = []
        page = 1
        while True:
            data, _ = await self._get(
                f"/repos/{owner}/{repo}/releases",
                params={"per_page": "100", "page": str(page)},
            )
            releases.extend(data)
            if len(data) < 100:
                break
            page += 1
        return releases

    async def _get_issue_count(self, owner: str, repo: str, state: str) -> int:
        """Return the number of issues in a given state, excluding pull requests."""
        query = f"repo:{owner}/{repo} type:issue state:{state}"
        data, _ = await self._get(
            "/search/issues", params={"q": query, "per_page": "1"}
        )
        return int(data.get("total_count", 0))

    async def async_validate(self, repository: str) -> None:
        """Validate that the token can read the repository."""
        owner, _, repo = repository.partition("/")
        await self._get_repository(owner, repo)

    async def async_get_insights(self, repository: str) -> RepositoryInsights:
        """Fetch and aggregate every metric for the repository."""
        owner, _, repo = repository.partition("/")

        repository_data = await self._get_repository(owner, repo)
        owner_login = repository_data["owner"]["login"]
        default_branch = repository_data.get("default_branch")

        commits, releases, open_issues, closed_issues, account = await asyncio.gather(
            self._get_commit_count(owner, repo, default_branch),
            self._get_releases(owner, repo),
            self._get_issue_count(owner, repo, "open"),
            self._get_issue_count(owner, repo, "closed"),
            self._get_user(owner_login),
        )

        # Drafts are not publicly visible, so they count neither as releases nor
        # towards download totals. Prereleases are real releases and are kept,
        # but "latest release" mirrors the GitHub ``/releases/latest`` semantics
        # (newest published, non-prerelease) release.
        published = [release for release in releases if not release["draft"]]
        total_downloads = sum(
            asset["download_count"]
            for release in published
            for asset in release["assets"]
        )

        stable = sorted(
            (release for release in published if not release["prerelease"]),
            key=lambda release: release["published_at"] or "",
            reverse=True,
        )
        latest = stable[0] if stable else None

        return RepositoryInsights(
            stargazers=repository_data.get("stargazers_count", 0),
            followers=account.get("followers", 0),
            commits=commits,
            releases=len(published),
            latest_release_name=(
                (latest["name"] or latest["tag_name"]) if latest else None
            ),
            latest_release_tag=latest["tag_name"] if latest else None,
            latest_release_url=latest["html_url"] if latest else None,
            latest_release_downloads=(
                sum(asset["download_count"] for asset in latest["assets"])
                if latest
                else 0
            ),
            total_downloads=total_downloads,
            open_issues=open_issues,
            closed_issues=closed_issues,
        )
