import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta


def compute_scenarios(crude_data, historical_data=None):
    """
    crude_data: {"dates": [str "YYYY-MM-DD"], "values": [float], "changes": [float]}
    historical_data: optional 5-year historical for seasonal patterns

    Returns dict with actual + 4 scenario projection lines.
    """
    if crude_data is None or not crude_data.get("values"):
        return None

    dates = [pd.to_datetime(d) for d in crude_data["dates"]]
    values = crude_data["values"]
    changes = crude_data["changes"]

    # Latest data point
    current_level = values[0]  # most recent week (dates are reverse chronological)
    current_date = dates[0]

    # How many weeks from current date to end of 2026
    end_date = pd.to_datetime("2026-12-31")
    if current_date >= end_date:
        end_date = current_date + timedelta(days=30)

    weeks_to_project = max(1, int((end_date - current_date).days / 7))
    future_dates = pd.date_range(start=current_date, periods=weeks_to_project + 1, freq="W")

    # ── Actual line (Dec 2025 → today) ──
    actual_dates = dates[::-1]  # forward chronological
    actual_values = values[::-1]
    actual_change = changes[::-1]

    result = {
        "actual": {
            "dates": [d.strftime("%Y-%m-%d") for d in actual_dates],
            "values": actual_values,
        },
    }

    # ── Status Quo: 8-week moving average of weekly change ──
    recent_changes = [c for c in changes[1:9] if c is not None and not np.isnan(c)]
    if len(recent_changes) == 0:
        recent_changes = [0]
    avg_weekly_change = np.mean(recent_changes)

    # ── Ceasefire: half the draw/build rate ──
    ceasefire_rate = avg_weekly_change * 0.5

    # ── Worsening: supplies tighten, draws accelerate ──
    # If already drawing, double the draw. If building, reverse to a draw.
    if avg_weekly_change < 0:
        worsening_rate = avg_weekly_change * 2.0
    else:
        worsening_rate = -abs(avg_weekly_change) * 2.0

    # ── Back to Normal: seasonal pattern ──
    seasonal_changes = _get_seasonal_pattern(historical_data, current_date, weeks_to_project, changes, dates)

    # Build projections
    scenarios = {
        "status_quo": {"rate": avg_weekly_change, "label": "Status Quo (current trend)"},
        "ceasefire": {"rate": ceasefire_rate, "label": "Ceasefire Normalized"},
        "worsening": {"rate": worsening_rate, "label": "Worsening Scenario"},
        "back_to_normal": {"rate": "seasonal", "label": "Back to Normal (5yr avg)"},
    }

    for key, info in scenarios.items():
        projected = [float(current_level)]
        for i in range(1, weeks_to_project + 1):
            if info["rate"] == "seasonal":
                ch = seasonal_changes[i - 1] if i <= len(seasonal_changes) else 0
            else:
                ch = info["rate"]
            projected.append(projected[-1] + ch)
        result[key] = {
            "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "values": projected,
            "label": info["label"],
            "annual_rate": info["rate"] * 52 if isinstance(info["rate"], (int, float)) else None,
        }

    return result


def _get_seasonal_pattern(historical, current_date, weeks, recent_changes, dates):
    """Build a seasonal projection using recent data patterns.
    Falls back to simple moving average if no historical data."""
    if historical is None or not historical.get("changes"):
        # No 5-year data: use a dampened version of recent trend
        recent = [c for c in recent_changes[1:20] if c is not None and not np.isnan(c)]
        if not recent:
            return [0] * weeks
        base = np.mean(recent)
        # Oscillate around base with a 13-week cycle (quarterly seasonal)
        pattern = []
        for i in range(weeks):
            seasonal = base * (0.5 + 0.5 * np.sin(2 * np.pi * i / 13))
            pattern.append(seasonal)
        return pattern

    # If 5-year data is available, compute the average change for each calendar week
    # and map to target weeks
    hist_changes = historical["changes"]
    hist_dates = historical["dates"]

    # Build a lookup: week_number → average change
    week_avg = {}
    for i, d in enumerate(hist_dates):
        if i < len(hist_changes) and hist_changes[i] is not None:
            dt = pd.to_datetime(d)
            week_num = dt.isocalendar()[1]
            if week_num not in week_avg:
                week_avg[week_num] = []
            if not np.isnan(hist_changes[i]):
                week_avg[week_num].append(hist_changes[i])

    # Compute mean per week
    week_mean = {w: np.mean(vals) for w, vals in week_avg.items()}

    # Project forward using seasonal pattern
    pattern = []
    for i in range(weeks):
        future_dt = current_date + timedelta(weeks=i)
        wk = future_dt.isocalendar()[1]
        change = week_mean.get(wk, 0)
        pattern.append(change if not np.isnan(change) else 0)

    return pattern
