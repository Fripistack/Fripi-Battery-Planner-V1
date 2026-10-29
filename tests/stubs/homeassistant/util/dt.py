
import datetime
from zoneinfo import ZoneInfo
TZ=ZoneInfo("Europe/Amsterdam")
NOW=[datetime.datetime(2026,9,28,22,40,tzinfo=TZ)]
def now(): return NOW[0]
def get_default_time_zone(): return TZ
def as_local(d): return d.astimezone(TZ)
def parse_datetime(s):
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None
