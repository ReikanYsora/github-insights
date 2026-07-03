"""Constants for the GitHub Insights integration."""

from logging import Logger, getLogger
from typing import Final

DOMAIN: Final = "github_insights"

LOGGER: Logger = getLogger(__package__)

CONF_REPOSITORY: Final = "repository"
CONF_UPDATE_INTERVAL: Final = "update_interval"

API_BASE_URL: Final = "https://api.github.com"
API_VERSION: Final = "2022-11-28"
REQUEST_TIMEOUT: Final = 30

# Polling interval, in minutes, exposed to the user through the options flow.
DEFAULT_UPDATE_INTERVAL: Final = 5
MIN_UPDATE_INTERVAL: Final = 1
MAX_UPDATE_INTERVAL: Final = 1440

ATTRIBUTION: Final = "Data provided by the GitHub API"
