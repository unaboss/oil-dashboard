import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import re


def render_inventory_tab(eia_data, pm_markets=None):
    st.subheader("Inventory Analysis — Scenario Projections")

    if eia_data is None:
        st.warning("EIA data not available. Check EIA_API_KEY in .env")
        return

    crude = eia_data.get("crude")
    if crude is None:
        st.warning("No crude inventory data available.")
        return

    from analysis.inventory_scenarios import compute_scenarios

    scenarios = compute_scenarios(crude)
    if scenarios is None:
        st.warning("Could not compute scenarios.")
        return

    # ── Metrics row ──
    spr = eia_data.get("spr")
    gasoline = eia_data.get("gasoline")
    distillate = eia_data.get("distillate")

    cols = st.columns(5)
    with cols[0]:
        crude_latest = crude["values"][0] / 1000 if crude.get("values") else None
        crude_chg = crude["changes"][0] / 1000 if crude.get("changes") and crude["changes"][0] else None
        st.metric("Crude Stocks", f"{crude_latest:.1f}M bbl" if crude_latest else "N/A",
                  delta=f"{crude_chg:+.1f}M" if crude_chg else None)
    with cols[1]:
        spr_latest = spr["values"][0] / 1000 if spr and spr.get("values") else None
        st.metric("SPR Level", f"{spr_latest:.1f}M bbl" if spr_latest else "N/A")
    with cols[2]:
        gas_latest = gasoline["values"][0] / 1000 if gasoline and gasoline.get("values") else None
        st.metric("Gasoline Stocks", f"{gas_latest:.1f}M bbl" if gas_latest else "N/A")
    with cols[3]:
        dist_latest = distillate["values"][0] / 1000 if distillate and distillate.get("values") else None
        st.metric("Distillate Stocks", f"{dist_latest:.1f}M bbl" if dist_latest else "N/A")
    with cols[4]:
        chg_weekly = crude["changes"][0] / 1000 if crude.get("changes") and crude["changes"][0] else None
        st.metric("Weekly Change", f"{chg_weekly:+.1f}M bbl" if chg_weekly else "N/A")

    # ── Chart 1: Inventory Health Timeline ──
    st.markdown("### Crude Oil Inventory Health — Dec 2025 to Dec 2026")

    fig1 = go.Figure()

    scenario_colors = {
        "status_quo": ("green", "dash"),
        "ceasefire": ("blue", "dot"),
        "back_to_normal": ("gray", "dash"),
        "worsening": ("red", "dot"),
    }

    # Actual line
    actual = scenarios["actual"]
    fig1.add_trace(go.Scatter(
        x=pd.to_datetime(actual["dates"]),
        y=[v / 1000 for v in actual["values"]],
        mode="lines", name="Actual Inventory",
        line=dict(color="white", width=2),
    ))

    # Projection lines
    for key, (color, dash) in scenario_colors.items():
        proj = scenarios.get(key, {})
        if proj:
            fig1.add_trace(go.Scatter(
                x=pd.to_datetime(proj["dates"]),
                y=[v / 1000 for v in proj["values"]],
                mode="lines", name=proj.get("label", key),
                line=dict(color=color, width=2, dash=dash),
            ))

    # Polymarket inventory bet horizontal lines
    if pm_markets:
        pm_lines = _extract_inventory_bets(pm_markets)
        for bet in pm_lines:
            target_level_m = bet["target"] / 1000 if bet["target"] > 1000 else bet["target"]
            try:
                end_dt = pd.to_datetime(bet["end_date"])
            except Exception:
                end_dt = pd.Timestamp("2026-08-01")

            fig1.add_shape(
                type="line",
                x0=pd.Timestamp.now(), x1=end_dt,
                y0=target_level_m, y1=target_level_m,
                line=dict(color="orange", width=2, dash="dot"),
            )
            fig1.add_annotation(
                x=end_dt, y=target_level_m,
                text=bet["label"][:60],
                showarrow=True, arrowhead=1,
                font=dict(size=10, color="orange"),
                bgcolor="rgba(0,0,0,0.7)",
            )

    # Today marker
    today = pd.Timestamp.now()
    fig1.add_vline(x=today, line_dash="dash", line_color="yellow", line_width=1,
                   annotation_text="Today")

    fig1.update_layout(
        height=500, template="plotly_dark",
        title="Crude Oil Stocks — Actual & Scenario Projections",
        xaxis_title="Date", yaxis_title="Million Barrels",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Scenario details
    st.markdown("---")
    st.markdown("### Scenario Projection Details")
    scenario_data = []
    for key in ["status_quo", "ceasefire", "back_to_normal", "worsening"]:
        proj = scenarios.get(key, {})
        vals = proj.get("values", [])
        end_val = vals[-1] / 1000 if vals else None
        rate = proj.get("annual_rate")
        rate_str = f"{rate / 1000:+.1f}M/year" if rate and abs(rate) > 1000 else (
            f"{rate:+.1f}K/year" if rate else "N/A"
        )
        scenario_data.append({
            "Scenario": proj.get("label", key).replace("_", " ").title(),
            "Dec 2026 Level": f"{end_val:.1f}M bbl" if end_val else "N/A",
            "Annual Rate": rate_str,
        })
    st.dataframe(pd.DataFrame(scenario_data), use_container_width=True, hide_index=True)

    # ── Chart 2: Refinery Time-Series ──
    st.markdown("---")
    st.markdown("### Refinery & Production Health")

    refinery_inputs = eia_data.get("refinery_inputs")
    refinery_util = eia_data.get("refinery_utilization")
    gas_prod = eia_data.get("gasoline_production")
    dist_prod = eia_data.get("distillate_production")

    if any([refinery_inputs, refinery_util, gas_prod, dist_prod]):
        fig2 = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Refinery Crude Inputs (K bbl/day)",
                "Refinery Utilization (%)",
                "Gasoline Production (K bbl/day)",
                "Distillate Production (K bbl/day)",
            ),
            vertical_spacing=0.12, horizontal_spacing=0.08,
        )

        def _plot_sub(data, row, col, color, name):
            if data and data.get("dates"):
                d_dates = pd.to_datetime([d for d in data["dates"]][::-1])
                d_vals = data["values"][::-1]
                fig2.add_trace(
                    go.Scatter(x=d_dates, y=d_vals, mode="lines", name=name,
                               line=dict(color=color, width=1.5)),
                    row=row, col=col,
                )

        _plot_sub(refinery_inputs, 1, 1, "cyan", "Crude Inputs")
        _plot_sub(refinery_util, 1, 2, "orange", "Utilization %")
        _plot_sub(gas_prod, 2, 1, "lime", "Gasoline Prod")
        _plot_sub(dist_prod, 2, 2, "magenta", "Distillate Prod")

        fig2.update_layout(
            height=550, template="plotly_dark",
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Interpretation
        st.markdown("**How to read this:**")
        st.markdown("- Falling stocks + high utilization = demand-pull → bullish but sustainable")
        st.markdown("- Falling stocks + low utilization = supply issue → more bullish, less sustainable")
        st.markdown("- Rising stocks + high utilization = overproduction → bearish")
        st.markdown("- Falling stocks + SPR draining = government masking real deficit")
    else:
        st.info("Refinery data not available. Check EIA API series codes.")


def _extract_inventory_bets(markets):
    """Extract inventory target bets with strike levels and dates."""
    bets = []
    for m in markets:
        q = (m.get("question") or "").strip()
        end_date = m.get("endDate", "") or m.get("_event_end", "") or ""

        # Extract numeric target from question (e.g., "fall to 380M" → 380)
        # Match patterns like: 300M, 380 million, 300 million barrels
        patterns = [
            r"(\d+)\s*(?:million|M)\s*(?:barrels)?",
            r"(\d{3})\s*(?:M|million)",
            r"(?:below|above|to|at)\s*(\d+\.?\d*)\s*(?:million|M)",
        ]

        target = None
        for pat in patterns:
            match = re.search(pat, q, re.IGNORECASE)
            if match:
                target = float(match.group(1))
                if target < 1000:  # likely in millions, convert to K
                    target = target * 1000
                break

        if target is None:
            continue

        # Extract date
        date_match = re.search(
            r"(?:by|on)\s+(January|February|March|April|May|June|July|"
            r"August|September|October|November|December)\s+(\d{1,2})",
            q, re.IGNORECASE
        )
        if date_match:
            parsed_date = f"2026-{date_match.group(1)[:3]}-{date_match.group(2).zfill(2)}"

        bets.append({
            "label": q[:80],
            "target": target,
            "end_date": parsed_date if date_match else end_date,
            "volume": float(m.get("volumeNum") or 0),
        })

    return bets
