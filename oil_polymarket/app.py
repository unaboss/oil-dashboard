import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Oil — Polymarket Dashboard",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from data.fetcher_price import get_wti, get_wti_intraday
from data.fetcher_cot import get_cot_data
from data.fetcher_eia import get_all_eia_data
from data.fetcher_aaa import get_aaa_gas_price
from data.fetcher_polymarket import get_polymarket_markets, get_aggregated_sentiment, get_up_down_history_all
from analysis.polymarket_curve import build_polymarket_signal

from ui.tab_price_polymarket import render_price_polymarket_tab
from ui.tab_cot import render_cot_tab
from ui.tab_inventories import render_inventories_tab
from ui.tab_sentiment import render_sentiment_tab
from ui.tab_calendar import render_calendar_tab

CACHE_TTL_PRICE = 3600
CACHE_TTL_INTRADAY = 300
CACHE_TTL_EIA = 86400
CACHE_TTL_COT = 86400
CACHE_TTL_AAA = 86400
CACHE_TTL_PM = 3600
CACHE_TTL_PM_HISTORY = 300


@st.cache_data(ttl=CACHE_TTL_PRICE)
def load_wti(start, end):
    return get_wti(start=str(start), end=str(end))


@st.cache_data(ttl=CACHE_TTL_INTRADAY)
def load_wti_intraday():
    return get_wti_intraday()


@st.cache_data(ttl=CACHE_TTL_EIA)
def load_eia(start, end):
    return get_all_eia_data(start=str(start), end=str(end))


@st.cache_data(ttl=CACHE_TTL_COT)
def load_cot():
    return get_cot_data()


@st.cache_data(ttl=CACHE_TTL_AAA)
def load_aaa():
    return get_aaa_gas_price()


@st.cache_data(ttl=CACHE_TTL_PM)
def load_polymarket():
    pm_markets = get_polymarket_markets()
    sentiment = get_aggregated_sentiment()
    return {"markets": pm_markets, "sentiment": sentiment}


@st.cache_data(ttl=CACHE_TTL_PM_HISTORY)
def load_pm_history():
    return get_up_down_history_all()


def main():
    st.title("Oil Dashboard — Polymarket & Positioning")

    from config import DEFAULT_START, DEFAULT_END

    st.sidebar.header("Date Range")
    start_date = st.sidebar.date_input("Start", pd.to_datetime("2025-12-01"))
    end_date = st.sidebar.date_input("End", pd.to_datetime(DEFAULT_END))

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    with st.spinner("Loading WTI price data..."):
        wti_data = load_wti(start_str, end_str)
        wti_intraday = load_wti_intraday()

    with st.spinner("Loading EIA inventories..."):
        eia_data = load_eia(start_str, end_str)

    with st.spinner("Loading COT positioning..."):
        cot_data = load_cot()

    with st.spinner("Loading AAA gas price..."):
        aaa_data = load_aaa()

    with st.spinner("Loading Polymarket data..."):
        pm_raw = load_polymarket()
        pm_history = load_pm_history()

    # Phase multiplier for calendar scoring
    phase_mult = 1.0
    if wti_intraday and pm_history:
        from analysis.phase_detector import align_series, detect_phases
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        w_times, w_prices = [], []
        for ts_str, p in zip(wti_intraday.get("timestamps", []), wti_intraday.get("prices", [])):
            dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
            if dt.date() == today:
                w_times.append(ts_str)
                w_prices.append(p)
        p_times, p_prices = [], []
        for h in pm_history:
            ts = datetime.fromtimestamp(h["timestamp"], tz=timezone.utc)
            if ts.date() == today:
                p_times.append(ts.isoformat())
                p_prices.append(h["price"] * 100)
        if w_times and p_times:
            anchor = wti_intraday.get("today_open")
            merged = align_series(w_times, w_prices, p_times, p_prices)
            if merged is not None and not merged.empty:
                _, phase_mult, _, _ = detect_phases(merged, anchor)

    market_data = {"wti": wti_data}

    current_wti = wti_data["close"][-1] if (
        wti_data and wti_data.get("close") and len(wti_data["close"]) > 0
    ) else None

    pm_markets_dict = pm_raw.get("markets", {}) if pm_raw else {}
    all_pm_markets = pm_markets_dict.get("markets", [])
    polymarket_signal = build_polymarket_signal(all_pm_markets, wti_current_price=current_wti)
    pm_sentiment = pm_raw.get("sentiment", {}) if pm_raw else {}

    # Sidebar divergence based on daily direction
    daily_dir = polymarket_signal.get("daily_direction") if polymarket_signal else None
    if daily_dir and daily_dir.get("net_sentiment") is not None and current_wti is not None:
        net = daily_dir["net_sentiment"]
        with st.sidebar:
            st.markdown("---")
            st.subheader("Direction Signal")
            color = "green" if net > 0.10 else ("red" if net < -0.10 else "orange")
            st.markdown(f":{color}[**{daily_dir.get('interpretation', 'neutral').upper()}**] "
                        f"({daily_dir['prob_up'] * 100:.1f}% Up)")

    wti_dates = wti_data.get('dates', []) if wti_data else []
    eia_crude_raw = eia_data.get("crude") if isinstance(eia_data, dict) else None
    eia_dates = (eia_crude_raw or {}).get("dates", []) if eia_crude_raw else []
    cot_avail = cot_data.get('net_long') if cot_data else None
    aaa_price = aaa_data.get('price') if aaa_data else None

    with st.sidebar:
        st.markdown("---")
        st.subheader("Data Status")
        st.caption(f"WTI: {len(wti_dates)} days ({start_str} → {end_str})")
        st.caption(f"EIA: {len(eia_dates)} weeks")
        st.caption(f"COT: {'Available' if cot_avail else 'Unavailable'}")
        st.caption(f"Polymarket: {polymarket_signal.get('total_classified', 0)} oil markets")
        st.caption(f"AAA: {'$' + str(aaa_price) if aaa_price else 'Unavailable'}")

    tabs = st.tabs([
        "1. Price & Polymarket",
        "2. COT Positioning & Impact",
        "3. Inventories & Pump Gap",
        "4. Retail Sentiment",
        "5. Trading Calendar",
    ])

    with tabs[0]:
        render_price_polymarket_tab(market_data, polymarket_signal, pm_history, wti_intraday)

    with tabs[1]:
        render_cot_tab(market_data, cot_data)

    with tabs[2]:
        render_inventories_tab(market_data, eia_data, aaa_data)

    with tabs[3]:
        render_sentiment_tab(polymarket_signal, pm_sentiment)

    with tabs[4]:
        render_calendar_tab(market_data, polymarket_signal, cot_data, eia_data, phase_mult)


if __name__ == "__main__":
    main()
