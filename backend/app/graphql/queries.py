import strawberry
from typing import List
import pandas as pd
from pandas.tseries.offsets import BDay
from app.services.price_cache import price_cache
from app.models.predictor import predictor
from app.services.prediction_service import prediction_service

# -----------------------------
# GraphQL Types
# -----------------------------
@strawberry.type
class PriceSeries:
    """
    Represents historical price data for a symbol.
    """
    dates: List[str]   # List of dates for historical prices
    prices: List[float]  # Closing prices corresponding to the dates

@strawberry.type
class PredictedSeries:
    """
    Represents predicted future prices along with high/low bands.
    """
    dates: List[str]   # Future trading dates
    prices: List[float]  # Predicted closing prices
    high: List[float]  # Upper bound prices
    low: List[float]   # Lower bound prices

@strawberry.type
class Prediction:
    """
    Combines actual historical data and predicted future prices.
    """
    actual: PriceSeries
    predicted: PredictedSeries

# -----------------------------
# GraphQL Query
# -----------------------------
@strawberry.type
class Query:
    @strawberry.field
    async def predict_stock(self, symbol: str) -> Prediction:
        """
        Predict future stock prices for a given symbol using global XGBoost model.
        Returns both historical and predicted data.
        """

        symbol = symbol.upper()  # Ensure symbol is uppercase (e.g., AAPL)
        await price_cache.connect()  # Connect to Redis if not already connected

        # -----------------------------
        # Load historical daily data
        # -----------------------------
        prices, volumes, dates = await price_cache.get_daily_history(symbol)
        if not prices or not volumes:
            raise ValueError("No daily data loaded for symbol")

        # -----------------------------
        # Display settings
        # -----------------------------
        DISPLAY_WINDOW = max(7, predictor.look_back)  # Show last N days of actual data
        STEPS = 5  # Predict next N trading days

        if len(prices) < predictor.look_back:
            raise ValueError(f"Not enough data for prediction (need {predictor.look_back} days)")

        # Slice the last N actual prices and dates for display
        display_prices = prices[-DISPLAY_WINDOW:]
        display_dates = dates[-DISPLAY_WINDOW:]

        # -----------------------------
        # Predict future values using the PredictionService
        # -----------------------------
        predicted = await prediction_service.predict_next_with_dates(symbol, steps=STEPS)

        # -----------------------------
        # DEBUG logging (optional)
        # -----------------------------
        print(f"Symbol: {symbol}")
        print("Display dates:", display_dates)
        print("Predicted future dates:", predicted["dates"])
        print("Predicted prices:", predicted["prices"])

        # -----------------------------
        # Return structured GraphQL response
        # -----------------------------
        return Prediction(
            actual=PriceSeries(dates=display_dates, prices=display_prices),
            predicted=PredictedSeries(
                dates=predicted["dates"],
                prices=predicted["prices"],
                high=predicted["high"],
                low=predicted["low"]
            )
        )
