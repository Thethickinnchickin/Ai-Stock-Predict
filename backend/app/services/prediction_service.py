# app/services/prediction_service.py

import asyncio
from datetime import datetime, timedelta
from ..services.price_cache import price_cache
from ..utils.logger import log
from ..models.registry import model_registry
from app.models.predictor import predictor

logger = log

# -----------------------------
# Global-model prediction service
# -----------------------------
class PredictionService:
    """
    Provides predictions using a single shared XGBoost model trained across all symbols.
    Handles:
      - Core prediction logic
      - Generating predictions with future dates
      - High/low price bands for visualization or alerts
    """

    def __init__(self, steps: int = 5):
        """
        Args:
            steps (int): Number of future steps (days) to predict by default
        """
        self.steps = steps
        # Dictionary of asyncio queues for subscribers (future feature for real-time updates)
        self._subscribers: dict[str, asyncio.Queue] = {}

    # -----------------------------
    # Core prediction method
    # -----------------------------
    async def predict_next(self, symbol: str, steps: int | None = None):
        """
        Predict the next `steps` future prices for a given symbol.
        Uses the global XGBoost model from model_registry.

        Returns:
            List[float]: Predicted prices
        """
        model = model_registry.get()
        if not model or not model.trained:
            logger.warning("Model not ready — skipping prediction")
            return []

        # Fetch historical prices and volumes from cache
        prices, volumes, _ = await price_cache.get_daily_history(symbol)
        if not prices or not volumes:
            logger.warning(f"No history for {symbol}")
            return []

        try:
            return model.predict(prices=prices, volumes=volumes, steps=steps or self.steps)
        except Exception as e:
            logger.error(f"Prediction failed for {symbol}: {e}")
            return []

    # -----------------------------
    # Prediction with future dates and high/low bands
    # -----------------------------
    async def predict_next_with_dates(self, symbol: str, steps: int | None = None):
        """
        Predict future prices and generate corresponding future trading dates.
        Also computes high/low bands for each predicted price (useful for visualization).

        Returns:
            dict: {
                "dates": list of predicted dates (str),
                "prices": predicted prices,
                "high": upper price band,
                "low": lower price band
            }
        """
        steps = steps or self.steps
        preds = await self.predict_next(symbol, steps=steps)
        if not preds:
            return {"dates": [], "prices": [], "high": [], "low": []}

        # Get last actual trading date from cache
        _, _, dates = await price_cache.get_daily_history(symbol)
        last_date_str = dates[-1]
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")

        # Generate future trading dates, skipping weekends
        predicted_dates = []
        current_date = last_date
        while len(predicted_dates) < len(preds):
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:  # Mon-Fri only
                predicted_dates.append(current_date.strftime("%Y-%m-%d"))

        # Compute high/low bands based on historical volatility
        prices, volumes, _ = await price_cache.get_daily_history(symbol)
        high, low = predictor.predict_high_low(prices, volumes, steps=steps)

        return {
            "dates": predicted_dates,
            "prices": preds,
            "high": high,
            "low": low
        }

# -----------------------------
# Global instance to be used throughout the app
# -----------------------------
prediction_service = PredictionService()
