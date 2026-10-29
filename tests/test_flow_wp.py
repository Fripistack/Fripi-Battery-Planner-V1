import sys, asyncio
import os as _os
_HIER = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_HIER, "test_flow.py")).read().split("async def main")[0])
async def main():
    hass = HomeAssistant()
    hass.states.set("sensor.pv_omvormer_total_pv_power", 0)
    entry = ce.ConfigEntry({"soc_entity": "sensor.soc"}, dict(__import__("batterij_planner.const", fromlist=["x"]).STANDAARD_INSTELLINGEN))
    o = cf.BatterijPlannerOptionsFlow(); o.hass = hass; o.config_entry = entry
    print("menu:", (await o.async_step_init())["menu"])
    r = await o.async_step_warmtepomp(); sch = r["schema"]
    standaard = sch({"apparaten": {}, "regeling": {}, "thermostaat": {}})
    print("defaults thermostaat:", standaard["thermostaat"])
    print("defaults regeling:", standaard["regeling"])
    standaard["apparaten"] = {"wp_setpoint_entity": "climate.wp", "wp_thermostaat_entity": "climate.t6"}
    standaard["regeling"]["wp_min_temp"] = 60
    print("fout:", (await o.async_step_warmtepomp(standaard))["errors"])
    standaard["regeling"]["wp_min_temp"] = 20
    standaard["thermostaat"]["wp_t6_min_temp"] = 23
    print("fout t6:", (await o.async_step_warmtepomp(standaard))["errors"])
    standaard["thermostaat"]["wp_t6_min_temp"] = 17
    r = await o.async_step_warmtepomp(standaard)
    print("opgeslagen:", {k: v for k, v in r["data"].items() if k.startswith("wp_")})
asyncio.run(main())
