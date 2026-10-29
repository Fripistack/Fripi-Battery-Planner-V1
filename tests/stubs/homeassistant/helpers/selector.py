from enum import StrEnum
from typing import TypedDict
class SelectOptionDict(TypedDict):
    value: str; label: str
class NumberSelectorMode(StrEnum):
    BOX="box"; SLIDER="slider"
class SelectSelectorMode(StrEnum):
    DROPDOWN="dropdown"; LIST="list"
class _Cfg(dict):
    def __init__(s, **kw): super().__init__(**kw)
EntitySelectorConfig = SelectSelectorConfig = _Cfg
class NumberSelectorConfig(_Cfg):
    def __init__(s, **kw):
        st = kw.get("step", 1)
        if st != "any" and float(st) < 1e-3:
            raise ValueError(f"step {st} < 0.001 (HA weigert dit)")
        if "unit_of_measurement" in kw and not isinstance(kw["unit_of_measurement"], str):
            raise ValueError("unit_of_measurement moet een str zijn (HA weigert None)")
        for k in kw:
            if k not in ("min", "max", "step", "unit_of_measurement", "mode", "translation_key"):
                raise ValueError(f"onbekende sleutel {k}")
        super().__init__(**kw)
class _Sel:
    def __init__(s, cfg): s.cfg = cfg
    def __call__(s, v): return v
    def __repr__(s): return f"{type(s).__name__}({dict(s.cfg)})"
class EntitySelector(_Sel): pass
class NumberSelector(_Sel): pass
class SelectSelector(_Sel): pass
class BooleanSelector(_Sel):
    def __init__(s, cfg=None): s.cfg = cfg or {}
