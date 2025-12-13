# graphql/subscriptions.py

import strawberry
from typing import AsyncGenerator
from ..services.price_cache import PriceCache
from ..services.prediction_service import PredictionService


price_cache = PriceCache()
predictor_service = PredictionService()


@strawberry.type
class PriceStream:
    symbol: str
    price: float
    timestamp: str


@strawberry.type
class PredictionStream:
    symbol: str
    next_price: float
    timestamp: str


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def price_updates(self, symbol: str) -> AsyncGenerator[PriceStream, None]:
        symbol = symbol.upper()

        async for update in price_cache.stream_prices(symbol):
            yield PriceStream(
                symbol=symbol,
                price=update["price"],
                timestamp=update["timestamp"].isoformat(),
            )

    @strawberry.subscription
    async def prediction_updates(
        self, symbol: str
    ) -> AsyncGenerator[PredictionStream, None]:
        symbol = symbol.upper()

        async for pred in predictor_service.stream_predictions(symbol):
            yield PredictionStream(
                symbol=symbol,
                next_price=pred["prediction"],
                timestamp=pred["timestamp"].isoformat(),
            )
