# app/main.py

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from pydantic import BaseModel

from .services.price_cache import price_cache
from .services.prediction_service import prediction_service
from app.graphql.schema import schema
from app.tasks.runner import start_background_tasks
from app.models.model_store import model_store
from app.models.predictor import get_predictor


app = FastAPI(
    title="AI Stock Predictive Backend",
    description="Real-time GraphQL + WebSocket backend for stock/crypto predictions.",
    version="1.0.0",
)

# ---------------------------
# CORS
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# GraphQL
# ---------------------------
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

# ---------------------------
# Background tasks
# ---------------------------
@app.on_event("startup")
async def on_startup():
    # Starts ALL background loops (fetcher, trainer, alerts)
    asyncio.create_task(start_background_tasks())
    print("🚀 Background tasks started")

# ---------------------------
# Health check
# ---------------------------
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "AI Stock Backend Running",
        "graphql": "/graphql",
    }

# ---------------------------
# API: Latest prices
# ---------------------------
@app.get("/api/prices")
async def get_prices():
    await price_cache.connect()
    symbols = await price_cache.get_tracked_symbols()
    data = {}

    for symbol in symbols:
        price = await price_cache.get_price(symbol)
        if price is not None:
            data[symbol] = price

    return data

# ---------------------------
# API: Latest predictions
# ---------------------------
@app.get("/api/predictions")
async def get_predictions():
    await price_cache.connect()
    symbols = await price_cache.get_tracked_symbols()
    data = {}

    for symbol in symbols:
        pred = await price_cache.get_prediction(symbol)
        if pred is not None:
            data[symbol] = pred

    return data

# ======================================================
# 🚀 PREDICTION ROUTES
# ======================================================

class PredictRequest(BaseModel):
    symbol: str

# ---------------------------
# POST /predict — run immediate prediction
# ---------------------------
@app.post("/predict")
async def predict_stock(body: PredictRequest):
    symbol = body.symbol.upper()
    await price_cache.connect()

    try:
        prediction = await prediction_service.run_prediction(symbol)

        if prediction is None:
            raise HTTPException(
                status_code=400,
                detail=f"No history for {symbol}, cannot predict"
            )

        await price_cache.save_prediction(symbol, prediction)
        return prediction

    except Exception as e:
        print(f"[ERROR] /predict failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# GET /recent — last 10 predictions
# ---------------------------
@app.get("/recent")
async def get_recent_predictions():
    await price_cache.connect()
    history = await price_cache.get_recent_predictions(limit=10)
    return history

# ---------------------------
# GET /alerts — active alerts
# ---------------------------
@app.get("/alerts")
async def get_alerts():
    await price_cache.connect()
    try:
        alerts = await price_cache.get_alerts()
        return alerts or []
    except Exception as e:
        print("ERROR reading alerts:", e)
        return []

# ======================================================
# 📈 PROBABILITY ROUTE
# ======================================================

class ProbabilityRequest(BaseModel):
    symbol: str           # Stock symbol, e.g., "AAPL"
    target_price: float   # The price the user wants to check probability for
    days_ahead: int = 5   # How many days into the future to simulate
    simulations: int = 100
    
@app.post("/predict/probability")
async def predict_probability(req: ProbabilityRequest):
    symbol = req.symbol.upper()
    await price_cache.connect()

    history = await price_cache.get_history(symbol)
    if not history:
        raise HTTPException(status_code=400, detail=f"No history for {symbol}")

    model = model_store.get(symbol)
    if not model:
        # Auto-create & train
        model = get_predictor("lstm")
        model.train(history)
        model_store.set(symbol, model)

    if not hasattr(model, "probability_target"):
        raise HTTPException(status_code=400, detail="Probability not implemented for this model type")

    prob = model.probability_target(
        history=history,
        target_price=req.target_price,
        days_ahead=req.days_ahead,
        simulations=req.simulations,
        noise_std=1.0,
    )

    return {
        "symbol": symbol,
        "target_price": req.target_price,
        "days_ahead": req.days_ahead,
        "probability": round(float(prob), 4),
    }
