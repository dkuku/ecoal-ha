"""Switches for Ogniwo Furnace."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OgniwoCoordinator


@dataclass(frozen=True, kw_only=True)
class OgniwoSwitchDescription(SwitchEntityDescription):
    value_key: str
    param: int | None = None
    is_auto_mode: bool = False
    requires_sensor: str | None = None


SWITCH_DESCRIPTIONS: tuple[OgniwoSwitchDescription, ...] = (
    OgniwoSwitchDescription(
        key="ch_pump",
        value_key="ch_pump",
        translation_key="ch_pump",
        icon="mdi:pump",
        param=0x0D,
    ),
    OgniwoSwitchDescription(
        key="dhw_pump",
        value_key="dhw_pump",
        translation_key="dhw_pump",
        icon="mdi:pump",
        param=0x0E,
    ),
    OgniwoSwitchDescription(
        key="mixer_pump",
        value_key="mixer_pump",
        translation_key="mixer_pump",
        icon="mdi:pump",
        param=0x0F,
        requires_sensor="floor_temp",
    ),
    OgniwoSwitchDescription(
        key="air_pump",
        value_key="air_pump",
        translation_key="air_pump",
        icon="mdi:fan",
        param=0x0B,
    ),
    OgniwoSwitchDescription(
        key="coal_feeder",
        value_key="coal_feeder",
        translation_key="coal_feeder",
        icon="mdi:screw-flat-top",
        param=0x0C,
    ),
    OgniwoSwitchDescription(
        key="auto_mode",
        value_key="auto_mode",
        translation_key="auto_mode",
        icon="mdi:auto-mode",
        is_auto_mode=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OgniwoCoordinator = hass.data[DOMAIN][entry.entry_id]
    connected = coordinator.connected_sensors
    async_add_entities(
        OgniwoSwitch(coordinator, description, entry)
        for description in SWITCH_DESCRIPTIONS
        if not description.requires_sensor or description.requires_sensor in connected
    )


class OgniwoSwitch(CoordinatorEntity[OgniwoCoordinator], SwitchEntity):
    entity_description: OgniwoSwitchDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OgniwoCoordinator,
        description: OgniwoSwitchDescription,
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        desc = self.entity_description
        if desc.is_auto_mode:
            await self.coordinator.client.set_auto_mode(True)
        else:
            await self.coordinator.client.set_switch(desc.param, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        desc = self.entity_description
        if desc.is_auto_mode:
            await self.coordinator.client.set_auto_mode(False)
        else:
            await self.coordinator.client.set_switch(desc.param, False)
        await self.coordinator.async_request_refresh()
