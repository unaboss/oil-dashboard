import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def render_price_polymarket_tab(market_data, polymarket_signal, pm_history=None, wti_intraday=None):
    st.subheader("WTI Price & Polymarket Signals")

    if market_data is None:
        st.warning("Market data not available.")
        return

    wti = market_data.get("wti", {})
    dates = wti.get("dates", [])
    close = wti.get("close", [])

    if not dates or not close:
        st.warning("No WTI price data available.")
        return

    current_wti = close[-1] if close else None
    prev_close = close[-2] if len(close) >= 2 else None
    daily_dir = polymarket_signal.get("daily_direction") if polymarket_signal else None

    # ── Section A0: WTI Price vs Polymarket Up% Over Time ──
    if pm_history:
        from datetime import datetime, timezone, timedelta

        st.markdown("### WTI Price vs Polymarket Up% Probability")

        today_utc = datetime.now(timezone.utc).date()

        pm_times = []
        pm_prices = []
        for h in pm_history:
            try:
                ts = datetime.fromtimestamp(h["timestamp"], tz=timezone.utc)
                if ts.date() == today_utc:
                    pm_times.append(ts)
                    pm_prices.append(h["price"] * 100)
            except Exception:
                continue

        if not pm_times:
            st.info("No intraday PM data available yet for today.")
        else:
            # WTI intraday for today
            wti_times = []
            wti_prices = []
            if wti_intraday:
                for ts_str, price in zip(wti_intraday.get("timestamps", []),
                                          wti_intraday.get("prices", [])):
                    try:
                        dt = datetime.fromisoformat(ts_str)
                        if dt.date() == today_utc:
                            wti_times.append(dt)
                            wti_prices.append(price)
                    except Exception:
                        continue

            fig0 = make_subplots(specs=[[{"secondary_y": True}]])

            fig0.add_trace(go.Scatter(
                x=pm_times, y=pm_prices, mode="lines",
                name="PM Up% Odds", line=dict(color="red", width=2),
            ), secondary_y=True)

            if wti_times:
                fig0.add_trace(go.Scatter(
                    x=wti_times, y=wti_prices, mode="lines",
                    name="WTI Price", line=dict(color="white", width=2),
                ), secondary_y=False)
            else:
                # fallback: yesterday close → current
                wti_x_today = [pd.to_datetime(dates[-2]), pd.to_datetime(dates[-1])]
                wti_y_today = [close[-2], close[-1]] if len(close) >= 2 else [close[-1], close[-1]]
                fig0.add_trace(go.Scatter(
                    x=wti_x_today, y=wti_y_today, mode="lines+markers",
                    name="WTI Price (daily)", line=dict(color="white", width=2, dash="dot"),
                    marker=dict(size=6, symbol="diamond"),
                ), secondary_y=False)

            fig0.add_hline(y=50, line_dash="dot", line_color="gray",
                           annotation_text="50% (neutral)", secondary_y=True)

            fig0.update_yaxes(title_text="WTI Price ($)", secondary_y=False)
            fig0.update_yaxes(
                title_text="PM Up Probability (%)", secondary_y=True,
                range=[0, 100], tickformat=".0f",
            )
            fig0.update_xaxes(title_text="Time (UTC)")

            fig0.update_layout(
                height=450, template="plotly_dark",
                hovermode="x unified",
                legend=dict(orientation="h", y=1.15),
            )
            st.plotly_chart(fig0, use_container_width=True)

        # Lag note
        if daily_dir and daily_dir.get("prob_up") is not None:
            prob_up = daily_dir["prob_up"]
            wti_change = ((current_wti - prev_close) / prev_close * 100) if current_wti and prev_close else 0
            pm_direction = "bullish" if prob_up > 0.50 else "bearish"
            wti_direction = "up" if wti_change > 0 else "down"
            if (pm_direction == "bullish" and wti_direction == "down") or \
               (pm_direction == "bearish" and wti_direction == "up"):
                st.info(f"Divergence: PM odds {pm_direction} ({prob_up*100:.0f}% Up) but WTI {wti_direction} ({wti_change:+.2f}%) — watch for PM leading price.")

    # ── Section A: Daily Direction Overlay ──
    st.markdown("### Daily Direction Signal")

    pm_dates = pd.to_datetime(dates[-30:])
    pm_close = close[-30:]

    daily_dir = polymarket_signal.get("daily_direction") if polymarket_signal else None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pm_dates, y=pm_close, mode="lines",
        name="WTI Close", line=dict(color="white", width=2),
    ))

    if daily_dir:
        prob_up = daily_dir.get("prob_up")
        if prob_up is not None:
            color = "green" if prob_up > 0.55 else ("red" if prob_up < 0.45 else "orange")
            date_label = daily_dir.get("date", "today")
            fig.add_trace(go.Scatter(
                x=[pm_dates[-1]], y=[pm_close[-1]],
                mode="markers+text",
                name=f"{prob_up * 100:.0f}% Up",
                marker=dict(size=16, color=color, symbol="diamond"),
                text=[f"{prob_up * 100:.0f}% Up"],
                textposition="top center",
                showlegend=True,
            ))

    fig.update_layout(
        title="WTI Price (30d) with Daily Polymarket Direction Signal",
        height=450, template="plotly_dark", hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    if daily_dir:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Prob Up Today", f"{daily_dir.get('prob_up', 0) * 100:.1f}%" if daily_dir.get('prob_up') else "N/A")
        with col2:
            st.metric("Prob Down Today", f"{daily_dir.get('prob_down', 0) * 100:.1f}%" if daily_dir.get('prob_down') else "N/A")
        with col3:
            st.metric("Net Signal", f"{daily_dir.get('net_sentiment', 0):+.3f}" if daily_dir.get('net_sentiment') is not None else "N/A",
                      delta=daily_dir.get("interpretation", "").upper())

    # ── Section B: Daily Implied Distribution ──
    daily_targets = polymarket_signal.get("daily_targets") if polymarket_signal else None
    if daily_targets and daily_targets.get("distribution"):
        st.markdown("---")
        st.markdown("### Daily Close — Market-Implied Distribution")

        dist = daily_targets["distribution"]
        if dist.get("x_fine") and dist.get("pdf_fine"):
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=dist["x_fine"], y=dist["pdf_fine"],
                mode="lines", fill="tozeroy",
                name="Implied PDF", line=dict(color="cyan"),
            ))
            if current_wti:
                fig2.add_vline(x=current_wti, line_dash="dash", line_color="white",
                               annotation_text=f"Current: ${current_wti:.2f}")
            fig2.add_vline(x=dist["expected"], line_dash="dot", line_color="lime",
                           annotation_text=f"Expected: ${dist['expected']}")
            fig2.update_layout(
                title=f"Implied Close Distribution ({daily_targets.get('date', 'today')})",
                height=350, template="plotly_dark",
                xaxis_title="WTI Price ($)", yaxis_title="Probability Density",
            )
            st.plotly_chart(fig2, use_container_width=True)

            cols = st.columns(5)
            with cols[0]: st.metric("Expected", f"${dist['expected']}")
            with cols[1]: st.metric("Median", f"${dist['median']}")
            with cols[2]: st.metric("Mode", f"${dist['mode']}")
            with cols[3]: st.metric("IQR", f"${dist['iqr']}")
            with cols[4]: st.metric("80% CI", f"${dist['p10']}–${dist['p90']}")

    # ── Section C: Weekly/Monthly Probability Curves ──
    horizon = st.selectbox("Horizon", ["Monthly", "Weekly"], key="pm_horizon_select")
    key = "monthly_targets" if horizon == "Monthly" else "weekly_targets"
    targets = polymarket_signal.get(key) if polymarket_signal else None

    if targets:
        st.markdown("---")
        st.markdown(f"### {horizon} Price Targets — Probability Curve")

        upside = targets.get("upside", {})
        downside = targets.get("downside", {})

        fig3 = go.Figure()

        if upside.get("strikes"):
            u_strikes = [s["strike"] for s in upside["strikes"]]
            u_probs = [s["prob"] * 100 for s in upside["strikes"]]
            fig3.add_trace(go.Scatter(
                x=u_strikes, y=u_probs, mode="markers+lines",
                name=f"P(hit HIGH) %", line=dict(color="lime"),
                marker=dict(size=8),
            ))

        if downside.get("strikes"):
            d_strikes = [s["strike"] for s in downside["strikes"]]
            d_probs = [s["prob"] * 100 for s in downside["strikes"]]
            fig3.add_trace(go.Scatter(
                x=d_strikes, y=d_probs, mode="markers+lines",
                name=f"P(hit LOW) %", line=dict(color="red"),
                marker=dict(size=8),
            ))

        if current_wti:
            fig3.add_vline(x=current_wti, line_dash="dash", line_color="white",
                           annotation_text=f"WTI ${current_wti:.2f}")

        fig3.update_layout(
            title=f"{horizon} Implied Probability of Touching Price Levels",
            height=400, template="plotly_dark",
            xaxis_title="Strike Price ($)", yaxis_title="Probability (%)",
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Skew metrics
        if targets.get("upside_skew") is not None or targets.get("downside_skew") is not None:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                sh = targets.get("most_likely_high")
                st.metric("Most Likely High", f"${sh}" if sh else "N/A",
                          delta=f"+${targets['upside_skew']}" if targets.get("upside_skew") else None)
            with col_b:
                sl = targets.get("most_likely_low")
                st.metric("Most Likely Low", f"${sl}" if sl else "N/A",
                          delta=f"${targets['downside_skew']}" if targets.get("downside_skew") else None)
            with col_c:
                if sh and sl:
                    st.metric("Expected Range", f"${sl}–${sh}")

    # ── Section D: Strike Detail Table ──
    if targets:
        st.markdown("---")
        show_side = st.radio("Show", ["Upside (HIGH)", "Downside (LOW)"], horizontal=True, key="pm_strike_side")
        side_key = "upside" if "Upside" in show_side else "downside"
        side_data = targets.get(side_key, {})

        if side_data.get("strikes"):
            rows = []
            for s in side_data["strikes"]:
                prob = s.get("prob", 0)
                rows.append({
                    "Strike ($)": s["strike"],
                    "P(Hit)": f"{prob * 100:.1f}%",
                    "Odds": f"{1/prob:.0f}-to-1" if prob and prob > 0 else "N/A",
                    "Volume ($)": f"${s.get('volume', 0):,.0f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
