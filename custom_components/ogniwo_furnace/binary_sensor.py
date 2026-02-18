"""Binary sensors for Ogniwo Furnace."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OgniwoCoordinator


@dataclass(frozen=True, kw_only=True)
class OgniwoBinarySensorDescription(BinarySensorEntityDescription):
    value_key: str


BINARY_SENSOR_DESCRIPTIONS: tuple[OgniwoBinarySensorDescription, ...] = (
    OgniwoBinarySensorDescription(
        key="alarm_active",
        value_key="alarm_active",
        translation_key="alarm_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle",
    ),
    OgniwoBinarySensorDescription(
        key="co_lowered_active",
        value_key="co_lowered_active",
        translation_key="co_lowered_active",
        icon="mdi:thermometer-minus",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoBinarySensorDescription(
        key="cwu_lowered_active",
        value_key="cwu_lowered_active",
        translation_key="cwu_lowered_active",
        icon="mdi:thermometer-minus",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoBinarySensorDescription(
        key="is_summer",
        value_key="is_summer",
        translation_key="is_summer",
        icon="mdi:weather-sunny",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

# Extra output state sensors - disabled by default, no manual control PARAM known
OUTPUT_BINARY_SENSOR_DESCRIPTIONS: tuple[OgniwoBinarySensorDescription, ...] = (
    OgniwoBinarySensorDescription(
        key="z1_pump",
        value_key="z1_pump",
        translation_key="z1_pump",
        icon="mdi:pump",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    OgniwoBinarySensorDescription(
        key="valve_3d",
        value_key="valve_3d",
        translation_key="valve_3d",
        icon="mdi:valve",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    OgniwoBinarySensorDescription(
        key="cwu_mixer",
        value_key="cwu_mixer",
        translation_key="cwu_mixer",
        icon="mdi:valve",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OgniwoCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = [
        OgniwoBinarySensor(coordinator, description, entry)
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]
    entities.extend(
        OgniwoBinarySensor(coordinator, description, entry)
        for description in OUTPUT_BINARY_SENSOR_DESCRIPTIONS
    )
    async_add_entities(entities)


class OgniwoBinarySensor(CoordinatorEntity[OgniwoCoordinator], BinarySensorEntity):
    entity_description: OgniwoBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OgniwoCoordinator,
        description: OgniwoBinarySensorDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ogniwo Furnace",
            manufacturer="Ogniwo Biecz",
            model="eCoal Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.value_key)
