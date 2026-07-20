import pandas as pd
import numpy as np


def cross_correlation(series_a, series_b, max_lag=30):
    sa = pd.Series(series_a).pct_change().dropna()
    sb = pd.Series(series_b).pct_change().dropna()
    results = {}
    for lag in range(max_lag + 1):
        if lag == 0:
            corr = sa.corr(sb)
            results[lag] = round(corr, 4) if not np.isnan(corr) else 0.0
        else:
            shifted = sb.shift(lag).dropna()
            aligned = sa.iloc[-len(shifted):] if len(shifted) < len(sa) else sa
            c = aligned.corr(shifted)
            results[lag] = round(c, 4) if not np.isnan(c) else 0.0
    return results


def optimal_lag(series_a, series_b, max_lag=30):
    cc = cross_correlation(series_a, series_b, max_lag)
    if not cc:
        return {"lag": None, "correlation": 0.0}
    best_lag = max(cc.items(), key=lambda x: abs(x[1]))
    return {"lag": best_lag[0], "correlation": best_lag[1]}


def build_lag_matrix(wti_close, eia_crude_changes, cot_net_long=None):
    matrix = []

    if wti_close and len(wti_close) >= 30:
        wti_returns = pd.Series(wti_close).pct_change().dropna().tolist()
    else:
        wti_returns = []

    if eia_crude_changes and len(eia_crude_changes) >= 10:
        eia_vals = [v for v in eia_crude_changes if v is not None and not np.isnan(v)]
    else:
        eia_vals = []

    if eia_vals and wti_returns:
        eia_aligned = eia_vals[-len(wti_returns):] if len(eia_vals) > len(wti_returns) else eia_vals
        wti_aligned = wti_returns[-len(eia_aligned):] if len(wti_returns) > len(eia_aligned) else wti_returns
        if len(eia_aligned) > 5 and len(wti_aligned) > 5:
            opt = optimal_lag(eia_aligned, wti_aligned)
            matrix.append({
                "source": "EIA Crude Change",
                "optimal_lag_days": opt["lag"],
                "correlation": opt["correlation"],
                "interpretation": f"EIA crude changes {'lead' if opt['lag'] and opt['lag'] > 0 else 'lag'} WTI by {opt['lag']} weeks" if opt["lag"] else "No significant lag found",
            })

    matrix.append({
        "source": "COT Net Positioning",
        "optimal_lag_days": "N/A (snapshot only)",
        "correlation": None,
        "interpretation": "Historical COT time series needed for lag analysis",
    })

    matrix.append({
        "source": "Polymarket Sentiment",
        "optimal_lag_days": "N/A (real-time)",
        "correlation": None,
        "interpretation": "Real-time odds — compare with WTI direction on same day for divergence",
    })

    return matrix
