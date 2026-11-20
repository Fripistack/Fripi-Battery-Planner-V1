"""Tests voor 5.4.0: gebruiksmodus 'goedkoop inkopen voor eigen verbruik' en zelflerende benodigde energie."""
import sys, asyncio, datetime
import os as _os
_HIER = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.join(_HIER, "stubs"))
sys.path.insert(0, _os.path.join(_HIER, "..", "custom_components"))
sys.path.insert(0, _HIER)
from helpers import price_day, TZ
from batterij_planner import optimizer
from batterij_planner import profiel as prof


def prijs(h):
    if 6.75 <= h < 9: return 0.20
    if 11 <= h < 15.5: return 0.01
    if 17.5 <= h < 21: return 0.18
    if 1 <= h < 5: return 0.06
    return 0.10


def plan(modus, verbruik_w=400, cap=16.0, jaar=2026, pv=0.0):
    nu = datetime.datetime(jaar, 10, 13 if jaar == 2026 else 12, 0, 5, tzinfo=TZ)
    p = [price_day(nu.date(), prijs), price_day(nu.date() + datetime.timedelta(days=1), prijs)]
    inst = optimizer.Instellingen(capaciteit_kwh=cap, gebruiksmodus=modus, verbruik_marge=1.0)
    slots = optimizer.bouw_slots(p, nu, TZ)
    optimizer.zet_terugleverprijs(slots, inst)
    optimizer.zet_verbruik(slots, None, None, verbruik_w)
    for s in slots:
        if 10 <= s.start.hour < 15:
            s.pv = pv * 0.25 * s.frac
    return slots, inst, optimizer.optimaliseer(slots, 10, inst)


# 1. nooit ontladen naar het net (met saldering loont dat in 'optimaal' wel)
_, _, opt = plan("optimaal")
_, _, zelf = plan("inkopen_zelfverbruik")
assert any(s[1] == "O" for s in opt["slots"]), "optimaal zou moeten ontladen"
assert all(s[1] != "O" for s in zelf["slots"]), "zelfverbruik mag nooit ontladen"
assert any(s[1] == "L" for s in zelf["slots"]), "zelfverbruik moet goedkoop inkopen"
assert zelf["gebruiksmodus"] == "inkopen_zelfverbruik"
print("1) nooit ontladen ok; netladen", zelf["netladen_gepland_kwh"], "kWh; benodigd", zelf["benodigd_kwh"], "kWh")

# 2. niet meer inkopen dan nodig: grote accu, laag verbruik
slots, inst, res = plan("inkopen_zelfverbruik", verbruik_w=200, cap=40.0, jaar=2027)
nodig = sum(s.verbruik for s in slots) / 0.95 + inst.reserve_na_horizon_kwh
assert res["netladen_gepland_kwh"] <= nodig + 1.0, (res["netladen_gepland_kwh"], nodig)
max_soc = max(s[2] for s in res["slots"])
assert max_soc < 50, max_soc
print("2) grote accu laag verbruik: max SOC", max_soc, "% (niet vol)")

# 3. schaalt mee met verbruik en accugrootte
_, _, laag = plan("inkopen_zelfverbruik", verbruik_w=200, cap=40.0, jaar=2027)
_, _, hoog = plan("inkopen_zelfverbruik", verbruik_w=800, cap=40.0, jaar=2027)
assert hoog["benodigd_kwh"] > laag["benodigd_kwh"] * 2
_, _, klein = plan("inkopen_zelfverbruik", verbruik_w=800, cap=5.0, jaar=2027)
assert klein["benodigd_kwh"] <= 5.0 * 0.9 + 1e-6
print("3) benodigd laag/hoog/kleine accu:", laag["benodigd_kwh"], hoog["benodigd_kwh"], klein["benodigd_kwh"])

# 4. zonne-overschot verlaagt de inkoop
_, _, zon = plan("inkopen_zelfverbruik", verbruik_w=400, cap=16.0, jaar=2027, pv=3000)
_, _, geen = plan("inkopen_zelfverbruik", verbruik_w=400, cap=16.0, jaar=2027)
assert zon["netladen_gepland_kwh"] < geen["netladen_gepland_kwh"]
print("4) netladen met/zonder zon:", zon["netladen_gepland_kwh"], geen["netladen_gepland_kwh"])

# 5. benodigde energie: PV vult aan, begrensd op ruimte
assert optimizer.benodigde_energie([2, 0, 1], [0, 3, 0], 1.0, 1.0, 0.0, 100.0) == [2.0, 0.0, 1.0, 0.0]
assert optimizer.benodigde_energie([1, 1], [0, 0], 1.0, 0.5, 0.0, 3.0)[0] == 3.0

# 6. leren: marge en weekdagprofiel
assert prof.leer_marge([]) == prof.MARGE_STANDAARD
assert prof.leer_marge([0.5] * 10) == 1.0 and prof.leer_marge([3.0] * 10) == 1.5
p = prof.VerbruiksProfiel(None, "test", 400)
t = datetime.datetime(2026, 11, 2, 0, 0, tzinfo=TZ)  # maandag
for q in range(4 * 24 * 8):
    w = 1500 if (t.weekday() == 0 and 17 <= t.hour < 20) else 300
    p.meting(w, t); p.meting(w, t + datetime.timedelta(minutes=7))
    t += datetime.timedelta(minutes=15)
    p.afsluiten(t)
assert p.voorspel_w(0, 18) > 1000 and p.voorspel_w(1, 18) < 500, (p.voorspel_w(0, 18), p.voorspel_w(1, 18))
assert len(p.verbruik_verhoudingen) >= 7
print("6) leren: ma 18u", p.voorspel_w(0, 18), "W, di 18u", p.voorspel_w(1, 18), "W, marge", p.verbruik_marge)


# 7. coordinator: modus bewaren en toepassen
async def coordinator_test():
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.util import dt as dt_util
    from batterij_planner.coordinator import BatterijPlannerCoordinator
    from batterij_planner.const import STANDAARD_INSTELLINGEN, SUGGESTIES
    hass = HomeAssistant()
    now = dt_util.NOW[0]
    hass.states.set("sensor.frank_prices_today", 96, {"prices": price_day(now.date(), prijs)})
    hass.states.set("sensor.frank_prices_tomorrow", 96, {"prices": price_day(now.date() + datetime.timedelta(days=1), prijs)})
    hass.states.set("sensor.pv_omvormer_battery_soc", 40)
    hass.states.set("sensor.pv_omvormer_household_load_power", 500)
    entry = ConfigEntry(dict(SUGGESTIES), dict(STANDAARD_INSTELLINGEN))
    c = BatterijPlannerCoordinator(hass, entry)
    await c.async_start()
    await c.async_zet_gebruiksmodus("inkopen_zelfverbruik")
    await c.async_refresh()
    assert c.data["gebruiksmodus"] == "inkopen_zelfverbruik", c.data
    assert all(s[1] != "O" for s in c.data["slots"])
    assert "benodigd_kwh" in c.data and "leren" in c.data
    # na herstart staat de keuze er weer, vóór de eerste berekening
    c2 = BatterijPlannerCoordinator(hass, entry)
    await c2.async_start()
    assert c2.gebruiksmodus == "inkopen_zelfverbruik"
    try:
        await c2.async_zet_gebruiksmodus("onzin")
        raise AssertionError("ongeldige modus geaccepteerd")
    except ValueError:
        pass
    print("7) coordinator ok: benodigd", c.data["benodigd_kwh"], "kWh, SOC", c.data["benodigd_soc"], "%")

asyncio.run(coordinator_test())
print("ALLES OK")
