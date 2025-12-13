# graphql/queries.py

import strawberry
from typing import List
from datetime import datetime

from ..services.price_cache import PriceCache
from ..config.settings import settings

price_cache = PriceCache()


@strawberry.type
class PricePoint:
    symbol: str
    price: float
    timestamp: datetime


@strawberry.type
class Query:
    @strawberry.field
    async def current_price(self, symbol: str) -> PricePoint | None:
        price = await price_cache.get_last_price(symbol)
        if not price:
            return None
        return PricePoint(symbol=symbol, price=price["price"], timestamp=price["timestamp"])

    @strawberry.field
    async def price_history(self, symbol: str, limit: int = 100) -> List[PricePoint]:
        history = await price_cache.get_price_history(symbol, limit)
        return [
            PricePoint(
                symbol=symbol,
                price=dp["price"],
                timestamp=dp["timestamp"],
            )
            for dp in history
        ]

    @strawberry.field
    def tracked_symbols(self) -> List[str]:
        return settings.SYMBOLS
