import asyncio
import httpx
from ..utils.logger import log
from .price_cache import PriceCache
from ..config.settings import settings

logger = log
price_cache = PriceCache()  # shared cache instance

class PriceFetcher:
    def __init__(self):
        self.api_key = settings.POLYGON_API_KEY
        if not self.api_key:
            logger.error("POLYGON_API_KEY not set. Live price fetch will fail.")
        self.stock_base_url = "https://api.polygon.io/v2/aggs/ticker/"

    async def fetch_price(self, symbol: str) -> float:
        """
        Fetch the most recent price.
        Free-tier: works only for US stocks.
        """
        if "-" in symbol:  # simple check for crypto symbols
            logger.warning(f"Skipping crypto {symbol} — free-tier Polygon cannot fetch real-time.")
            return None

        url = f"{self.stock_base_url}{symbol}/prev?apiKey={self.api_key}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=5)
                response.raise_for_status()
                data = response.json()
                return float(data["results"][0]["c"])  # previous close
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Rate limit reached for {symbol}. Skipping...")
                else:
                    logger.error(f"Error fetching price for {symbol}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error for {symbol}: {e}")
        return None


# -------------------------------
# Background price fetching loop
# -------------------------------
async def fetch_live_prices_loop():
    """
    Continuously fetches prices for a set of symbols and stores them in Redis.
    """
    fetcher = PriceFetcher()
    symbols = settings.SYMBOLS

    while True:
        try:
            for symbol in symbols:
                price = await fetcher.fetch_price(symbol)
                if price is not None:
                    await price_cache.save_price(symbol, price)
                    logger.info(f"Saved {symbol}: {price} to Redis")
            await asyncio.sleep(settings.FETCH_INTERVAL)
        except Exception as e:
            logger.error(f"Error in fetch_live_prices_loop: {e}")
            await asyncio.sleep(5)
