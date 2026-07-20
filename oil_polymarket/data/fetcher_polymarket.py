import requests
from datetime import datetime, timezone

from data.cache import get as cache_get, set as cache_set
from config import (
    POLYMARKET_GAMMA_URL,
    POLYMARKET_OIL_KEYWORDS, CACHE_TTL_POLYMARKET,
)

CACHE_KEY_MARKETS = "polymarket_oil_markets"
CACHE_KEY_SENTIMENT = "polymarket_sentiment"


def _search_oil(keyword):
    try:
        url = f"{POLYMARKET_GAMMA_URL}/public-search"
        params = {
            "q": keyword,
            "events_status": "active",
            "limit_per_type": 30,
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def get_polymarket_markets():
    data, _, _, stale = cache_get(CACHE_KEY_MARKETS)
    if data is not None and not stale:
        return data

    all_events = []
    seen_slugs = set()

    for keyword in POLYMARKET_OIL_KEYWORDS:
        result = _search_oil(keyword)
        if not result:
            continue
        events = result.get("events", [])
        for ev in events:
            slug = ev.get("slug")
            if slug and slug not in seen_slugs:
                seen_slugs.add(slug)
                all_events.append(ev)

    all_markets = []
    for ev in all_events:
        markets = ev.get("markets", [])
        for m in markets:
            m["_event_title"] = ev.get("title", "")
            m["_event_slug"] = ev.get("slug", "")
            m["_event_end"] = ev.get("endDate", "")
            m["_event_volume"] = ev.get("volume", 0)
            m["_event_active"] = ev.get("active", False)
            m["_event_closed"] = ev.get("closed", False)
            all_markets.append(m)

    result = {
        "markets": all_markets,
        "events": all_events,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(all_markets),
    }

    last_upd = datetime.now(timezone.utc).isoformat()
    cache_set(CACHE_KEY_MARKETS, result, CACHE_TTL_POLYMARKET, last_updated=last_upd)
    return result


def get_aggregated_sentiment():
    data, _, _, stale = cache_get(CACHE_KEY_SENTIMENT)
    if data is not None and not stale:
        return data

    pm = get_polymarket_markets()
    markets = pm.get("markets", [])

    bullish_markets = []
    bearish_markets = []
    all_questions = []

    for m in markets:
        title = m.get("question") or m.get("_event_title") or ""
        title_lower = title.lower()

        outcome_prices = m.get("outcomePrices")
        if outcome_prices:
            try:
                prices = eval(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                price = float(prices[0]) if prices else None
            except Exception:
                price = None
        else:
            price = m.get("lastTradePrice") or m.get("bestBid")

        volume = float(m.get("volumeNum") or m.get("_event_volume") or 0)

        if not title_lower:
            continue

        is_bullish = any(w in title_lower for w in ["above", "higher", "rise", "increase", "bull", "up "])
        is_bearish = any(w in title_lower for w in ["below", "lower", "fall", "decrease", "bear", "down "])

        all_questions.append({
            "title": title,
            "price": price,
            "volume": volume,
            "bullish": is_bullish,
            "bearish": is_bearish,
        })

        if is_bullish:
            bullish_markets.append({"price": price, "volume": volume, "title": title})
        elif is_bearish:
            bearish_markets.append({"price": price, "volume": volume, "title": title})

    b_prices = [b["price"] for b in bullish_markets if b["price"] is not None]
    be_prices = [b["price"] for b in bearish_markets if b["price"] is not None]

    b_avg = sum(b_prices) / len(b_prices) if b_prices else None
    be_avg = sum(be_prices) / len(be_prices) if be_prices else None

    total_bull = len(bullish_markets)
    total_bear = len(bearish_markets)
    net = (total_bull - total_bear) / max(total_bull + total_bear, 1)

    total_volume = sum(b["volume"] for b in bullish_markets + bearish_markets)

    result = {
        "bullish_avg": b_avg,
        "bearish_avg": be_avg,
        "bullish_count": total_bull,
        "bearish_count": total_bear,
        "bullish_volume": sum(b["volume"] for b in bullish_markets),
        "bearish_volume": sum(b["volume"] for b in bearish_markets),
        "total_volume": total_volume,
        "net_sentiment": net,
        "all_questions": all_questions,
    }

    cache_set(CACHE_KEY_SENTIMENT, result, CACHE_TTL_POLYMARKET, last_updated=datetime.now(timezone.utc).isoformat())
    return result
