import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from analysis.calendar_predictor import compute_calendar_signals, backtest_calendar


def render_calendar_tab(market_data, polymarket_curve, cot_data, eia_data):
    st.subheader("Trading Calendar — 180d Back | 3d Forward")

    if market_data is None:
        st.warning("Market data not available.")
        return
    if cot_data is None:
        cot_data = {}
    if eia_data is None:
        eia_data = {}

    wti = market_data.get("wti", {})

    with st.spinner("Computing calendar signals..."):
        calendar = compute_calendar_signals(wti, polymarket_curve, cot_data, eia_data)

    if not calendar:
        st.warning("No calendar data available.")
        return

    enriched = backtest_calendar(calendar)

    today = datetime.now(timezone.utc).date()

    col1, col2, col3 = st.columns(3)
    with col1:
        past_correct = sum(1 for r in enriched if r.get("result") == "correct")
        past_total = sum(1 for r in enriched if r.get("result") in ("correct", "wrong"))
        hit_rate = f"{(past_correct / past_total * 100):.1f}%" if past_total > 0 else "N/A"
        st.metric("Historical Hit Rate", hit_rate, delta=f"{past_correct}/{past_total} signals")
    with col2:
        future_bullish = sum(1 for r in enriched if r["is_future"] and r["direction"] == "bullish")
        future_bearish = sum(1 for r in enriched if r["is_future"] and r["direction"] == "bearish")
        st.metric("Next 3d Outlook",
                  f"{future_bullish}B / {future_bearish}S",
                  delta="Bullish bias" if future_bullish > future_bearish else "Bearish bias")
    with col3:
        st.metric("Date Range",
                  f"{enriched[0]['date']} → {enriched[-1]['date']}",
                  delta=f"{len(enriched)} days")

    st.markdown("---")
    st.subheader("Date Detail Viewer")

    selected_date = st.date_input(
        "Select a date to view details",
        value=today,
        min_value=enriched[0]["date"],
        max_value=enriched[-1]["date"],
    )

    selected_row = None
    for r in enriched:
        if r["date"] == selected_date:
            selected_row = r
            break

    if selected_row:
        is_future = selected_row["is_future"]
        is_past = selected_row["is_past"]

        if is_future:
            st.info(f"**Prediction for {selected_date}**")
        elif is_past:
            st.info(f"**Historical — {selected_date}**")
        else:
            st.info(f"**Today — {selected_date}**")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            direction_color = "green" if selected_row["direction"] == "bullish" else ("red" if selected_row["direction"] == "bearish" else "gray")
            st.markdown(f"**Direction:** :{direction_color}[{selected_row['direction'].upper()}]")
        with col_b:
            conf = selected_row["confidence"]
            conf_color = "green" if conf > 60 else ("orange" if conf > 40 else "red")
            st.markdown(f"**Confidence:** :{conf_color}[{conf:.1f}%]")
        with col_c:
            st.markdown(f"**Score:** {selected_row['score']}")

        if is_past:
            result = selected_row.get("result", "N/A")
            result_display = {
                "correct": "✅ CORRECT",
                "wrong": "❌ WRONG",
                "neutral": "⬜ NEUTRAL",
                "flat": "➖ FLAT",
                "no_data": "❓ NO DATA",
            }.get(result, result)
            st.markdown(f"**Result:** {result_display}")

            if selected_row.get("actual_3d_return") is not None:
                ret = selected_row["actual_3d_return"]
                st.metric("Actual 3-Day Return", f"{ret:+.2f}%", delta=f"${selected_row.get('actual_3d_price', 'N/A')}")

        st.markdown("---")
        st.subheader("Signal Breakdown")
        signals = selected_row.get("signals", {})
        signal_df = pd.DataFrame([
            {"Signal": s.replace("_", " ").title(), "Value": v, "Weight": 1}
            for s, v in signals.items()
        ])
        st.dataframe(signal_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Calendar Heatmap (Past 90 + Future 3 Days)")

    display_rows = enriched[-93:]

    heatmap_data = []
    for r in display_rows:
        d = r["date"]
        conf = r["confidence"]

        if r.get("result") == "correct":
            status = "✓"
        elif r.get("result") == "wrong":
            status = "✗"
        elif r["is_future"]:
            status = "→"
        else:
            status = "·"

        heatmap_data.append({
            "Date": d.strftime("%b %d"),
            "DOW": d.strftime("%a"),
            "Direction": r["direction"].upper(),
            "Confidence%": conf,
            "WTI": f"${r.get('wti_close', 'N/A'):.2f}" if r.get("wti_close") else "N/A",
            "Result": status,
        })

    heatmap_df = pd.DataFrame(heatmap_data)

    def color_direction(val):
        if val == "BULLISH":
            return "color: #00ff88"
        elif val == "BEARISH":
            return "color: #ff4444"
        return "color: gray"

    def color_result(val):
        if val == "✓":
            return "color: #00ff88"
        elif val == "✗":
            return "color: #ff4444"
        elif val == "→":
            return "color: cyan"
        return ""

    styled = heatmap_df.style.map(color_direction, subset=["Direction"])
    styled = styled.map(color_result, subset=["Result"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.caption("✓ = correct prediction | ✗ = wrong prediction | → = pending (future) | · = neutral/flat")
