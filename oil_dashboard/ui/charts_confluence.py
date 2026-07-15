"""Tab 6: Confluence Score Dashboard — live 6-signal board."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from analysis.confluence import compute_confluence, compute_cot_extreme, CONFLUENCE_SIGNALS
from config import BULLISH_THRESHOLD, BEARISH_THRESHOLD


def render_confluence_tab(market_data, eia_data, cot_data):
    st.subheader("Confluence Score — Fake Move Detection")

    score = compute_confluence(market_data, eia_data, cot_data, latest_only=True)
    cot_extreme = compute_cot_extreme(cot_data) if cot_data else {"is_extreme": False}

    # Update COT signal based on extreme check
    if cot_data and cot_data.get("net_long") is not None:
        if cot_extreme.get("is_extreme"):
            score["signals"]["cot"] = -1
        else:
            score["signals"]["cot"] = 1

    total = sum(score["signals"].get(s, 0) for s in CONFLUENCE_SIGNALS)

    st.markdown(f"### Score: **{total}/6** — Direction: **{score['direction'].upper()}**")

    cols = st.columns(3)
    signal_config = [
        ("Volume", "volume", "WTI volume > 20d avg"),
        ("COT", "cot", "MM not at extreme"),
        ("Inventories", "inventories", "Crude drawing"),
        ("Crack", "crack", "RBOB-WTI widening"),
        ("DXY", "dxy", "Dollar weakening"),
        ("Curve", "curve", "Backwardation"),
    ]

    for i, (label, key, desc) in enumerate(signal_config):
        col_idx = i % 3
        val = score["signals"].get(key, 0)
        if val == 1:
            icon = "✅"
            color = "#4CAF50"
        elif val == -1:
            icon = "⚠️"
            color = "#F44336"
        else:
            icon = "⬜"
            color = "#9E9E9E"

        with cols[col_idx]:
            st.markdown(f"<span style='color:{color};font-size:20px'>{icon}</span> **{label}**",
                        unsafe_allow_html=True)
            st.caption(desc)

    # Confluence gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+delta",
        value=total,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [-6, 6]},
            "bar": {"color": "#4CAF50" if total >= BULLISH_THRESHOLD else "#F44336" if total <= BEARISH_THRESHOLD else "#FFC107"},
            "steps": [
                {"range": [-6, BEARISH_THRESHOLD], "color": "rgba(244,67,54,0.3)"},
                {"range": [BEARISH_THRESHOLD, BULLISH_THRESHOLD], "color": "rgba(255,193,7,0.3)"},
                {"range": [BULLISH_THRESHOLD, 6], "color": "rgba(76,175,80,0.3)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.75,
                "value": total,
            },
        },
        title={"text": "Confluence Score"},
    ))
    fig.update_layout(height=250, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # Scoring rules
    with st.expander("Scoring Rules"):
        st.markdown(f"""
        | Signal | +1 (Bullish) | -1 (Bearish) | 0 (Neutral) |
        |---|---|---|---|
        | Volume | WTI volume > 20d avg | Below avg | No data |
        | COT | MM not at extreme | MM extreme long/short | No data |
        | Inventories | Crude drawing | Crude building | No data |
        | Crack | Crack > 5d MA | Crack < 5d MA | No data |
        | DXY | Dollar weakening | Dollar strengthening | No data |
        | Curve | Backwardation (B-W > 0) | Contango | No data |

        **Score >= {BULLISH_THRESHOLD}**: Bullish setup — move likely real
        **Score <= {BEARISH_THRESHOLD}**: Bearish setup — move likely real
        **Score between**: Mixed signals — stay neutral
        """)
