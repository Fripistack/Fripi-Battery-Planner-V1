import sys, asyncio, json
import os as _os
_HIER = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.join(_HIER, "stubs"))
sys.path.insert(0, _os.path.join(_HIER, "..", "custom_components"))
import homeassistant.config_entries as ce
# minimal flow-gedrag
def show_form(self, step_id, data_schema=None, errors=None, **kw): return {"type":"form","step_id":step_id,"schema":data_schema,"errors":errors or {}}
def create_entry(self, title=None, data=None, options=None, **kw): return {"type":"create_entry","title":title,"data":data,"options":options}
def show_menu(self, step_id, menu_options): return {"type":"menu","menu":menu_options}
async def set_uid(self, uid): pass
for cls in (ce.ConfigFlow, ce.OptionsFlow):
    cls.async_show_form = show_form; cls.async_create_entry = create_entry; cls.async_show_menu = show_menu
ce.ConfigFlow.async_set_unique_id = set_uid; ce.ConfigFlow._abort_if_unique_id_configured = lambda s: None
ce.ConfigFlow.add_suggested_values_to_schema = lambda s, sch, v: sch
import homeassistant.core as core
core.callback = lambda f: f
from homeassistant.core import HomeAssistant
from batterij_planner import config_flow as cf
from batterij_planner.const import SUGGESTIES
import voluptuous as vol

async def main():
    hass = HomeAssistant()
    for e in SUGGESTIES.values(): hass.states.set(e, "1")
    hass.states.set("sensor.frank_prices_today", 96, {"prices": []})
    hass.states.set("select.pv_omvormer_work_mode", "Self-Use", {"options": ["Self-Use", "Self-Use + TOU", "Feed-in priority"]})
    f = cf.BatterijPlannerConfigFlow(); f.hass = hass
    r = await f.async_step_user()
    print("user velden:", [(str(k), (k.default() if callable(k.default) else None)) for k in r["schema"].schema])
    ingevuld = {str(k): k.default() for k in r["schema"].schema if callable(getattr(k, "default", None)) and k.default() is not None}
    hass.states.set("sensor.pv_omvormer_battery_soc", "abc")
    print("fout bij niet-numerieke SOC:", (await f.async_step_user(ingevuld))["errors"])
    hass.states.set("sensor.pv_omvormer_battery_soc", "55")
    r = await f.async_step_user(ingevuld); print("-> volgende stap:", r["step_id"])
    om = {str(k): k.default() for k in r["schema"].schema if callable(getattr(k, "default", None)) and k.default() is not None}
    r = await f.async_step_omvormer(om)
    print("entry:", r["type"], "data-sleutels:", len(r["data"]), "solcast:", r["data"]["solcast_vandaag_entity"])
    entry = ce.ConfigEntry(r["data"], r["options"])
    o = cf.BatterijPlannerOptionsFlow(); o.hass = hass; o.config_entry = entry
    print("menu:", (await o.async_step_init())["menu"])
    r = await o.async_step_instellingen()
    sch = r["schema"]
    standaard = sch({k: {} for k in ["accu", "prijzen", "voorspelling", "omvormer", "meldingen"]})  # secties
    print("secties:", list(standaard))
    print("instellingen standaard:", json.dumps(standaard)[:200], "...")
    standaard["accu"]["min_soc"] = 90; standaard["accu"]["max_soc"] = 80
    print("fout min>max:", (await o.async_step_instellingen(standaard))["errors"])
    standaard["accu"]["min_soc"] = 15; standaard["accu"]["max_soc"] = 95; standaard["omvormer"]["werkmodus_tou"] = "Self-Use + TOU"
    r = await o.async_step_instellingen(standaard); print("opgeslagen min_soc/tou:", r["data"]["min_soc"], r["data"]["werkmodus_tou"])
    entry.options = r["data"]
    r = await o.async_step_bronnen(); print("bronnen form ok:", r["step_id"])
asyncio.run(main())
