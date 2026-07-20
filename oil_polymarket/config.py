import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

EIA_API_KEY = os.getenv("EIA_API_KEY", "PLACEHOLDER")

DEFAULT_START = "2025-12-01"
DEFAULT_END = datetime.now(timezone.utc).strftime("%Y-%m-%d")

TICKER_WTI = "CL=F"
TICKER_RBOB = "RB=F"

EIA_BASE = "https://api.eia.gov/v2"

COT_URL = "https://www.cftc.gov/dea/futures/deacmesf.htm"
COT_CACHE_FILE = DATA_DIR / "cot_cache.csv"

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"

POLYMARKET_OIL_KEYWORDS = [
    "crude oil",
    "WTI",
    "brent",
    "oil price",
    "crude",
    "oil",
    "gasoline",
    "OPEC",
]

CACHE_TTL_YFINANCE = 3600
CACHE_TTL_EIA = 86400 * 3
CACHE_TTL_COT = 86400 * 3
CACHE_TTL_AAA = 86400
CACHE_TTL_POLYMARKET = 3600

CALENDAR_FORWARD_DAYS = 3
CALENDAR_LOOKBACK_DAYS = 180
SIGNAL_CONFIDENCE_THRESHOLD = 0.55

CONFLUENCE_SIGNALS = [
    "polymarket_daily",
    "polymarket_weekly",
    "polymarket_monthly",
    "cot_net_long",
    "eia_crude",
]

SIGNAL_WEIGHTS = {
    "polymarket_daily": 1.5,
    "polymarket_weekly": 1.0,
    "polymarket_monthly": 0.8,
    "cot_net_long": 1.0,
    "eia_crude": 1.0,
}

BULLISH_THRESHOLD = 2
BEARISH_THRESHOLD = -2

COT_EXTREME_LONG_PCT = 80
COT_EXTREME_SHORT_PCT = 20

VOLUME_MA_DAYS = 20

def next_eia_release():
    now = datetime.now(timezone.utc)
    release_hour = 15
    days_until_wed = (2 - now.weekday()) % 7
    if days_until_wed == 0 and now.hour >= release_hour:
        days_until_wed = 7
    return now.replace(hour=release_hour, minute=30, second=0, microsecond=0) + timedelta(days=days_until_wed)

def next_cot_release():
    now = datetime.now(timezone.utc)
    release_hour = 20
    days_until_fri = (4 - now.weekday()) % 7
    if days_until_fri == 0 and now.hour >= release_hour:
        days_until_fri = 7
    return now.replace(hour=release_hour, minute=30, second=0, microsecond=0) + timedelta(days=days_until_fri)
