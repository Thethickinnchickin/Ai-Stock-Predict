import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from .tasks.runner import start_background_tasks
from .models.predictor import get_predictor
from .graphql.schema import schema

app = FastAPI(
    title="AI Stock Predictive Backend",
    description="Real-time GraphQL + WebSocket backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Startup: preload history & train global model
# -----------------------------
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_background_tasks())
    print("🚀 Background tasks started")

    global predictor
    predictor = get_predictor("xgb")
    await predictor.train()
    print("✅ Global XGBoost model trained")

# -----------------------------
# Mount GraphQL
# -----------------------------
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

# graphql_app = GraphQLRouter(schema)
# app.include_router(graphql_app, prefix="/graphql")

# -----------------------------
# Startup: preload history & train global model
# -----------------------------
# @app.on_event("startup")
# async def on_startup():
#     asyncio.create_task(start_background_tasks())
#     print("🚀 Background tasks started")

#     # Train global XGBoost across all symbols
#     global predictor
#     predictor = get_predictor("xgb")
#     await predictor.train()
#     print("✅ Global XGBoost model trained")


# # -----------------------------
# # Request model
# # -----------------------------
# class PredictRequest(BaseModel):
#     symbol: str


# -----------------------------
# Predict single symbol (next 10 days)
# -----------------------------
# @app.post("/predict")
# async def predict_stock(body: PredictRequest):
#     symbol = body.symbol.upper()
#     await price_cache.connect()

#     prices = await price_cache.get_daily_prices(symbol)
#     volumes = await price_cache.get_daily_volumes(symbol)

#     if not prices or not volumes:
#         raise HTTPException(status_code=400, detail=f"No history for {symbol}")

#     predicted = predictor.predict(prices, volumes, steps=10)
#     high, low = predictor.predict_high_low(prices, volumes, steps=10)

#     prediction = {"predicted": predicted, "high": high, "low": low}
#     await price_cache.save_prediction(symbol, prediction)
#     return prediction


# # -----------------------------
# # Get prediction + actual data JSON (for Plotly)
# # -----------------------------
# @app.get("/predict/data/{symbol}")
# async def predict_data(symbol: str):
#     symbol = symbol.upper()
#     await price_cache.connect()

#     # Fetch full historical data
#     prices, volumes, dates = await price_cache.get_daily_history(symbol)
#     if not prices or not volumes or not dates:
#         raise HTTPException(status_code=400, detail="No daily data loaded")

#     # -----------------------------
#     # Parameters
#     # -----------------------------
#     DISPLAY_WINDOW = 7  # show last 7 days of actual data
#     STEPS = 5           # predict 5 days ahead

#     # Ensure we have enough data for the model's look_back
#     if len(prices) < predictor.look_back:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Not enough data for prediction (need at least {predictor.look_back} days)"
#         )

#     # -----------------------------
#     # Predict with full historical data (keep look_back intact)
#     # -----------------------------
#     predicted = predictor.predict(prices, volumes, steps=STEPS)
#     high, low = predictor.predict_high_low(prices, volumes, steps=STEPS)

#     # -----------------------------
#     # Slice only last DISPLAY_WINDOW days for actual data
#     # -----------------------------
#     display_prices = prices[-DISPLAY_WINDOW:]
#     display_dates = dates[-DISPLAY_WINDOW:]

#     last_date = pd.to_datetime(display_dates[-1])
#     future_dates = pd.date_range(
#         start=last_date + pd.Timedelta(days=1),
#         periods=len(predicted),
#         freq="D",
#     )

#     return {
#         "actual": {
#             "dates": display_dates,
#             "prices": display_prices,
#         },
#         "predicted": {
#             "dates": future_dates.strftime("%Y-%m-%d").tolist(),
#             "prices": predicted,
#             "high": high,
#             "low": low,
#         },
#     }

# # -----------------------------
# # Plot predictions (PNG)
# # -----------------------------
# @app.get("/predict/plot/{symbol}")
# async def plot_predictions(symbol: str):
#     symbol = symbol.upper()
#     await price_cache.connect()

#     prices, volumes, dates = await price_cache.get_daily_history(symbol)
#     if not prices or not volumes or not dates:
#         raise HTTPException(status_code=400, detail=f"No daily data loaded for {symbol}")

#     STEPS = 100
#     predicted = predictor.predict(prices, volumes, steps=STEPS)
#     high, low = predictor.predict_high_low(prices, volumes, steps=STEPS)

#     plt.figure(figsize=(12, 6))

#     dates_dt = pd.to_datetime(dates)
#     plt.plot(dates_dt, prices, label="Actual")

#     last_date = dates_dt[-1]
#     future_dates = pd.date_range(
#         start=last_date + pd.Timedelta(days=1),
#         periods=len(predicted),
#         freq="D",
#     )

#     plt.plot(future_dates, predicted, "--", label="Predicted")
#     plt.fill_between(future_dates, high, low, alpha=0.3, label="High / Low")

#     # Date ticks every 7 days
#     all_dates = pd.to_datetime(list(dates_dt) + list(future_dates))
#     tick_dates = all_dates[::7]
#     plt.xticks(tick_dates, tick_dates.strftime("%Y-%m-%d"), rotation=45)

#     plt.legend()
#     plt.grid(True)

#     buf = io.BytesIO()
#     plt.savefig(buf, format="png", bbox_inches="tight")
#     plt.close()
#     buf.seek(0)

#     return StreamingResponse(buf, media_type="image/png")
