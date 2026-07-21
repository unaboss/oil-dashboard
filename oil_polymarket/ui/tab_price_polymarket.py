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
    daily_dir = polymarket_signal.get("daily_direction") if polymarket_signal else None

    # ════════════════════════════════════════════════════════════
    # Section A0: Intraday WTI vs PM with day navigation
    # ════════════════════════════════════════════════════════════
    if pm_history:
        from datetime import datetime, timezone, timedelta

        st.markdown("### WTI Price vs Polymarket Up% Probability")

        if "day_offset" not in st.session_state:
            st.session_state["day_offset"] = 0

        today_utc = datetime.now(timezone.utc).date()
        target_date = today_utc - timedelta(days=st.session_state["day_offset"])

        # Skip weekends in navigation
        def is_trading_day(d):
            return d.weekday() < 5

        def prev_trading_day(d):
            d = d - timedelta(days=1)
            while not is_trading_day(d) and d >= today_utc - timedelta(days=14):
                d = d - timedelta(days=1)
            return d

        def next_trading_day(d):
            d = d + timedelta(days=1)
            while not is_trading_day(d) and d <= today_utc:
                d = d + timedelta(days=1)
            return d

        prev_candidate = prev_trading_day(target_date)
        next_candidate = next_trading_day(target_date)
        can_go_back = is_trading_day(prev_candidate) and prev_candidate >= today_utc - timedelta(days=10)
        can_go_forward = next_candidate <= today_utc and st.session_state["day_offset"] > 0

        pm_times, pm_prices = [], []
        prev_p = None
        for h in pm_history:
            try:
                ts = datetime.fromtimestamp(h["timestamp"], tz=timezone.utc)
                p = h["price"]
                if ts.date() == target_date:
                    pm_times.append(ts)
                    pm_prices.append(p * 100)
            except Exception:
                continue

        wti_times, wti_prices = [], []
        if wti_intraday:
            for ts_str, price in zip(wti_intraday.get("timestamps", []),
                                      wti_intraday.get("prices", [])):
                try:
                    dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
                    if dt.date() == target_date:
                        wti_times.append(dt)
                        wti_prices.append(price)
                except Exception:
                    continue

        target_open = None
        if wti_times:
            target_open = wti_prices[0]
        if target_open is None and len(close) >= 2:
            pd_dates = [pd.to_datetime(d).date() for d in dates]
            for i, d in enumerate(pd_dates):
                if d == target_date - timedelta(days=1) and i < len(close):
                    target_open = close[i]
                    break
        anchor_price = target_open

        show_phase = False
        phase_data = None

        if not wti_times:
            st.info(f"No WTI trading data for {target_date.isoformat()}.")
        elif not pm_times:
            st.info(f"No Polymarket Up/Down data for {target_date.isoformat()}.")
        else:
            # Phase detection
            phase_data = None
            current_phase = "neutral"
            phase_multiplier = 0.0
            lag_minutes = 0

            from analysis.phase_detector import align_series, detect_phases
            merged = align_series(
                [t.isoformat() for t in wti_times], wti_prices,
                [t.isoformat() for t in pm_times], pm_prices,
            )
            if merged is not None and not merged.empty:
                phase_data, phase_multiplier, current_phase, lag_minutes = detect_phases(
                    merged, anchor_price
                )

            # Chart
            fig0 = go.Figure()
            fig0.update_layout(
                yaxis=dict(title="WTI Price ($)"),
                yaxis2=dict(title="PM Up Probability (%)", overlaying="y", side="right",
                            range=[0, 100], tickformat=".0f"),
                xaxis=dict(title="Time (UTC)", range=[
                    target_date.isoformat() + "T00:00:00",
                    target_date.isoformat() + "T23:59:59",
                ]),
                height=450, template="plotly_dark",
                hovermode="x unified",
                legend=dict(orientation="h", y=1.15),
            )

            show_phase = st.checkbox("Show Phase Bands", value=True,
                                     key=f"phase_toggle_{st.session_state['day_offset']}")

            if show_phase and phase_data is not None and "phase" in phase_data.columns:
                phase_colors = {
                    "pm_lagging": "rgba(0,200,0,0.30)",
                    "converging": "rgba(255,255,0,0.25)",
                    "pm_ahead": "rgba(255,165,0,0.30)",
                    "divergence": "rgba(255,0,0,0.35)",
                    "neutral": "rgba(128,128,128,0.08)",
                }
                phases = list(phase_data["phase"].values)
                t_idx = [t.to_pydatetime().replace(tzinfo=None) if hasattr(t, 'to_pydatetime')
                          else t for t in phase_data.index]
                segs = []
                cur = phases[0]; start = 0
                for k in range(1, len(phases)):
                    if phases[k] != cur:
                        segs.append((cur, start, k))
                        cur = phases[k]; start = k
                segs.append((cur, start, len(phases)))

                for ph, s, e in segs:
                    color = phase_colors.get(ph, "rgba(0,0,0,0)")
                    x0 = t_idx[s]
                    x1 = t_idx[min(e, len(t_idx) - 1)]
                    if x0 == x1:
                        x1 = x0 + timedelta(minutes=5)
                    fig0.add_vrect(x0=x0, x1=x1, fillcolor=color, layer="below",
                                   line_width=0, opacity=0.5)

            fig0.add_trace(go.Scatter(
                x=pm_times, y=pm_prices, mode="lines",
                name="PM Up% Odds", line=dict(color="red", width=2), yaxis="y2",
            ))
            fig0.add_trace(go.Scatter(
                x=wti_times, y=wti_prices, mode="lines",
                name="WTI Price", line=dict(color="white", width=2),
            ))

            if anchor_price:
                fig0.add_hline(y=50, line_dash="dot", line_color="gray",
                               annotation_text=f"50% — Open ${anchor_price:.2f}", yref="y2")
            else:
                fig0.add_hline(y=50, line_dash="dot", line_color="gray",
                               annotation_text="50% (neutral)", yref="y2")

            if anchor_price:
                all_w = wti_prices + [anchor_price]
                max_dev = max(abs(p - anchor_price) for p in all_w)
                pad = max(max_dev * 0.3, 0.80)
                fig0.update_layout(
                    yaxis=dict(range=[anchor_price - max_dev - pad, anchor_price + max_dev + pad])
                )

            st.plotly_chart(fig0, use_container_width=True)

            # Metrics
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
                cur_p = wti_prices[-1] if wti_prices else None
                if cur_p and anchor_price:
                    chg = (cur_p - anchor_price) / anchor_price * 100
                    st.metric("WTI vs Open", f"{chg:+.2f}%", delta="Up" if chg > 0 else "Down")

        # Navigation — always visible, even when no data for target date
        st.markdown("---")
        c_prev, c_label, c_reset, c_next = st.columns([1, 2, 1, 1])
        with c_prev:
            if st.button("← Prev", use_container_width=True, disabled=not can_go_back,
                         help="Previous trading day"):
                prev = prev_trading_day(target_date)
                st.session_state["day_offset"] = (today_utc - prev).days
                st.rerun()
        with c_label:
            if st.session_state["day_offset"] == 0:
                lbl = "Today"
            else:
                lbl = target_date.strftime("%a, %b %d")
            st.caption(f"**{lbl}**")
        with c_reset:
            if st.button("Today", use_container_width=True,
                         disabled=(st.session_state["day_offset"] == 0)):
                st.session_state["day_offset"] = 0
                st.rerun()
        with c_next:
            if st.button("Next →", use_container_width=True, disabled=not can_go_forward,
                         help="Next trading day"):
                nxt = next_trading_day(target_date)
                st.session_state["day_offset"] = max(0, (today_utc - nxt).days)
                st.rerun()

        # Live data validation
        with st.expander("Chart Data Validation"):
            st.write(f"**Target date:** {target_date.isoformat()} (offset={st.session_state['day_offset']})")
            st.write(f"**WTI points:** {len(wti_times)} | range: {wti_times[0] if wti_times else 'none'} - {wti_times[-1] if wti_times else 'none'}")
            st.write(f"**WTI prices:** {wti_prices[0] if wti_prices else '?'} - {wti_prices[-1] if wti_prices else '?'}")
            st.write(f"**PM points:** {len(pm_times)} | range: {pm_times[0] if pm_times else 'none'} - {pm_times[-1] if pm_times else 'none'}")
            st.write(f"**PM prices:** {pm_prices[0] if pm_prices else '?'} - {pm_prices[-1] if pm_prices else '?'}")
            st.write(f"**Anchor (open):** {anchor_price}")
            st.write(f"**Phase data:** {'None' if phase_data is None else f'{len(phase_data)} rows'}")
            if phase_data is not None and 'phase' in phase_data.columns:
                st.write(f"**Unique phases:** {list(phase_data['phase'].unique())}")
            st.write(f"**Show phase:** {show_phase}")

    # ════════════════════════════════════════════════════════════
    # Section A: 30-day daily direction overlay
    # ════════════════════════════════════════════════════════════
    st.markdown("### Daily Direction Signal")

    pm_dates = pd.to_datetime(dates[-30:])
    pm_close = close[-30:]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pm_dates, y=pm_close, mode="lines",
        name="WTI Close", line=dict(color="white", width=2),
    ))

    if daily_dir:
        prob_up = daily_dir.get("prob_up")
        if prob_up is not None:
            color = "green" if prob_up > 0.55 else ("red" if prob_up < 0.45 else "orange")
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

    # ════════════════════════════════════════════════════════════
    # Section B: Daily implied distribution
    # ════════════════════════════════════════════════════════════
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

    # ════════════════════════════════════════════════════════════
    # Section C: Weekly/Monthly probability curves
    # ════════════════════════════════════════════════════════════
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
                name="P(hit HIGH) %", line=dict(color="lime"), marker=dict(size=8),
            ))

        if downside.get("strikes"):
            d_strikes = [s["strike"] for s in downside["strikes"]]
            d_probs = [s["prob"] * 100 for s in downside["strikes"]]
            fig3.add_trace(go.Scatter(
                x=d_strikes, y=d_probs, mode="markers+lines",
                name="P(hit LOW) %", line=dict(color="red"), marker=dict(size=8),
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

    # ════════════════════════════════════════════════════════════
    # Section D: Strike detail table
    # ════════════════════════════════════════════════════════════
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
