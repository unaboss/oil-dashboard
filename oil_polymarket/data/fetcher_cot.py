import csv
import io
import requests
from datetime import datetime, timezone

from data.cache import get, set
from config import CACHE_TTL_COT, next_cot_release

CACHE_KEY = "polymarket_cot"
COT_URL = "https://www.cftc.gov/dea/newcot/c_disagg.txt"


def get_cot_data():
    data, _, _, stale = get(CACHE_KEY)
    if data is not None and not stale:
        return data

    result = {
        "managed_money_long": None,
        "managed_money_short": None,
        "net_long": None,
        "report_date": None,
    }

    try:
        r = requests.get(COT_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        reader = csv.reader(io.StringIO(r.text))
        for row in reader:
            name = row[0].strip('"').strip()
            if "WTI-PHYSICAL" in name and "NEW YORK MERCANTILE" in name:
                parts = [p.strip('"').strip() for p in row]
                mm_long = float(parts[13]) if parts[13] else 0
                mm_short = float(parts[14]) if parts[14] else 0
                net = mm_long - mm_short
                result = {
                    "managed_money_long": mm_long,
                    "managed_money_short": mm_short,
                    "net_long": net,
                    "report_date": parts[2][:10] if parts[2] else None,
                }
                break
    except Exception:
        pass

    next_upd = next_cot_release().isoformat()
    last_upd = datetime.now(timezone.utc).isoformat()
    set(CACHE_KEY, result, CACHE_TTL_COT, last_updated=last_upd, next_update=next_upd)
    return result
