"""Buttons for eCoal controller."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoalCoordinator


@dataclass(frozen=True, kw_only=True)
class EcoalButtonDescription(ButtonEntityDescription):
    """Class describing eCoal button entities."""

    press_fn: Callable[[EcoalCoordinator], Coroutine[Any, Any, None]]


BUTTON_DESCRIPTIONS: tuple[EcoalButtonDescription, ...] = (
    EcoalButtonDescription(
        key="refill_hopper",
        translation_key="refill_hopper",
        icon="mdi:tray-arrow-down",
        press_fn=lambda coord: coord.async_refill_hopper(),
    ),
    EcoalButtonDescription(
        key="ack_alarms",
        translation_key="ack_alarms",
        icon="mdi:bell-check",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coord: _ack_and_refresh(coord),
    ),
    EcoalButtonDescription(
        key="sync_clock",
        translation_key="sync_clock",
        icon="mdi:clock-check-outline",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coord: _sync_and_refresh(coord),
    ),
)


async def _ack_and_refresh(coord: EcoalCoordinator) -> None:
    await coord.client.ack_alarms()
    await coord.async_request_refresh()


async def _sync_and_refresh(coord: EcoalCoordinator) -> None:
    await coord.client.sync_clock()
    await coord.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eCoal button entities."""
    coordinator: EcoalCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EcoalButton(coordinator, description, entry)
        for description in BUTTON_DESCRIPTIONS
    )


class EcoalButton(CoordinatorEntity[EcoalCoordinator], ButtonEntity):
    """Representation of an eCoal button entity."""

    entity_description: EcoalButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcoalCoordinator,
        description: EcoalButtonDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="eCoal",
            manufacturer="eCoal",
            model="Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    async def async_press(self) -> None:
        """Handle button press."""
        await self.entity_description.press_fn(self.coordinator)
