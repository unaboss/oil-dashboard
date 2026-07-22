import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

EIA_API_KEY = os.getenv("EIA_API_KEY", "PLACEHOLDER")
EIA_BASE = "https://api.eia.gov/v2"

DEFAULT_START = "2025-12-01"
DEFAULT_END = datetime.now(timezone.utc).strftime("%Y-%m-%d")

TICKER_WTI = "CL=F"

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"

POLYMARKET_OIL_KEYWORDS = [
    "crude oil",
    "WTI crude",
    "oil price",
    "OPEC oil",
    "crude",
]

CACHE_TTL_YFINANCE = 3600
CACHE_TTL_EIA = 86400 * 3
CACHE_TTL_POLYMARKET = 3600
VOLUME_MA_DAYS = 20

# EIA Series Codes
EIA_CRUDE_STOCKS = "/petroleum/stoc/wstk"
EIA_RETAIL_GAS = "/petroleum/pri/gnd"

# Standard facets
FACETS_CRUDE = {"duoarea": "NUS", "product": "EPC0", "series": "WCESTUS1"}
FACETS_GASOLINE = {"duoarea": "NUS", "product": "EPM0", "series": "WGTSTUS1"}
FACETS_DISTILLATE = {"duoarea": "NUS", "product": "EPD0", "series": "WDISTUS1"}
FACETS_REFINERY_INPUT = {"duoarea": "NUS", "product": "EPC0", "series": "WCRIPUS1"}
FACETS_REFINERY_UTIL = {"duoarea": "NUS", "product": "EPC0", "series": "WCRPUNUS1"}
FACETS_GAS_PROD = {"duoarea": "NUS", "product": "EPM0", "series": "WGFRPUS1"}
FACETS_DIST_PROD = {"duoarea": "NUS", "product": "EPD0", "series": "WDPRPUS1"}
FACETS_SPR = {"duoarea": "NUS", "product": "EPC0", "series": "WCRSTUS1"}
FACETS_RETAIL = {"duoarea": "NUS", "product": "EPMR"}

# Polymarket inventory keywords
PM_INVENTORY_KEYWORDS = [
    "crude oil reserves",
    "oil inventory",
    "crude stocks",
    "US oil reserve",
    "crude oil stockpile",
    "SPR crude oil",
]
