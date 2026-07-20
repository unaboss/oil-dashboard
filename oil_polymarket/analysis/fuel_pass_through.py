import pandas as pd
import numpy as np


def compute_fuel_pass_through(eia_data, aaa_price=None, wti_close=None):
    crude = eia_data.get("crude") if isinstance(eia_data, dict) else None
    retail = eia_data.get("retail_gas") if isinstance(eia_data, dict) else None
    if crude is None:
        crude = {}
    if retail is None:
        retail = {}

    crude_changes = crude.get("changes", [])
    crude_dates = crude.get("dates", [])
    retail_prices = retail.get("values", []) if retail else []
    retail_dates = retail.get("dates", []) if retail else []

    if not crude_changes or not retail_prices:
        return {
            "pass_through_lag": None,
            "current_crude_change": None,
            "current_retail": None,
            "retail_vs_crude_direction": None,
            "historical_samples": 0,
        }

    min_len = min(len(crude_changes), len(retail_prices))
    crude_aligned = crude_changes[:min_len]
    retail_aligned = retail_prices[:min_len]

    direction_match = 0
    total = 0
    for i in range(min_len - 1):
        if crude_aligned[i] is None or retail_aligned[i + 1] is None:
            continue
        if np.isnan(crude_aligned[i]) or np.isnan(retail_aligned[i + 1]):
            continue
        crude_dir = 1 if crude_aligned[i] < 0 else -1
        retail_dir = 1 if retail_aligned[i + 1] > retail_aligned[i] else -1
        if crude_dir == retail_dir:
            direction_match += 1
        total += 1

    direction_score = direction_match / max(total, 1)

    latest_crude_change = crude_changes[0] if crude_changes else None
    current_retail = retail_prices[0] if retail_prices else None
    aaa_current = aaa_price.get("price") if aaa_price else None

    retail_direction = "rising" if (latest_crude_change and latest_crude_change < 0) else "falling"

    return {
        "pass_through_lag": f"{direction_score:.0%} 1-week alignment" if total > 0 else "Unknown",
        "current_crude_change": latest_crude_change,
        "current_retail_eia": current_retail,
        "current_retail_aaa": aaa_current,
        "retail_vs_crude_direction": retail_direction,
        "alignment_score": round(direction_score * 100, 1),
        "historical_samples": total,
    }
