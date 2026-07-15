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
    )

    st.plotly_chart(fig, use_container_width=True)

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
