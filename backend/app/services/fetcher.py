import asyncio
from typing import Tuple
import httpx
import yfinance as yf
from ..utils.logger import log
from .price_cache import price_cache
from ..config.settings import settings

logger = log

# -----------------------------
# PriceFetcher: Handles fetching live and historical price data
# -----------------------------
class PriceFetcher:
    """
    Fetches both live and historical prices for tracked symbols.
    - Uses Polygon.io for live intraday prices
    - Uses yfinance for historical daily prices
    """

    def __init__(self):
        # API key and base URL for Polygon.io
        self.api_key = settings.POLYGON_API_KEY
        self.base = "https://api.polygon.io/v2/aggs/ticker/"

    # -----------------------------
    # Fetch latest live price and volume
    # -----------------------------
    async def fetch_price_and_volume(self, symbol: str) -> Tuple[float, float]:
        """
        Fetch the previous close price and volume for a symbol from Polygon.io.

        Args:
            symbol (str): Stock or crypto ticker

        Returns:
            Tuple[float, float]: (price, volume) or (None, None) on failure
        """
        if "-" in symbol:  # Skip invalid symbols (e.g., options)
            return None, None

        url = f"{self.base}{symbol}/prev?apiKey={self.api_key}"

        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(url, timeout=5)
                r.raise_for_status()
                d = r.json()["results"][0]
                return float(d["c"]), float(d["v"])
            except Exception as e:
                logger.error(f"Live fetch failed {symbol}: {e}")
                return None, None

    # -----------------------------
    # Preload historical daily prices
    # -----------------------------
    async def preload_daily_history(self, symbol: str, period="5y"):
        """
        Download historical daily OHLCV data from Yahoo Finance and save to cache.

        Args:
            symbol (str): Stock or crypto ticker
            period (str): Duration of history, e.g., "5y"
        """
        data = yf.download(
            symbol,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="column",
        )

        if data.empty:
            logger.warning(f"No daily history for {symbol}")
            return

        # Extract daily closing prices, volumes, and dates
        close = data["Close"].ffill().squeeze().tolist()
        volume = data["Volume"].ffill().squeeze().tolist()
        dates = data.index.strftime("%Y-%m-%d").tolist()

        # Save to Redis cache
        await price_cache.save_daily_history(symbol, close, volume, dates)
        logger.info(f"📦 Preloaded {len(close)} daily candles for {symbol}")


# -----------------------------
# Continuous live price fetch loop
# -----------------------------
async def fetch_live_prices_loop():
    """
    Continuously fetch live prices for all symbols in settings.SYMBOLS.
    Saves prices and volumes to the cache.
    Loops indefinitely with configurable interval and per-symbol delay.
    """
    fetcher = PriceFetcher()
    while True:
        try:
            for symbol in settings.SYMBOLS:
                price, volume = await fetcher.fetch_price_and_volume(symbol)
                if price is not None:
                    await price_cache.save_live_price(symbol, price, volume)

                # Small delay per symbol to avoid API rate limits
                await asyncio.sleep(1)

            # Wait for configured fetch interval before next batch
            await asyncio.sleep(settings.FETCH_INTERVAL)
        except Exception as e:
            logger.error(f"fetch_live_prices_loop error: {e}")
            # Wait a bit before retrying on errors
            await asyncio.sleep(5)
