"""Hulpfuncties voor de tests: Frank-achtige prijsreeks per kwartier."""
import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Amsterdam")


def price_day(day, fn):
    out = []
    for q in range(96):
        st = datetime.datetime(day.year, day.month, day.day, q // 4, (q % 4) * 15, tzinfo=TZ)
        mkt = fn(st.hour + st.minute / 60)
        tot = mkt * 1.21 + 0.0182 * 1.21 + 0.1108  # ruwe benadering all-in
        out.append({"from": st.isoformat(), "till": (st + datetime.timedelta(minutes=15)).isoformat(),
                    "market_price": round(mkt, 5), "total_price_eur_kwh": round(tot, 5)})
    return out
