"""Config flow en options flow voor Batterij Planner."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .const import (
    BRON_KEYS,
    CONF_LAAD_EIND,
    CONF_LAAD_START,
    CONF_LAAD_STROOM,
    CONF_NOTIFY,
    CONF_ONTLAAD_EIND,
    CONF_ONTLAAD_START,
    CONF_ONTLAAD_STROOM,
    CONF_PRIJS_MORGEN,
    CONF_PRIJS_VANDAAG,
    CONF_PV_MORGEN,
    CONF_PV_REST,
    CONF_SOC,
    CONF_SOLCAST_MORGEN,
    CONF_SOLCAST_VANDAAG,
    CONF_SPANNING,
    CONF_VASTHOUDEN_STROOM,
    CONF_VERBRUIK,
    CONF_WERKMODUS,
    CONF_WERKMODUS_TOU,
    CONF_WP_BUFFER,
    CONF_WP_BUITEN,
    CONF_WP_MIN_MINUTEN,
    CONF_WP_PV,
    CONF_WP_SETPOINT,
    CONF_WP_THERMOSTAAT,
    DOMAIN,
    WP_ENTITY_KEYS,
    GEEN_MELDING,
    NIET_WIJZIGEN,
    OMVORMER_KEYS,
    STANDAARD_INSTELLINGEN,
    SUGGESTIES,
)

VERPLICHT = {CONF_SOC, CONF_VERBRUIK, CONF_PRIJS_VANDAAG, CONF_PRIJS_MORGEN,
             CONF_LAAD_START, CONF_LAAD_EIND, CONF_ONTLAAD_START, CONF_ONTLAAD_EIND,
             CONF_LAAD_STROOM, CONF_ONTLAAD_STROOM}

DOMEIN_PER_KEY = {
    CONF_SOC: "sensor", CONF_VERBRUIK: "sensor", CONF_PRIJS_VANDAAG: "sensor",
    CONF_PRIJS_MORGEN: "sensor", CONF_PV_REST: "sensor", CONF_PV_MORGEN: "sensor",
    CONF_SOLCAST_VANDAAG: "sensor", CONF_SOLCAST_MORGEN: "sensor",
    CONF_LAAD_START: "time", CONF_LAAD_EIND: "time", CONF_ONTLAAD_START: "time",
    CONF_ONTLAAD_EIND: "time", CONF_LAAD_STROOM: "number", CONF_ONTLAAD_STROOM: "number",
    CONF_WERKMODUS: "select",
    CONF_WP_SETPOINT: ["number", "climate", "water_heater"],
    CONF_WP_BUFFER: "sensor",
    CONF_WP_BUITEN: "sensor",
    CONF_WP_THERMOSTAAT: "climate",
    CONF_WP_PV: "sensor",
}


def _voorstel(hass: HomeAssistant, key: str, huidig: dict[str, Any]) -> str | None:
    if key in huidig:
        return huidig.get(key)
    sug = SUGGESTIES.get(key)
    if sug and hass.states.get(sug) is not None:
        return sug
    return None


def _entity_schema(hass: HomeAssistant, keys: list[str], huidig: dict[str, Any]) -> vol.Schema:
    velden: dict[Any, Any] = {}
    for key in keys:
        sel = selector.EntitySelector(selector.EntitySelectorConfig(domain=DOMEIN_PER_KEY[key]))
        voorstel = _voorstel(hass, key, huidig)
        if key in VERPLICHT:
            if voorstel:
                velden[vol.Required(key, default=voorstel)] = sel
            else:
                velden[vol.Required(key)] = sel
        else:
            velden[vol.Optional(key, description={"suggested_value": voorstel})] = sel
    return vol.Schema(velden)


def _met_lege_optionele(keys: list[str], user_input: dict[str, Any]) -> dict[str, Any]:
    """Leeggemaakte optionele velden expliciet op None zetten."""
    return {k: user_input.get(k) for k in keys}


def _controleer_bronnen(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    fouten: dict[str, str] = {}
    soc = hass.states.get(data.get(CONF_SOC) or "")
    if soc is None:
        fouten[CONF_SOC] = "niet_gevonden"
    else:
        try:
            float(soc.state)
        except ValueError:
            fouten[CONF_SOC] = "geen_getal"
    prijs = hass.states.get(data.get(CONF_PRIJS_VANDAAG) or "")
    if prijs is None or not isinstance(prijs.attributes.get("prices"), list):
        fouten[CONF_PRIJS_VANDAAG] = "geen_prijzen"
    return fouten


def _num(minimum: float, maximum: float, stap: float | str, eenheid: str | None = None) -> selector.NumberSelector:
    # unit_of_measurement alleen meegeven als er een eenheid is: HA eist een str
    # en weigert None (dan opent het formulier niet).
    extra = {"unit_of_measurement": eenheid} if eenheid else {}
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum, max=maximum, step=stap, mode=selector.NumberSelectorMode.BOX, **extra
        )
    )


SECTIES: dict[str, list[str]] = {
    "accu": [
        "capaciteit_kwh", "min_soc", "max_soc", "max_laad_w", "max_ontlaad_w",
        "vermogen_stappen", "rendement_laden", "rendement_ontladen", "slijtage_eur_kwh",
    ],
    "prijzen": ["saldering", "saldering_correctie", "teruglever_opslag", "eindwaarde_factor"],
    "voorspelling": ["pv_factor", "verbruik_fallback_w"],
    "omvormer": [CONF_SPANNING, CONF_VASTHOUDEN_STROOM, CONF_WERKMODUS_TOU],
    "meldingen": [CONF_NOTIFY],
}


def _plat(user_input: dict[str, Any]) -> dict[str, Any]:
    """Secties uit het formulier platslaan naar één dict met instellingen."""
    plat: dict[str, Any] = {}
    for key, waarde in user_input.items():
        if key in SECTIES and isinstance(waarde, dict):
            plat.update(waarde)
        else:
            plat[key] = waarde
    return plat


def _select(opties: list, custom: bool = False, vertaling: str | None = None) -> selector.SelectSelector:
    extra = {"translation_key": vertaling} if vertaling else {}
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=opties, custom_value=custom, mode=selector.SelectSelectorMode.DROPDOWN, **extra
        )
    )


def _instellingen_schema(hass: HomeAssistant, huidig: dict[str, Any]) -> vol.Schema:
    w = {**STANDAARD_INSTELLINGEN, **{k: v for k, v in huidig.items() if v is not None}}

    werkmodus_opties = [
        selector.SelectOptionDict(
            value=NIET_WIJZIGEN,
            label="Don't change the Storage Mode (inverter already in a TOU mode)",
        )
    ]
    sel_entity = huidig.get(CONF_WERKMODUS)
    st = hass.states.get(sel_entity) if sel_entity else None
    if st is not None:
        for opt in st.attributes.get("options", []):
            werkmodus_opties.append(selector.SelectOptionDict(value=str(opt), label=str(opt)))

    notify_opties = [
        selector.SelectOptionDict(value=GEEN_MELDING, label="No notification")
    ]
    for naam in sorted(hass.services.async_services_for_domain("notify")):
        notify_opties.append(selector.SelectOptionDict(value=f"notify.{naam}", label=f"notify.{naam}"))

    velden: dict[str, Any] = {
        "capaciteit_kwh": _num(1, 100, 0.1, "kWh"),
        "min_soc": _num(0, 60, 1, "%"),
        "max_soc": _num(40, 100, 1, "%"),
        "max_laad_w": _num(100, 20000, 100, "W"),
        "max_ontlaad_w": _num(100, 20000, 100, "W"),
        "vermogen_stappen": selector.BooleanSelector(),
        "rendement_laden": _num(70, 100, 0.5, "%"),
        "rendement_ontladen": _num(70, 100, 0.5, "%"),
        "slijtage_eur_kwh": _num(0, 0.3, 0.001, "€/kWh"),
        "saldering": _select(["auto", "aan", "uit"], vertaling="saldering"),
        "saldering_correctie": _num(0, 0.2, "any", "€/kWh"),
        "teruglever_opslag": _num(-0.1, 0.2, "any", "€/kWh"),
        "eindwaarde_factor": _num(0.3, 1.5, 0.05),
        "pv_factor": _num(0.3, 1.5, 0.05),
        "verbruik_fallback_w": _num(0, 5000, 10, "W"),
        CONF_SPANNING: _num(10, 1000, 0.1, "V"),
        CONF_VASTHOUDEN_STROOM: _num(0, 100, 1, "A"),
        CONF_WERKMODUS_TOU: _select(werkmodus_opties, custom=True),
        CONF_NOTIFY: _select(notify_opties, custom=True),
    }
    schema: dict[Any, Any] = {}
    for sectie, keys in SECTIES.items():
        sub = vol.Schema({vol.Required(k, default=w[k]): velden[k] for k in keys})
        schema[vol.Required(sectie)] = section(sub, {"collapsed": False})
    return vol.Schema(schema)


def _wp_schema(hass: HomeAssistant, huidig: dict[str, Any]) -> vol.Schema:
    w = {**STANDAARD_INSTELLINGEN, **{k: v for k, v in huidig.items() if v is not None}}
    regeling = vol.Schema(
        {
            vol.Required("wp_basis_temp", default=w["wp_basis_temp"]): _num(15, 70, 0.5, "°C"),
            vol.Required("wp_verhoging", default=w["wp_verhoging"]): _num(0, 20, 0.5, "K"),
            vol.Required("wp_verlaging", default=w["wp_verlaging"]): _num(0, 20, 0.5, "K"),
            vol.Required("wp_min_temp", default=w["wp_min_temp"]): _num(10, 70, 0.5, "°C"),
            vol.Required("wp_max_temp", default=w["wp_max_temp"]): _num(15, 75, 0.5, "°C"),
            vol.Required("wp_goedkoop_aandeel", default=w["wp_goedkoop_aandeel"]): _num(0, 50, 5, "%"),
            vol.Required("wp_duur_aandeel", default=w["wp_duur_aandeel"]): _num(0, 50, 5, "%"),
            vol.Required("wp_stooklijn", default=w["wp_stooklijn"]): _num(0, 3, 0.1, "K/°C"),
            vol.Required("wp_pv_overschot_w", default=w["wp_pv_overschot_w"]): _num(0, 10000, 100, "W"),
            vol.Required("wp_pv_min_soc", default=w["wp_pv_min_soc"]): _num(0, 100, 1, "%"),
            vol.Required("wp_niet_verlagen_bij_vraag", default=w["wp_niet_verlagen_bij_vraag"]): selector.BooleanSelector(),
            vol.Required(CONF_WP_MIN_MINUTEN, default=w[CONF_WP_MIN_MINUTEN]): _num(0, 240, 5, "min"),
        }
    )
    thermostaat = vol.Schema(
        {
            vol.Required("wp_t6_verhoging", default=w["wp_t6_verhoging"]): _num(0, 3, 0.5, "K"),
            vol.Required("wp_t6_verlaging", default=w["wp_t6_verlaging"]): _num(0, 3, 0.5, "K"),
            vol.Required("wp_t6_min_temp", default=w["wp_t6_min_temp"]): _num(10, 25, 0.5, "°C"),
            vol.Required("wp_t6_max_temp", default=w["wp_t6_max_temp"]): _num(15, 28, 0.5, "°C"),
        }
    )
    return vol.Schema(
        {
            vol.Required("apparaten"): section(_entity_schema(hass, WP_ENTITY_KEYS, huidig), {"collapsed": False}),
            vol.Required("regeling"): section(regeling, {"collapsed": False}),
            vol.Required("thermostaat"): section(thermostaat, {"collapsed": False}),
        }
    )


class BatterijPlannerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Eerste installatie: bronnen en omvormer kiezen."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        fouten: dict[str, str] = {}
        if user_input is not None:
            fouten = _controleer_bronnen(self.hass, user_input)
            if not fouten:
                self._data.update(_met_lege_optionele(BRON_KEYS, user_input))
                return await self.async_step_omvormer()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _entity_schema(self.hass, BRON_KEYS, {}), user_input or {}
            ),
            errors=fouten,
        )

    async def async_step_omvormer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(_met_lege_optionele(OMVORMER_KEYS, user_input))
            return self.async_create_entry(
                title="Batterij Planner",
                data=self._data,
                options=dict(STANDAARD_INSTELLINGEN),
            )
        return self.async_show_form(
            step_id="omvormer",
            data_schema=_entity_schema(self.hass, OMVORMER_KEYS, {}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BatterijPlannerOptionsFlow()


class BatterijPlannerOptionsFlow(OptionsFlow):
    """Later aanpassen via Configureren."""

    def _huidig(self) -> dict[str, Any]:
        return {**self.config_entry.data, **self.config_entry.options}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init", menu_options=["instellingen", "bronnen", "omvormer", "warmtepomp"]
        )

    async def async_step_warmtepomp(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fouten: dict[str, str] = {}
        if user_input is not None:
            apparaten = user_input.get("apparaten", {}) or {}
            regeling = user_input.get("regeling", {}) or {}
            thermostaat = user_input.get("thermostaat", {}) or {}
            if regeling.get("wp_min_temp", 0) >= regeling.get("wp_max_temp", 100):
                fouten["base"] = "wp_bereik"
            elif thermostaat.get("wp_t6_min_temp", 0) >= thermostaat.get("wp_t6_max_temp", 100):
                fouten["base"] = "t6_bereik"
            else:
                return self.async_create_entry(
                    data={
                        **self.config_entry.options,
                        **_met_lege_optionele(WP_ENTITY_KEYS, apparaten),
                        **regeling,
                        **thermostaat,
                    }
                )
        return self.async_show_form(
            step_id="warmtepomp", data_schema=_wp_schema(self.hass, self._huidig()), errors=fouten
        )

    async def async_step_instellingen(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            plat = _plat(user_input)
            if plat.get("min_soc", 0) >= plat.get("max_soc", 100):
                return self.async_show_form(
                    step_id="instellingen",
                    data_schema=_instellingen_schema(self.hass, {**self._huidig(), **plat}),
                    errors={"base": "soc_bereik"},
                )
            return self.async_create_entry(data={**self.config_entry.options, **plat})
        return self.async_show_form(
            step_id="instellingen", data_schema=_instellingen_schema(self.hass, self._huidig())
        )

    async def async_step_bronnen(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fouten: dict[str, str] = {}
        if user_input is not None:
            fouten = _controleer_bronnen(self.hass, user_input)
            if not fouten:
                return self.async_create_entry(
                    data={**self.config_entry.options, **_met_lege_optionele(BRON_KEYS, user_input)}
                )
        return self.async_show_form(
            step_id="bronnen",
            data_schema=_entity_schema(self.hass, BRON_KEYS, self._huidig()),
            errors=fouten,
        )

    async def async_step_omvormer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={**self.config_entry.options, **_met_lege_optionele(OMVORMER_KEYS, user_input)}
            )
        return self.async_show_form(
            step_id="omvormer", data_schema=_entity_schema(self.hass, OMVORMER_KEYS, self._huidig())
        )
