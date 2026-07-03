"""Sensor platform for the GitHub Insights integration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import RepositoryInsights
from .const import ATTRIBUTION, DOMAIN
from .coordinator import GitHubInsightsConfigEntry, GitHubInsightsCoordinator


@dataclass(frozen=True, kw_only=True)
class GitHubInsightsSensorEntityDescription(SensorEntityDescription):
    """Describes a GitHub Insights sensor entity."""

    value_fn: Callable[[RepositoryInsights], StateType]
    attr_fn: Callable[[RepositoryInsights], Mapping[str, Any] | None] = (
        lambda data: None
    )


SENSOR_DESCRIPTIONS: tuple[GitHubInsightsSensorEntityDescription, ...] = (
    GitHubInsightsSensorEntityDescription(
        key="commits",
        translation_key="commits",
        native_unit_of_measurement="commits",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.commits,
    ),
    GitHubInsightsSensorEntityDescription(
        key="releases",
        translation_key="releases",
        native_unit_of_measurement="releases",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.releases,
    ),
    GitHubInsightsSensorEntityDescription(
        key="latest_release",
        translation_key="latest_release",
        value_fn=lambda data: data.latest_release_tag,
        attr_fn=lambda data: {
            "name": data.latest_release_name,
            "url": data.latest_release_url,
        },
    ),
    GitHubInsightsSensorEntityDescription(
        key="latest_release_downloads",
        translation_key="latest_release_downloads",
        native_unit_of_measurement="downloads",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.latest_release_downloads,
    ),
    GitHubInsightsSensorEntityDescription(
        key="total_downloads",
        translation_key="total_downloads",
        native_unit_of_measurement="downloads",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.total_downloads,
    ),
    GitHubInsightsSensorEntityDescription(
        key="stargazers",
        translation_key="stargazers",
        native_unit_of_measurement="stars",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stargazers,
    ),
    GitHubInsightsSensorEntityDescription(
        key="followers",
        translation_key="followers",
        native_unit_of_measurement="followers",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.followers,
    ),
    GitHubInsightsSensorEntityDescription(
        key="open_issues",
        translation_key="open_issues",
        native_unit_of_measurement="issues",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.open_issues,
    ),
    GitHubInsightsSensorEntityDescription(
        key="closed_issues",
        translation_key="closed_issues",
        native_unit_of_measurement="issues",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.closed_issues,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GitHubInsightsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the GitHub Insights sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        GitHubInsightsSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class GitHubInsightsSensor(CoordinatorEntity[GitHubInsightsCoordinator], SensorEntity):
    """Representation of a GitHub Insights sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    entity_description: GitHubInsightsSensorEntityDescription

    def __init__(
        self,
        coordinator: GitHubInsightsCoordinator,
        entity_description: GitHubInsightsSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{coordinator.repository}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.repository)},
            name=coordinator.repository,
            manufacturer="GitHub",
            configuration_url=f"https://github.com/{coordinator.repository}",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    @override
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    @override
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the extra state attributes."""
        return self.entity_description.attr_fn(self.coordinator.data)
