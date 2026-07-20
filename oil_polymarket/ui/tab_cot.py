import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from analysis.cot_impact import compute_cot_impact_on_price, compute_cot_divergence


def render_cot_tab(market_data, cot_data):
    st.subheader("CFTC COT — Managed Money Positioning & Price Impact")

    if market_data is None or cot_data is None:
        st.warning("COT or market data not available.")
        return

    wti = market_data.get("wti", {})
    dates = wti.get("dates", [])
    close = wti.get("close", [])

    impact = compute_cot_impact_on_price(cot_data, market_data)
    divergence = compute_cot_divergence(cot_data, market_data)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Managed Money Long", f"{impact.get('current_mm_long', 'N/A'):,.0f}" if impact.get('current_mm_long') else "N/A")
    with col2:
        st.metric("Managed Money Short", f"{impact.get('current_mm_short', 'N/A'):,.0f}" if impact.get('current_mm_short') else "N/A")
    with col3:
        nl = impact.get("current_net_long")
        st.metric("Net Long", f"{nl:,.0f}" if nl is not None else "N/A",
                  delta=f"{impact.get('side', '').upper()} | {impact.get('magnitude', '')}")
    with col4:
        zone = impact.get("extreme_zone")
        zone_display = zone.replace("_", " ").upper() if zone else "NORMAL"
        st.metric("Zone", zone_display)

    st.markdown("---")
    st.subheader("COT Impact on Price — Forward Returns")

    impact_table = impact.get("impact_table", [])
    if impact_table:
        impact_df = pd.DataFrame(impact_table)
        impact_df.columns = ["Horizon (Days)", "Forward Return (%)", "Direction"]
        st.dataframe(impact_df, use_container_width=True, hide_index=True)
    else:
        st.info("Insufficient data for forward return analysis.")

    if divergence:
        st.markdown("---")
        st.subheader("COT-Price Divergence Alerts")
        for d in divergence:
            icon = "🔴" if "long" in d.get("type", "") else "🟢"
            st.warning(f"{icon} **{d.get('description', '')}**")
            st.caption(f"Net Long: {d.get('net_long', 'N/A'):,.0f} | WTI 5d: {d.get('wti_5d', 'N/A')}%")

    if dates and close:
        st.markdown("---")
        st.subheader("Price & COT Positioning")

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(dates[-90:]),
                y=close[-90:],
                mode="lines",
                name="WTI Close",
                line=dict(color="white", width=2),
            ),
            secondary_y=False,
        )

        nl_val = impact.get("current_net_long", 0) or 0
        today = pd.Timestamp.now().date()
        color = "green" if nl_val > 0 else "red"
        fig.add_trace(
            go.Bar(
                x=[today],
                y=[nl_val / 1000],
                name="Net Long (K contracts)",
                marker_color=color,
                opacity=0.7,
            ),
            secondary_y=True,
        )

        fig.update_layout(
            title="WTI Price (90d) vs Current COT Net Positioning",
            height=450,
            template="plotly_dark",
            hovermode="x unified",
        )
        fig.update_yaxes(title_text="WTI Price ($)", secondary_y=False)
        fig.update_yaxes(title_text="Net Long (K contracts)", secondary_y=True)

        st.plotly_chart(fig, use_container_width=True)
