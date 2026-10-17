"""Tests for eCoal config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.ecoal.const import DOMAIN


@pytest.mark.asyncio
async def test_config_flow_form(hass: HomeAssistant) -> None:
    """Test initial form display."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_config_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test connection error handling."""
    with patch(
        "custom_components.ecoal.config_flow.EcoalClient.test_connection",
        AsyncMock(return_value=False),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_HOST: "192.168.1.50",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "secret",
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_config_flow_success(hass: HomeAssistant) -> None:
    """Test successful config flow creation."""
    with patch(
        "custom_components.ecoal.config_flow.EcoalClient.test_connection",
        AsyncMock(return_value=True),
    ), patch(
        "custom_components.ecoal.async_setup_entry",
        AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_HOST: "192.168.1.50",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "secret",
            },
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "eCoal (192.168.1.50)"
        assert result["data"] == {
            CONF_HOST: "192.168.1.50",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
        }
        assert result["result"].unique_id == "192.168.1.50"
