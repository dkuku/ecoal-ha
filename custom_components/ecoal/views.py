"""HTTP Views and API endpoints for eCoal integration."""
from __future__ import annotations

import logging
import os
from typing import Any

from aiohttp import web
from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import EcoalCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_coordinator(hass: HomeAssistant) -> EcoalCoordinator | None:
    coordinators = hass.data.get(DOMAIN, {})
    if not coordinators:
        return None
    return next(iter(coordinators.values()), None)


class EcoalComProxyView(HomeAssistantView):
    """Proxy view tunneling binary eCoal hex frames to/from furnace."""

    url = "/api/ecoal/com"
    name = "api:ecoal:com"
    requires_auth = False
    cors_allowed = True

    async def get(self, request: web.Request) -> web.Response:
        return await self._handle(request)

    async def post(self, request: web.Request) -> web.Response:
        return await self._handle(request)

    async def _handle(self, request: web.Request) -> web.Response:
        com = request.query.get("com")
        if not com and request.method == "POST":
            try:
                body = await request.json()
                com = body.get("com")
            except Exception:
                pass

        if not com:
            return web.Response(text="Missing 'com' parameter", status=400)

        coordinator = _get_coordinator(request.app["hass"])
        if coordinator is None or coordinator.client is None:
            return web.Response(text="eCoal coordinator not available", status=503)

        response_text = await coordinator.client.send_raw_command(com)
        if response_text is None:
            return web.Response(text="Failed to communicate with furnace", status=502)

        return web.Response(text=response_text, content_type="text/plain")


class EcoalStatusView(HomeAssistantView):
    """View providing instant JSON cached status from coordinator."""

    url = "/api/ecoal/status"
    name = "api:ecoal:status"
    requires_auth = False
    cors_allowed = True

    async def get(self, request: web.Request) -> web.Response:
        coordinator = _get_coordinator(request.app["hass"])
        if coordinator is None or coordinator.data is None:
            return web.Response(text="eCoal status not available", status=503)

        return self.json(coordinator.data)


class EcoalControlView(HomeAssistantView):
    """High-level REST control endpoint for quick furnace operations."""

    url = "/api/ecoal/control"
    name = "api:ecoal:control"
    requires_auth = False
    cors_allowed = True

    async def post(self, request: web.Request) -> web.Response:
        coordinator = _get_coordinator(request.app["hass"])
        if coordinator is None:
            return self.json({"error": "eCoal coordinator not available"}, status_code=503)

        try:
            body = await request.json()
        except Exception:
            return self.json({"error": "Invalid JSON body"}, status_code=400)

        action = body.get("action")
        value = body.get("value")

        if action == "set_boiler_temp":
            if value is None:
                return self.json({"error": "Missing value"}, status_code=400)
            success = await coordinator.client.set_target_boiler_temp(int(value))
        elif action == "set_dhw_temp":
            if value is None:
                return self.json({"error": "Missing value"}, status_code=400)
            success = await coordinator.client.set_target_dhw_temp(int(value))
        elif action == "refill_hopper":
            kg = body.get("kg", coordinator.hopper_capacity_kg)
            success = await coordinator.async_refill_hopper(int(kg))
        elif action == "set_feeder_mode":
            if value is None:
                return self.json({"error": "Missing value"}, status_code=400)
            success = await coordinator.async_set_feeder_mode(int(value))
        elif action == "set_dhw_priority":
            if value is None:
                return self.json({"error": "Missing value"}, status_code=400)
            success = await coordinator.async_set_dhw_priority(bool(value))
        elif action == "set_blower_correction":
            if value is None:
                return self.json({"error": "Missing value"}, status_code=400)
            success = await coordinator.async_set_blower_correction(int(value))
        elif action == "set_exhaust_temp_regulator":
            if value is None:
                return self.json({"error": "Missing value"}, status_code=400)
            success = await coordinator.async_set_exhaust_temp_regulator(bool(value))
        elif action == "ack_alarm":
            success = await coordinator.client.ack_alarms()
        else:
            return self.json({"error": f"Unknown action: {action}"}, status_code=400)

        if success:
            await coordinator.async_request_refresh()
            return self.json({"success": True})
        return self.json({"error": "Furnace rejected command"}, status_code=500)


async def async_setup_views(hass: HomeAssistant) -> None:
    """Register HTTP views and static directory for eCoal UI."""
    www_dir = os.path.join(os.path.dirname(__file__), "www")
    if hasattr(hass, "http") and hass.http is not None:
        try:
            await hass.http.async_register_static_paths([
                StaticPathConfig("/ecoal_ui", www_dir, cache_headers=False)
            ])
        except Exception as err:
            _LOGGER.debug("Could not register static path /ecoal_ui: %s", err)

        try:
            hass.http.register_view(EcoalComProxyView)
            hass.http.register_view(EcoalStatusView)
            hass.http.register_view(EcoalControlView)
        except Exception as err:
            _LOGGER.debug("Could not register HTTP views: %s", err)

    # Register HA Sidebar Panel
    if hasattr(frontend, "async_register_built_in_panel") and "frontend" in hass.config.components:
        try:
            frontend.async_register_built_in_panel(
                hass,
                component_name="iframe",
                sidebar_title="Kocioł eCoal",
                sidebar_icon="mdi:fire",
                frontend_url_path="ecoal_panel",
                config={"url": "/ecoal_ui/index.html"},
                require_admin=False,
                update=True,
            )
        except Exception as err:
            _LOGGER.debug("Could not register sidebar panel: %s", err)


async def async_unload_views(hass: HomeAssistant) -> None:
    """Unregister HA sidebar panel if no entries remain."""
    if hasattr(frontend, "async_remove_panel") and "frontend" in hass.config.components:
        try:
            frontend.async_remove_panel(hass, "ecoal_panel")
        except Exception as err:
            _LOGGER.debug("Could not remove sidebar panel: %s", err)
