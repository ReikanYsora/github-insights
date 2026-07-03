"""Constants for the GitHub Insights integration."""

from datetime import timedelta
from logging import Logger, getLogger
from typing import Final

DOMAIN: Final = "github_insights"

LOGGER: Logger = getLogger(__package__)

CONF_REPOSITORY: Final = "repository"

API_BASE_URL: Final = "https://api.github.com"
API_VERSION: Final = "2022-11-28"
REQUEST_TIMEOUT: Final = 30

UPDATE_INTERVAL: Final = timedelta(minutes=15)

ATTRIBUTION: Final = "Data provided by the GitHub API"
