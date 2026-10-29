import sys, asyncio, datetime
import os as _os
_HIER = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.join(_HIER, "stubs"))
sys.path.insert(0, _os.path.join(_HIER, "..", "custom_components"))
sys.path.insert(0, _HIER)
from helpers import price_day
from homeassistant.core import HomeAssistant, Event, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from batterij_planner.coordinator import BatterijPlannerCoordinator
from batterij_planner.const import STANDAARD_INSTELLINGEN, SUGGESTIES, CONF_NOTIFY
TZ = dt_util.TZ

def prijs(h):
    if 6.75 <= h < 9: return 0.20
    if 11 <= h < 15.5: return 0.01
    if 17.5 <= h < 21: return 0.18
    if 1 <= h < 5: return 0.06
    return 0.10

async def main():
    hass = HomeAssistant()
    now = dt_util.NOW[0]
    hass.states.set("sensor.frank_prices_today", 96, {"prices": price_day(now.date(), prijs)})
    hass.states.set("sensor.frank_prices_tomorrow", "unavailable", {})
    hass.states.set("sensor.pv_omvormer_battery_soc", 40)
    hass.states.set("sensor.pv_omvormer_household_load_power", 500)
    hass.states.set("sensor.energy_production_today_remaining", 0, {"unit_of_measurement": "kWh"})
    hass.states.set("sensor.energy_production_tomorrow", 12000, {"unit_of_measurement": "Wh"})
    for k, e in SUGGESTIES.items():
        if e.startswith("time."): hass.states.set(e, "00:00:00")
        if e.startswith("number."): hass.states.set(e, 50)
    hass.states.set("select.pv_omvormer_work_mode", "Self-Use", {"options": ["Self-Use", "Self-Use + TOU"]})
    opts = dict(STANDAARD_INSTELLINGEN); opts["werkmodus_tou"] = "Self-Use + TOU"; opts[CONF_NOTIFY] = "notify.mobile_app_frits"
    entry = ConfigEntry(dict(SUGGESTIES), opts)
    c = BatterijPlannerCoordinator(hass, entry)
    await c.async_start()
    await c.async_refresh()
    print("1) alleen vandaag, sturing uit:", c.data["modus"], "| fout:", c.data.get("fout"), "| calls:", len(hass.services.calls))

    # morgenprijzen komen binnen -> melding + herberekening
    old = hass.states.get("sensor.frank_prices_tomorrow")
    hass.states.set("sensor.frank_prices_tomorrow", 96, {"prices": price_day(now.date() + datetime.timedelta(days=1), prijs)})
    c.actief = True
    c._prijzen_event(Event({"old_state": old, "new_state": hass.states.get("sensor.frank_prices_tomorrow")}))
    await asyncio.sleep(0.05)
    print("2) met morgen:", c.data["modus"], "tot", c.data["blok_einde"], "pv", c.data["pv_verwacht_kwh"], "besparing", c.data["besparing"])
    for call in hass.services.calls: print("    ", call)
    hass.services.calls.clear()

    # tijd vooruit naar 01:05 -> laden verwacht
    dt_util.NOW[0] = datetime.datetime(2026, 9, 29, 1, 5, tzinfo=TZ)
    await c.async_refresh()
    print("3) 01:05:", c.data["modus"], "tot", c.data["blok_einde"])
    for call in hass.services.calls: print("    ", call)
    hass.services.calls.clear()
    await c.async_refresh()
    print("4) zelfde situatie opnieuw -> calls:", hass.services.calls)

    dt_util.NOW[0] = datetime.datetime(2026, 9, 29, 7, 2, tzinfo=TZ)
    hass.states.set("sensor.pv_omvormer_battery_soc", 60)
    await c.async_refresh()
    print("5) 07:02:", c.data["modus"], "tot", c.data["blok_einde"])
    for call in hass.services.calls: print("    ", call)
    hass.services.calls.clear()

    c.actief = False
    await c.async_naar_zelfverbruik()
    print("6) uitgezet:")
    for call in hass.services.calls: print("    ", call)
    hass.services.calls.clear()

    hass.states.set("sensor.pv_omvormer_battery_soc", "unavailable")
    c.actief = True
    await c.async_refresh()
    print("7) SOC weg:", c.data, hass.services.calls)

    # profiel
    p = c.profiel
    t0 = datetime.datetime(2026, 9, 29, 9, 0, tzinfo=TZ)
    p.meting(300, t0); p.meting(900, t0 + datetime.timedelta(minutes=5))
    p.afsluiten(t0 + datetime.timedelta(minutes=15))
    print("8) profiel uur 9 na 1e meting (300W 5min, 900W 10min => 700):", p.werkdag[9], p.n_werkdag[9])
    p.meting(500, t0 + datetime.timedelta(minutes=15)); p.afsluiten(t0 + datetime.timedelta(minutes=30))
    print("   na 2e meting (500):", p.werkdag[9])

asyncio.run(main())
