import json
import redis.asyncio as aioredis
from ..utils.logger import log

logger = log

# -----------------------------
# Redis-based caching for prices, volumes, predictions, and alerts
# -----------------------------
class PriceCache:
    def __init__(self, redis_url="redis://localhost:6379"):
        """
        Initialize PriceCache.

        Args:
            redis_url (str): Redis server URL
        """
        self.redis_url = redis_url
        self.redis = None  # Will hold the Redis connection
        # Default symbols to track; can be updated dynamically
        self.tracked_symbols = ["AAPL", "TSLA", "ETH-USD", "NVDA"]

    # -----------------------------
    # Connect to Redis
    # -----------------------------
    async def connect(self):
        """
        Establishes an async connection to Redis.
        Connects only once to avoid repeated connections.
        """
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis")

    # -----------------------------
    # SYMBOL TRACKING
    # -----------------------------
    async def get_tracked_symbols(self) -> list[str]:
        """Return the list of symbols currently tracked."""
        return self.tracked_symbols

    # -----------------------------
    # LIVE PRICE STORAGE
    # -----------------------------
    async def save_live_price(self, symbol: str, price: float, volume: float | None = None):
        """
        Save the latest live price and volume for a symbol.
        Also maintains a rolling history of the last 500 prices.
        """
        await self.connect()
        await self.redis.set(f"live:price:{symbol}", price)
        await self.redis.lpush(f"live:price_history:{symbol}", price)
        await self.redis.ltrim(f"live:price_history:{symbol}", 0, 500)

        if volume is not None:
            await self.redis.set(f"live:volume:{symbol}", volume)

    async def get_live_price(self, symbol: str):
        """
        Fetch the latest live price for a symbol.
        Returns float or None if not available.
        """
        await self.connect()
        val = await self.redis.get(f"live:price:{symbol}")
        return float(val) if val else None

    # Alias for backward compatibility
    async def get_price(self, symbol: str) -> float | None:
        return await self.get_live_price(symbol)

    # -----------------------------
    # DAILY HISTORICAL STORAGE
    # -----------------------------
    async def save_daily_history(self, symbol: str, prices: list[float], volumes: list[float], dates: list[str]):
        """
        Save full daily historical prices, volumes, and dates for a symbol.
        Clears previous data before saving new history.

        Raises:
            ValueError: If lengths of prices, volumes, dates do not match
        """
        await self.connect()
        if len(prices) != len(volumes) or len(prices) != len(dates):
            raise ValueError("Prices, volumes, and dates must have same length")

        price_key = f"daily:prices:{symbol}"
        volume_key = f"daily:volumes:{symbol}"
        date_key = f"daily:dates:{symbol}"

        # Use pipeline to execute multiple Redis commands efficiently
        pipe = self.redis.pipeline()
        pipe.delete(price_key)
        pipe.delete(volume_key)
        pipe.delete(date_key)

        for p, v, d in zip(prices, volumes, dates):
            pipe.rpush(price_key, p)
            pipe.rpush(volume_key, v)
            pipe.rpush(date_key, d)

        await pipe.execute()
        logger.info(f"Saved {len(prices)} daily candles for {symbol}")

    async def get_daily_history(self, symbol: str, limit: int | None = None):
        """
        Retrieve full daily historical prices, volumes, and dates.
        Optionally return only the last `limit` entries.
        """
        await self.connect()
        prices = [float(x) for x in await self.redis.lrange(f"daily:prices:{symbol}", 0, -1)]
        volumes = [float(x) for x in await self.redis.lrange(f"daily:volumes:{symbol}", 0, -1)]
        dates = await self.redis.lrange(f"daily:dates:{symbol}", 0, -1)

        if limit:
            prices = prices[-limit:]
            volumes = volumes[-limit:]
            dates = dates[-limit:]

        return prices, volumes, dates

    # Helper methods to get individual components
    async def get_daily_prices(self, symbol: str, limit: int | None = None) -> list[float]:
        prices, _, _ = await self.get_daily_history(symbol, limit=limit)
        return prices

    async def get_daily_volumes(self, symbol: str, limit: int | None = None) -> list[float]:
        _, volumes, _ = await self.get_daily_history(symbol, limit=limit)
        return volumes

    async def get_daily_dates(self, symbol: str, limit: int | None = None) -> list[str]:
        _, _, dates = await self.get_daily_history(symbol, limit=limit)
        return dates

    # -----------------------------
    # Legacy helper methods (needed by trainer & alerts)
    # -----------------------------
    async def get_history(self, symbol: str, limit: int | None = None) -> list[float]:
        """Return historical closing prices for a symbol (legacy method)."""
        prices, _, _ = await self.get_daily_history(symbol, limit=limit)
        return prices

    # -----------------------------
    # PREDICTIONS / ALERTS STORAGE
    # -----------------------------
    async def save_prediction(self, symbol: str, prediction: dict):
        """Save a prediction dict for a symbol in Redis."""
        await self.connect()
        await self.redis.set(f"prediction:{symbol}", json.dumps(prediction))

    async def get_prediction(self, symbol: str):
        """Retrieve the latest prediction for a symbol from Redis."""
        await self.connect()
        raw = await self.redis.get(f"prediction:{symbol}")
        return json.loads(raw) if raw else None

    async def save_alert(self, alert: dict):
        """
        Save an alert dict into Redis list 'alerts'.
        Only keeps the latest 20 alerts.
        """
        await self.connect()
        await self.redis.lpush("alerts", json.dumps(alert))
        await self.redis.ltrim("alerts", 0, 20)

    async def get_alerts(self):
        """Retrieve the most recent 20 alerts from Redis."""
        await self.connect()
        raw = await self.redis.lrange("alerts", 0, 20)
        return [json.loads(x) for x in raw]


# -----------------------------
# Global instance for app usage
# -----------------------------
price_cache = PriceCache()
