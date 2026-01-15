import asyncio
import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from strawberry.fastapi import GraphQLRouter

from .tasks.runner import start_background_tasks
from .models.predictor import get_predictor
from .graphql.schema import schema
from .models.registry import model_registry
from .services.price_cache import price_cache
from .services.prediction_service import prediction_service
from .models.predictor import predictor
from .config.settings import settings
from .utils.logger import log

_START_TIME = time.time()

# -----------------------------
# Initialize FastAPI app
# -----------------------------
app = FastAPI(
    title="AI Stock Predictive Backend",
    description="Real-time GraphQL + WebSocket backend",
    version="1.0.0",
)

# -----------------------------
# Enable CORS for all origins
# This allows frontend clients from any domain to access the API
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP methods
    allow_headers=["*"],  # allow all headers
)

# -----------------------------
# Startup Event: runs when the server starts
# -----------------------------
@app.on_event("startup")
async def on_startup():
    """
    1. Launches background tasks for:
       - Fetching live prices
       - Monitoring alerts
       - Periodic model training
    2. Loads/trains the global XGBoost model via model_registry
    """
    # Start background tasks in an asyncio task (non-blocking)
    asyncio.create_task(start_background_tasks())
    print("🚀 Background tasks started")

    # NOTE: Duplicate call—should remove one to avoid running tasks twice
    asyncio.create_task(start_background_tasks())

    # Load the global model into memory (train if not already trained)
    await model_registry.load()
    print("✅ Global XGBoost model trained")

# -----------------------------
# Mount GraphQL API at /graphql
# This exposes queries like predict_stock(symbol)
# -----------------------------
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

_rate_buckets = defaultdict(deque)


@app.middleware("http")
async def rate_limit_and_log(request: Request, call_next):
    path = request.url.path
    if path.startswith("/ws"):
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _rate_buckets[ip]
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= settings.RATE_LIMIT_MAX:
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
    bucket.append(now)

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info(f"{ip} {request.method} {path} {response.status_code} {duration_ms}ms")
    return response


@app.get("/health")
async def health():
    """System health summary for UI and monitoring."""
    await price_cache.connect()
    redis_ok = False
    try:
        pong = await price_cache.redis.ping()
        redis_ok = bool(pong)
    except Exception:
        redis_ok = False

    now = datetime.now(timezone.utc)
    symbols = []
    for symbol in settings.SYMBOLS:
        price = await price_cache.get_live_price(symbol)
        ts = await price_cache.get_live_timestamp(symbol)
        age_seconds = None
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                age_seconds = int((now - dt).total_seconds())
            except ValueError:
                age_seconds = None
        symbols.append(
            {
                "symbol": symbol,
                "price": price,
                "last_update": ts,
                "age_seconds": age_seconds,
            }
        )

    model_meta_path = os.path.join(settings.MODEL_DIR, settings.MODEL_META_FILE)
    model_trained_at = None
    if os.path.exists(model_meta_path):
        try:
            with open(model_meta_path, "r", encoding="utf-8") as handle:
                meta = json.load(handle)
                model_trained_at = meta.get("trained_at")
        except Exception:
            model_trained_at = None

    backtest_last_run = None
    if os.path.exists(settings.BACKTEST_LOG_PATH):
        try:
            with open(settings.BACKTEST_LOG_PATH, "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        backtest_last_run = line.split(" | ", 1)[0].strip()
        except Exception:
            backtest_last_run = None

    return {
        "ok": True,
        "server_time": now.isoformat(),
        "redis": {"ok": redis_ok},
        "symbols": symbols,
        "model": {"trained_at": model_trained_at},
        "backtest": {"last_run": backtest_last_run},
    }


@app.get("/status")
async def status():
    now = datetime.now(timezone.utc)
    uptime_seconds = int(time.time() - _START_TIME)
    symbols = []
    for symbol in settings.SYMBOLS:
        ts = await price_cache.get_live_timestamp(symbol)
        age_seconds = None
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                age_seconds = int((now - dt).total_seconds())
            except ValueError:
                age_seconds = None
        symbols.append(
            {
                "symbol": symbol,
                "last_update": ts,
                "age_seconds": age_seconds,
            }
        )

    backtest_last_run = None
    if os.path.exists(settings.BACKTEST_LOG_PATH):
        try:
            with open(settings.BACKTEST_LOG_PATH, "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        backtest_last_run = line.split(" | ", 1)[0].strip()
        except Exception:
            backtest_last_run = None

    return {
        "uptime_seconds": uptime_seconds,
        "server_time": now.isoformat(),
        "backtest_last_run": backtest_last_run,
        "symbols": symbols,
    }


@app.websocket("/ws/live")
async def live_prices_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            snapshot = []
            for symbol in settings.SYMBOLS:
                price = await price_cache.get_live_price(symbol)
                change = await price_cache.get_live_change_percent(symbol)
                volume = await price_cache.get_live_volume(symbol)
                ts = await price_cache.get_live_timestamp(symbol)
                snapshot.append(
                    {
                        "symbol": symbol,
                        "price": price,
                        "change_percent": change,
                        "volume": volume,
                        "last_update": ts,
                    }
                )
            await websocket.send_text(json.dumps({"type": "live_prices", "data": snapshot}))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.close()


@app.websocket("/ws/predict/{symbol}")
async def prediction_socket(websocket: WebSocket, symbol: str):
    await websocket.accept()
    sym = symbol.upper()
    try:
        while True:
            prices, volumes, dates = await price_cache.get_hourly_history(sym)
            if not prices or not volumes:
                await websocket.send_text(json.dumps({"error": "No hourly data loaded"}))
                await asyncio.sleep(settings.PREDICT_INTERVAL)
                continue

            display_window = max(24, predictor.look_back)
            display_prices = prices[-display_window:]
            display_dates = dates[-display_window:]

            predicted = await prediction_service.predict_next_with_dates(sym, steps=6)

            payload = {
                "actual": {"dates": display_dates, "prices": display_prices},
                "predicted": predicted,
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(settings.PREDICT_INTERVAL)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.close()
