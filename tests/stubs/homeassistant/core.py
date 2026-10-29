
from typing import Generic, TypeVar
T = TypeVar("T")
class Event(Generic[T]):
    def __init__(self, data): self.data=data
EventStateChangedData = dict
class State:
    def __init__(self, entity_id, state, attributes=None):
        self.entity_id=entity_id; self.state=str(state); self.attributes=attributes or {}
def callback(f): return f
class _States:
    def __init__(s): s.d={}
    def get(s, e): return s.d.get(e)
    def set(s, e, st, attrs=None): s.d[e]=State(e, st, attrs)
class _Services:
    def __init__(s, hass): s.calls=[]; s.hass=hass
    async def async_call(s, domain, service, data, blocking=False):
        s.calls.append((domain, service, dict(data)))
        e=data.get("entity_id")
        if e:
            v = data.get("time", data.get("value", data.get("option")))
            old = s.hass.states.get(e)
            s.hass.states.set(e, v if not isinstance(v,(int,float)) else float(v), old.attributes if old else {})
    def async_services(s): return {}
    def async_services_for_domain(s, d): return {"mobile_app_frits": None} if d == "notify" else {}
class HomeAssistant:
    def __init__(s):
        s.states=_States(); s.services=_Services(s); s.data={}
    async def async_add_executor_job(s, f, *a): return f(*a)
    def async_create_task(s, c):
        import asyncio; return asyncio.ensure_future(c)
