"""HTTP Views and API endpoints for eCoal integration."""
from __future__ import annotations

import logging
import os
import re
import time

from aiohttp import web
from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import EcoalCoordinator

_LOGGER = logging.getLogger(__name__)


VIEWS_REGISTERED = "ecoal_views_registered"


def _get_coordinator(hass: HomeAssistant, entry_id: str | None = None) -> EcoalCoordinator | None:
    coordinators = hass.data.get(DOMAIN, {})
    if not coordinators:
        return None
    if entry_id and entry_id in coordinators:
        return coordinators[entry_id]
    return next(iter(coordinators.values()), None)


class EcoalComProxyView(HomeAssistantView):
    """Proxy view tunneling binary eCoal hex frames to/from furnace."""

    url = "/api/ecoal/com"
    name = "api:ecoal:com"
    requires_auth = False
    cors_allowed = False

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

        entry_id = request.query.get("entry_id")
        coordinator = _get_coordinator(request.app["hass"], entry_id)
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
    cors_allowed = False

    async def get(self, request: web.Request) -> web.Response:
        entry_id = request.query.get("entry_id")
        coordinator = _get_coordinator(request.app["hass"], entry_id)
        if coordinator is None or coordinator.data is None:
            return web.Response(text="eCoal status not available", status=503)

        return self.json(coordinator.data)


class EcoalControlView(HomeAssistantView):
    """High-level REST control endpoint for quick furnace operations."""

    url = "/api/ecoal/control"
    name = "api:ecoal:control"
    requires_auth = False
    cors_allowed = False

    async def post(self, request: web.Request) -> web.Response:
        entry_id = request.query.get("entry_id")
        coordinator = _get_coordinator(request.app["hass"], entry_id)
        if coordinator is None:
            return self.json({"error": "eCoal coordinator not available"}, status_code=503)

        try:
            body = await request.json()
        except Exception:
            return self.json({"error": "Invalid JSON body"}, status_code=400)

        action = body.get("action")
        value = body.get("value")

        try:
            if action == "set_boiler_temp":
                if value is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                temp = int(value)
                if not (30 <= temp <= 85):
                    return self.json({"error": f"Boiler temperature {temp}°C out of range [30..85]"}, status_code=400)
                success = await coordinator.client.set_target_boiler_temp(temp)
            elif action == "set_dhw_temp":
                if value is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                temp = int(value)
                if not (30 <= temp <= 70):
                    return self.json({"error": f"DHW temperature {temp}°C out of range [30..70]"}, status_code=400)
                success = await coordinator.client.set_target_dhw_temp(temp)
            elif action == "set_room_day_temp":
                temp_val = body.get("value", body.get("temp"))
                if temp_val is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                try:
                    temp = float(temp_val)
                except (ValueError, TypeError):
                    return self.json({"error": "Invalid room temperature value"}, status_code=400)
                if not (10.0 <= temp <= 35.0):
                    return self.json({"error": f"Room day temp {temp}°C out of range [10..35]"}, status_code=400)
                success = await coordinator.async_set_room_day_temp(temp)
            elif action == "set_room_night_temp":
                temp_val = body.get("value", body.get("temp"))
                if temp_val is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                try:
                    temp = float(temp_val)
                except (ValueError, TypeError):
                    return self.json({"error": "Invalid room temperature value"}, status_code=400)
                if not (10.0 <= temp <= 35.0):
                    return self.json({"error": f"Room night temp {temp}°C out of range [10..35]"}, status_code=400)
                success = await coordinator.async_set_room_night_temp(temp)
            elif action == "refill_hopper":
                kg_raw = body.get("kg", coordinator.hopper_capacity_kg)
                kg = int(kg_raw)
                if not (10 <= kg <= 1000):
                    return self.json({"error": f"Hopper capacity {kg} kg out of range [10..1000]"}, status_code=400)
                success = await coordinator.async_refill_hopper(kg)
            elif action == "set_feeder_mode":
                if value is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                mode = int(value)
                if mode not in (0, 1, 2, 3):
                    return self.json({"error": f"Invalid feeder mode {mode}. Expected 0, 1, 2, or 3"}, status_code=400)
                success = await coordinator.async_set_feeder_mode(mode)
            elif action == "set_dhw_priority":
                if value is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                success = await coordinator.async_set_dhw_priority(bool(value))
            elif action == "set_blower_correction":
                if value is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                corr = int(value)
                if not (-6 <= corr <= 6):
                    return self.json({"error": f"Blower correction {corr}% out of range [-6..6]"}, status_code=400)
                success = await coordinator.async_set_blower_correction(corr)
            elif action == "set_exhaust_temp_regulator":
                if value is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                success = await coordinator.async_set_exhaust_temp_regulator(bool(value))
            elif action == "set_mixer_mode":
                if value is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                mode = int(value)
                if mode not in (0, 1, 2):
                    return self.json({"error": f"Invalid mixer mode {mode}. Expected 0, 1, or 2"}, status_code=400)
                success = await coordinator.async_set_mixer_mode(mode)
            elif action == "ack_alarm":
                success = await coordinator.client.ack_alarms()
            elif action == "force_co_mode":
                lowered = bool(body.get("lowered", True))
                hours = int(body.get("hours", 2))
                success = await coordinator.async_force_co_mode(lowered=lowered, hours=hours)
            elif action == "force_schedule_mode":
                schedule_id = int(body.get("schedule_id", 24))
                lowered = bool(body.get("lowered", True))
                hours = int(body.get("hours", 2))
                if hasattr(coordinator, "async_force_schedule_mode"):
                    success = await coordinator.async_force_schedule_mode(schedule_id=schedule_id, lowered=lowered, hours=hours)
                else:
                    success = await coordinator.async_force_co_mode(lowered=lowered, hours=hours)
            elif action == "start_legionella":
                duration = int(body.get("duration", 30))
                target_dhw = int(body.get("target_dhw", 60))
                target_co = int(body.get("target_co", 65))
                success = await coordinator.async_start_legionella(
                    target_dhw=target_dhw,
                    target_co=target_co,
                    duration_mins=duration,
                )
            elif action == "stop_legionella":
                success = await coordinator.async_stop_legionella(reason="manual_cancel")
            elif action == "record_cleaning":
                success = await coordinator.async_record_cleaning()
            elif action == "set_cleaning_date":
                cleaned_at = body.get("last_cleaned_at") or body.get("date") or value
                coal_burned = body.get("coal_burned_kg")
                if coal_burned is not None:
                    try:
                        coal_burned = float(coal_burned)
                    except (ValueError, TypeError):
                        coal_burned = None
                success = await coordinator.async_set_cleaning_data(
                    last_cleaned_at=str(cleaned_at) if cleaned_at else None,
                    coal_burned_kg=coal_burned,
                )
            elif action == "set_legionella_date":
                last_run = body.get("last_run") or body.get("date") or value
                success = await coordinator.async_set_legionella_date(
                    str(last_run) if last_run else None
                )
            elif action == "extinguish":
                success = await coordinator.async_extinguish_furnace()
            elif action == "set_auto_mode":
                if value is None:
                    return self.json({"error": "Missing value"}, status_code=400)
                success = await coordinator.client.set_auto_mode(bool(value))
            elif action == "sync_clock":
                success = await coordinator.client.sync_clock()
            else:
                return self.json({"error": f"Unknown action: {action}"}, status_code=400)
        except (ValueError, TypeError) as err:
            return self.json({"error": f"Invalid parameter format: {err}"}, status_code=400)

        if success:
            await coordinator.async_request_refresh()
            return self.json({"success": True})
        return self.json({"error": "Furnace rejected command"}, status_code=500)


class EcoalIndexView(HomeAssistantView):
    """Serve index.html with strict anti-cache headers and dynamic asset versioning."""

    url = "/ecoal_ui/index.html"
    extra_urls = ["/ecoal_ui", "/ecoal_ui/"]
    name = "ecoal_ui:index"
    requires_auth = False
    cors_allowed = True

    async def get(self, request: web.Request) -> web.Response:
        return await self._serve(request)

    async def head(self, request: web.Request) -> web.Response:
        return await self._serve(request)

    async def _serve(self, request: web.Request) -> web.Response:
        index_path = os.path.join(os.path.dirname(__file__), "www", "index.html")
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return web.Response(status=404, text="index.html not found")

        ts = int(time.time())
        content = re.sub(r'bundle\.js(\?v=[^"\'\s>]+)?', f'bundle.js?v={ts}', content)
        content = re.sub(r'bundle\.css(\?v=[^"\'\s>]+)?', f'bundle.css?v={ts}', content)

        return web.Response(
            text=content,
            content_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )


async def async_setup_views(hass: HomeAssistant) -> None:
    """Register HTTP views and static directory for eCoal UI."""
    if hass.data.get(VIEWS_REGISTERED):
        return
    hass.data[VIEWS_REGISTERED] = True

    www_dir = os.path.join(os.path.dirname(__file__), "www")
    if hasattr(hass, "http") and hass.http is not None:
        try:
            await hass.http.async_register_static_paths([
                StaticPathConfig("/ecoal_ui", www_dir, cache_headers=False)
            ])
        except Exception as err:
            _LOGGER.debug("Could not register static path /ecoal_ui: %s", err)

        try:
            hass.http.register_view(EcoalIndexView)
            hass.http.register_view(EcoalComProxyView)
            hass.http.register_view(EcoalStatusView)
            hass.http.register_view(EcoalControlView)
        except Exception as err:
            _LOGGER.debug("Could not register HTTP views: %s", err)

    # Register HA Sidebar Panel with cache-busting timestamp
    ts = int(time.time())
    if hasattr(frontend, "async_register_built_in_panel") and "frontend" in hass.config.components:
        try:
            frontend.async_register_built_in_panel(
                hass,
                component_name="iframe",
                sidebar_title="Kocioł eCoal",
                sidebar_icon="mdi:fire",
                frontend_url_path="ecoal_panel",
                config={"url": f"/ecoal_ui/index.html?v={ts}"},
                require_admin=False,
                update=True,
            )
        except Exception as err:
            _LOGGER.debug("Could not register sidebar panel: %s", err)


async def async_unload_views(hass: HomeAssistant) -> None:
    """Unregister HA sidebar panel if no entries remain."""
    hass.data.pop(VIEWS_REGISTERED, None)
    if hasattr(frontend, "async_remove_panel") and "frontend" in hass.config.components:
        try:
            frontend.async_remove_panel(hass, "ecoal_panel")
        except Exception as err:
            _LOGGER.debug("Could not remove sidebar panel: %s", err)
