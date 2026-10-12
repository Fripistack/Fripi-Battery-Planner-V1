"""Sensoren van Batterij Planner."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BatterijPlannerConfigEntry
from .entity import BatterijPlannerEntity
from homeassistant.util import dt as dt_util

from .optimizer import MODI

DAGEN = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MODUS_NAAM = {"zelfverbruik": "Self-consumption", "vasthouden": "Hold", "laden": "Charge", "ontladen": "Discharge"}

ICONEN = {
    "zelfverbruik": "mdi:home-battery",
    "vasthouden": "mdi:battery-lock",
    "laden": "mdi:battery-charging",
    "ontladen": "mdi:battery-arrow-down",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: BatterijPlannerConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    c = entry.runtime_data
    async_add_entities(
        [ModusSensor(c), BesparingSensor(c), VolgendeActieSensor(c), DoelSocSensor(c), VerbruikSensor(c)]
    )


class ModusSensor(BatterijPlannerEntity, SensorEntity):
    """Huidige modus + het volledige plan als attributen."""

    _attr_translation_key = "modus"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(MODI)
    _unrecorded_attributes = frozenset({"blokken", "slots"})

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "modus")

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data or {}).get("modus")

    @property
    def icon(self) -> str:
        return ICONEN.get(self.native_value or "", "mdi:battery-alert")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data or {}
        sleutels = (
            "fout", "blok_einde", "soc_nu", "soc_doel_einde_blok", "kosten_plan", "kosten_zelfverbruik",
            "doorvoer_kwh", "horizon_einde", "kwartieren", "restwaarde_eur_kwh", "pv_bron",
            "pv_verwacht_kwh", "verbruik_verwacht_kwh", "sturing_actief", "bijgewerkt", "blokken", "slots",
        )
        attrs = {k: d[k] for k in sleutels if k in d}
        attrs["laatste_schrijfacties"] = self.coordinator.laatste_schrijfacties
        return attrs


class BesparingSensor(BatterijPlannerEntity, SensorEntity):
    _attr_translation_key = "besparing"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:cash-plus"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "besparing")

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("besparing")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data or {}
        return {"toelichting": "verschil met alleen zelfverbruik over de hele bekende prijshorizon",
                "horizon_einde": d.get("horizon_einde")}


class VolgendeActieSensor(BatterijPlannerEntity, SensorEntity):
    _attr_translation_key = "volgende_actie"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "volgende_actie")

    @property
    def native_value(self) -> str | None:
        blokken = (self.coordinator.data or {}).get("blokken") or []
        for b in blokken[1:]:
            if b["modus"] != "zelfverbruik":
                start = dt_util.parse_datetime(b["start"])
                eind = dt_util.parse_datetime(b["eind"])
                if start is None or eind is None:
                    return b["modus"]
                start, eind = dt_util.as_local(start), dt_util.as_local(eind)
                return f"{MODUS_NAAM[b['modus']]} {DAGEN[start.weekday()]} {start:%H:%M}–{eind:%H:%M}"
        return "None planned"


class DoelSocSensor(BatterijPlannerEntity, SensorEntity):
    _attr_translation_key = "doel_soc"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:battery-arrow-up-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "doel_soc")

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("soc_doel_einde_blok")


class VerbruikSensor(BatterijPlannerEntity, SensorEntity):
    _attr_translation_key = "verbruiksprofiel"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:chart-bell-curve"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "verbruiksprofiel")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.profiel.laatste_kwartier_w

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        p = self.coordinator.profiel
        return {"profiel_werkdag": p.werkdag, "profiel_weekend": p.weekend,
                "metingen_werkdag": p.n_werkdag, "metingen_weekend": p.n_weekend}
