"""Tab 3: CFTC COT Managed Money Positioning."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from analysis.confluence import compute_cot_extreme


def render_cot_tab(cot_data, market_data):
    st.subheader("Positioning & COT")

    wti = market_data.get("wti")
    extreme = compute_cot_extreme(cot_data) if cot_data else {"is_extreme": False, "side": "", "net_long": None}

    col1, col2, col3 = st.columns(3)
    with col1:
        mm_long = cot_data.get("managed_money_long") if cot_data else None
        st.metric("Managed Money Long", f"{mm_long:,.0f}" if mm_long else "N/A")
    with col2:
        mm_short = cot_data.get("managed_money_short") if cot_data else None
        st.metric("Managed Money Short", f"{mm_short:,.0f}" if mm_short else "N/A")
    with col3:
        nl = extreme.get("net_long")
        nl_display = f"{nl:,.0f}" if nl is not None else "N/A"
        st.metric("MM Net Position", nl_display)

    if extreme.get("is_extreme"):
        st.warning(f"Managed Money at extreme {extreme['side']} — reversal risk elevated")

    if wti and wti.get("dates"):
        dates = [pd.to_datetime(d) for d in wti["dates"]]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(x=dates, y=wti["close"], mode="lines",
                       name="WTI Close", line=dict(color="#FF9800", width=2)),
            secondary_y=False,
        )

        if nl is not None:
            fig.add_hline(
                y=nl, line_dash="dash", line_color="#4CAF50", opacity=0.5,
                annotation_text=f"MM Net: {nl:,.0f}",
                secondary_y=True,
            )

        fig.update_layout(
            title="WTI Price vs Managed Money Positioning",
            height=450,
            hovermode="x unified",
            template="plotly_dark",
        )
        fig.update_yaxes(title_text="WTI ($/bbl)", secondary_y=False)
        fig.update_yaxes(title_text="Net Contracts", secondary_y=True)

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    ### How to Read
    - **MM extreme long** (>80th percentile) + price overbought = reversal imminent
    - **MM extreme short** (<20th percentile) + price oversold = rally setup
    - **Producers opposite position** = the smart money is hedging against specs
    - This data is weekly (Tue positions, released Fri) — useful for swing, not intraday
    """)
