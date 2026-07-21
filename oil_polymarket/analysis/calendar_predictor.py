import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from config import (
    CALENDAR_FORWARD_DAYS, CALENDAR_LOOKBACK_DAYS,
    SIGNAL_CONFIDENCE_THRESHOLD, CONFLUENCE_SIGNALS, SIGNAL_WEIGHTS,
    BULLISH_THRESHOLD, BEARISH_THRESHOLD,
)


def compute_calendar_signals(wti_data, polymarket_signal, cot_data, eia_data, phase_multiplier=1.0):
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=CALENDAR_LOOKBACK_DAYS)
    end_date = today + timedelta(days=CALENDAR_FORWARD_DAYS + 1)

    date_range = pd.date_range(start=start_date, end=end_date)

    wti_dates = wti_data.get("dates", [])
    wti_close = wti_data.get("close", [])

    calendar_rows = []

    pm_daily_dir = polymarket_signal.get("daily_direction") if polymarket_signal else None
    pm_weekly = polymarket_signal.get("weekly_targets") if polymarket_signal else None
    pm_monthly = polymarket_signal.get("monthly_targets") if polymarket_signal else None

    cot_nl = cot_data.get("net_long")
    cot_extreme = abs(cot_nl) > 100000 if cot_nl else False
    cot_side = "long" if (cot_nl and cot_nl > 0) else "short"

    eia_crude = eia_data.get("crude") if isinstance(eia_data, dict) else None
    if eia_crude is None:
        eia_crude = {}
    eia_dates = eia_crude.get("dates", [])
    eia_changes = eia_crude.get("changes", [])

    wti_dict = {}
    for i, d in enumerate(wti_dates):
        try:
            wti_dict[pd.to_datetime(d).date()] = {"close": wti_close[i], "idx": i}
        except Exception:
            continue

    for d in date_range:
        date_key = d.date()

        signals = {}
        score = 0

        # Daily direction signal
        if pm_daily_dir and pm_daily_dir.get("net_sentiment") is not None:
            pm_daily_score = 1 if pm_daily_dir["net_sentiment"] > 0.05 else (-1 if pm_daily_dir["net_sentiment"] < -0.05 else 0)
        else:
            pm_daily_score = 0
        signals["polymarket_daily"] = pm_daily_score

        # Weekly targets signal
        if pm_weekly:
            weekly_skew = pm_weekly.get("upside_skew")
            weekly_down = pm_weekly.get("downside_skew")
            if weekly_skew is not None and weekly_down is not None:
                ratio = abs(weekly_skew) / max(abs(weekly_down), 0.01)
                pm_weekly_score = 1 if ratio > 1.2 else (-1 if ratio < 0.8 else 0)
            else:
                pm_weekly_score = 0
        else:
            pm_weekly_score = 0
        signals["polymarket_weekly"] = pm_weekly_score

        # Monthly targets signal
        if pm_monthly:
            monthly_skew = pm_monthly.get("upside_skew")
            monthly_down = pm_monthly.get("downside_skew")
            if monthly_skew is not None and monthly_down is not None:
                ratio = abs(monthly_skew) / max(abs(monthly_down), 0.01)
                pm_monthly_score = 1 if ratio > 1.2 else (-1 if ratio < 0.8 else 0)
            else:
                pm_monthly_score = 0
        else:
            pm_monthly_score = 0
        signals["polymarket_monthly"] = pm_monthly_score

        cot_score = 0
        if cot_nl is not None:
            if cot_nl > 50000:
                cot_score = 1
            elif cot_nl < -50000:
                cot_score = -1
        if cot_extreme:
            cot_score *= -0.5
        signals["cot_net_long"] = cot_score

        eia_score = 0
        if eia_dates and eia_changes:
            best_j = None
            best_diff = None
            for j, ed in enumerate(eia_dates):
                try:
                    ed_dt = pd.to_datetime(ed).date()
                    diff = abs((date_key - ed_dt).days)
                    if best_diff is None or diff < best_diff:
                        best_diff = diff
                        best_j = j
                except Exception:
                    continue
            if best_j is not None and best_diff is not None and best_diff < 10 and best_j < len(eia_changes):
                ch = eia_changes[best_j]
                if ch is not None and not np.isnan(ch):
                    eia_score = 1 if ch < 0 else -1
        signals["eia_crude"] = eia_score

        total = sum(signals.get(s, 0) * SIGNAL_WEIGHTS.get(s, 1) for s in CONFLUENCE_SIGNALS)

        if date_key >= today and phase_multiplier != 1.0:
            total = total * phase_multiplier

        if total >= BULLISH_THRESHOLD:
            direction = "bullish"
        elif total <= BEARISH_THRESHOLD:
            direction = "bearish"
        else:
            direction = "neutral"

        confidence = min(abs(total) / max(abs(BULLISH_THRESHOLD) + 2, 1), 1.0) * 100

        wti_entry = wti_dict.get(date_key)
        wti_price = wti_entry["close"] if wti_entry else None

        is_future = date_key > today
        is_past = date_key < today

        calendar_rows.append({
            "date": date_key,
            "direction": direction,
            "confidence": round(confidence, 1),
            "score": total,
            "signals": signals,
            "wti_close": wti_price,
            "is_future": is_future,
            "is_past": is_past,
        })

    return calendar_rows


def backtest_calendar(calendar_rows):
    enriched = []
    for i, row in enumerate(calendar_rows):
        entry = dict(row)
        if row["is_past"]:
            if i + 3 < len(calendar_rows):
                future_row = calendar_rows[i + 3]
                if row["wti_close"] and future_row["wti_close"]:
                    actual_return = (future_row["wti_close"] / row["wti_close"] - 1) * 100
                    price_moved_up = actual_return > 0.5
                    price_moved_down = actual_return < -0.5
                    predicted_up = row["direction"] == "bullish"
                    predicted_down = row["direction"] == "bearish"

                    if predicted_up and price_moved_up:
                        entry["result"] = "correct"
                    elif predicted_down and price_moved_down:
                        entry["result"] = "correct"
                    elif not predicted_up and not predicted_down:
                        entry["result"] = "neutral"
                    elif (predicted_up and price_moved_down) or (predicted_down and price_moved_up):
                        entry["result"] = "wrong"
                    else:
                        entry["result"] = "flat"
                    entry["actual_3d_return"] = round(actual_return, 2)
                    entry["actual_3d_price"] = future_row["wti_close"]
                else:
                    entry["result"] = "no_data"
            else:
                entry["result"] = "no_data"
        else:
            entry["result"] = "pending"
        enriched.append(entry)
    return enriched
