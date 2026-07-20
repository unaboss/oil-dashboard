from analysis.polymarket_classifier import classify_all
from analysis.implied_distribution import compute_implied_distribution, compute_hit_distribution


def build_polymarket_signal(markets, wti_current_price=None):
    classified = classify_all(markets)

    families = {}
    for c in classified:
        fam = c["family"]
        if fam not in families:
            families[fam] = []
        families[fam].append(c)

    output = {
        "total_classified": len(classified),
        "daily_direction": _build_daily_direction(families.get("daily_direction", [])),
        "daily_targets": _build_daily_targets(families.get("daily_price_targets", [])),
        "weekly_targets": _build_price_targets(families.get("weekly_price_targets", []), "weekly"),
        "monthly_targets": _build_price_targets(families.get("monthly_price_targets", []), "monthly"),
        "opec_geopolitics": _build_opec(families.get("opec_geopolitics", [])),
        "geo_sanctions": _build_opec(families.get("geo_sanctions", [])),
        "all_time_high": families.get("all_time_high", []),
        "inventory_targets": families.get("inventory_targets", []),
        "production_targets": families.get("production_targets", []),
        "other": families.get("unknown", []) + families.get("price_targets", []),
    }

    if wti_current_price:
        output["current_wti"] = wti_current_price
        _add_skew(output, wti_current_price)

    return output


def _build_daily_direction(markets):
    if not markets:
        return None

    m = markets[0]
    prob_up = m["price"] if m["price"] is not None else None
    prob_down = 1 - prob_up if prob_up is not None else None
    net = prob_up - prob_down if prob_up is not None and prob_down is not None else None

    interpretation = "neutral"
    if net is not None:
        if net > 0.10:
            interpretation = "bullish"
        elif net < -0.10:
            interpretation = "bearish"

    return {
        "date": m["target_date"],
        "prob_up": prob_up,
        "prob_down": prob_down,
        "net_sentiment": round(net, 3) if net is not None else None,
        "interpretation": interpretation,
        "volume": m["volume"],
        "question": m["question"],
    }


def _build_daily_targets(markets):
    if len(markets) < 3:
        return None

    strikes_data = []
    for m in markets:
        prob = m["price"]
        if prob is not None and prob > 0:
            strikes_data.append({
                "strike": m["strike"],
                "prob_above": prob,
                "volume": m["volume"],
                "question": m["question"],
            })

    strikes_data.sort(key=lambda x: x["strike"])

    distribution = compute_implied_distribution(strikes_data)

    return {
        "date": markets[0]["target_date"],
        "strikes": strikes_data,
        "distribution": distribution if "error" not in distribution else None,
    }


def _build_price_targets(markets, horizon):
    if not markets:
        return None

    upside = [m for m in markets if m["direction"] == "upside"]
    downside = [m for m in markets if m["direction"] == "downside"]

    result = {"horizon": horizon}

    if upside:
        upside_data = []
        for m in upside:
            prob = m["price"]
            if prob is not None:
                upside_data.append({
                    "strike": m["strike"],
                    "prob": prob,
                    "volume": m["volume"],
                    "question": m["question"],
                })
        upside_data.sort(key=lambda x: x["strike"])
        result["upside"] = {
            "strikes": upside_data,
            "distribution": compute_hit_distribution(upside_data, "upside"),
        }

    if downside:
        downside_data = []
        for m in downside:
            prob = m["price"]
            if prob is not None:
                downside_data.append({
                    "strike": m["strike"],
                    "prob": prob,
                    "volume": m["volume"],
                    "question": m["question"],
                })
        downside_data.sort(key=lambda x: x["strike"])
        result["downside"] = {
            "strikes": downside_data,
            "distribution": compute_hit_distribution(downside_data, "downside"),
        }

    return result if (result.get("upside") or result.get("downside")) else None


def _build_opec(markets):
    if not markets:
        return []
    return [{"question": m["question"], "prob_yes": m["price"], "volume": m["volume"]} for m in markets]


def _add_skew(output, wti_price):
    monthly = output.get("monthly_targets")
    if monthly:
        upside = monthly.get("upside", {})
        dist = upside.get("distribution", {}) if upside else {}
        if "error" not in dist and dist.get("most_likely"):
            monthly["upside_skew"] = round(dist["most_likely"] - wti_price, 2)
            monthly["expected_high"] = dist.get("expected_extreme")
            monthly["most_likely_high"] = dist.get("most_likely")

        downside = monthly.get("downside", {})
        dist_d = downside.get("distribution", {}) if downside else {}
        if "error" not in dist_d and dist_d.get("most_likely"):
            monthly["downside_skew"] = round(dist_d["most_likely"] - wti_price, 2)
            monthly["most_likely_low"] = dist_d.get("most_likely")

    weekly = output.get("weekly_targets")
    if weekly:
        upside = weekly.get("upside", {})
        dist = upside.get("distribution", {}) if upside else {}
        if "error" not in dist and dist.get("most_likely"):
            weekly["upside_skew"] = round(dist["most_likely"] - wti_price, 2)
            weekly["expected_high"] = dist.get("expected_extreme")
            weekly["most_likely_high"] = dist.get("most_likely")

        downside = weekly.get("downside", {})
        dist_d = downside.get("distribution", {}) if downside else {}
        if "error" not in dist_d and dist_d.get("most_likely"):
            weekly["downside_skew"] = round(dist_d["most_likely"] - wti_price, 2)
            weekly["most_likely_low"] = dist_d.get("most_likely")
