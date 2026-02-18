"""Data update coordinator for Ogniwo furnace."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import SENSOR_NAMES, OgniwoClient

_LOGGER = logging.getLogger(__name__)


class OgniwoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls furnace status every 30 seconds."""

    def __init__(self, hass: HomeAssistant, client: OgniwoClient) -> None:
        super().__init__(
            hass, _LOGGER, name="Ogniwo Furnace", update_interval=timedelta(seconds=30)
        )
        self.client = client
        self.firmware_version: str | None = None
        self.connected_sensors: set[str] = set()

    async def _async_update_data(self) -> dict[str, Any]:
        status = await self.client.get_status()
        if status is None:
            raise UpdateFailed("Failed to get status from furnace")
        if self.firmware_version is None:
            self.firmware_version = await self.client.get_firmware_version()
        if not self.connected_sensors:
            self.connected_sensors = {
                name for name in SENSOR_NAMES
                if status.get(f"{name}_state", 1) == 0
            }
        return status
