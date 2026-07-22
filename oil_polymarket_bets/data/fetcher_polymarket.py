import requests
from datetime import datetime, timezone, timedelta

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

    from analysis.polymarket_classifier import classify_all

    classified = classify_all(markets)

    daily_direction = [c for c in classified if c["family"] == "daily_direction"]
    most_recent = daily_direction[0] if daily_direction else None

    bullish_count = sum(1 for c in classified if c["direction"] == "upside" and c.get("strike"))
    bearish_count = sum(1 for c in classified if c["direction"] == "downside" and c.get("strike"))

    result = {
        "daily_direction": {
            "prob_up": most_recent["price"] if most_recent else None,
            "date": most_recent["target_date"] if most_recent else None,
        } if most_recent else None,
        "bullish_targets": bullish_count,
        "bearish_targets": bearish_count,
        "total_oil_markets": len(classified),
        "all_classified": classified,
    }

    cache_set(CACHE_KEY_SENTIMENT, result, CACHE_TTL_POLYMARKET, last_updated=datetime.now(timezone.utc).isoformat())
    return result


def get_up_down_history(target_date=None):
    cache_key = f"polymarket_updown_{target_date.isoformat() if target_date else 'active'}"
    data, _, _, stale = cache_get(cache_key)
    if data is not None and not stale:
        return data

    from datetime import datetime, timezone

    result = []

    pm = get_polymarket_markets()
    markets_list = pm.get("markets", [])

    # Also search for resolved markets if target_date is in the past
    if target_date:
        try:
            date_str = target_date.strftime("%B %d").replace(" 0", " ")
            r = requests.get(
                f"{POLYMARKET_GAMMA_URL}/public-search",
                params={"q": f"WTI Up or Down {target_date.strftime('%B %d')}", "closed": True, "limit_per_type": 3},
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            r.raise_for_status()
            resolved_events = r.json().get("events", [])
            for ev in resolved_events:
                for m in ev.get("markets", []):
                    q = (m.get("question") or "")
                    if "Up or Down" in q:
                        markets_list.append(m)
        except Exception:
            pass

    for m in markets_list:
        q = (m.get("question") or "")
        if "Up or Down" not in q:
            continue
        if m.get("closed") and not target_date:
            continue
        ids = m.get("clobTokenIds")
        if not ids:
            continue
        try:
            ids_parsed = eval(ids) if isinstance(ids, str) else ids
            token_id = str(ids_parsed[0] if isinstance(ids_parsed, list) else ids_parsed)
        except Exception:
            continue

        try:
            r = requests.get(
                "https://clob.polymarket.com/prices-history",
                params={"market": token_id, "interval": "max"},
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            r.raise_for_status()
            for h in r.json().get("history", []):
                result.append({"timestamp": h["t"], "price": h["p"]})
        except Exception:
            continue

    result.sort(key=lambda x: x["timestamp"])
    result = [e for e in result if e["price"] != 0.50]
    # Dedupe by keeping max price per timestamp
    deduped = {}
    for e in result:
        deduped[e["timestamp"]] = e
    result = sorted(deduped.values(), key=lambda x: x["timestamp"])

    cache_set(cache_key, result, 300, last_updated=datetime.now(timezone.utc).isoformat())
    return result
    return result


def get_up_down_history_all():
    data, _, _, stale = cache_get("polymarket_updown_history")
    if data is not None and not stale:
        return data

    from datetime import datetime, timezone

    result = []
    today = datetime.now(timezone.utc).date()

    for offset in range(5):
        target = today - timedelta(days=offset)
        if target.weekday() >= 5:
            continue
        try:
            day_data = get_up_down_history(target)
            result.extend(day_data)
        except Exception:
            continue

    result.sort(key=lambda x: x["timestamp"])
    result = [e for e in result if e["price"] != 0.50]
    cache_set("polymarket_updown_history", result, 300, last_updated=datetime.now(timezone.utc).isoformat())
    return result
