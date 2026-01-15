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
