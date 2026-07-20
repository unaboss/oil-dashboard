import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from analysis.fuel_pass_through import compute_fuel_pass_through


def render_inventories_tab(market_data, eia_data, aaa_data):
    st.subheader("Inventories & Pump Gap")

    if market_data is None:
        st.warning("Market data not available.")
        return
    if eia_data is None:
        eia_data = {}
    if aaa_data is None:
        aaa_data = {}

    wti = market_data.get("wti", {})
    wti_close = wti.get("close", [])
    fuel = compute_fuel_pass_through(eia_data, aaa_data, wti_close)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ch = fuel.get("current_crude_change")
        st.metric(
            "Latest Crude Change",
            f"{ch:+,.0f}K bbl" if ch is not None else "N/A",
            delta="Draw" if (ch and ch < 0) else ("Build" if (ch and ch > 0) else None),
        )
    with col2:
        ret = fuel.get("current_retail_eia")
        st.metric("EIA Retail Gas", f"${ret:.3f}/gal" if ret is not None else "N/A")
    with col3:
        aaa_ret = fuel.get("current_retail_aaa")
        st.metric("AAA Retail Gas", f"${aaa_ret:.3f}/gal" if aaa_ret is not None else "N/A")
    with col4:
        st.metric("Pass-Through Alignment", f"{fuel.get('alignment_score', 'N/A')}%")

    st.caption(f"Crude to pump alignment: {fuel.get('pass_through_lag', 'Unknown')}")
    st.caption(f"Samples analyzed: {fuel.get('historical_samples', 0)} EIA weeks")

    st.markdown("---")
    st.subheader("EIA Inventory Trends")

    crude = eia_data.get("crude") if isinstance(eia_data, dict) else None
    gasoline = eia_data.get("gasoline") if isinstance(eia_data, dict) else None
    distillate = eia_data.get("distillate") if isinstance(eia_data, dict) else None
    retail_gas = eia_data.get("retail_gas") if isinstance(eia_data, dict) else None
    if crude is None:
        crude = {}
    if gasoline is None:
        gasoline = {}
    if distillate is None:
        distillate = {}
    if retail_gas is None:
        retail_gas = {}

    if crude:
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=("Crude Stocks Change (K bbl)", "Gasoline Stocks Change (K bbl)", "Distillate Stocks Change (K bbl)"),
        )

        def _safe_vals(data, field):
            return [v if v is not None and not np.isnan(v) else None for v in data.get(field, [])]

        c_dates = pd.to_datetime([d for d in crude.get("dates", [])][::-1])
        c_changes = _safe_vals(crude, "changes")[::-1]

        fig.add_trace(
            go.Bar(x=c_dates, y=c_changes, name="Crude Change", marker_color="orange"),
            row=1, col=1,
        )

        g_dates = pd.to_datetime([d for d in gasoline.get("dates", [])][::-1])
        g_changes = _safe_vals(gasoline, "changes")[::-1]
        fig.add_trace(
            go.Bar(x=g_dates, y=g_changes, name="Gasoline Change", marker_color="lightblue"),
            row=2, col=1,
        )

        d_dates = pd.to_datetime([d for d in distillate.get("dates", [])][::-1])
        d_changes = _safe_vals(distillate, "changes")[::-1]
        fig.add_trace(
            go.Bar(x=d_dates, y=d_changes, name="Distillate Change", marker_color="lightgreen"),
            row=3, col=1,
        )

        fig.update_layout(
            height=700,
            template="plotly_dark",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    if retail_gas:
        st.markdown("---")
        st.subheader("Retail Gas Price vs Crude Stocks")

        r_dates = pd.to_datetime([d for d in retail_gas.get("dates", [])][::-1])
        r_vals = retail_gas.get("values", [])[::-1]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Scatter(x=r_dates, y=r_vals, mode="lines+markers", name="Retail Gas ($/gal)", line=dict(color="gold")),
            secondary_y=False,
        )
        fig2.add_trace(
            go.Scatter(x=c_dates, y=[v for v in crude.get("values", [])][::-1],
                       mode="lines", name="Crude Stocks (K bbl)", line=dict(color="gray", dash="dot")),
            secondary_y=True,
        )
        fig2.update_layout(
            title="Retail Gas Price vs Crude Stocks",
            height=400,
            template="plotly_dark",
        )
        fig2.update_yaxes(title_text="$/gal", secondary_y=False)
        fig2.update_yaxes(title_text="K bbl", secondary_y=True)
        st.plotly_chart(fig2, use_container_width=True)
