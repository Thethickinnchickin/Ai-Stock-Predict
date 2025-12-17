import asyncio
from datetime import datetime
from ..models.predictor import get_predictor
from ..services.price_cache import price_cache
from ..utils.logger import log
from ..models.model_store import model_store

logger = log


class PredictionService:
    def __init__(self, model_type: str = "xgb", steps: int = 5):
        self.model_type = model_type
        self.model = get_predictor(model_type)
        self.steps = steps
        self._subscribers: dict[str, asyncio.Queue] = {}

    async def predict_next(self, symbol: str, steps: int = None):
        steps = steps or self.steps
        history = await price_cache.get_history(symbol)

        if not history:
            return []

        model = model_store.get(symbol)
        if not model:
            return []

        return model.predict(history, steps)

    async def broadcast_prediction(self, symbol: str):
        predictions = await self.predict_next(symbol)
        if not predictions:
            return

        next_price = float(predictions[0])
        event = {
            "symbol": symbol,
            "prediction": next_price,
            "timestamp": datetime.utcnow(),
        }

        await price_cache.save_prediction(symbol, next_price)

        for q_symbol, queue in self._subscribers.items():
            if q_symbol == symbol:
                await queue.put(event)

    async def periodic_prediction_loop(self, interval: int = 10):
        while True:
            try:
                symbols = await price_cache.get_tracked_symbols()
                await asyncio.gather(*(self.broadcast_prediction(s) for s in symbols))
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
                await asyncio.sleep(interval)

    async def run_prediction(self, symbol: str):
        history = await price_cache.get_history(symbol)
        model = model_store.get(symbol)

        if not history or not model:
            return None

        preds = model.predict(history, steps=1)
        if not preds:
            return None

        prediction_obj = {
            "symbol": symbol,
            "predicted_price": preds[0],
            "confidence": 0.7,
        }

        await price_cache.save_prediction(symbol, prediction_obj)
        await price_cache.save_prediction_entry(prediction_obj)
        return prediction_obj

    async def train_models(self):
        symbols = await price_cache.get_tracked_symbols()
        for symbol in symbols:
            history = await price_cache.get_history(symbol)
            if not history:
                continue

            model = model_store.get(symbol)
            if not model:
                model = get_predictor(self.model_type)
                model_store.set(symbol, model)

            model.train(history)


# global instance
prediction_service = PredictionService()
