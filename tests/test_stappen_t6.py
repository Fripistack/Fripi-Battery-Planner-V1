"""Tests voor 5.3.0: vermogensstappen 33/66 % en sturing van de kamerthermostaat (T6)."""
import sys, asyncio, datetime
import os as _os
_HIER = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.join(_HIER, "stubs"))
sys.path.insert(0, _os.path.join(_HIER, "..", "custom_components"))
sys.path.insert(0, _HIER)
from helpers import price_day, TZ
from batterij_planner import optimizer
from batterij_planner.warmtepomp import WpInstellingen, thermostaat_doel, BOOST, VERLAAGD, NORMAAL


# ---------------------------------------------------------------- vermogensstappen
def prijs(h):
    if 6.75 <= h < 9: return 0.20
    if 11 <= h < 15.5: return 0.01
    if 17.5 <= h < 21: return 0.18
    if 1 <= h < 5: return 0.06
    return 0.10


def plan(stappen, max_w=3000.0):
    nu = datetime.datetime(2026, 10, 13, 0, 5, tzinfo=TZ)
    p = [price_day(nu.date(), prijs), price_day(nu.date() + datetime.timedelta(days=1), prijs)]
    inst = optimizer.Instellingen(vermogen_stappen=stappen, max_laad_w=max_w, max_ontlaad_w=max_w)
    slots = optimizer.bouw_slots(p, nu, TZ)
    optimizer.zet_terugleverprijs(slots, inst)
    optimizer.zet_verbruik(slots, None, None, 400)
    return optimizer.optimaliseer(slots, 40, inst)


zonder, met = plan(False), plan(True)
assert {s[7] for s in zonder["slots"] if s[1] in "LO"} == {100}
assert {s[7] for s in zonder["slots"] if s[1] in "ZV"} == {0}
assert {s[7] for s in met["slots"]} <= {0, 33, 66, 100}
# meer keuzes kan nooit duurder uitkomen
assert met["kosten_plan"] <= zonder["kosten_plan"] + 0.005, (met["kosten_plan"], zonder["kosten_plan"])
for b in met["blokken"]:
    assert b["vermogen_pct"] == (0 if b["modus"] in ("zelfverbruik", "vasthouden") else b["vermogen_pct"])
print("stappen: zonder", zonder["kosten_plan"], "met", met["kosten_plan"],
      "| gebruikt:", sorted({(s[1], s[7]) for s in met["slots"]}))

# ---------------------------------------------------------------- thermostaat_doel
I = WpInstellingen()
assert thermostaat_doel(I, 20.0, BOOST) == 20.5
assert thermostaat_doel(I, 20.0, VERLAAGD) == 19.5
assert thermostaat_doel(I, 20.0, NORMAAL) == 20.0
assert thermostaat_doel(I, 22.0, BOOST) == 22.0          # niet boven max
assert thermostaat_doel(I, 23.0, BOOST) == 23.0          # basis boven max blijft staan
assert thermostaat_doel(I, 17.0, VERLAAGD) == 17.0       # niet onder min
assert thermostaat_doel(I, 15.0, VERLAAGD) == 15.0       # nachtverlaging blijft staan
assert thermostaat_doel(I, 20.3, NORMAAL) == 20.3
print("thermostaat_doel ok")

# ---------------------------------------------------------------- coordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from batterij_planner.coordinator import BatterijPlannerCoordinator
from batterij_planner.const import STANDAARD_INSTELLINGEN

T6 = "climate.thermostaat_t6_thermostat"
GOEDKOOP = [0.05] + [0.10] * 40 + [0.30] * 55
DUUR = [0.30] + [0.10] * 40 + [0.05] * 55
GEMIDDELD = [0.10] + [0.05] * 30 + [0.10] * 20 + [0.30] * 45


def res(prijzen):
    return {"slots": [[0, "Z", 50, p, p, 0, 0, 0] for p in prijzen]}


def t6_state(hass, temp, actie="idle"):
    hass.states.set(T6, "heat", {"temperature": temp, "current_temperature": 20.1, "hvac_action": actie})


async def main():
    hass = HomeAssistant()
    dt_util.NOW[0] = datetime.datetime(2026, 10, 13, 2, 3, tzinfo=TZ)
    nu = dt_util.NOW[0]
    hass.states.set("sensor.soc", 50)
    t6_state(hass, 20.0)
    opts = dict(STANDAARD_INSTELLINGEN)
    entry = ConfigEntry({"soc_entity": "sensor.soc", "wp_thermostaat_entity": T6}, opts)
    c = BatterijPlannerCoordinator(hass, entry)
    calls = hass.services.calls

    # schakelaar uit: alleen advies
    uit = await c._warmtepomp(nu, res(GOEDKOOP))
    assert uit["doel"] is None and uit["thermostaat"]["doel"] == 20.5, uit
    assert calls == []

    # aan + goedkoop -> 20,5
    c.t6_actief = True
    uit = await c._warmtepomp(nu, res(GOEDKOOP))
    assert calls[-1] == ("climate", "set_temperature", {"entity_id": T6, "temperature": 20.5}), calls
    t6_state(hass, 20.5)
    assert c.t6_basis == 20.0 and c.t6_geschreven == 20.5

    # duur, maar binnen de minimale tijd -> wachten
    n = len(calls)
    uit = await c._warmtepomp(nu + datetime.timedelta(minutes=5), res(DUUR))
    assert len(calls) == n and "wacht_tot" in uit["thermostaat"], uit["thermostaat"]

    # duur na 35 min -> 19,5, ook bij warmtevraag
    t6_state(hass, 20.5, "heating")
    nu = nu + datetime.timedelta(minutes=35)
    await c._warmtepomp(nu, res(DUUR))
    assert calls[-1][2]["temperature"] == 19.5, calls
    t6_state(hass, 19.5)

    # gebruiker zet zelf 21 -> nieuwe basis, planner wacht tot de prijsstand verandert
    t6_state(hass, 21.0)
    n = len(calls)
    nu = nu + datetime.timedelta(minutes=35)
    uit = await c._warmtepomp(nu, res(DUUR))
    assert len(calls) == n and c.t6_basis == 21.0 and "wacht" in uit["thermostaat"], uit["thermostaat"]
    # prijsstand wordt gemiddeld -> normaal = 21, niets te schrijven
    nu = nu + datetime.timedelta(minutes=35)
    await c._warmtepomp(nu, res(GEMIDDELD))
    assert len(calls) == n
    # goedkoop -> 21,5
    nu = nu + datetime.timedelta(minutes=35)
    await c._warmtepomp(nu, res(GOEDKOOP))
    assert calls[-1][2]["temperature"] == 21.5, calls
    t6_state(hass, 21.5)

    # uitzetten -> terug naar 21
    c.t6_actief = False
    await c.async_t6_normaal()
    assert calls[-1][2]["temperature"] == 21.0, calls
    assert c.t6_geschreven is None
    t6_state(hass, 21.0)

    # herstart terwijl verschoven: basis/geschreven komen terug uit de schakelaar
    c2 = BatterijPlannerCoordinator(hass, entry)
    c2.t6_basis, c2.t6_geschreven, c2.t6_actief = 21.0, 21.5, True
    t6_state(hass, 21.5)
    await c2._warmtepomp(nu, res(GEMIDDELD))
    assert calls[-1][2]["temperature"] == 21.0, calls

    # vermogensstap -> laadstroom in de coordinator
    c.conf["laad_stroom_entity"] = "number.laadstroom"
    lijst = c._schrijflijst({"modus": "laden", "laad_vermogen_w": 990, "blok_einde": None})
    assert ("number", "number.laadstroom", 19) in lijst, lijst  # 990 W / 51,2 V
    print("thermostaat ok")


asyncio.run(main())
print("ALLES OK")
