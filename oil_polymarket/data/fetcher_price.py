import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta

from data.cache import get, set
from config import DEFAULT_START, DEFAULT_END, TICKER_WTI, CACHE_TTL_YFINANCE, VOLUME_MA_DAYS

CACHE_KEY_WTI = "polymarket_yf_wti"
CACHE_KEY_WTI_INTRADAY = "polymarket_yf_wti_intraday"


def get_wti(start=DEFAULT_START, end=DEFAULT_END):
    data, _, _, stale = get(CACHE_KEY_WTI)
    if data is not None and not stale:
        return data

    df = yf.download(TICKER_WTI, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty:
        return {"dates": [], "close": [], "volume": [], "high": [], "low": [], "open": []}

    dates = [str(d.date()) for d in df.index]

    def _col(col_name, default_idx):
        if isinstance(df.columns, pd.MultiIndex):
            if col_name in df.columns:
                s = df[col_name]
            else:
                s = df.iloc[:, default_idx]
        else:
            s = df[col_name] if col_name in df.columns else df.iloc[:, default_idx]
        return [float(x) if not pd.isna(float(x)) else None for x in s.values.flatten()]

    close = _col("Close", 3)
    volume = _col("Volume", 5) if "Volume" in df.columns else [None] * len(dates)
    high = _col("High", 1)
    low = _col("Low", 2)
    opn = _col("Open", 0)

    result = {
        "dates": dates,
        "close": close,
        "volume": volume,
        "high": high,
        "low": low,
        "open": opn,
    }

    last_upd = datetime.now(timezone.utc).isoformat()
    set(CACHE_KEY_WTI, result, CACHE_TTL_YFINANCE, last_updated=last_upd)
    return result


def get_wti_intraday():
    data, _, _, stale = get(CACHE_KEY_WTI_INTRADAY)
    if data is not None and not stale:
        return data

    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    df = yf.download(TICKER_WTI, start=start, end=end, interval="5m", progress=False, auto_adjust=True)

    if df.empty:
        return {"timestamps": [], "prices": []}

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if "Close" in df.columns:
        close_col = df["Close"]
    else:
        close_col = df.iloc[:, 3]

    ts_list = []
    price_list = []
    today_open = None
    today_str = today.strftime("%Y-%m-%d")

    for idx, val in zip(close_col.index, close_col.values):
        v = float(val) if not pd.isna(val) else None
        if v is not None:
            ts_list.append(idx.isoformat())
            price_list.append(v)
            if today_open is None and str(idx.date()) == today_str:
                today_open = v

    result = {
        "timestamps": ts_list,
        "prices": price_list,
        "today_open": today_open,
    }
    set(CACHE_KEY_WTI_INTRADAY, result, 300, last_updated=datetime.now(timezone.utc).isoformat())
    return result


def get_volume_anomaly(start=DEFAULT_START, end=DEFAULT_END):
    wti = get_wti(start, end)
    if not wti or not wti.get("volume"):
        return None

    vols = pd.Series(wti["volume"])
    ma = vols.rolling(VOLUME_MA_DAYS).mean()
    ratio = vols / ma

    return {
        "dates": wti["dates"],
        "volume": wti["volume"],
        "volume_ma": ma.tolist(),
        "volume_ratio": ratio.tolist(),
    }
