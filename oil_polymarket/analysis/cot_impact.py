import numpy as np
import pandas as pd

from data.fetcher_price import get_wti


def compute_cot_impact_on_price(cot_data, market_data, lookback_days=[1, 3, 5, 10]):
    wti = market_data.get("wti") if isinstance(market_data, dict) else None
    if wti is None:
        wti = {}
    close = wti.get("close", [])
    dates = wti.get("dates", [])

    if not close or len(close) < 10:
        return {
            "current_net_long": cot_data.get("net_long"),
            "impact_table": [],
            "extreme_zone": None,
        }

    nl = cot_data.get("net_long")

    is_extreme = abs(nl) > 100000 if nl else False
    side = "long" if (nl and nl > 0) else "short"

    impact_rows = []
    for d in lookback_days:
        if d < len(close):
            fwd = (close[-1] / close[-d-1] - 1) * 100 if len(close) > d else None
            impact_rows.append({
                "horizon_days": d,
                "forward_return_pct": round(fwd, 2) if fwd is not None else None,
                "direction": "up" if (fwd and fwd > 0) else ("down" if (fwd and fwd < 0) else "flat"),
            })

    if nl is not None:
        magnitude = abs(nl) / 300000
        magnitude_category = "extreme" if magnitude > 0.8 else ("elevated" if magnitude > 0.4 else "neutral")
    else:
        magnitude_category = "unknown"

    return {
        "current_net_long": nl,
        "current_mm_long": cot_data.get("managed_money_long"),
        "current_mm_short": cot_data.get("managed_money_short"),
        "impact_table": impact_rows,
        "extreme_zone": "extreme_long" if (is_extreme and side == "long") else ("extreme_short" if (is_extreme and side == "short") else None),
        "magnitude": magnitude_category,
        "side": side,
    }


def compute_cot_divergence(cot_data, market_data):
    wti = market_data.get("wti") if isinstance(market_data, dict) else None
    if wti is None:
        wti = {}
    close = wti.get("close", [])

    if not close or len(close) < 5:
        return []

    nl = cot_data.get("net_long")
    if nl is None:
        return []

    recent_return = (close[-1] / close[-5] - 1) if len(close) >= 5 else 0

    divergence_signals = []

    if nl > 120000 and recent_return < 0:
        divergence_signals.append({
            "type": "cot_long_price_down",
            "description": "Managed Money heavily long but price is falling — potential liquidation risk",
            "net_long": nl,
            "wti_5d": round(recent_return * 100, 2),
        })

    if nl < -80000 and recent_return > 0:
        divergence_signals.append({
            "type": "cot_short_price_up",
            "description": "Managed Money heavily short but price is rising — potential short squeeze",
            "net_long": nl,
            "wti_5d": round(recent_return * 100, 2),
        })

    return divergence_signals
