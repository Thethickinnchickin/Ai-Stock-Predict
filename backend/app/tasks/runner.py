import asyncio
import os
from datetime import datetime, timedelta
from ..utils.logger import log
from ..services.fetcher import fetch_live_prices_loop, PriceFetcher
from ..services.alert_service import alert_monitor_loop
from ..services.prediction_service import PredictionService
from ..config.settings import settings
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
    Fetches and caches hourly historical prices for all symbols
    listed in settings.SYMBOLS.
    This ensures the model has sufficient data on startup.
    """
    fetcher = PriceFetcher()
    log.info("📦 Preloading hourly history...")

    for symbol in settings.SYMBOLS:
        try:
            await fetcher.preload_hourly_history(symbol, period=settings.HOURLY_HISTORY_PERIOD)
        except Exception as e:
            log.error(f"❌ Failed to preload {symbol}: {e}")

    log.info("✅ Hourly history preload complete")


# -----------------------------
# Periodic hourly history refresh
# -----------------------------
async def hourly_history_refresh_loop():
    """
    Periodically refreshes hourly historical prices for all symbols.
    """
    fetcher = PriceFetcher()
    while True:
        try:
            for symbol in settings.SYMBOLS:
                await fetcher.preload_hourly_history(symbol, period=settings.HOURLY_HISTORY_PERIOD)
            await asyncio.sleep(settings.HOURLY_REFRESH_INTERVAL)
        except Exception as e:
            log.error(f"Hourly history refresh failed: {e}")
            await asyncio.sleep(300)


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
# Nightly backtest loop
# -----------------------------
async def nightly_backtest_loop():
    """
    Runs a backtest once per day at the configured local hour.
    Logs results to a file for review.
    """
    log_path = settings.BACKTEST_LOG_PATH
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    while True:
        try:
            now = datetime.now()
            run_time = now.replace(hour=settings.BACKTEST_RUN_HOUR, minute=0, second=0, microsecond=0)
            if run_time <= now:
                run_time += timedelta(days=1)
            await asyncio.sleep((run_time - now).total_seconds())

            model = model_registry.get()
            if not model:
                await model_registry.load()
                model = model_registry.get()

            results = await model.backtest(val_size=settings.BACKTEST_VAL_SIZE)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if results:
                line = (
                    f"{timestamp} | MAE_model={results['mae_model']:.6f} "
                    f"MAE_baseline={results['mae_baseline']:.6f} "
                    f"DirAcc_model={results['directional_accuracy_model']:.3f} "
                    f"DirAcc_baseline={results['directional_accuracy_baseline']:.3f} "
                    f"Val={results['validation_size']}\n"
                )
            else:
                line = f"{timestamp} | No backtest results (insufficient data)\n"

            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(line)
        except Exception as e:
            log.error(f"Nightly backtest failed: {e}")
            await asyncio.sleep(300)


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
        asyncio.create_task(task_wrapper(hourly_history_refresh_loop, "Hourly History Refresh")),
        asyncio.create_task(task_wrapper(model_training_loop, "Model Trainer")),
        asyncio.create_task(task_wrapper(alert_monitor_loop, "Alert Monitor")),
        asyncio.create_task(task_wrapper(nightly_backtest_loop, "Nightly Backtest")),
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
