import requests
import pandas as pd
from datetime import datetime, timezone

from data.cache import get, set
from config import (
    EIA_API_KEY, EIA_BASE, EIA_CRUDE_STOCKS, EIA_RETAIL_GAS,
    DEFAULT_START, DEFAULT_END, CACHE_TTL_EIA,
    FACETS_CRUDE, FACETS_GASOLINE, FACETS_DISTILLATE,
    FACETS_REFINERY_INPUT, FACETS_REFINERY_UTIL,
    FACETS_GAS_PROD, FACETS_DIST_PROD, FACETS_SPR, FACETS_RETAIL,
)


def _eia_weekly(route, facets, cache_key, start=DEFAULT_START, end=DEFAULT_END):
    data, _, _, stale = get(cache_key)
    if data is not None and not stale:
        return data

    url = f"{EIA_BASE}{route}/data"
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "weekly",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 5000,
    }
    params["data[0]"] = "value"
    for k, v in facets.items():
        params[f"facets[{k}][]"] = v

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        js = resp.json()
    except Exception:
        return None

    if "response" not in js or "data" not in js["response"]:
        return None

    rows = js["response"]["data"]
    seen = {}
    for r in rows:
        period = r["period"]
        if period not in seen:
            seen[period] = float(r["value"]) if r.get("value") else None

    periods = sorted(seen.keys(), reverse=True)
    values = [seen[p] for p in periods]

    result = {"dates": periods, "values": values}
    set(cache_key, result, CACHE_TTL_EIA, last_updated=datetime.now(timezone.utc).isoformat())
    return result


def get_weekly_changes(data_dict):
    if data_dict is None:
        return None
    vals = pd.Series(data_dict["values"])
    changes = vals.diff().tolist()
    return {
        "dates": data_dict["dates"],
        "values": data_dict["values"],
        "changes": changes,
    }


# ── Inventory Series ──

def get_crude_stocks(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_CRUDE_STOCKS, FACETS_CRUDE, "bets_eia_crude", start, end)


def get_gasoline_stocks(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_CRUDE_STOCKS, FACETS_GASOLINE, "bets_eia_gasoline", start, end)


def get_distillate_stocks(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_CRUDE_STOCKS, FACETS_DISTILLATE, "bets_eia_distillate", start, end)


def get_spr_stocks(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_CRUDE_STOCKS, FACETS_SPR, "bets_eia_spr", start, end)


# ── Refinery Series ──

def get_refinery_inputs(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_CRUDE_STOCKS, FACETS_REFINERY_INPUT, "bets_eia_ref_input", start, end)


def get_refinery_utilization(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_CRUDE_STOCKS, FACETS_REFINERY_UTIL, "bets_eia_ref_util", start, end)


def get_gasoline_production(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_CRUDE_STOCKS, FACETS_GAS_PROD, "bets_eia_gas_prod", start, end)


def get_distillate_production(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_CRUDE_STOCKS, FACETS_DIST_PROD, "bets_eia_dist_prod", start, end)


def get_retail_gas_price(start=DEFAULT_START, end=DEFAULT_END):
    return _eia_weekly(EIA_RETAIL_GAS, FACETS_RETAIL, "bets_eia_retail", start, end)


# ── All data ──

def get_all_refinery_data(start=DEFAULT_START, end=DEFAULT_END):
    return {
        "crude": get_weekly_changes(get_crude_stocks(start, end)),
        "gasoline": get_weekly_changes(get_gasoline_stocks(start, end)),
        "distillate": get_weekly_changes(get_distillate_stocks(start, end)),
        "spr": get_weekly_changes(get_spr_stocks(start, end)),
        "refinery_inputs": get_refinery_inputs(start, end),
        "refinery_utilization": get_refinery_utilization(start, end),
        "gasoline_production": get_gasoline_production(start, end),
        "distillate_production": get_distillate_production(start, end),
        "retail_gas": get_retail_gas_price(start, end),
    }
