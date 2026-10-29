
import datetime
from zoneinfo import ZoneInfo
def get_astral_event_date(hass, event, d):
    tz=ZoneInfo("Europe/Amsterdam")
    t = datetime.time(7,38) if event=="sunrise" else datetime.time(19,22)
    return datetime.datetime.combine(d, t, tzinfo=tz).astimezone(datetime.timezone.utc)
