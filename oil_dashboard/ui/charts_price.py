"""Tab 1: WTI Price + RBOB Crack Spread + Volume + Event Markers."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from analysis.signals import compute_sma


def render_price_tab(market_data, events_df):
    st.subheader("Price & Flows")

    wti = market_data.get("wti")
    crack = market_data.get("crack")
    vol = market_data.get("volume_anomaly")

    if not wti or not wti.get("dates"):
        st.warning("No WTI data available. Check your date range or internet connection.")
        return

    dates = [pd.to_datetime(d) for d in wti["dates"]]
    close = wti["close"]
    volumes = wti.get("volume", [])

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=("WTI Crude Oil ($/bbl)", "RBOB-WTI Crack Spread ($/bbl)", "Volume"),
    )

    # WTI candlestick
    if len(close) > 1:
        sma20 = compute_sma(close, 20)
        sma50 = compute_sma(close, 50)

        fig.add_trace(
            go.Scatter(x=dates, y=close, mode="lines", name="WTI Close",
                       line=dict(color="#FF9800", width=2)),
            row=1, col=1,
        )
        if len([x for x in sma20 if x is not None and not pd.isna(x)]) > 0:
            fig.add_trace(
                go.Scatter(x=dates, y=sma20, mode="lines", name="20d MA",
                           line=dict(color="#2196F3", width=1, dash="dot")),
                row=1, col=1,
            )
        if len(close) >= 50 and len([x for x in sma50 if x is not None and not pd.isna(x)]) > 0:
            fig.add_trace(
                go.Scatter(x=dates, y=sma50, mode="lines", name="50d MA",
                           line=dict(color="#F44336", width=1, dash="dot")),
                row=1, col=1,
            )

    # Event markers
    if events_df is not None and not events_df.empty:
        for _, ev in events_df.iterrows():
            try:
                event_date = pd.to_datetime(ev["date"])
                label = ev.get("label", "Event")
                fig.add_vline(x=event_date, line_dash="dash", line_color="white",
                              opacity=0.4, row=1, col=1)
                fig.add_annotation(x=event_date, y=0.98, yref="paper",
                                   text=label, showarrow=False,
                                   font=dict(size=8, color="gray"),
                                   textangle=-90, row=1, col=1)
            except Exception:
                pass

    # Crack spread
    if crack and crack.get("dates"):
        c_dates = [pd.to_datetime(d) for d in crack["dates"]]
        c_vals = crack.get("crack", [])
        c_ma = crack.get("crack_5ma", [])

        fig.add_trace(
            go.Scatter(x=c_dates, y=c_vals, mode="lines", name="Crack Spread",
                       line=dict(color="#4CAF50", width=1.5)),
            row=2, col=1,
        )
        if c_ma:
            fig.add_trace(
                go.Scatter(x=c_dates, y=c_ma, mode="lines", name="Crack 5d MA",
                           line=dict(color="#8BC34A", width=1, dash="dot")),
                row=2, col=1,
            )
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.3, row=2, col=1)

    # Volume
    if vol and vol.get("dates") and volumes:
        v_dates = [pd.to_datetime(d) for d in vol["dates"]]
        v_ma = vol.get("volume_ma", [])
        colors = []
        for i, v in enumerate(volumes):
            if i > 0 and i < len(close):
                colors.append("#4CAF50" if close[i] >= close[i-1] else "#F44336")
            else:
                colors.append("#BDBDBD")

        fig.add_trace(
            go.Bar(x=dates, y=volumes, name="Volume", marker_color=colors,
                   opacity=0.6),
            row=3, col=1,
        )
        if v_ma:
            fig.add_trace(
                go.Scatter(x=v_dates, y=v_ma, mode="lines", name="20d Vol MA",
                           line=dict(color="#9C27B0", width=1)),
                row=3, col=1,
            )

    fig.update_layout(
        height=700,
        showlegend=True,
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
        template="plotly_dark",
    )
    fig.update_xaxes(rangeslider=dict(visible=False))

    st.plotly_chart(fig, use_container_width=True)
