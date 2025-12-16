import asyncio
from ..utils.logger import log
from ..services.fetcher import fetch_live_prices_loop, PriceFetcher
from ..services.alert_service import alert_monitor_loop
from ..services.prediction_service import PredictionService
from ..config.settings import settings

predictor_service = PredictionService(model_type="lstm")


async def preload_all_history():
    """
    Preload daily history for all tracked symbols on startup.
    """
    fetcher = PriceFetcher()
    log.info("📦 Preloading daily history...")

    for symbol in settings.SYMBOLS:
        try:
            await fetcher.preload_daily_history(symbol)
        except Exception as e:
            log.error(f"❌ Failed to preload {symbol}: {e}")

    log.info("✅ Daily history preload complete")


async def model_training_loop():
    log.info("🧠 Model training loop started")

    while True:
        try:
            await predictor_service.train_models()
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            log.warn("⚠️ Model training loop cancelled.")
            break
        except Exception as e:
            log.error(f"❌ Model training failed: {e}")
            await asyncio.sleep(60)


async def start_background_tasks():
    log.info("🚀 Starting background task manager...")

    # 🔒 Preload BEFORE loops
    await preload_all_history()

    tasks = [
        asyncio.create_task(task_wrapper(fetch_live_prices_loop, "Price Fetcher")),
        asyncio.create_task(task_wrapper(model_training_loop, "Model Trainer")),
        asyncio.create_task(task_wrapper(alert_monitor_loop, "Alert Monitor")),
    ]

    await asyncio.gather(*tasks)


async def task_wrapper(coro, name: str):
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
