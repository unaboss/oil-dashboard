"""Tab 9: Research & Narrative — Trump event study, bot-mention proxy, losing traders.

A navigable research tool. Three inner sub-tabs, each self-contained with a
methodology note. All data is free/manual (curated CSVs + Google Trends).
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from analysis.trump_event_study import compute_trump_event_study
from analysis.bot_narrative import compute_bot_narrative
from analysis.losing_traders import compute_losing_traders


CLASS_COLORS = {
    "Lagging": "#FFC107",
    "Pre-reversal": "#F44336",
    "Confirmation": "#4CAF50",
    "No signal": "#9E9E9E",
}


def render_research_tab(market_data, bot_trends_data, start=None, end=None):
    st.subheader("Research & Narrative")

    with st.expander("Methodology & caveats", expanded=False):
        st.markdown(
            "**Trump oil narrative** — event study on WTI. For each curated "
            "statement we measure the return *before* he spoke (5d) and *after* "
            "(3d). 'Lagging' = big pre-move, little after → announced after the "
            "move was done. 'Pre-reversal' = post-move reverses direction. "
            "Source: manually curated `data/trump_oil_statements.csv`."
        )
        st.markdown(
            "**Bot mentions** — NARRATIVE PROXY only: Google Trends search "
            "interest in bot/platform terms (MetaTrader, TradingView, 3Commas…). "
            "It is NOT a count of bots actually trading oil."
        )
        st.markdown(
            "**Losing oil traders** — anonymous/aggregate proxy from public CTA "
            "databases and social-copy leaderboards (`data/losing_traders.csv`). "
            "Individual retail P&L is private; named entities are public funds."
        )

    tab_trump, tab_bots, tab_traders = st.tabs([
        "Trump Oil Narrative",
        "Bot Mentions",
        "Losing Oil Traders",
    ])

    with tab_trump:
        _render_trump(market_data, start, end)

    with tab_bots:
        _render_bots(bot_trends_data, market_data)

    with tab_traders:
        _render_traders()


def _render_trump(market_data, start, end):
    study = compute_trump_event_study(market_data, start=start, end=end)

    if study["total"] == 0:
        st.info("No statements matched the current date range / WTI data.")
        return

    col_lag, col_sum = st.columns([1, 2])
    with col_lag:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=study["lag_rate"],
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#FFC107"},
                "steps": [
                    {"range": [0, 50], "color": "rgba(76,175,80,0.3)"},
                    {"range": [50, 100], "color": "rgba(255,193,7,0.3)"},
                ],
            },
            title={"text": "% Lagging (announced after move)"},
        ))
        fig.update_layout(height=220, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"{study['classified']} classified of {study['total']} statements")

    with col_sum:
        s = study["summary"]
        fig = go.Figure(go.Bar(
            x=list(s.keys()),
            y=list(s.values()),
            marker_color=[CLASS_COLORS.get(k, "#9E9E9E") for k in s.keys()],
        ))
        fig.update_layout(
            title="Statement classification",
            height=220,
            template="plotly_dark",
            yaxis_title="count",
        )
        st.plotly_chart(fig, use_container_width=True)

    events = study["events"]
    if events:
        fig = go.Figure()
        for klass, color in CLASS_COLORS.items():
            pts = [e for e in events if e["classification"] == klass]
            if not pts:
                continue
            fig.add_trace(go.Scatter(
                x=[e["pre_return_pct"] for e in pts],
                y=[e["fwd_return_pct"] for e in pts],
                mode="markers",
                name=klass,
                text=[f"{e['date']}: {e['statement']}" for e in pts],
                marker=dict(color=color, size=10),
            ))
        fig.add_hline(y=0, line=dict(color="#666", width=1))
        fig.add_vline(x=0, line=dict(color="#666", width=1))
        fig.update_layout(
            title="Pre-statement return (x) vs post-statement return (y)",
            height=420,
            template="plotly_dark",
            xaxis_title="5d return BEFORE statement (%)",
            yaxis_title="3d return AFTER statement (%)",
            hovermode="closest",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Statements")
    for e in events:
        color = CLASS_COLORS.get(e["classification"], "#9E9E9E")
        st.markdown(
            f"**{e['date']}** — <span style='color:{color}'>"
            f"{e['classification']}</span> — pre {e['pre_return_pct']:+.1f}% / "
            f"post {e['fwd_return_pct']:+.1f}%",
            unsafe_allow_html=True,
        )
        st.caption(e["statement"])


def _render_bots(bot_trends_data, market_data):
    narrative = compute_bot_narrative(bot_trends_data, market_data)

    if not narrative["available"]:
        st.info("Google Trends bot-mention data unavailable (rate-limited). Try refreshing later.")
        return

    dates = [pd.to_datetime(d) for d in narrative["dates"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=narrative["index"], mode="lines",
        name="Bot-mention index", line=dict(color="#00BCD4", width=2),
    ))
    fig.update_layout(
        title="Bot-Mention Index (normalized avg of search interest)",
        height=350,
        template="plotly_dark",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Latest index", narrative["latest_index"])
    col2.metric("Peak date", narrative["peak_date"] or "—")
    col3.metric("Corr. with WTI vol",
                f"{narrative['corr_vol']:.2f}" if narrative["corr_vol"] is not None else "—")

    st.markdown("#### Search interest by term")
    fig2 = go.Figure()
    for kw in narrative["keywords"]:
        vals = bot_trends_data["values"].get(kw, [])
        fig2.add_trace(go.Scatter(
            x=dates, y=vals, mode="lines", name=kw,
        ))
    fig2.update_layout(height=350, template="plotly_dark", hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Narrative proxy only — search interest, not actual bot trading volume.")


def _render_traders():
    data = compute_losing_traders()
    if not data["available"]:
        st.info("No losing-traders data found (data/losing_traders.csv).")
        return

    stats = data["stats"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tracked", stats["total"])
    c2.metric("Negative YTD", stats["negative"])
    c3.metric("Median YTD %", f"{stats['median_ytd']:+.1f}")
    c4.metric("Median drawdown %", f"{stats['median_drawdown']:.1f}")

    rows = data["rows"]
    names = [r["name"] for r in rows]
    ytd = [r["ytd_return_pct"] for r in rows]
    dd = [r["max_drawdown_pct"] for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names, x=ytd, orientation="h", name="YTD %",
        marker=dict(color=["#F44336" if v < 0 else "#4CAF50" for v in ytd]),
    ))
    fig.add_trace(go.Bar(
        y=names, x=dd, orientation="h", name="Max DD %",
        marker=dict(color="#9C27B0"),
    ))
    fig.update_layout(
        title="YTD return & max drawdown (worst at top)",
        height=420, template="plotly_dark", barmode="group",
        xaxis_title="%", yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Detail")
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    st.caption("Anonymous/aggregate proxy from public CTA & social-copy data. Named rows are public funds only.")
