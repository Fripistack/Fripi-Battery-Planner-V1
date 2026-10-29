"""Schakelaar om de sturing van de omvormer aan/uit te zetten."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import BatterijPlannerConfigEntry
from .entity import BatterijPlannerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: BatterijPlannerConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    c = entry.runtime_data
    async_add_entities([SturingSwitch(c), WarmtepompSwitch(c), ThermostaatSwitch(c)])


class SturingSwitch(BatterijPlannerEntity, SwitchEntity, RestoreEntity):
    """Uit = alleen rekenen (meekijken), aan = omvormer aansturen."""

    _attr_translation_key = "sturing"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "sturing")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        vorig = await self.async_get_last_state()
        if vorig is not None and vorig.state == "on":
            self.coordinator.actief = True
            self.hass.async_create_task(self.coordinator.async_request_refresh())

    @property
    def is_on(self) -> bool:
        return self.coordinator.actief

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.actief = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.actief = False
        self.async_write_ha_state()
        await self.coordinator.async_naar_zelfverbruik()


class WarmtepompSwitch(BatterijPlannerEntity, SwitchEntity, RestoreEntity):
    """Uit = alleen adviseren, aan = streeftemperatuur buffervat aansturen."""

    _attr_translation_key = "wp_sturing"
    _attr_icon = "mdi:heat-pump"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "wp_sturing")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        vorig = await self.async_get_last_state()
        if vorig is not None and vorig.state == "on":
            self.coordinator.wp_actief = True

    @property
    def is_on(self) -> bool:
        return self.coordinator.wp_actief

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.wp_actief = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.wp_actief = False
        self.async_write_ha_state()
        await self.coordinator.async_wp_normaal()
        await self.coordinator.async_request_refresh()


class ThermostaatSwitch(BatterijPlannerEntity, SwitchEntity, RestoreEntity):
    """Uit = alleen adviseren, aan = setpoint kamerthermostaat verschuiven."""

    _attr_translation_key = "t6_sturing"
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "t6_sturing")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        vorig = await self.async_get_last_state()
        if vorig is None:
            return
        # basis en geschreven setpoint bewaren over een herstart heen, anders
        # wordt een verschoven setpoint na een herstart de nieuwe basis
        try:
            basis = vorig.attributes.get("basis_setpoint")
            geschreven = vorig.attributes.get("planner_setpoint")
            self.coordinator.t6_basis = None if basis is None else float(basis)
            self.coordinator.t6_geschreven = None if geschreven is None else float(geschreven)
        except (TypeError, ValueError):
            pass
        if vorig.state == "on":
            self.coordinator.t6_actief = True

    @property
    def is_on(self) -> bool:
        return self.coordinator.t6_actief

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "basis_setpoint": self.coordinator.t6_basis,
            "planner_setpoint": self.coordinator.t6_geschreven,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.t6_actief = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.t6_actief = False
        await self.coordinator.async_t6_normaal()
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
