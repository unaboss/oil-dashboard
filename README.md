# Oil Dashboard

A WTI Crude Oil swing-trading dashboard built with Streamlit — an oil-market
analytics platform that connects geopolitics to markets.

## Features

- Price & flows, curve divergence, CFTC COT positioning, EIA inventories
- 6-signal confluence scoring for fake-move detection
- Signal audit with hit-rate tracking
- Trade calendar with monthly heatmap
- Research: Trump event study, bot-mention proxy, losing-trader contrarian data

## What this demonstrates

- Multi-source data engineering: Yahoo Finance, EIA API, CFTC HTML scrape, Google
  Trends and AAA retail prices combined into one pipeline
- Analytical trading logic: a confluence model that turns raw market signals into
  scored trade setups with audit trails
- A complete Streamlit product: config, data layer, analysis and UI in a small,
  runnable package

Companion apps (`oil_polymarket/`, `oil_polymarket_bets/`) cover Polymarket oil-contract bets.

## Setup

### Prerequisites
- Python 3.9+
- EIA API key (free) from https://www.eia.gov/opendata/

### Install

```
git clone https://github.com/unaboss/oil-dashboard.git
cd oil-dashboard
pip install -r oil_dashboard/requirements.txt
```

### Configure

Create a `.env` file inside `oil_dashboard/` with your EIA key:

```
EIA_API_KEY=your_actual_key_here
```

### Run

```
streamlit run oil_dashboard/app.py
```

## Data Sources

| Source | Method | Data |
|---|---|---|
| Yahoo Finance | yfinance | WTI, Brent, RBOB, OVX, DXY prices |
| EIA API | requests | Crude, gasoline, distillate stocks |
| CFTC | HTML scrape | Managed Money COT positioning |
| Google Trends | pytrends | Sentiment and bot-mention proxies |
| AAA | HTML scrape | US retail gas price |
