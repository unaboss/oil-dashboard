"""Centralized configuration for Oil Dashboard."""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

EIA_API_KEY = os.getenv("EIA_API_KEY", "PLACEHOLDER")

# ── Date Range ──────────────────────────────────────────────────────────────────
DEFAULT_START = "2025-12-01"
DEFAULT_END = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ── yfinance Tickers ────────────────────────────────────────────────────────────
TICKER_WTI = "CL=F"
TICKER_BRENT = "BZ=F"
TICKER_RBOB = "RB=F"
TICKER_OVX = "^OVX"
TICKER_DXY = "DX-Y.NYB"

# ── EIA API v2 Routes ───────────────────────────────────────────────────────────
EIA_BASE = "https://api.eia.gov/v2"

EIA_ROUTES = {
    "crude_stocks": "/petroleum/stoc/wstk",
    "gasoline_stocks": "/petroleum/stoc/wstk",
    "distillate_stocks": "/petroleum/stoc/wstk",
    "cushing_stocks": "/petroleum/stoc/wstk",
    "retail_gas_price": "/petroleum/pri/gnd",
    "gasoline_stocks_change": "/petroleum/stoc/wstk",
    "distillate_stocks_change": "/petroleum/stoc/wstk",
}

# ── CFTC COT Report ─────────────────────────────────────────────────────────────
COT_URL = "https://www.cftc.gov/dea/futures/deacmesf.htm"
COT_CACHE_FILE = DATA_DIR / "cot_cache.csv"

# ── Cache TTLs (seconds) ────────────────────────────────────────────────────────
# yfinance: 3600 market hours, 21600 otherwise
CACHE_TTL_YFINANCE_MARKET = 60 * 60
CACHE_TTL_YFINANCE_OFFHOURS = 60 * 60 * 6
CACHE_TTL_EIA = 60 * 60 * 24 * 3  # until next Wednesday
CACHE_TTL_COT = 60 * 60 * 24 * 3  # until next Friday
CACHE_TTL_AAA = 60 * 60 * 24
CACHE_TTL_TRENDS = 60 * 60 * 24
CACHE_TTL_CALENDAR = 60 * 60 * 6

# ── EIA Weekly Release Schedule ─────────────────────────────────────────────────
# EIA Petroleum Status: Wednesdays at 10:30 AM ET (15:30 UTC daylight, 14:30 UTC standard)
def next_eia_release():
    now = datetime.now(timezone.utc)
    release_hour = 15  # 10:30 AM ET = 14:30/15:30 UTC depending on DST
    days_until_wed = (2 - now.weekday()) % 7
    if days_until_wed == 0 and now.hour >= release_hour:
        days_until_wed = 7
    next_wed = now.replace(hour=release_hour, minute=30, second=0, microsecond=0) + timedelta(days=days_until_wed)
    return next_wed

# COT Report: Fridays at 3:30 PM ET
def next_cot_release():
    now = datetime.now(timezone.utc)
    release_hour = 20  # 3:30 PM ET
    days_until_fri = (4 - now.weekday()) % 7
    if days_until_fri == 0 and now.hour >= release_hour:
        days_until_fri = 7
    next_fri = now.replace(hour=release_hour, minute=30, second=0, microsecond=0) + timedelta(days=days_until_fri)
    return next_fri

# ── Confluence Score Thresholds ─────────────────────────────────────────────────
CONFLUENCE_SIGNALS = [
    "volume",      # WTI volume > 20d avg
    "cot",         # COT managed money extreme long/short
    "inventories", # EIA crude draw/build
    "crack",       # RBOB-WTI crack widening/narrowing
    "dxy",         # Dollar weakening/strengthening
    "curve",       # Futures curve backwardation/contango
]

SIGNAL_WEIGHTS = {
    "volume": 1,
    "cot": 1,
    "inventories": 1,
    "crack": 1,
    "dxy": 1,
    "curve": 1,
}

BULLISH_THRESHOLD = 2
BEARISH_THRESHOLD = -2

# ── Volume Anomaly ──────────────────────────────────────────────────────────────
VOLUME_MA_DAYS = 20

# ── COT Extreme Thresholds ──────────────────────────────────────────────────────
COT_EXTREME_LONG_PCT = 80
COT_EXTREME_SHORT_PCT = 20

# ── Returns thresholds for audit ────────────────────────────────────────────────
AUDIT_RETURN_THRESHOLD = 0.03  # 3% move to flag as significant
AUDIT_LOOKBACK_DAYS = 30
AUDIT_FORWARD_DAYS = 3  # check 3-day forward return

# ── Research & Narrative Tab ─────────────────────────────────────────────────────
RESEARCH_TRUMP_CSV = DATA_DIR / "trump_oil_statements.csv"
RESEARCH_TRADERS_CSV = DATA_DIR / "losing_traders.csv"

# Trump event-study windows (trading days)
TRUMP_PRE_LOOKBACK = 5    # move already done before he spoke
TRUMP_FWD_LOOKBACK = 3    # move after he spoke
TRUMP_MOVE_THRESHOLD = 0.02  # 2% to count as a "significant" move

# Bot-mention proxy keywords (Google Trends)
BOT_KEYWORDS = [
    "MetaTrader oil EA",
    "TradingView oil bot",
    "Pine Script oil",
    "3Commas oil",
    "oil trading bot",
]
