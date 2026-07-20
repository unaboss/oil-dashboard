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

from data.fetcher_price import get_wti
from data.fetcher_cot import get_cot_data
from data.fetcher_eia import get_all_eia_data
from data.fetcher_aaa import get_aaa_gas_price
from data.fetcher_polymarket import get_polymarket_markets, get_aggregated_sentiment
from analysis.polymarket_curve import build_polymarket_curve, compute_divergence
from analysis.lag_engine import build_lag_matrix

from ui.tab_price_polymarket import render_price_polymarket_tab
from ui.tab_cot import render_cot_tab
from ui.tab_inventories import render_inventories_tab
from ui.tab_sentiment import render_sentiment_tab
from ui.tab_calendar import render_calendar_tab

CACHE_TTL_PRICE = 3600
CACHE_TTL_EIA = 86400
CACHE_TTL_COT = 86400
CACHE_TTL_AAA = 86400
CACHE_TTL_PM = 3600


@st.cache_data(ttl=CACHE_TTL_PRICE)
def load_wti(start, end):
    return get_wti(start=str(start), end=str(end))


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

    with st.spinner("Loading EIA inventories..."):
        eia_data = load_eia(start_str, end_str)

    with st.spinner("Loading COT positioning..."):
        cot_data = load_cot()

    with st.spinner("Loading AAA gas price..."):
        aaa_data = load_aaa()

    with st.spinner("Loading Polymarket data..."):
        pm_raw = load_polymarket()

    market_data = {"wti": wti_data}

    pm_markets_dict = pm_raw.get("markets", {}) if pm_raw else {}
    all_pm_markets = pm_markets_dict.get("markets", [])
    polymarket_curve = build_polymarket_curve(all_pm_markets)
    pm_sentiment = pm_raw.get("sentiment", {}) if pm_raw else {}

    divergence = compute_divergence(market_data, pm_sentiment)

    if divergence:
        with st.sidebar:
            st.markdown("---")
            st.subheader("Divergence Alerts")
            for d in divergence:
                st.warning(f"**{d.get('description', '')}**")
                st.caption(f"WTI: {d.get('wti_change', 'N/A')}% | PM: {d.get('pm_bias', 'N/A')}")

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
        st.caption(f"Polymarket: {len(all_pm_markets)} markets")
        st.caption(f"AAA: {'$' + str(aaa_price) if aaa_price else 'Unavailable'}")

    tabs = st.tabs([
        "1. Price & Polymarket",
        "2. COT Positioning & Impact",
        "3. Inventories & Pump Gap",
        "4. Retail Sentiment",
        "5. Trading Calendar",
    ])

    with tabs[0]:
        render_price_polymarket_tab(market_data, polymarket_curve)

    with tabs[1]:
        render_cot_tab(market_data, cot_data)

    with tabs[2]:
        render_inventories_tab(market_data, eia_data, aaa_data)

    with tabs[3]:
        render_sentiment_tab(polymarket_curve)

    with tabs[4]:
        render_calendar_tab(market_data, polymarket_curve, cot_data, eia_data)


if __name__ == "__main__":
    main()
