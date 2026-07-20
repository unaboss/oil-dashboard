import numpy as np
import pandas as pd
from datetime import datetime, timezone


def align_series(wti_times, wti_prices, pm_times, pm_prices, freq="5min"):
    wti_df = pd.DataFrame({"t": pd.to_datetime(wti_times), "wti": wti_prices}).set_index("t")
    pm_df = pd.DataFrame({"t": pd.to_datetime(pm_times), "pm": pm_prices}).set_index("t")

    if hasattr(wti_df.index, "tz") and wti_df.index.tz is None:
        wti_df.index = wti_df.index.tz_localize("UTC")
    if hasattr(pm_df.index, "tz") and pm_df.index.tz is None:
        pm_df.index = pm_df.index.tz_localize("UTC")

    wti_df.index = wti_df.index.tz_convert("UTC")
    pm_df.index = pm_df.index.tz_convert("UTC")

    wti_r = wti_df[~wti_df.index.duplicated()].resample(freq).last().interpolate(limit=3)
    pm_r = pm_df[~pm_df.index.duplicated()].resample(freq).nearest().ffill(limit=3)

    merged = wti_r.join(pm_r, how="inner").dropna()
    return merged


def detect_phases(merged, wti_open):
    if merged.empty or wti_open is None:
        return merged, 0.0, "neutral"

    wti_pct = (merged["wti"].values - wti_open) / wti_open * 100
    pm_dev = merged["pm"].values - 50

    phases = np.full(len(wti_pct), "neutral", dtype=object)

    for i in range(len(wti_pct)):
        w = wti_pct[i]
        p = pm_dev[i]

        if abs(w) < 0.05 and abs(p) < 2:
            phases[i] = "neutral"
        elif w > 0.05 and p > 2:
            if w > p * 0.8:
                phases[i] = "pm_lagging"
            elif p > w * 1.5:
                phases[i] = "pm_ahead"
            else:
                phases[i] = "converging"
        elif w > 0.05 and p < -2:
            phases[i] = "divergence"
        elif w < -0.05 and p < -2:
            if abs(w) > abs(p) * 0.8:
                phases[i] = "pm_lagging"
            elif abs(p) > abs(w) * 1.5:
                phases[i] = "pm_ahead"
            else:
                phases[i] = "converging"
        elif w < -0.05 and p > 2:
            phases[i] = "divergence"

    merged = merged.copy()
    merged["phase"] = phases

    current_phase = phases[-1] if len(phases) > 0 else "neutral"

    # Current phase multiplier
    multipliers = {
        "pm_lagging": 1.2,
        "converging": 1.0,
        "pm_ahead": 0.8,
        "divergence": -1.5,
        "neutral": 0.0,
    }
    current_multiplier = multipliers.get(current_phase, 0.0)

    # Lag time: cross-correlation peak
    lag_minutes = _compute_lead_lag(wti_pct, pm_dev)

    return merged, current_multiplier, current_phase, lag_minutes


def _compute_lead_lag(wti_pct, pm_dev, max_lag=30):
    if len(wti_pct) < 10:
        return 0

    best_lag = 0
    best_corr = 0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            x = wti_pct[-lag:]
            y = pm_dev[:lag]
        elif lag > 0:
            x = wti_pct[:-lag] if lag < len(wti_pct) else wti_pct[:0]
            y = pm_dev[lag:]
        else:
            x = wti_pct
            y = pm_dev
        if len(x) < 5 or len(y) < 5:
            continue
        n = min(len(x), len(y))
        corr = np.corrcoef(x[:n], y[:n])[0, 1]
        if not np.isnan(corr) and abs(corr) > abs(best_corr):
            best_corr = corr
            best_lag = lag

    return best_lag * 5  # multiply by 5 min intervals
