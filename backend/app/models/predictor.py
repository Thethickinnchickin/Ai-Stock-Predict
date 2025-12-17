import asyncio
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
import yfinance as yf
from ..services.price_cache import price_cache


class XGBoostPredictor:
    """
    XGBoost predictor trained across all symbols with market returns as a feature.
    Predicts log returns, then converts to prices recursively.
    """

    def __init__(self, look_back=20, symbols=None, market_index="SPY"):
        self.look_back = look_back
        self.symbols = symbols or ["AAPL", "TSLA", "NVDA"]
        self.market_index = market_index

        self.model = XGBRegressor(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
        )

        self.scaler = StandardScaler()
        self.trained = False
        self.market_returns = None

    # --------------------------
    # Load market returns
    # --------------------------
    def _get_market_returns(self):
        data = yf.download(
            self.market_index, period="1y", interval="1d",
            auto_adjust=True, progress=False
        )

        if data.empty:
            raise ValueError(f"No market data returned for {self.market_index}")

        prices = data["Close"].ffill().to_numpy()
        if len(prices) < 2:
            raise ValueError(f"Not enough data to compute returns for {self.market_index}")

        prices = prices.flatten()
        returns = np.diff(np.log(prices), prepend=np.log(prices[0]))
        return returns

    # --------------------------
    # Feature engineering per symbol
    # --------------------------
    def _make_features_for_symbol(self, prices, volumes, market_returns):
        prices = np.array(prices, dtype=float)
        volumes = np.array(volumes, dtype=float)
        log_returns = np.diff(np.log(prices), prepend=np.log(prices[0]))

        rolling_mean = pd.Series(prices).rolling(5).mean().bfill().values
        rolling_std = pd.Series(prices).rolling(5).std().fillna(0).values

        features = np.column_stack([
            prices,
            volumes,
            log_returns,
            rolling_mean,
            rolling_std,
            market_returns[-len(prices):],
        ])
        return features

    # --------------------------
    # Build global dataset
    # --------------------------
    async def _build_global_dataset(self):
        X_all, y_all = [], []

        try:
            self.market_returns = self._get_market_returns()
        except Exception as e:
            print(f"⚠️ Failed to load market returns: {e}")
            self.market_returns = np.zeros(1)

        for symbol in self.symbols:
            prices, volumes, _ = await price_cache.get_daily_history(symbol)
            if len(prices) < self.look_back + 30:
                continue

            prices = np.array(prices)
            volumes = np.array(volumes)
            market_slice = self.market_returns[-len(prices):]
            if len(market_slice) < len(prices):
                market_slice = np.pad(market_slice, (len(prices)-len(market_slice), 0))

            features = self._make_features_for_symbol(prices, volumes, market_slice)

            for i in range(self.look_back, len(prices)-1):
                window = features[i-self.look_back:i].flatten()
                X_all.append(window)
                y_all.append(np.log(prices[i+1]/prices[i]))

        if not X_all:
            return np.array([]), np.array([])

        X_all = np.array(X_all)
        y_all = np.array(y_all)
        X_all_scaled = self.scaler.fit_transform(X_all)
        return X_all_scaled, y_all

    # --------------------------
    # Training
    # --------------------------
    async def train(self):
        X, y = await self._build_global_dataset()
        if len(X) == 0:
            print("⚠️ Not enough data to train")
            return
        self.model.fit(X, y)
        self.trained = True
        print(f"✅ XGBoost trained on {len(X)} samples across {len(self.symbols)} symbols")

    # --------------------------
    # Recursive prediction
    # --------------------------
    def predict(self, prices, volumes=None, steps=10):
        if not self.trained or volumes is None:
            return []

        prices = list(prices)
        volumes = list(volumes)
        preds = []

        for _ in range(steps):
            market_slice = self.market_returns[-self.look_back:]
            if len(market_slice) < self.look_back:
                market_slice = np.pad(market_slice, (self.look_back-len(market_slice), 0))

            features = np.column_stack([
                prices[-self.look_back:],
                volumes[-self.look_back:],
                np.diff(np.log(prices[-self.look_back:]), prepend=np.log(prices[-self.look_back])),
                pd.Series(prices[-self.look_back:]).rolling(5).mean().bfill().values,
                pd.Series(prices[-self.look_back:]).rolling(5).std().fillna(0).values,
                market_slice
            ])
            window = self.scaler.transform(features.flatten().reshape(1, -1))
            pred_ret = float(self.model.predict(window)[0])

            next_price = prices[-1] * np.exp(pred_ret)
            preds.append(round(next_price, 2))

            prices.append(next_price)
            volumes.append(volumes[-1])

        return preds

    def predict_high_low(self, prices, volumes=None, steps=10):
        preds = self.predict(prices, volumes, steps)
        high = [p * (1 + 0.01 + i * 0.002) for i, p in enumerate(preds)]
        low = [p * (1 - 0.01 - i * 0.002) for i, p in enumerate(preds)]
        return high, low


# --------------------------
# Factory function & global predictor
# --------------------------
def get_predictor(model_type="xgb"):
    if model_type == "xgb":
        return XGBoostPredictor()

# Global instance for the app
predictor = get_predictor("xgb")
