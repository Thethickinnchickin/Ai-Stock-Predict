import json
import redis.asyncio as aioredis
from ..utils.logger import log

logger = log


class PriceCache:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
        self.tracked_symbols = ["AAPL", "TSLA", "ETH-USD", "NVDA"]

    async def connect(self):
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis")

    # -------------------------
    # SYMBOL TRACKING
    # -------------------------
    async def get_tracked_symbols(self) -> list[str]:
        return self.tracked_symbols

    # -------------------------
    # LIVE PRICE STORAGE
    # -------------------------
    async def save_live_price(self, symbol: str, price: float, volume: float | None = None):
        await self.connect()
        await self.redis.set(f"live:price:{symbol}", price)
        await self.redis.lpush(f"live:price_history:{symbol}", price)
        await self.redis.ltrim(f"live:price_history:{symbol}", 0, 500)
        if volume is not None:
            await self.redis.set(f"live:volume:{symbol}", volume)

    async def get_live_price(self, symbol: str):
        await self.connect()
        val = await self.redis.get(f"live:price:{symbol}")
        return float(val) if val else None

    # Alias for backward compatibility
    async def get_price(self, symbol: str) -> float | None:
        return await self.get_live_price(symbol)

    # -------------------------
    # DAILY HISTORICAL STORAGE
    # -------------------------
    async def save_daily_history(self, symbol: str, prices: list[float], volumes: list[float], dates: list[str]):
        await self.connect()
        if len(prices) != len(volumes) or len(prices) != len(dates):
            raise ValueError("Prices, volumes, and dates must have same length")

        price_key = f"daily:prices:{symbol}"
        volume_key = f"daily:volumes:{symbol}"
        date_key = f"daily:dates:{symbol}"

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
        await self.connect()
        prices = [float(x) for x in await self.redis.lrange(f"daily:prices:{symbol}", 0, -1)]
        volumes = [float(x) for x in await self.redis.lrange(f"daily:volumes:{symbol}", 0, -1)]
        dates = await self.redis.lrange(f"daily:dates:{symbol}", 0, -1)

        if limit:
            prices = prices[-limit:]
            volumes = volumes[-limit:]
            dates = dates[-limit:]

        return prices, volumes, dates

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
        """Return historical closing prices for a symbol."""
        prices, _, _ = await self.get_daily_history(symbol, limit=limit)
        return prices

    # -------------------------
    # PREDICTIONS / ALERTS
    # -------------------------
    async def save_prediction(self, symbol: str, prediction: dict):
        await self.connect()
        await self.redis.set(f"prediction:{symbol}", json.dumps(prediction))

    async def get_prediction(self, symbol: str):
        await self.connect()
        raw = await self.redis.get(f"prediction:{symbol}")
        return json.loads(raw) if raw else None

    async def save_alert(self, alert: dict):
        await self.connect()
        await self.redis.lpush("alerts", json.dumps(alert))
        await self.redis.ltrim("alerts", 0, 20)

    async def get_alerts(self):
        await self.connect()
        raw = await self.redis.lrange("alerts", 0, 20)
        return [json.loads(x) for x in raw]


price_cache = PriceCache()
