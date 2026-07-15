"""Tab 5: Retail & Sentiment — RBOB vs Pump Price, Google Trends, DXY."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def render_sentiment_tab(market_data, eia_data, trends_data):
    st.subheader("Retail & Sentiment")

    rbob = market_data.get("rbob")
    dxy = market_data.get("dxy")
    retail = eia_data.get("retail_gas") if eia_data else None

    tab_inner1, tab_inner2, tab_inner3 = st.tabs(["RBOB vs Pump", "Google Trends", "DXY Dollar Index"])

    with tab_inner1:
        _render_rbob_vs_pump(rbob, retail)

    with tab_inner2:
        _render_trends(trends_data)

    with tab_inner3:
        _render_dxy(dxy)


def _render_rbob_vs_pump(rbob, retail):
    if not rbob or not rbob.get("dates"):
        st.info("RBOB data loading...")
        return

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    rbob_dates = [pd.to_datetime(d) for d in rbob["dates"]]
    fig.add_trace(
        go.Scatter(x=rbob_dates, y=rbob["close"], mode="lines",
                   name="RBOB Futures ($/gal)", line=dict(color="#FF9800", width=2)),
        secondary_y=False,
    )

    if retail and retail.get("dates") and retail.get("values"):
        r_dates = [pd.to_datetime(d) for d in retail["dates"]]
        r_vals = retail["values"]  # already in $/gal
        fig.add_trace(
            go.Scatter(x=r_dates, y=r_vals, mode="lines",
                       name="US Retail Gas ($/gal)", line=dict(color="#4CAF50", width=2, dash="dash")),
            secondary_y=True,
        )

    fig.update_layout(
        title="RBOB Futures vs US Retail Gasoline",
        height=400,
        hovermode="x unified",
        template="plotly_dark",
    )
    fig.update_yaxes(title_text="RBOB ($/gal)", secondary_y=False)
    fig.update_yaxes(title_text="Retail ($/gal)", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

    st.caption("Retail pump price typically lags RBOB by 5-10 days. RBOB leads the move.")


def _render_trends(trends_data):
    if not trends_data or not trends_data.get("available"):
        st.info("Google Trends data unavailable (may be rate-limited). Try again later.")
        return

    dates = [pd.to_datetime(d) for d in trends_data["dates"]]
    fig = go.Figure()
    for kw, vals in trends_data["values"].items():
        fig.add_trace(go.Scatter(x=dates, y=vals, mode="lines", name=kw))

    fig.update_layout(
        title="Google Trends — US Interest",
        height=300,
        hovermode="x unified",
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Spikes in 'gas prices' searches often coincide with media coverage — may mark sentiment extremes.")


def _render_dxy(dxy):
    if not dxy or not dxy.get("dates"):
        st.info("DXY data loading...")
        return

    dates = [pd.to_datetime(d) for d in dxy["dates"]]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=dates, y=dxy["close"], mode="lines",
                   name="DXY", fill="tozeroy",
                   line=dict(color="#9C27B0", width=2)),
    )
    fig.update_layout(
        title="US Dollar Index (DXY)",
        height=300,
        hovermode="x unified",
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("DXY up = headwind for oil (priced in USD). DXY down = tailwind.")
