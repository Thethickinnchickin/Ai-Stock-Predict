import json
import redis.asyncio as aioredis
from ..utils.logger import log


class PriceCache:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None

        # symbols tracked by the prediction engine
        self.tracked_symbols = ["AAPL", "TSLA", "BTC-USD", "ETH-USD"]

    async def connect(self):
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            log.info("Connected to Redis")

    # ---------------------------------------------------
    # PRICE STORAGE
    # ---------------------------------------------------
    async def save_price(self, symbol: str, price: float):
        await self.connect()
        await self.redis.set(f"price:{symbol}", price)
        await self.redis.lpush(f"history:{symbol}", price)
        await self.redis.ltrim(f"history:{symbol}", 0, 200)

    async def get_price(self, symbol: str):
        await self.connect()
        price = await self.redis.get(f"price:{symbol}")
        return float(price) if price else None

    async def get_history(self, symbol: str, limit=200):
        await self.connect()
        history = await self.redis.lrange(f"history:{symbol}", 0, limit)
        return [float(x) for x in history]

    async def get_tracked_symbols(self):
        return self.tracked_symbols

    # ---------------------------------------------------
    # 🔥 PREDICTION STORAGE (FULL OBJECTS)
    # ---------------------------------------------------

    async def save_prediction(self, symbol: str, prediction: dict):
        """
        Save single latest prediction for the symbol.
        Example prediction:
        {
            "symbol": "AAPL",
            "predicted_price": 191.22,
            "confidence": 0.84,
            "timestamp": "2025-12-11T02:33:00Z"
        }
        """
        await self.connect()
        await self.redis.set(f"prediction:{symbol}", json.dumps(prediction))

    async def get_prediction(self, symbol: str):
        await self.connect()
        raw = await self.redis.get(f"prediction:{symbol}")
        return json.loads(raw) if raw else None

    # ---------------------------------------------------
    # 🕒 RECENT PREDICTIONS LIST
    # ---------------------------------------------------

    async def save_prediction_entry(self, prediction_obj: dict):
        """
        Push into recent predictions list.
        """
        await self.connect()
        await self.redis.lpush("recent_predictions", json.dumps(prediction_obj))
        await self.redis.ltrim("recent_predictions", 0, 50)

    async def get_recent_predictions(self, limit=10):
        await self.connect()
        entries = await self.redis.lrange("recent_predictions", 0, limit - 1)
        return [json.loads(x) for x in entries]

    # ---------------------------------------------------
    # 🚨 ALERT SYSTEM
    # ---------------------------------------------------

    async def save_alert(self, alert: dict):
        """
        alert example:
        { "symbol": "AAPL", "message": "Price dropped 5%" }
        """
        await self.connect()
        await self.redis.lpush("alerts", json.dumps(alert))
        await self.redis.ltrim("alerts", 0, 20)

    async def get_alerts(self):
        await self.connect()
        raw_alerts = await self.redis.lrange("alerts", 0, 20)
        return [json.loads(a) for a in raw_alerts]


# global instance
price_cache = PriceCache()
