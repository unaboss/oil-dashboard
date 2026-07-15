# Oil Dashboard

WTI Crude Oil swing-trading dashboard built with Streamlit.

## Features

- Price & flows, curve divergence, CFTC COT positioning, EIA inventories
- 6-signal confluence scoring for fake-move detection
- Signal audit with hit-rate tracking
- Trade calendar with monthly heatmap
- Research: Trump event study, bot-mention proxy, losing-trader contrarian data

## Setup

### Prerequisites
- Python 3.9+
- EIA API key (free) from https://www.eia.gov/opendata/

### Install

```
git clone https://github.com/YOUR_USERNAME/oil-dashboard.git
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
