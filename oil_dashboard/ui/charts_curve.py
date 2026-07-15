"""Tab 2: Futures Curve & Divergence (CFD Proxy — Brent-WTI spread)."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def render_curve_tab(market_data):
    st.subheader("Curve & Divergence")

    curve = market_data.get("curve")
    wti = market_data.get("wti")
    brent = market_data.get("brent")

    if not wti or not brent:
        st.warning("No curve data available.")
        return

    wti_dates = [pd.to_datetime(d) for d in wti["dates"]]
    brent_dates = [pd.to_datetime(d) for d in brent["dates"]]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.6, 0.4],
        subplot_titles=("WTI vs Brent", "Brent-WTI Spread (CFD Proxy)"),
    )

    fig.add_trace(
        go.Scatter(x=wti_dates, y=wti["close"], mode="lines",
                   name="WTI", line=dict(color="#FF9800", width=2)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=brent_dates, y=brent["close"], mode="lines",
                   name="Brent", line=dict(color="#00BCD4", width=2)),
        row=1, col=1,
    )

    if curve and curve.get("brent_wti_spread") and curve.get("spread_dates"):
        spread_dates = [pd.to_datetime(d) for d in curve["spread_dates"]]
        spread_vals = curve["brent_wti_spread"]

        colors = ["#4CAF50" if v > 0 else "#F44336" for v in spread_vals]
        fig.add_trace(
            go.Bar(x=spread_dates, y=spread_vals, name="Brent-WTI Spread",
                   marker_color=colors, opacity=0.7),
            row=2, col=1,
        )
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5, row=2, col=1)

        avg_spread = sum(spread_vals) / len(spread_vals) if spread_vals else 0
        fig.add_hline(y=avg_spread, line_dash="dash", line_color="white", opacity=0.3,
                      annotation_text=f"Avg: ${avg_spread:.1f}", row=2, col=1)

    fig.update_layout(
        height=550,
        showlegend=True,
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
        template="plotly_dark",
        dragmode="pan",
    )

    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })

    st.markdown("---")
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown("""
        **Brent and WTI** are the two most important types of crude oil. Brent is the global benchmark (mined in the North Sea), and WTI is the US benchmark. They usually trade close together, but the gap between them tells you a lot.

        **What the spread means:**
        - When Brent is more expensive than WTI (spread > 0), the global market is tight. Buyers are willing to pay a premium for Brent. This is called **backwardation** and is generally bullish.
        - When WTI catches up or exceeds Brent (spread < 0), it sometimes means paper traders are bidding up WTI faster than physical buyers can absorb it. This is called **contango** and can be a warning sign.

        **Bottom chart — the spread as colored bars:**
        - Green = Brent premium (normal/tight market).
        - Red = WTI premium (unusual — pay attention).
        - The white dashed line is the average spread. When the current spread is far from average, it may revert back.
        """)

    # Interpretation
    st.markdown("### Interpretation")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Spread > 0 (Backwardation proxy)**
        - Physical crude commanding a premium
        - Physical market tighter than paper suggests
        - Bullish signal for near-term pricing
        """)
    with col2:
        st.markdown("""
        **Spread < 0 (Contango proxy)**
        - Paper bidding above physical reality
        - Speculation may be driving price
        - Fragile — watch for unwind
        """)

    if curve and curve.get("brent_wti_spread"):
        current = curve["brent_wti_spread"][-1] if curve["brent_wti_spread"] else 0
        st.metric("Current Brent-WTI Spread", f"${current:.2f}")
