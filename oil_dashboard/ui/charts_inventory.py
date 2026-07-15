"""Tab 4: EIA Weekly Inventory Changes."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def render_inventory_tab(eia_data):
    st.subheader("Inventories — Weekly Changes")

    if not eia_data:
        st.warning("No EIA inventory data available. This requires an EIA API key.")
        st.caption("Set EIA_API_KEY in .env and click Refresh All Data.")
        return

    crude = eia_data.get("crude")
    gasoline = eia_data.get("gasoline")
    distillate = eia_data.get("distillate")

    if not crude and not gasoline and not distillate:
        st.warning("EIA inventory data unavailable. Verify your API key is valid.")
        return

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "Crude Oil Stocks Change (M bbl)",
            "Gasoline Stocks Change (M bbl)",
            "Distillate Stocks Change (M bbl)",
        ),
    )

    def _plot_inventory(fig, data, row, name, color_neg, color_pos):
        if not data or not data.get("dates"):
            return
        dates = [pd.to_datetime(d) for d in data["dates"]]
        changes = data.get("changes", [])
        if not changes:
            return

        colors = [color_neg if c < 0 else color_pos for c in changes]
        fig.add_trace(
            go.Bar(x=dates, y=changes, name=name,
                   marker_color=colors, opacity=0.8),
            row=row, col=1,
        )
        fig.add_hline(y=0, line_dash="solid", line_color="gray",
                      opacity=0.3, row=row, col=1)

    _plot_inventory(fig, crude, 1, "Crude", "#4CAF50", "#F44336")
    _plot_inventory(fig, gasoline, 2, "Gasoline", "#4CAF50", "#F44336")
    _plot_inventory(fig, distillate, 3, "Distillate", "#4CAF50", "#F44336")

    fig.update_layout(
        height=600,
        showlegend=False,
        template="plotly_dark",
        hovermode="x unified",
        dragmode="pan",
    )

    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })

    st.markdown("### Key Levels")
    col1, col2, col3 = st.columns(3)

    def _latest_change(data, label, col):
        if data and data.get("changes"):
            last = data["changes"][-1]
            if last is not None and not pd.isna(last):
                col.metric(label, f"{last:+.1f} M bbl")
            else:
                col.metric(label, "N/A")
        else:
            col.metric(label, "N/A")

    _latest_change(crude, "Crude", col1)
    _latest_change(gasoline, "Gasoline", col2)
    _latest_change(distillate, "Distillate", col3)

    st.markdown("---")
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown("""
        **What is EIA data?**
        Every Wednesday morning, the US Energy Information Administration releases the Weekly Petroleum Status Report. It tells us how much crude oil, gasoline, and distillate (diesel/heating oil) is sitting in US storage tanks.

        **What the charts show:**
        - **Green bars** = inventories went DOWN (a "draw"). This means more oil was consumed than produced. Bullish for oil prices — demand is outpacing supply.
        - **Red bars** = inventories went UP (a "build"). More oil is piling up in storage. Bearish — supply is outpacing demand.
        - The taller the bar, the bigger the surprise versus expectations.

        **The three products:**
        1. **Crude Oil** — The raw stuff. A big draw means refineries are processing a lot. A big build means oil is backing up.
        2. **Gasoline** — Made from crude. Big draw during summer = people driving a lot (bullish for crude demand). Big build in winter = normal seasonal pattern.
        3. **Distillate** — Diesel, jet fuel, heating oil. A big draw can signal strong industrial activity or cold weather.

        **How to use it:**
        - A large crude draw + rising gasoline demand = strong fundamental support for higher prices.
        - A large crude build + falling product demand = weak fundamentals, be careful buying.
        - The "Key Levels" metrics show the most recent week's change in millions of barrels.
        """)
