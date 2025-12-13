import asyncio
from ..utils.logger import log
from ..services.fetcher import fetch_live_prices_loop
from ..services.alert_service import alert_monitor_loop
from ..services.prediction_service import PredictionService

# Initialize PredictionService (LSTM per-symbol models)
predictor_service = PredictionService(model_type="lstm")


async def model_training_loop():
    """
    Periodically trains models for all tracked symbols.
    Runs in the background and NEVER blocks API requests.
    """
    log.info("🧠 Model training loop started")

    while True:
        try:
            await predictor_service.train_models()
            await asyncio.sleep(300)  # train every 5 minutes
        except asyncio.CancelledError:
            log.warn("⚠️ Model training loop cancelled.")
            break
        except Exception as e:
            log.error(f"❌ Model training failed: {e}")
            await asyncio.sleep(60)


async def start_background_tasks():
    """
    Starts all long-running async background tasks.
    Each runs forever but inside safe try/except loops.
    """

    log.info("🚀 Starting background task manager...")

    tasks = [
        asyncio.create_task(
            task_wrapper(fetch_live_prices_loop, "Price Fetcher")
        ),
        asyncio.create_task(
            task_wrapper(model_training_loop, "Model Trainer")
        ),
        asyncio.create_task(
            task_wrapper(alert_monitor_loop, "Alert Monitor")
        ),
    ]

    # Wait forever until any task fails (should rarely happen)
    await asyncio.gather(*tasks)


async def task_wrapper(coro, name: str):
    """
    Wraps each background loop so a failure doesn’t kill the entire backend.
    Automatically restarts the task after 5 seconds.
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
            await asyncio.sleep(5)
            log.info(f"🔄 Restarting {name}...")
