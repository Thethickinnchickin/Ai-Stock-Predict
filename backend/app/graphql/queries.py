import json
import os
import strawberry
from typing import List, Optional
import pandas as pd
from pandas.tseries.offsets import BDay
from app.services.price_cache import price_cache
from app.models.predictor import predictor
from app.services.prediction_service import prediction_service
from app.models.registry import model_registry
from app.config.settings import settings

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

@strawberry.type
class LivePrice:
    symbol: str
    price: Optional[float]
    change_percent: Optional[float]
    volume: Optional[float]


@strawberry.type
class BacktestResult:
    timestamp: str
    mae_model: float
    mae_baseline: float
    directional_accuracy_model: float
    directional_accuracy_baseline: float
    validation_size: int


@strawberry.type
class DriftMetrics:
    window: int
    recent_mae: Optional[float]
    prior_mae: Optional[float]
    delta: Optional[float]
    status: str


@strawberry.type
class FeatureImportance:
    name: str
    importance: float


@strawberry.type
class FeatureImportanceSnapshot:
    timestamp: str
    features: List[FeatureImportance]


def _parse_backtest_line(line: str) -> Optional[BacktestResult]:
    if " | " not in line:
        return None
    timestamp, metrics = line.strip().split(" | ", 1)
    normalized = (
        metrics.replace("MAE model=", "MAE_model=")
        .replace("MAE baseline=", "MAE_baseline=")
        .replace("DirAcc model=", "DirAcc_model=")
        .replace("DirAcc baseline=", "DirAcc_baseline=")
    )
    parts = normalized.split()
    values = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key.strip()] = value.strip()

    try:
        return BacktestResult(
            timestamp=timestamp,
            mae_model=float(values["MAE_model"]),
            mae_baseline=float(values["MAE_baseline"]),
            directional_accuracy_model=float(values["DirAcc_model"]),
            directional_accuracy_baseline=float(values["DirAcc_baseline"]),
            validation_size=int(values["Val"]),
        )
    except (KeyError, ValueError):
        return None

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
        prices, volumes, dates = await price_cache.get_hourly_history(symbol)
        if not prices or not volumes:
            raise ValueError("No hourly data loaded for symbol")

        # -----------------------------
        # Display settings
        # -----------------------------
        DISPLAY_WINDOW = max(24, predictor.look_back)  # Show last N hours of actual data
        STEPS = 6  # Predict next N hours

        if len(prices) < predictor.look_back:
            raise ValueError(f"Not enough data for prediction (need {predictor.look_back} hours)")

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

    @strawberry.field
    async def live_prices(self, symbols: Optional[List[str]] = None) -> List[LivePrice]:
        """
        Return latest live prices for provided symbols.
        If no symbols are provided, use settings.SYMBOLS.
        """
        await price_cache.connect()
        tracked = symbols or settings.SYMBOLS
        results: List[LivePrice] = []

        for symbol in tracked:
            sym = symbol.upper()
            price = await price_cache.get_live_price(sym)
            change = await price_cache.get_live_change_percent(sym)
            volume = await price_cache.get_live_volume(sym)
            results.append(
                LivePrice(
                    symbol=sym,
                    price=price,
                    change_percent=change,
                    volume=volume,
                )
            )

        return results

    @strawberry.field
    async def backtest_results(self, limit: int = 30) -> List[BacktestResult]:
        """
        Return the most recent backtest results from the log file.
        """
        path = settings.BACKTEST_LOG_PATH
        if not os.path.exists(path):
            return []

        with open(path, "r", encoding="utf-8") as handle:
            lines = [line for line in handle.readlines() if line.strip()]

        results: List[BacktestResult] = []
        for line in lines[-limit:]:
            parsed = _parse_backtest_line(line)
            if parsed:
                results.append(parsed)

        return results

    @strawberry.field
    async def drift_metrics(self, window: int = 5) -> DriftMetrics:
        """
        Compare recent MAE against the prior window to detect drift.
        """
        path = settings.BACKTEST_LOG_PATH
        if not os.path.exists(path):
            return DriftMetrics(window=window, recent_mae=None, prior_mae=None, delta=None, status="no-data")

        with open(path, "r", encoding="utf-8") as handle:
            lines = [line for line in handle.readlines() if line.strip()]

        parsed = []
        for line in lines:
            result = _parse_backtest_line(line)
            if result:
                parsed.append(result)

        if len(parsed) < window * 2:
            return DriftMetrics(window=window, recent_mae=None, prior_mae=None, delta=None, status="insufficient")

        recent = parsed[-window:]
        prior = parsed[-(window * 2):-window]
        recent_mae = sum(r.mae_model for r in recent) / window
        prior_mae = sum(r.mae_model for r in prior) / window
        delta = recent_mae - prior_mae

        if delta > 0.0005:
            status = "degrading"
        elif delta < -0.0005:
            status = "improving"
        else:
            status = "stable"

        return DriftMetrics(
            window=window,
            recent_mae=recent_mae,
            prior_mae=prior_mae,
            delta=delta,
            status=status,
        )

    @strawberry.field
    async def feature_importances(self, top_k: int = 10) -> List[FeatureImportance]:
        model = model_registry.get()
        if not model:
            return []
        values = model.get_feature_importances(top_k=top_k)
        return [FeatureImportance(**item) for item in values]

    @strawberry.field
    async def feature_importance_trend(self, limit: int = 30) -> List[FeatureImportanceSnapshot]:
        path = settings.FEATURE_IMPORTANCE_LOG_PATH
        if not os.path.exists(path):
            return []

        with open(path, "r", encoding="utf-8") as handle:
            lines = [line for line in handle.readlines() if line.strip()]

        snapshots: List[FeatureImportanceSnapshot] = []
        for line in lines[-limit:]:
            try:
                payload = json.loads(line)
                features = [
                    FeatureImportance(**item) for item in payload.get("features", [])
                ]
                snapshots.append(
                    FeatureImportanceSnapshot(
                        timestamp=payload.get("timestamp", ""),
                        features=features,
                    )
                )
            except (json.JSONDecodeError, TypeError):
                continue

        return snapshots
