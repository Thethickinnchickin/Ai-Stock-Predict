import strawberry
from typing import List
import pandas as pd
from app.services.price_cache import price_cache
from app.models.predictor import predictor

@strawberry.type
class PriceSeries:
    dates: List[str]
    prices: List[float]

@strawberry.type
class PredictedSeries:
    dates: List[str]
    prices: List[float]
    high: List[float]
    low: List[float]

@strawberry.type
class Prediction:
    actual: PriceSeries
    predicted: PredictedSeries

@strawberry.type
class Query:
    @strawberry.field
    async def predict_stock(self, symbol: str) -> Prediction:
        symbol = symbol.upper()

        # Ensure price_cache is connected
        await price_cache.connect()

        prices, volumes, dates = await price_cache.get_daily_history(symbol)
        if not prices or not volumes or not dates:
            raise ValueError("No daily data loaded")

        DISPLAY_WINDOW = 7
        STEPS = 5

        if len(prices) < predictor.look_back:
            raise ValueError(f"Not enough data for prediction (need {predictor.look_back} days)")

        # Predict
        predicted = predictor.predict(prices, volumes, steps=STEPS)
        high, low = predictor.predict_high_low(prices, volumes, steps=STEPS)

        display_prices = prices[-DISPLAY_WINDOW:]
        display_dates = dates[-DISPLAY_WINDOW:]

        last_date = pd.to_datetime(display_dates[-1])
        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=len(predicted),
            freq="D"
        )

        return Prediction(
            actual=PriceSeries(dates=display_dates, prices=display_prices),
            predicted=PredictedSeries(
                dates=future_dates.strftime("%Y-%m-%d").tolist(),
                prices=predicted,
                high=high,
                low=low
            )
        )
