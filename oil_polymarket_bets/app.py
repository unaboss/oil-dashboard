import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Oil — Polymarket Bets",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from data.fetcher_price import get_wti
from data.fetcher_eia import get_all_refinery_data
from data.fetcher_polymarket import get_polymarket_markets
from analysis.polymarket_classifier import classify_all

from ui.tabs_placeholder import render_daily_tab, render_weekly_tab, render_monthly_tab
from ui.tab_inventory import render_inventory_tab

CACHE_TTL_PRICE = 3600
CACHE_TTL_EIA = 86400
CACHE_TTL_PM = 3600


@st.cache_data(ttl=CACHE_TTL_PRICE)
def load_wti(start, end):
    return get_wti(start=str(start), end=str(end))


@st.cache_data(ttl=CACHE_TTL_EIA)
def load_eia(start, end):
    return get_all_refinery_data(start=str(start), end=str(end))


@st.cache_data(ttl=CACHE_TTL_PM)
def load_polymarket():
    pm = get_polymarket_markets()
    return pm


def main():
    st.title("Oil — Polymarket Bets Dashboard")

    from config import DEFAULT_START, DEFAULT_END

    start_str = DEFAULT_START
    end_str = DEFAULT_END

    with st.spinner("Loading WTI price data..."):
        wti_data = load_wti(start_str, end_str)

    with st.spinner("Loading EIA inventory & refinery data..."):
        eia_data = load_eia(start_str, end_str)

    with st.spinner("Loading Polymarket oil markets..."):
        pm_raw = load_polymarket()

    all_markets = pm_raw.get("markets", []) if pm_raw else []
    classified = classify_all(all_markets)
    inventory_markets = [c for c in classified if c.get("family") == "inventory_targets"]

    with st.sidebar:
        st.markdown("---")
        st.subheader("Data Status")
        wti_dates = wti_data.get("dates", []) if wti_data else []
        st.caption(f"WTI: {len(wti_dates)} days ({start_str} → {end_str})")
        crude = eia_data.get("crude") if eia_data else None
        eia_weeks = len(crude.get("dates", [])) if crude else 0
        st.caption(f"EIA: {eia_weeks} weeks of inventory data")
        st.caption(f"Polymarket: {len(classified)} oil markets classified")
        st.caption(f"Inventory bets: {len(inventory_markets)} markets")

    tabs = st.tabs([
        "1. Daily Bets",
        "2. Weekly Bets",
        "3. Monthly Bets",
        "4. Inventory Analysis",
    ])

    with tabs[0]:
        render_daily_tab()

    with tabs[1]:
        render_weekly_tab()

    with tabs[2]:
        render_monthly_tab()

    with tabs[3]:
        render_inventory_tab(eia_data, all_markets)


if __name__ == "__main__":
    main()
