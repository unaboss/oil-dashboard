import pandas as pd
import numpy as np

from config import CONFLUENCE_SIGNALS, SIGNAL_WEIGHTS, BULLISH_THRESHOLD, BEARISH_THRESHOLD


def classify_polymarket_markets_by_horizon(markets):
    daily = []
    weekly = []
    monthly = []
    other = []

    for m in markets:
        title = (m.get("question") or m.get("_event_title") or "").lower()
        end_date = m.get("endDate") or m.get("_event_end") or ""
        if "daily" in title or "day" in title or "24h" in title or "24" in title:
            daily.append(m)
        elif "weekly" in title or "week" in title or "wk" in title or "w/" in title:
            weekly.append(m)
        elif "monthly" in title or "month" in title or "mo" in title:
            monthly.append(m)
        elif end_date:
            try:
                end_dt = pd.to_datetime(end_date)
                now = pd.Timestamp.now(tz="UTC")
                days = (end_dt - now).days
                if days <= 2:
                    daily.append(m)
                elif days <= 10:
                    weekly.append(m)
                elif days <= 45:
                    monthly.append(m)
                else:
                    other.append(m)
            except Exception:
                other.append(m)
        else:
            other.append(m)

    return {"daily": daily, "weekly": weekly, "monthly": monthly, "other": other}


def _parse_price(m):
    price = m.get("lastTradePrice")
    if price is None:
        price = m.get("bestBid")
    if price is None:
        outcome_prices = m.get("outcomePrices")
        if outcome_prices:
            try:
                prices = eval(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                price = prices[0] if prices else None
            except Exception:
                price = None
    try:
        return float(price) if price is not None else None
    except (ValueError, TypeError):
        return None


def compute_horizon_sentiment(markets):
    if not markets:
        return {"avg_price": None, "count": 0, "direction": "neutral", "volume": 0}

    prices = []
    volume = 0
    bullish_count = 0
    bearish_count = 0

    for m in markets:
        price = _parse_price(m)
        title = (m.get("question") or m.get("_event_title") or "").lower()

        if price is not None:
            prices.append(price)

        v = float(m.get("volumeNum") or m.get("_event_volume") or 0)
        volume += v

        is_bullish = any(w in title for w in ["above", "higher", "rise", "increase", "bull", "up "])
        is_bearish = any(w in title for w in ["below", "lower", "fall", "decrease", "bear", "down "])

        if is_bullish and price is not None and price > 0.50:
            bullish_count += 1
        elif is_bearish and price is not None and price > 0.50:
            bearish_count += 1

    avg_price = np.mean(prices) if prices else None

    if bullish_count > bearish_count:
        direction = "bullish"
    elif bearish_count > bullish_count:
        direction = "bearish"
    else:
        direction = "neutral"

    return {
        "avg_price": avg_price,
        "count": len(markets),
        "direction": direction,
        "volume": volume,
        "bullish_signals": bullish_count,
        "bearish_signals": bearish_count,
    }


def build_polymarket_curve(markets, wti_dates=None):
    classified = classify_polymarket_markets_by_horizon(markets)
    daily = compute_horizon_sentiment(classified["daily"])
    weekly = compute_horizon_sentiment(classified["weekly"])
    monthly = compute_horizon_sentiment(classified["monthly"])

    return {
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "raw_daily": classified["daily"],
        "raw_weekly": classified["weekly"],
        "raw_monthly": classified["monthly"],
        "raw_other": classified["other"],
    }


def compute_divergence(market_data, polymarket_sentiment):
    wti = market_data.get("wti") if isinstance(market_data, dict) else None
    if wti is None:
        wti = {}
    close = wti.get("close", [])
    dates = wti.get("dates", [])

    if not close or len(close) < 5:
        return []

    recent_return = (close[-1] / close[-5] - 1) if len(close) >= 5 else 0

    divergence_events = []

    pm_direction = polymarket_sentiment.get("net_sentiment", 0)

    if recent_return > 0.01 and pm_direction <= 0:
        divergence_events.append({
            "type": "price_up_pm_flat",
            "description": "Price rising but Polymarket odds not confirming — potential fake move",
            "wti_change": round(recent_return * 100, 2),
            "pm_bias": "bearish" if pm_direction < 0 else "neutral",
        })
    elif recent_return < -0.01 and pm_direction >= 0:
        divergence_events.append({
            "type": "price_down_pm_flat",
            "description": "Price falling but Polymarket odds not confirming — potential bounce",
            "wti_change": round(recent_return * 100, 2),
            "pm_bias": "bullish" if pm_direction > 0 else "neutral",
        })

    if polymarket_sentiment.get("bullish_avg") and polymarket_sentiment.get("bearish_avg"):
        b_avg = polymarket_sentiment["bullish_avg"]
        be_avg = polymarket_sentiment["bearish_avg"]
        if b_avg > be_avg and recent_return < 0:
            divergence_events.append({
                "type": "pm_bullish_price_down",
                "description": "Polymarket odds bullish but price declining — contrarian signal",
                "pm_bull_avg": round(b_avg * 100, 1),
                "pm_bear_avg": round(be_avg * 100, 1),
            })

    return divergence_events
