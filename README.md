# AI Stock Predict

[![CI](https://github.com/jerryreiley/Ai-Stock-Predict/actions/workflows/ci.yml/badge.svg)](https://github.com/jerryreiley/Ai-Stock-Predict/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jerryreiley/Ai-Stock-Predict/branch/main/graph/badge.svg)](https://codecov.io/gh/jerryreiley/Ai-Stock-Predict)

AI Stock Predict is a full-stack project that demonstrates how to build a
real-time data pipeline, serve ML-backed predictions, and present them in a
modern web UI. It is designed as a portfolio piece to showcase system design,
backend async workflows, data ingestion, and frontend visualization.

## Why This Project
- Shows end-to-end ownership: data ingestion, model inference, API design, and UI
- Emphasizes async systems and background task orchestration
- Demonstrates GraphQL integration with a modern React frontend
- Highlights pragmatic ML usage for time-series forecasting

## Highlights
- Live price ingestion (Polygon.io) and historical data (yfinance)
- GraphQL API serving actual + predicted series
- Background tasks for data refresh, alerts, and model training
- Interactive Plotly charts in a Next.js UI

## System Overview
- FastAPI app starts background loops for live prices, retraining, and alerts
- Redis stores live prices, historical candles, predictions, and alerts
- GraphQL query `predictStock(symbol)` returns actual + predicted series
- Next.js renders an interactive chart and symbol selector

## Architecture Diagram
```
                 +---------------------------+
                 |        Next.js UI         |
                 |  /predict, /results, /... |
                 +-------------+-------------+
                               |
                               | HTTPS (Nginx reverse proxy)
                               v
                 +---------------------------+
                 |         FastAPI           |
                 |  GraphQL + WebSocket API  |
                 +-------------+-------------+
                               |
           +-------------------+-------------------+
           |                                       |
           v                                       v
  +---------------------+               +---------------------+
  |        Redis        |               |    Data Sources     |
  | live prices/history |               | Polygon + yfinance  |
  +---------------------+               +---------------------+
                               |
                               v
                     +---------------------+
                     |   XGBoost Model     |
                     | hourly training     |
                     +---------------------+

## Tech Stack
- Backend: FastAPI, Strawberry GraphQL, Redis, asyncio
- ML: scikit-learn, pandas, numpy
- Frontend: Next.js (App Router), React, Plotly

## Repo Layout
- `backend/` FastAPI + Strawberry GraphQL backend
- `frontend/` Next.js app (App Router)

## Prerequisites
- Python 3.10+ and pip
- Node.js 18+ and npm
- Redis running locally
- Optional: Polygon.io API key for live prices

## Quick Start

### 1) Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# optional, for live prices
export POLYGON_API_KEY=your_key_here

uvicorn app.main:app --reload --port 8000
```

The GraphQL endpoint is available at `http://localhost:8000/graphql`.

### 2) Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

Note: the frontend currently posts to `/api/graphql`. You can either add a
Next.js rewrite/proxy or update the fetch call to point at
`http://localhost:8000/graphql`.

## Configuration
Backend settings are defined in `backend/app/config/settings.py` and can be
overridden via a `.env` file. Common options:
- `SYMBOLS` list of tickers to track
- `FETCH_INTERVAL`, `PREDICT_INTERVAL`, `ALERT_INTERVAL`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- `POLYGON_API_KEY`

## GraphQL Example
```graphql
query StockPrediction($symbol: String!) {
  predictStock(symbol: $symbol) {
    actual { dates prices }
    predicted { dates prices high low }
  }
}
```

## Tests
```bash
cd backend
pytest
```

## Future Improvements
- Add REST endpoints alongside GraphQL for broader client support
- Improve model evaluation metrics and tracking
- Persist trained models and add versioning

## Deployment Guide (macOS + Nginx + launchd)
This project can be deployed locally behind Nginx with HTTPS and a launchd service
for the backend. Example setup:

1) Backend service (launchd)
- Ensure your `com.aistock.backend.plist` runs gunicorn/uvicorn from the venv
- Logs should go to `/tmp/aistock-backend.log` and `/tmp/aistock-backend.err`
- Start/restart:
```bash
launchctl kickstart -k gui/$(id -u)/com.aistock.backend
```

2) Nginx reverse proxy
- Terminate TLS on Nginx and proxy to Next.js + FastAPI
- Ensure `/api/` includes WebSocket upgrade headers
- Reload after config changes:
```bash
sudo nginx -s reload
```

3) Frontend
- Run Next.js on `http://127.0.0.1:3000`
- Backend on `http://127.0.0.1:8000`
- Nginx serves `https://localhost`

## Explainable ML (Interpretability)
Current interpretability approach:
- Feature set includes RSI, MACD, rolling volatility, volume z-score, and market context (SPY/QQQ/VIX)
- Backtests track MAE and directional accuracy over time

Recommended additions for explainability:
- Use XGBoost `feature_importances_` to publish top drivers
- Log feature importances with each nightly backtest
- Add a small UI panel summarizing the top 5 features
