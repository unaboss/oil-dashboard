import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render_sentiment_tab(polymarket_signal, sentiment_raw):
    st.subheader("Retail Sentiment — Polymarket Analysis")

    if polymarket_signal is None:
        st.warning("No Polymarket data available.")
        return

    daily_dir = polymarket_signal.get("daily_direction")

    # ── Gauge: Daily Direction ──
    if daily_dir and daily_dir.get("prob_up") is not None:
        st.markdown("### Today's Direction Signal")
        prob_up = daily_dir["prob_up"]
        prob_down = daily_dir.get("prob_down", 1 - prob_up)

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+delta",
            value=prob_up * 100,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Probability WTI Goes UP Today"},
            delta={"reference": 50, "increasing": {"color": "lime"}, "decreasing": {"color": "red"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "cyan"},
                "steps": [
                    {"range": [0, 40], "color": "rgba(255,0,0,0.3)"},
                    {"range": [40, 60], "color": "rgba(255,165,0,0.3)"},
                    {"range": [60, 100], "color": "rgba(0,255,0,0.3)"},
                ],
                "threshold": {"line": {"color": "white", "width": 3}, "thickness": 0.75, "value": 50},
            },
        ))
        fig_gauge.update_layout(height=280, template="plotly_dark")
        st.plotly_chart(fig_gauge, use_container_width=True)

        cols = st.columns(4)
        with cols[0]: st.metric("Prob Up", f"{prob_up * 100:.1f}%")
        with cols[1]: st.metric("Prob Down", f"{prob_down * 100:.1f}%")
        with cols[2]: st.metric("Date", daily_dir.get("date", "N/A"))
        with cols[3]: st.metric("Volume", f"${daily_dir.get('volume', 0):,.0f}")

    # ── Risk/Reward Asymmetry ──
    st.markdown("---")
    st.markdown("### Risk/Reward Asymmetry")

    current_wti = polymarket_signal.get("current_wti")

    monthly = polymarket_signal.get("monthly_targets")
    weekly = polymarket_signal.get("weekly_targets")

    asymmetry_data = []
    if monthly:
        asymmetry_data.append({
            "Horizon": "Monthly",
            "Upside ($)": f"+${monthly.get('upside_skew', 'N/A')}" if monthly.get('upside_skew') is not None else "N/A",
            "Downside ($)": f"${monthly.get('downside_skew', 'N/A')}" if monthly.get('downside_skew') is not None else "N/A",
            "Most Likely High": f"${monthly.get('most_likely_high', 'N/A')}" if monthly.get('most_likely_high') else "N/A",
            "Most Likely Low": f"${monthly.get('most_likely_low', 'N/A')}" if monthly.get('most_likely_low') else "N/A",
        })
    if weekly:
        asymmetry_data.append({
            "Horizon": "Weekly",
            "Upside ($)": f"+${weekly.get('upside_skew', 'N/A')}" if weekly.get('upside_skew') is not None else "N/A",
            "Downside ($)": f"${weekly.get('downside_skew', 'N/A')}" if weekly.get('downside_skew') is not None else "N/A",
            "Most Likely High": f"${weekly.get('most_likely_high', 'N/A')}" if weekly.get('most_likely_high') else "N/A",
            "Most Likely Low": f"${weekly.get('most_likely_low', 'N/A')}" if weekly.get('most_likely_low') else "N/A",
        })

    if asymmetry_data:
        st.dataframe(pd.DataFrame(asymmetry_data), use_container_width=True, hide_index=True)

    if current_wti and monthly:
        upside = monthly.get("upside", {})
        down = monthly.get("downside", {})

        if upside.get("strikes") or down.get("strikes"):
            fig_bar = go.Figure()

            if upside.get("strikes"):
                u_s = [s["strike"] for s in upside["strikes"][:10]]
                u_p = [s["prob"] * 100 for s in upside["strikes"][:10]]
                fig_bar.add_trace(go.Bar(
                    y=u_s, x=u_p,
                    orientation="h", name="Upside Prob %",
                    marker_color="lime", opacity=0.7,
                ))

            if down.get("strikes"):
                d_s = [s["strike"] for s in down["strikes"][:10]]
                d_p = [s["prob"] * 100 for s in down["strikes"][:10]]
                fig_bar.add_trace(go.Bar(
                    y=d_s, x=d_p,
                    orientation="h", name="Downside Prob %",
                    marker_color="red", opacity=0.7,
                ))

            fig_bar.add_hline(y=current_wti, line_dash="dash", line_color="white",
                              annotation_text=f"Current: ${current_wti:.1f}")
            fig_bar.update_layout(
                title="Monthly Probability by Strike Level",
                height=400, template="plotly_dark",
                xaxis_title="Probability (%)", yaxis_title="Strike Price",
                barmode="group",
            )
            fig_bar.update_yaxes(tickprefix="$", tickformat=".0f")
            st.plotly_chart(fig_bar, use_container_width=True)

    # ── OPEC & Geopolitical Risk ──
    st.markdown("---")
    st.markdown("### Geopolitical & OPEC Risk")

    opec = polymarket_signal.get("opec_geopolitics", [])
    sanctions = polymarket_signal.get("geo_sanctions", [])
    ath = polymarket_signal.get("all_time_high", [])

    risk_items = opec + sanctions + ath
    if risk_items:
        col_risk = st.columns(min(len(risk_items), 3))
        for i, item in enumerate(risk_items[:3]):
            with col_risk[i]:
                prob = item.get("prob_yes") or item.get("price")
                prob_disp = f"{prob * 100:.1f}%" if prob is not None else "N/A"
                st.metric(
                    item.get("question", "Unknown")[:60],
                    prob_disp,
                    delta=f"Vol: ${(item.get('volume') or 0):,.0f}",
                )
    else:
        st.info("No active OPEC, sanctions, or all-time-high markets.")

    # ── Market Count Summary ──
    st.markdown("---")
    st.subheader("Market Classification Summary")

    if sentiment_raw:
        classified = sentiment_raw.get("all_classified", [])
        family_counts = {}
        for c in classified:
            fam = c.get("family", "unknown")
            family_counts[fam] = family_counts.get(fam, 0) + 1

        if family_counts:
            family_df = pd.DataFrame([
                {"Family": k.replace("_", " ").title(), "Count": v}
                for k, v in sorted(family_counts.items(), key=lambda x: -x[1])
            ])
            st.dataframe(family_df, use_container_width=True, hide_index=True)
