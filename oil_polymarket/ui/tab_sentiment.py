import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from data.fetcher_polymarket import get_aggregated_sentiment


def render_sentiment_tab(polymarket_curve):
    st.subheader("Retail Sentiment — Polymarket Odds & Volume")

    sentiment = get_aggregated_sentiment()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Net Sentiment",
            f"{sentiment.get('net_sentiment', 0):+.2f}",
            delta="Bullish" if sentiment.get("net_sentiment", 0) > 0 else "Bearish",
        )
    with col2:
        b_avg = sentiment.get("bullish_avg")
        st.metric("Bullish Avg Odds", f"{b_avg * 100:.1f}%" if b_avg else "N/A")
    with col3:
        be_avg = sentiment.get("bearish_avg")
        st.metric("Bearish Avg Odds", f"{be_avg * 100:.1f}%" if be_avg else "N/A")
    with col4:
        st.metric("Total Betting Vol", f"${sentiment.get('total_volume', 0):,.0f}")

    st.markdown("---")
    st.subheader("Sentiment Breakdown by Horizon")

    daily = polymarket_curve.get("daily", {})
    weekly = polymarket_curve.get("weekly", {})
    monthly = polymarket_curve.get("monthly", {})

    horizon_data = {
        "Horizon": ["Daily", "Weekly", "Monthly"],
        "Bullish Signals": [
            daily.get("bullish_signals", 0),
            weekly.get("bullish_signals", 0),
            monthly.get("bullish_signals", 0),
        ],
        "Bearish Signals": [
            daily.get("bearish_signals", 0),
            weekly.get("bearish_signals", 0),
            monthly.get("bearish_signals", 0),
        ],
        "Avg Odds (%)": [
            f"{daily.get('avg_price', 0) * 100:.1f}" if daily.get('avg_price') else "N/A",
            f"{weekly.get('avg_price', 0) * 100:.1f}" if weekly.get('avg_price') else "N/A",
            f"{monthly.get('avg_price', 0) * 100:.1f}" if monthly.get('avg_price') else "N/A",
        ],
        "Volume ($)": [
            f"${daily.get('volume', 0):,.0f}",
            f"${weekly.get('volume', 0):,.0f}",
            f"${monthly.get('volume', 0):,.0f}",
        ],
        "Direction": [
            daily.get("direction", "neutral").upper(),
            weekly.get("direction", "neutral").upper(),
            monthly.get("direction", "neutral").upper(),
        ],
    }
    st.dataframe(pd.DataFrame(horizon_data), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Sentiment Intensity (Aggregated Odds)")

    labels = ["Bullish Markets", "Bearish Markets"]
    values = [sentiment.get("bullish_count", 0), sentiment.get("bearish_count", 0)]

    if sum(values) > 0:
        fig = go.Figure(data=[
            go.Pie(labels=labels, values=values, hole=0.4,
                   marker_colors=["green", "red"],
                   textinfo="label+percent")
        ])
        fig.update_layout(
            title="Bullish vs Bearish Market Distribution",
            height=350,
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("All Polymarket Oil Markets")

    all_questions = sentiment.get("all_questions", [])
    if all_questions:
        rows = []
        for m in all_questions[:30]:
            title = m.get("title", "Unknown")
            price = m.get("price")
            try:
                price_str = f"{float(price) * 100:.1f}%" if price is not None else "N/A"
            except (ValueError, TypeError):
                price_str = "N/A"
            volume = float(m.get("volume", 0))
            bias = "Bullish" if m.get("bullish") else ("Bearish" if m.get("bearish") else "Neutral")
            rows.append({
                "Market": title[:80],
                "Current Odds": price_str,
                "Bias": bias,
                "Volume": f"${volume:,.0f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No Polymarket oil markets found.")
