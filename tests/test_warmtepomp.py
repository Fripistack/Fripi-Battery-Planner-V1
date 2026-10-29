import sys, asyncio, datetime
import os as _os
_HIER = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.join(_HIER, "stubs"))
sys.path.insert(0, _os.path.join(_HIER, "..", "custom_components"))
from batterij_planner.warmtepomp import WpInstellingen, bepaal
I = WpInstellingen()
prijzen = [0.10]*20 + [0.20]*40 + [0.35]*36
def t(naam, **kw): b = bepaal(I, **kw); print(f"{naam:38s} -> {b.doel:5.1f} {b.stand:9s} rang={b.prijs_rang} | {b.reden}")
t("goedkoop", huidige_prijs=0.10, komende_prijzen=prijzen)
t("gemiddeld", huidige_prijs=0.20, komende_prijzen=prijzen)
t("duur", huidige_prijs=0.35, komende_prijzen=prijzen)
t("duur + warmtevraag", huidige_prijs=0.35, komende_prijzen=prijzen, warmtevraag=True)
t("gemiddeld + zon, accu vol", huidige_prijs=0.20, komende_prijzen=prijzen, pv_overschot_w=2500, accu_soc=96)
t("gemiddeld + zon, accu niet vol", huidige_prijs=0.20, komende_prijzen=prijzen, pv_overschot_w=2500, accu_soc=50)
t("geen prijzen", huidige_prijs=None, komende_prijzen=[])
I.stooklijn = 0.5; I.max_temp = 55
t("stooklijn, -5 C, duur", huidige_prijs=0.35, komende_prijzen=prijzen, buiten_temp=-5)
t("stooklijn, -5 C, goedkoop (max 55)", huidige_prijs=0.10, komende_prijzen=prijzen, buiten_temp=-5)

# coordinator
sys.path.insert(0, _HIER)
from helpers import price_day
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from batterij_planner.coordinator import BatterijPlannerCoordinator
from batterij_planner.const import STANDAARD_INSTELLINGEN, SUGGESTIES
def prijs(h): return 0.30 if 17 <= h < 21 else (0.02 if 1 <= h < 5 else 0.10)
async def main():
    hass = HomeAssistant(); TZ = dt_util.TZ
    dt_util.NOW[0] = datetime.datetime(2026, 10, 13, 2, 3, tzinfo=TZ)
    now = dt_util.NOW[0]
    hass.states.set("sensor.frank_prices_today", 96, {"prices": price_day(now.date(), prijs)})
    hass.states.set("sensor.frank_prices_tomorrow", 96, {"prices": price_day(now.date()+datetime.timedelta(days=1), prijs)})
    hass.states.set("sensor.pv_omvormer_battery_soc", 50); hass.states.set("sensor.pv_omvormer_household_load_power", 400)
    hass.states.set("sensor.pv_omvormer_total_pv_power", 0)
    hass.states.set("climate.warmtepomp_buffer", "heat", {"temperature": 45})
    hass.states.set("climate.t6", "heat", {"hvac_action": "idle"})
    for e in SUGGESTIES.values():
        if e.startswith("time."): hass.states.set(e, "00:00:00")
        if e.startswith("number."): hass.states.set(e, 50)
    opts = dict(STANDAARD_INSTELLINGEN, wp_setpoint_entity="climate.warmtepomp_buffer", wp_thermostaat_entity="climate.t6",
                wp_pv_vermogen_entity="sensor.pv_omvormer_total_pv_power")
    c = BatterijPlannerCoordinator(hass, ConfigEntry(dict(SUGGESTIES), opts))
    await c.async_start(); await c.async_refresh()
    print("\n02:03 advies (sturing uit):", {k: c.data["warmtepomp"][k] for k in ("doel","stand","reden")}, "calls:", hass.services.calls)
    c.wp_actief = True; await c.async_refresh()
    print("02:03 sturing aan:", hass.services.calls, "|", c.data["warmtepomp"]["laatste_actie"]); hass.services.calls.clear()
    hass.states.set("climate.warmtepomp_buffer", "heat", {"temperature": 50})
    dt_util.NOW[0] = datetime.datetime(2026, 10, 13, 18, 3, tzinfo=TZ); await c.async_refresh()
    print("18:03 duur:", c.data["warmtepomp"]["stand"], hass.services.calls); hass.services.calls.clear()
    hass.states.set("climate.warmtepomp_buffer", "heat", {"temperature": 40})
    hass.states.set("climate.t6", "heat", {"hvac_action": "heating"})
    dt_util.NOW[0] = datetime.datetime(2026, 10, 13, 18, 13, tzinfo=TZ); await c.async_refresh()
    print("18:13 duur + warmtevraag (binnen 30 min):", c.data["warmtepomp"]["stand"], c.data["warmtepomp"].get("wacht_tot"), hass.services.calls)
    dt_util.NOW[0] = datetime.datetime(2026, 10, 13, 18, 40, tzinfo=TZ); await c.async_refresh()
    print("18:40 duur + warmtevraag:", c.data["warmtepomp"]["stand"], hass.services.calls); hass.services.calls.clear()
    c.wp_actief = False; await c.async_wp_normaal(); print("uitgezet:", hass.services.calls)
asyncio.run(main())
