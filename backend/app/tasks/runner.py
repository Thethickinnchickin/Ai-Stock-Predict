import asyncio
from ..utils.logger import log
from ..services.fetcher import fetch_live_prices_loop, PriceFetcher
from ..services.alert_service import alert_monitor_loop
from ..services.prediction_service import PredictionService
from ..config.settings import settings
from ..models.predictor import predictor
from ..models.registry import model_registry

# -----------------------------
# Global prediction service instance
# -----------------------------
predictor_service = PredictionService()

# -----------------------------
# Preload historical data
# -----------------------------
async def preload_all_history():
    """
    Fetches and caches daily historical prices for all symbols
    listed in settings.SYMBOLS.
    This ensures the model has sufficient data on startup.
    """
    fetcher = PriceFetcher()
    log.info("📦 Preloading daily history...")

    for symbol in settings.SYMBOLS:
        try:
            await fetcher.preload_daily_history(symbol)
        except Exception as e:
            log.error(f"❌ Failed to preload {symbol}: {e}")

    log.info("✅ Daily history preload complete")


# -----------------------------
# Periodic model training loop
# -----------------------------
async def model_training_loop():
    """
    Continuously retrains the global XGBoost model every hour.
    Uses a lock to prevent concurrent access to the model during training.
    On failure, waits 5 minutes before retrying.
    """
    while True:
        try:
            async with model_registry.lock:
                await model_registry.model.train()
            await asyncio.sleep(3600)  # wait 1 hour before next training
        except Exception as e:
            log.error(f"Training failed: {e}")
            await asyncio.sleep(300)  # wait 5 minutes before retrying


# -----------------------------
# Start all background tasks
# -----------------------------
async def start_background_tasks():
    """
    Launches all essential background tasks in parallel:
      1. Preload historical prices (blocking)
      2. Fetch live prices continuously
      3. Retrain model periodically
      4. Monitor alerts in real-time
    """
    log.info("🚀 Starting background task manager...")

    # Preload history first to ensure model has data
    await preload_all_history()

    # Wrap loops in a task wrapper for error handling & automatic restart
    tasks = [
        asyncio.create_task(task_wrapper(fetch_live_prices_loop, "Price Fetcher")),
        asyncio.create_task(task_wrapper(model_training_loop, "Model Trainer")),
        asyncio.create_task(task_wrapper(alert_monitor_loop, "Alert Monitor")),
    ]

    # Run all tasks concurrently and wait for them indefinitely
    await asyncio.gather(*tasks)


# -----------------------------
# Task wrapper for robust looping
# -----------------------------
async def task_wrapper(coro, name: str):
    """
    Wraps a coroutine with:
      - Logging on start
      - Automatic restart on exception
      - Graceful handling of cancellation
    """
    while True:
        try:
            log.info(f"🔥 Starting: {name}")
            await coro()
        except asyncio.CancelledError:
            log.warn(f"⚠️ {name} cancelled.")
            break
        except Exception as e:
            log.error(f"❌ {name} crashed: {e}")
            await asyncio.sleep(5)  # small delay before restarting
            log.info(f"🔄 Restarting {name}...")
