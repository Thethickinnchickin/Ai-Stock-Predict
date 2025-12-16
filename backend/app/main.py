import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from pydantic import BaseModel
import matplotlib.pyplot as plt
import io
from fastapi.responses import StreamingResponse
import pandas as pd

from .services.price_cache import price_cache
from app.graphql.schema import schema
from app.tasks.runner import start_background_tasks
from app.models.predictor import get_predictor

app = FastAPI(title="AI Stock Predictive Backend", description="Real-time GraphQL + WebSocket backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_background_tasks())
    print("🚀 Background tasks started")

class PredictRequest(BaseModel):
    symbol: str

@app.post("/predict")
async def predict_stock(body: PredictRequest):
    symbol = body.symbol.upper()
    await price_cache.connect()
    prices = await price_cache.get_daily_prices(symbol)
    volumes = await price_cache.get_daily_volumes(symbol)

    if not prices:
        raise HTTPException(status_code=400, detail=f"No history for {symbol}")

    model = get_predictor("xgb")
    model.train(prices, volumes)
    predicted = model.predict(prices, volumes, steps=10)
    high, low = model.predict_high_low(prices, volumes, steps=10)

    prediction = {"predicted": predicted, "high": high, "low": low}
    await price_cache.save_prediction(symbol, prediction)
    return prediction

@app.get("/predict/plot/{symbol}")
async def plot_predictions(symbol: str):
    symbol = symbol.upper()
    await price_cache.connect()

    prices, volumes, dates = await price_cache.get_daily_history(symbol)
    if not prices or not volumes or not dates:
        raise HTTPException(status_code=400, detail=f"No daily data loaded for {symbol}")

    model = get_predictor("xgb")
    model.train(prices, volumes)

    STEPS = 100  # <-- make this whatever horizon you want
    predicted = model.predict(prices, volumes, steps=STEPS)
    high, low = model.predict_high_low(prices, volumes, steps=STEPS)

    plt.figure(figsize=(12, 6))

    # --- Convert dates ---
    dates_dt = pd.to_datetime(dates)

    # --- Plot actual ---
    plt.plot(dates_dt, prices, label="Actual")

    # --- Future dates ---
    last_date = dates_dt[-1]
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=len(predicted),
        freq="D",
    )

    # --- Plot prediction ---
    plt.plot(future_dates, predicted, "--", label="Predicted")
    plt.fill_between(future_dates, high, low, alpha=0.3, label="High / Low")

    # =====================================================
    # ✅ THIS IS WHERE #4 GOES (date labels every 7 days)
    # =====================================================
    all_dates = pd.to_datetime(
        list(dates_dt) + list(future_dates)
    )

    tick_dates = all_dates[::7]
    plt.xticks(tick_dates, tick_dates.strftime("%Y-%m-%d"), rotation=45)
    # =====================================================

    plt.legend()
    plt.grid(True)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
