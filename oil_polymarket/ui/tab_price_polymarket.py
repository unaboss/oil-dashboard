import streamlit as st
import plotly.graph_objects as go
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

            # ── Phase Detection ──
            phase_data = None
            current_phase = "neutral"
            phase_multiplier = 0.0
            lag_minutes = 0

            today_open = wti_intraday.get("today_open") if wti_intraday else None
            anchor_price = today_open or (close[-2] if len(close) >= 2 else None)

            if wti_times and pm_times:
                from analysis.phase_detector import align_series, detect_phases
                merged = align_series(
                    [t.isoformat() for t in wti_times], wti_prices,
                    [t.isoformat() for t in pm_times], pm_prices,
                )
                if merged is not None and not merged.empty:
                    phase_data, phase_multiplier, current_phase, lag_minutes = detect_phases(
                        merged, anchor_price
                    )

            fig0 = go.Figure()

            fig0.update_layout(
                yaxis=dict(title="WTI Price ($)"),
                yaxis2=dict(
                    title="PM Up Probability (%)",
                    overlaying="y",
                    side="right",
                    range=[0, 100],
                    tickformat=".0f",
                ),
                xaxis=dict(title="Time (UTC)"),
                height=450, template="plotly_dark",
                hovermode="x unified",
                legend=dict(orientation="h", y=1.15),
            )

            # Phase toggle
            show_phase = st.checkbox("Show Phase Bands", value=True, key="phase_toggle")
            if show_phase and phase_data is not None and "phase" in phase_data.columns:
                phase_colors = {
                    "pm_lagging": "rgba(0,200,0,0.15)",
                    "converging": "rgba(255,255,0,0.10)",
                    "pm_ahead": "rgba(255,165,0,0.15)",
                    "divergence": "rgba(255,0,0,0.20)",
                    "neutral": "rgba(128,128,128,0.03)",
                }
                phases = list(phase_data["phase"].values)
                times = [t.to_pydatetime().replace(tzinfo=None) if hasattr(t, 'to_pydatetime')
                         else t for t in phase_data.index]
                segs = []
                current = phases[0]
                start = 0
                for k in range(1, len(phases)):
                    if phases[k] != current:
                        segs.append((current, start, k))
                        current = phases[k]
                        start = k
                segs.append((current, start, len(phases)))

                for phase, s, e in segs:
                    color = phase_colors.get(phase, "rgba(0,0,0,0)")
                    x0 = times[s]
                    x1 = times[min(e, len(times) - 1)]
                    if x0 == x1:
                        from datetime import timedelta
                        x1 = x0 + timedelta(minutes=5)
                    fig0.add_vrect(
                        x0=x0, x1=x1,
                        fillcolor=color, layer="below", line_width=0,
                        opacity=0.5,
                    )

            fig0.add_trace(go.Scatter(
                x=pm_times, y=pm_prices, mode="lines",
                name="PM Up% Odds", line=dict(color="red", width=2),
                yaxis="y2",
            ))

            if wti_times:
                fig0.add_trace(go.Scatter(
                    x=wti_times, y=wti_prices, mode="lines",
                    name="WTI Price", line=dict(color="white", width=2),
                ))
            else:
                wti_x_today = [pd.to_datetime(dates[-2]), pd.to_datetime(dates[-1])]
                wti_y_today = [close[-2], close[-1]] if len(close) >= 2 else [close[-1], close[-1]]
                fig0.add_trace(go.Scatter(
                    x=wti_x_today, y=wti_y_today, mode="lines+markers",
                    name="WTI Price (daily)", line=dict(color="white", width=2, dash="dot"),
                    marker=dict(size=6, symbol="diamond"),
                ))

            if anchor_price:
                fig0.add_hline(y=50, line_dash="dot", line_color="gray",
                               annotation_text=f"50% — Open ${anchor_price:.2f}",
                               yref="y2")
            else:
                fig0.add_hline(y=50, line_dash="dot", line_color="gray",
                               annotation_text="50% (neutral)",
                               yref="y2")

            # Center WTI axis around anchor
            if anchor_price and wti_times:
                all_wti = wti_prices + [anchor_price]
                max_dev = max(abs(p - anchor_price) for p in all_wti)
                pad = max(max_dev * 0.3, 0.80)
                fig0.update_layout(
                    yaxis=dict(range=[anchor_price - max_dev - pad, anchor_price + max_dev + pad])
                )
            st.plotly_chart(fig0, use_container_width=True)

            # Phase metrics
            phase_labels = {
                "pm_lagging": "PM Lagging — traders catching up, early trend",
                "converging": "Converging — PM confirming price move",
                "pm_ahead": "PM Ahead — FOMO zone, possible exhaustion",
                "divergence": "Divergence — PM opposing price, reversal risk",
                "neutral": "Neutral — no clear signal",
            }
            phase_desc = phase_labels.get(current_phase, "Unknown")

            cols = st.columns(4)
            with cols[0]:
                color_map = {"pm_lagging": "green", "converging": "yellow", "pm_ahead": "orange", "divergence": "red", "neutral": "gray"}
                st.metric("Phase", current_phase.replace("_", " ").title(),
                          delta=f"Multiplier: {phase_multiplier:+.1f}" if phase_multiplier != 0 else None)
                st.caption(phase_desc)
            with cols[1]:
                st.metric("Est. Lag", f"{lag_minutes:+d} min",
                          delta="PM behind" if lag_minutes < -5 else ("PM ahead" if lag_minutes > 5 else "Aligned"))
            with cols[2]:
                if daily_dir and daily_dir.get("prob_up") is not None:
                    st.metric("PM Direction", f"{daily_dir['prob_up']*100:.0f}% Up")
            with cols[3]:
                if current_wti and anchor_price:
                    wti_chg = (current_wti - anchor_price) / anchor_price * 100
                    st.metric("WTI vs Open", f"{wti_chg:+.2f}%",
                              delta="Up" if wti_chg > 0 else "Down")


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
