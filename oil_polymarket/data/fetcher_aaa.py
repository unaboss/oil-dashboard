import requests
import re
from datetime import datetime, timezone

from data.cache import get, set
from config import CACHE_TTL_AAA

CACHE_KEY = "polymarket_aaa_gas"


def get_aaa_gas_price():
    data, _, _, stale = get(CACHE_KEY)
    if data is not None and not stale:
        return data

    price = None
    try:
        url = "https://gasprices.aaa.com/"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        candidates = []
        for m in re.finditer(r'\$(\d+\.\d{3})', resp.text):
            val = float(m.group(1))
            if 2.0 < val < 8.0:
                candidates.append(val)
        if candidates:
            price = candidates[0]
    except Exception:
        pass

    result = {
        "price": price,
        "source": "AAA" if price else "UNAVAILABLE",
        "date": datetime.now(timezone.utc).isoformat()[:10],
    }

    last_upd = datetime.now(timezone.utc).isoformat()
    set(CACHE_KEY, result, CACHE_TTL_AAA, last_updated=last_upd)
    return result
