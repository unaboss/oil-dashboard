"""Tab 8: Signal Audit — confirmed vs missed moves, hit rate."""

import streamlit as st
import plotly.graph_objects as go

from analysis.audit import compute_audit


def render_audit_tab(market_data, eia_data, cot_data):
    st.subheader("Signal Audit")

    audit = compute_audit(market_data, eia_data, cot_data)

    col_rate, _ = st.columns([1, 2])
    with col_rate:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=audit["hit_rate"],
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#4CAF50" if audit["hit_rate"] >= 50 else "#FFC107" if audit["hit_rate"] >= 30 else "#F44336"},
                "steps": [
                    {"range": [0, 30], "color": "rgba(244,67,54,0.3)"},
                    {"range": [30, 70], "color": "rgba(255,193,7,0.3)"},
                    {"range": [70, 100], "color": "rgba(76,175,80,0.3)"},
                ],
            },
            title={"text": "Hit Rate"},
        ))
        fig.update_layout(height=200, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"{audit['total_signals']} signals, {audit['missed_count']} missed moves")

    tab_conf, tab_missed, tab_false = st.tabs(["Confirmed", "Missed", "False Signals"])

    with tab_conf:
        st.markdown("#### Top 3 Confirmed Signals")
        if not audit["confirmed"]:
            st.caption("No confirmed signals in lookback period.")
        for c in audit["confirmed"]:
            color = "#4CAF50" if c["direction"] == "bullish" else "#F44336"
            st.markdown(
                f"**{c['date']}** — <span style='color:{color}'>{c['direction'].upper()} "
                f"(Score: {c['score']})</span> → {c['fwd_return_pct']:+.1f}% in 3 days",
                unsafe_allow_html=True,
            )
            signals_display = " | ".join(
                f"{k}: {'+' if v==1 else '-' if v==-1 else '0'}" for k, v in c["signals"].items()
            )
            st.caption(signals_display)

    with tab_missed:
        st.markdown("#### Top 3 Missed Moves")
        if not audit["missed"]:
            st.caption("No missed moves in lookback period.")
        for m in audit["missed"]:
            direction_emoji = "↑" if m["move_direction"] == "up" else "↓"
            st.markdown(
                f"**{m['date']}** — WTI {direction_emoji} {m['fwd_return_pct']:+.1f}% "
                f"— Model score: {m['score']} (no signal)",
                unsafe_allow_html=True,
            )
            st.caption("Possible: shipping disruption, geopolitics, surprise news")

    with tab_false:
        st.markdown("#### Top 3 False Signals")
        if not audit["false_signals"]:
            st.caption("No false signals in lookback period.")
        for f in audit["false_signals"]:
            color = "#4CAF50" if f["direction"] == "bullish" else "#F44336"
            st.markdown(
                f"**{f['date']}** — <span style='color:{color}'>{f['direction'].upper()} "
                f"(Score: {f['score']})</span> → {f['fwd_return_pct']:+.1f}% (moved opposite)",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.caption("Audit uses 3-day forward return to evaluate if confluence signals correctly predicted direction.")
