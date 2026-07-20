import numpy as np


def compute_implied_distribution(targets):
    if len(targets) < 3:
        return {"error": "Need at least 3 strikes for distribution fitting"}

    strikes = np.array([t["strike"] for t in targets])
    probs = np.array([t["prob_above"] for t in targets])

    sort_idx = np.argsort(strikes)
    strikes = strikes[sort_idx]
    probs = probs[sort_idx]

    probs = np.maximum.accumulate(probs[::-1])[::-1]
    probs = np.clip(probs, 0.001, 0.999)

    if strikes[-1] - strikes[0] < 0.01:
        return {"error": "Strike range too narrow"}

    try:
        from scipy.interpolate import PchipInterpolator
        surv_func = PchipInterpolator(strikes, probs)
    except ImportError:
        surv_func = lambda x: np.interp(x, strikes, probs)

    dx = 0.05
    x_min = max(strikes[0] - 1, 0)
    x_max = strikes[-1] + 1
    x_fine = np.arange(x_min, x_max + dx, dx)

    surv_fine = surv_func(x_fine)
    surv_fine = np.clip(surv_fine, 0.001, 0.999)

    pdf_fine = -np.gradient(surv_fine, dx)
    pdf_fine = np.clip(pdf_fine, 0, None)
    total = pdf_fine.sum() * dx
    if total > 0:
        pdf_fine = pdf_fine / total

    expected = np.sum(x_fine * pdf_fine * dx)

    cdf_fine = 1 - surv_fine
    cdf_fine = np.clip(cdf_fine, 0, 1)

    n = len(x_fine) - 1
    p10 = x_fine[min(np.searchsorted(cdf_fine, 0.10), n)]
    p25 = x_fine[min(np.searchsorted(cdf_fine, 0.25), n)]
    p50 = x_fine[min(np.searchsorted(cdf_fine, 0.50), n)]
    p75 = x_fine[min(np.searchsorted(cdf_fine, 0.75), n)]
    p90 = x_fine[min(np.searchsorted(cdf_fine, 0.90), n)]

    mode_idx = np.argmax(pdf_fine)
    mode = x_fine[mode_idx]

    return {
        "expected": round(float(expected), 2),
        "median": round(float(p50), 2),
        "mode": round(float(mode), 2),
        "p10": round(float(p10), 2),
        "p25": round(float(p25), 2),
        "p75": round(float(p75), 2),
        "p90": round(float(p90), 2),
        "iqr": round(float(p75 - p25), 2),
        "strikes": strikes.tolist(),
        "prob_above": probs.tolist(),
        "x_fine": x_fine.tolist() if len(x_fine) < 800 else None,
        "pdf_fine": pdf_fine.tolist() if len(x_fine) < 800 else None,
        "surv_fine": surv_fine.tolist() if len(x_fine) < 800 else None,
    }


def compute_hit_distribution(targets, direction="upside"):
    if len(targets) < 3:
        return {"error": "Need at least 3 strikes"}

    strikes = np.array([t["strike"] for t in targets])
    probs = np.array([t["prob"] for t in targets])

    sort_idx = np.argsort(strikes)
    strikes = strikes[sort_idx]
    probs = probs[sort_idx]

    if direction == "upside":
        probs = np.maximum.accumulate(probs[::-1])[::-1]
    else:
        probs = np.minimum.accumulate(probs)

    probs = np.clip(probs, 0.001, 0.999)

    try:
        from scipy.interpolate import PchipInterpolator
        prob_func = PchipInterpolator(strikes, probs)
    except ImportError:
        prob_func = lambda x: np.interp(x, strikes, probs)

    dx = 0.05
    x_min, x_max = strikes[0], strikes[-1]
    if x_max - x_min < 0.01:
        return {"error": "Strike range too narrow"}

    x_range = np.arange(x_min, x_max + dx, dx)
    prob_fine = prob_func(x_range)

    if direction == "upside":
        pdf_fine = -np.gradient(prob_fine, dx)
    else:
        pdf_fine = np.gradient(prob_fine, dx)

    pdf_fine = np.clip(pdf_fine, 0, None)
    total = pdf_fine.sum() * dx
    if total > 0:
        pdf_fine = pdf_fine / total

    mode_idx = np.argmax(pdf_fine)
    most_likely = x_range[mode_idx]
    expected = np.sum(x_range * pdf_fine * dx)

    return {
        "expected_extreme": round(float(expected), 2),
        "most_likely": round(float(most_likely), 2),
        "direction": direction,
        "strikes": strikes.tolist(),
        "probabilities": probs.tolist(),
        "x_range": x_range.tolist() if len(x_range) < 800 else None,
        "prob_fine": prob_fine.tolist() if len(prob_fine) < 800 else None,
        "pdf_fine": pdf_fine.tolist() if len(pdf_fine) < 800 else None,
    }
