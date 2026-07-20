import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from analysis.polymarket_curve import build_polymarket_curve, compute_divergence


def render_price_polymarket_tab(market_data, polymarket_curve):
    st.subheader("WTI Price & Polymarket Odds")

    if market_data is None:
        st.warning("Market data not available.")
        return

    wti = market_data.get("wti", {})
    dates = wti.get("dates", [])
    close = wti.get("close", [])

    if not dates or not close:
        st.warning("No WTI price data available.")
        return

    col_toggles = st.columns(3)
    with col_toggles[0]:
        show_daily = st.checkbox("Show Daily Polymarket", value=True, key="pm_daily")
    with col_toggles[1]:
        show_weekly = st.checkbox("Show Weekly Polymarket", value=True, key="pm_weekly")
    with col_toggles[2]:
        show_monthly = st.checkbox("Show Monthly Polymarket", value=True, key="pm_monthly")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=pd.to_datetime(dates),
            y=close,
            mode="lines",
            name="WTI Close",
            line=dict(color="white", width=2),
        ),
        secondary_y=False,
    )

    pm_daily = polymarket_curve.get("daily", {})
    pm_weekly = polymarket_curve.get("weekly", {})
    pm_monthly = polymarket_curve.get("monthly", {})

    today = pd.Timestamp.now().date()
    pm_dates = [today]

    if show_daily and pm_daily.get("avg_price") is not None:
        fig.add_trace(
            go.Scatter(
                x=pm_dates,
                y=[pm_daily["avg_price"] * 100],
                mode="markers",
                name=f"Daily PM ({pm_daily.get('direction', '')})",
                marker=dict(size=12, color="cyan", symbol="diamond"),
                yaxis="y2",
            ),
            secondary_y=True,
        )

    if show_weekly and pm_weekly.get("avg_price") is not None:
        fig.add_trace(
            go.Scatter(
                x=pm_dates,
                y=[pm_weekly["avg_price"] * 100],
                mode="markers",
                name=f"Weekly PM ({pm_weekly.get('direction', '')})",
                marker=dict(size=14, color="orange", symbol="triangle-up"),
                yaxis="y2",
            ),
            secondary_y=True,
        )

    if show_monthly and pm_monthly.get("avg_price") is not None:
        fig.add_trace(
            go.Scatter(
                x=pm_dates,
                y=[pm_monthly["avg_price"] * 100],
                mode="markers",
                name=f"Monthly PM ({pm_monthly.get('direction', '')})",
                marker=dict(size=14, color="lime", symbol="square"),
                yaxis="y2",
            ),
            secondary_y=True,
        )

    fig.update_layout(
        title="WTI Price with Polymarket Implied Probability Overlays",
        xaxis_title="Date",
        height=500,
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12),
    )
    fig.update_yaxes(title_text="WTI Price ($)", secondary_y=False)
    fig.update_yaxes(title_text="Polymarket Odds (%)", secondary_y=True, range=[0, 100])

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Polymarket Curve Summary")

    col1, col2, col3 = st.columns(3)
    with col1:
        daily_avg = pm_daily.get('avg_price')
        st.metric(
            "Daily Odds",
            f"{daily_avg * 100:.1f}%" if daily_avg else "N/A",
            delta=f"{pm_daily.get('direction', '').upper()}" if pm_daily.get('direction') else None,
        )
        st.caption(f"{pm_daily.get('count', 0)} markets | Vol: {pm_daily.get('volume', 0):,.0f}")
    with col2:
        weekly_avg = pm_weekly.get('avg_price')
        st.metric(
            "Weekly Odds",
            f"{weekly_avg * 100:.1f}%" if weekly_avg else "N/A",
            delta=f"{pm_weekly.get('direction', '').upper()}" if pm_weekly.get('direction') else None,
        )
        st.caption(f"{pm_weekly.get('count', 0)} markets | Vol: {pm_weekly.get('volume', 0):,.0f}")
    with col3:
        monthly_avg = pm_monthly.get('avg_price')
        st.metric(
            "Monthly Odds",
            f"{monthly_avg * 100:.1f}%" if monthly_avg else "N/A",
            delta=f"{pm_monthly.get('direction', '').upper()}" if pm_monthly.get('direction') else None,
        )
        st.caption(f"{pm_monthly.get('count', 0)} markets | Vol: {pm_monthly.get('volume', 0):,.0f}")

    st.markdown("---")
    st.subheader("Active Polymarket Oil Markets")

    raw_markets = (
        polymarket_curve.get("raw_daily", [])
        + polymarket_curve.get("raw_weekly", [])
        + polymarket_curve.get("raw_monthly", [])
        + polymarket_curve.get("raw_other", [])
    )

    if raw_markets:
        rows = []
        for m in raw_markets[:20]:
            title = m.get("question") or m.get("_event_title") or "Unknown"
            price = m.get("lastTradePrice") or m.get("bestBid")
            if price is None:
                outcome_prices = m.get("outcomePrices")
                if outcome_prices:
                    try:
                        prices = eval(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                        price = prices[0] if prices else None
                    except Exception:
                        price = None
            try:
                price_str = f"{float(price) * 100:.1f}%" if price is not None else "N/A"
            except (ValueError, TypeError):
                price_str = "N/A"
            volume = float(m.get("volumeNum") or m.get("_event_volume") or 0)
            end_date = str(m.get("_event_end", "") or m.get("endDate", ""))[:10]
            rows.append({"Market": title, "Odds": price_str, "End": end_date, "Volume": f"${volume:,.0f}"})

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No active Polymarket oil markets found. Try again later.")
