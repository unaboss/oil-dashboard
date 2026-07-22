import re

PATTERN_UP_DOWN = re.compile(r"up or down", re.IGNORECASE)
PATTERN_CLOSES_ABOVE = re.compile(r"closes above\s*\$?(\d+)", re.IGNORECASE)
PATTERN_HIT_HIGH = re.compile(r"hit\s*\(HIGH\)\s*\$?(\d+)", re.IGNORECASE)
PATTERN_HIT_LOW = re.compile(r"hit\s*\(LOW\)\s*\$?(\d+)", re.IGNORECASE)
PATTERN_WEEK_OF = re.compile(r"week of|week\s+\d+", re.IGNORECASE)
PATTERN_MONTH_IN = re.compile(
    r"in\s+(January|February|March|April|May|June|July|"
    r"August|September|October|November|December)", re.IGNORECASE
)
PATTERN_ALL_TIME_HIGH = re.compile(r"all[.\-\s]?time\s+high", re.IGNORECASE)
PATTERN_ON_DATE = re.compile(r"on\s+(\w+\s+\d{1,2})", re.IGNORECASE)
PATTERN_SANCTION = re.compile(r"sanction", re.IGNORECASE)
PATTERN_OPEC = re.compile(r"OPEC", re.IGNORECASE)
PATTERN_RESERVES = re.compile(r"reserves|inventory|stockpile", re.IGNORECASE)
PATTERN_PRODUCTION = re.compile(r"production.*barrels|barrels.*production", re.IGNORECASE)
PATTERN_CRUDE_WTI = re.compile(r"crude|WTI|oil price|oil sanction|oil reserve|oil product|OPEC", re.IGNORECASE)

NON_OIL_BRENT = [
    re.compile(p, re.IGNORECASE) for p in [
        r"brent\s+van\s+moer", r"brent\s+hennrich", r"brent\s+rooker",
        r"brent\s+bien", r"brenton\s+doyle", r"brentford",
    ]
]
NON_OIL_BERNIE = re.compile(r"bernie.*say.*oil", re.IGNORECASE)


def is_genuine_oil_market(market):
    question = (market.get("question") or "").lower()
    event_title = (market.get("_event_title") or "").lower()
    combined = f"{question} {event_title}"

    if not PATTERN_CRUDE_WTI.search(combined):
        return False

    for pat in NON_OIL_BRENT:
        if pat.search(combined):
            return False

    if NON_OIL_BERNIE.search(combined):
        return False

    return True


def parse_price(market):
    outcome_prices = market.get("outcomePrices")
    if outcome_prices:
        try:
            prices = eval(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
            return float(prices[0]) if prices else None
        except Exception:
            pass
    price = market.get("lastTradePrice") or market.get("bestBid")
    try:
        return float(price) if price is not None else None
    except (ValueError, TypeError):
        return None


def classify_market(market):
    question = (market.get("question") or "").strip()
    event_title = (market.get("_event_title") or "").strip()
    text = f"{question} | {event_title}"
    price = parse_price(market)

    result = {
        "question": question,
        "event_title": event_title,
        "price": price,
        "end_date": market.get("endDate"),
        "volume": float(market.get("volumeNum") or 0),
        "family": "unknown",
        "strike": None,
        "direction": "neutral",
        "horizon_type": None,
        "target_date": None,
        "closed": market.get("closed", False),
    }

    if not PATTERN_CRUDE_WTI.search(text):
        result["family"] = "noise_non_oil"
        return result

    # 1. Daily Directional
    if PATTERN_UP_DOWN.search(question):
        result["family"] = "daily_direction"
        date_match = PATTERN_ON_DATE.search(question)
        if date_match:
            result["target_date"] = date_match.group(1)
        return result

    # 2. Daily closes-above price targets
    closes_match = PATTERN_CLOSES_ABOVE.search(question)
    if closes_match:
        result["family"] = "daily_price_targets"
        result["strike"] = float(closes_match.group(1))
        result["direction"] = "upside"
        date_match = PATTERN_ON_DATE.search(question)
        if date_match:
            result["target_date"] = date_match.group(1)
        return result

    # 3 & 4. Weekly/Monthly hit targets
    high_match = PATTERN_HIT_HIGH.search(question)
    low_match = PATTERN_HIT_LOW.search(question)
    strike_match = high_match or low_match

    if strike_match:
        strike = float(strike_match.group(1))
        direction = "upside" if high_match else "downside"

        if PATTERN_WEEK_OF.search(question):
            family = "weekly_price_targets"
            horizon = "weekly"
        elif PATTERN_MONTH_IN.search(question):
            family = "monthly_price_targets"
            horizon = "monthly"
        else:
            family = "price_targets"
            horizon = "unknown"

        result["family"] = family
        result["strike"] = strike
        result["direction"] = direction
        result["horizon_type"] = horizon

        date_match = PATTERN_ON_DATE.search(question)
        month_match = PATTERN_MONTH_IN.search(question) if not date_match else None
        if date_match:
            result["target_date"] = date_match.group(1)
        elif month_match:
            result["target_date"] = month_match.group(1)
        return result

    # 5. All-time high
    if PATTERN_ALL_TIME_HIGH.search(text):
        result["family"] = "all_time_high"
        result["direction"] = "upside"
        return result

    # 6. Sanctions
    if PATTERN_SANCTION.search(text):
        result["family"] = "geo_sanctions"
        return result

    # 7. OPEC
    if PATTERN_OPEC.search(text):
        result["family"] = "opec_geopolitics"
        return result

    # 8. Inventory
    if PATTERN_RESERVES.search(text):
        result["family"] = "inventory_targets"
        num_match = re.search(r"(?:to|below|above)\s*\$?(\d+\.?\d*[MBK]?)", question, re.IGNORECASE)
        if num_match:
            result["strike"] = num_match.group(1)
        return result

    # 9. Production
    if PATTERN_PRODUCTION.search(text):
        result["family"] = "production_targets"
        prod_match = re.search(r"reach\s+(\d+\.?\d*m)", question, re.IGNORECASE)
        if prod_match:
            result["strike"] = prod_match.group(1)
        return result

    return result


def classify_all(markets):
    results = []
    for m in markets:
        if not is_genuine_oil_market(m):
            continue
        classified = classify_market(m)
        results.append(classified)
    return results
