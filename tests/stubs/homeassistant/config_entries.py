
from typing import Generic, TypeVar
T = TypeVar("T")
class ConfigEntry(Generic[T]):
    def __init__(self, data, options, entry_id="e1"):
        self.data=data; self.options=options; self.entry_id=entry_id
class ConfigFlow:
    def __init_subclass__(cls, **kw): pass
class OptionsFlow: pass
ConfigFlowResult = dict
