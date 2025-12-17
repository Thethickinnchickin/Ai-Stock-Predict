import strawberry
import io
import matplotlib.pyplot as plt
import pandas as pd
from fastapi import HTTPException
from ..services.price_cache import price_cache
from ..models.predictor import predictor

@strawberry.type
class Mutation:
    @strawberry.field
    async def plot_stock(self, symbol: str) -> str:
        symbol = symbol.upper()
        await price_cache.connect()

        prices, volumes, dates = await price_cache.get_daily_history(symbol)
        if not prices or not volumes or not dates:
            raise HTTPException(status_code=400, detail=f"No daily data loaded for {symbol}")

        STEPS = 5
        predicted = predictor.predict(prices, volumes, steps=STEPS)
        high, low = predictor.predict_high_low(prices, volumes, steps=STEPS)

        plt.figure(figsize=(12, 6))
        dates_dt = pd.to_datetime(dates)
        plt.plot(dates_dt, prices, label="Actual")

        last_date = dates_dt[-1]
        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=len(predicted),
            freq="D",
        )

        plt.plot(future_dates, predicted, "--", label="Predicted")
        plt.fill_between(future_dates, high, low, alpha=0.3, label="High / Low")

        all_dates = pd.to_datetime(list(dates_dt) + list(future_dates))
        tick_dates = all_dates[::7]
        plt.xticks(tick_dates, tick_dates.strftime("%Y-%m-%d"), rotation=45)

        plt.legend()
        plt.grid(True)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close()
        buf.seek(0)

        return buf.getvalue().hex()
