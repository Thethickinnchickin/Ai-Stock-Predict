import asyncio
from typing import Tuple
import httpx
import yfinance as yf
from ..utils.logger import log
from .price_cache import price_cache
from ..config.settings import settings

logger = log

class PriceFetcher:
    def __init__(self):
        self.api_key = settings.POLYGON_API_KEY
        self.base = "https://api.polygon.io/v2/aggs/ticker/"

    async def fetch_price_and_volume(self, symbol: str) -> Tuple[float, float]:
        if "-" in symbol:
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

    async def preload_daily_history(self, symbol: str, period="5y"):
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

        close = data["Close"].ffill().squeeze().tolist()
        volume = data["Volume"].ffill().squeeze().tolist()
        dates = data.index.strftime("%Y-%m-%d").tolist()

        await price_cache.save_daily_history(symbol, close, volume, dates)
        logger.info(f"📦 Preloaded {len(close)} daily candles for {symbol}")

async def fetch_live_prices_loop():
    fetcher = PriceFetcher()
    while True:
        try:
            for symbol in settings.SYMBOLS:
                price, volume = await fetcher.fetch_price_and_volume(symbol)
                if price is not None:
                    await price_cache.save_live_price(symbol, price, volume)
                    logger.info(f"LIVE {symbol}: {price} vol={volume}")
            await asyncio.sleep(settings.FETCH_INTERVAL)
        except Exception as e:
            logger.error(f"fetch_live_prices_loop error: {e}")
            await asyncio.sleep(5)
