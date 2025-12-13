# app/services/alert_service.py

from typing import Callable, Dict
import asyncio
import numpy as np
from ..utils.logger import log  # use the existing logger object
from .price_cache import PriceCache

logger = log  # optional alias
price_cache = PriceCache()  # shared cache instance


class AlertService:
    def __init__(self):
        self.thresholds: Dict[str, float] = {}       # e.g. {"AAPL": 180.0}
        self.subscribers: Dict[str, Callable] = {}   # userId -> callback fn

    def set_threshold(self, symbol: str, price: float):
        logger.info(f"Set threshold for {symbol}: {price}")
        self.thresholds[symbol] = price

    def register_subscriber(self, user_id: str, callback: Callable):
        logger.info(f"Registered subscriber {user_id}")
        self.subscribers[user_id] = callback

    async def dispatch_alert(self, message: dict):
        logger.info(f"Dispatching alert: {message}")
        for sub, cb in self.subscribers.items():
            await cb(message)

    async def check_thresholds(self, symbol: str, price: float):
        if symbol in self.thresholds:
            threshold = self.thresholds[symbol]
            if price >= threshold:
                await self.dispatch_alert({
                    "type": "threshold_hit",
                    "symbol": symbol,
                    "price": price,
                    "threshold": threshold
                })

    async def ai_anomaly_detection(self, symbol: str, history: list[float]):
        """
        Simple AI anomaly detection using z-score.
        """
        if len(history) < 10:
            return  # Not enough data

        mean = np.mean(history)
        std = np.std(history)
        last = history[-1]

        if std == 0:
            return

        z_score = abs((last - mean) / std)
        if z_score >= 2.5:
            await self.dispatch_alert({
                "type": "anomaly",
                "symbol": symbol,
                "price": last,
                "z_score": float(z_score)
            })


# -------------------------------
# Background alert monitoring loop
# -------------------------------
async def alert_monitor_loop():
    """
    Continuously monitors all symbols in PriceCache for threshold hits or anomalies.
    Designed to be run as a background task.
    """
    alert_service = AlertService()
    
    # Example: set default thresholds (optional)
    alert_service.set_threshold("AAPL", 180.0)
    alert_service.set_threshold("TSLA", 900.0)

    while True:
        try:
            symbols = await price_cache.get_tracked_symbols()
            for symbol in symbols:
                price = await price_cache.get_price(symbol)
                if price is None:
                    continue

                await alert_service.check_thresholds(symbol, float(price))

                history = await price_cache.get_history(symbol)
                if history:
                    await alert_service.ai_anomaly_detection(symbol, history)

            await asyncio.sleep(2)  # alert checking interval
        except Exception as e:
            logger.error(f"Error in alert_monitor_loop: {e}")
            await asyncio.sleep(5)
