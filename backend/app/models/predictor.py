import asyncio
import json
import os
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import yfinance as yf
from ..services.price_cache import price_cache
from ..config.settings import settings

# -----------------------------
# XGBoostPredictor: global AI model for all symbols
# -----------------------------
class XGBoostPredictor:
    """
    Global XGBoost predictor trained across all symbols.
    Features:
      - Uses historical prices, volumes, and market returns
      - Predicts log returns and converts them recursively to prices
      - Provides high/low bands for predicted prices
    """

    def __init__(self, look_back=20, symbols=None, market_indices=None, interval="60m"):
        """
        Args:
            look_back (int): Number of past days to use for prediction
            symbols (list[str]): List of symbols to train on
            market_index (str): Market index used for global market returns
        """
        self.look_back = look_back
        self.symbols = symbols or ["AAPL", "TSLA", "NVDA"]
        self.market_indices = market_indices or ["SPY", "QQQ", "^VIX"]
        self.interval = interval
        self.history_period = settings.HOURLY_HISTORY_PERIOD

        # XGBoost regression model
        self.model = XGBRegressor(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
        )

        # StandardScaler for normalizing input features
        self.scaler = StandardScaler()
        self.trained = False
        self.market_returns = None
        self.feature_version = "v2"

    def _artifact_paths(self):
        model_dir = settings.MODEL_DIR
        return {
            "dir": model_dir,
            "model": os.path.join(model_dir, settings.MODEL_FILE),
            "scaler": os.path.join(model_dir, settings.SCALER_FILE),
            "meta": os.path.join(model_dir, settings.MODEL_META_FILE),
        }

    def save_artifacts(self):
        paths = self._artifact_paths()
        try:
            os.makedirs(paths["dir"], exist_ok=True)
            self.model.get_booster().save_model(paths["model"])
            joblib.dump(self.scaler, paths["scaler"])
            meta = {
                "trained_at": pd.Timestamp.utcnow().isoformat(),
                "look_back": self.look_back,
                "interval": self.interval,
                "history_period": self.history_period,
                "market_indices": self.market_indices,
                "feature_version": self.feature_version,
            }
            with open(paths["meta"], "w", encoding="utf-8") as handle:
                json.dump(meta, handle, indent=2)
        except Exception as exc:
            print(f"⚠️ Failed to save model artifacts: {exc}")

    def load_artifacts(self):
        paths = self._artifact_paths()
        if not (os.path.exists(paths["model"]) and os.path.exists(paths["scaler"])):
            return False
        try:
            self.model.get_booster().load_model(paths["model"])
            self.scaler = joblib.load(paths["scaler"])
            self.trained = True
            try:
                self.market_returns = self._get_market_returns()
            except Exception as exc:
                print(f"⚠️ Failed to load market returns: {exc}")
                self.market_returns = {symbol: np.zeros(1) for symbol in self.market_indices}
            return True
        except Exception as exc:
            print(f"⚠️ Failed to load model artifacts: {exc}")
            return False

    # -----------------------------
    # Load hourly market returns (e.g., SPY, QQQ, ^VIX)
    # -----------------------------
    def _get_market_returns(self):
        """
        Downloads market index data and computes hourly log returns.
        Returns:
            dict[str, np.ndarray]: Map of symbol -> log return series
        """
        returns = {}
        for symbol in self.market_indices:
            data = yf.download(
                symbol,
                period=self.history_period,
                interval=self.interval,
                auto_adjust=True,
                progress=False,
            )

            if data.empty:
                raise ValueError(f"No market data returned for {symbol}")

            prices = data["Close"].ffill().to_numpy()
            if len(prices) < 2:
                raise ValueError(f"Not enough data to compute returns for {symbol}")

            returns[symbol] = np.diff(np.log(prices), prepend=np.log(prices[0]))

        return returns

    def _calc_rsi(self, prices, period=14):
        series = pd.Series(prices)
        delta = series.diff().fillna(0)
        gain = delta.clip(lower=0).rolling(period, min_periods=1).mean()
        loss = (-delta.clip(upper=0)).rolling(period, min_periods=1).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        no_movement = (gain == 0) & (loss == 0)
        rsi = rsi.mask(no_movement, 50)
        rsi = rsi.fillna(100)
        return rsi.values

    def _calc_ema(self, prices, span):
        return pd.Series(prices).ewm(span=span, adjust=False).mean().values

    def get_feature_importances(self, top_k=10):
        if not self.trained:
            return []
        num_market = len(self.market_indices)
        base_features = [
            "price",
            "volume",
            "log_return",
            "rolling_mean",
            "rolling_std",
            "rsi",
            "macd",
            "macd_signal",
            "volume_z",
            "hour_of_day",
            "day_of_week",
        ]
        feature_names = base_features + [f"market_{sym}" for sym in self.market_indices]
        num_features = len(feature_names)

        importances = getattr(self.model, "feature_importances_", None)
        if importances is None or len(importances) == 0:
            return []

        total_expected = self.look_back * num_features
        if len(importances) != total_expected:
            return []

        reshaped = importances.reshape(self.look_back, num_features)
        aggregated = reshaped.mean(axis=0)
        ranked = sorted(
            zip(feature_names, aggregated),
            key=lambda item: item[1],
            reverse=True,
        )
        return [{"name": name, "importance": float(score)} for name, score in ranked[:top_k]]

    # -----------------------------
    # Feature engineering for a single symbol
    # -----------------------------
    def _make_features_for_symbol(self, prices, volumes, dates, market_features):
        """
        Constructs feature matrix including:
            - Prices, volumes, log returns
            - Rolling mean and std
            - RSI, MACD
            - Volume z-score
            - Market index returns
            - Time features (hour, day of week)
        """
        prices = np.array(prices, dtype=float)
        volumes = np.array(volumes, dtype=float)
        log_returns = np.diff(np.log(prices), prepend=np.log(prices[0]))

        rolling_mean = pd.Series(prices).rolling(5).mean().bfill().values
        rolling_std = pd.Series(prices).rolling(5).std().fillna(0).values
        rsi = self._calc_rsi(prices)
        ema_fast = self._calc_ema(prices, span=12)
        ema_slow = self._calc_ema(prices, span=26)
        macd = ema_fast - ema_slow
        macd_signal = pd.Series(macd).ewm(span=9, adjust=False).mean().values

        vol_mean = pd.Series(volumes).rolling(20).mean().bfill().values
        vol_std = pd.Series(volumes).rolling(20).std().fillna(1).values
        vol_z = (volumes - vol_mean) / vol_std

        dt_index = pd.to_datetime(pd.Series(dates), errors="coerce")
        hours = dt_index.dt.hour.fillna(0).values / 23.0
        weekdays = dt_index.dt.dayofweek.fillna(0).values / 6.0

        features = np.column_stack([
            prices,
            volumes,
            log_returns,
            rolling_mean,
            rolling_std,
            rsi,
            macd,
            macd_signal,
            vol_z,
            hours,
            weekdays,
            market_features,
        ])
        return features

    # -----------------------------
    # Build global dataset from all symbols
    # -----------------------------
    async def _build_global_dataset(self):
        """
        Creates feature and target arrays (X, y) for training.
        Returns:
            X_scaled (np.ndarray), y (np.ndarray)
        """
        X_all, y_all = [], []

        try:
            self.market_returns = self._get_market_returns()
        except Exception as e:
            print(f"⚠️ Failed to load market returns: {e}")
            self.market_returns = {symbol: np.zeros(1) for symbol in self.market_indices}

        for symbol in self.symbols:
            prices, volumes, dates = await price_cache.get_hourly_history(symbol)
            if len(prices) < self.look_back + 30:
                continue

            prices = np.array(prices)
            volumes = np.array(volumes)
            market_columns = []
            for market_symbol in self.market_indices:
                market_slice = self.market_returns.get(market_symbol, np.zeros(1))[-len(prices):]
                if len(market_slice) < len(prices):
                    market_slice = np.pad(market_slice, (len(prices)-len(market_slice), 0))
                market_columns.append(market_slice)
            market_features = np.column_stack(market_columns) if market_columns else np.zeros((len(prices), 0))

            features = self._make_features_for_symbol(prices, volumes, dates, market_features)

            # Sliding window for supervised learning
            for i in range(self.look_back, len(prices)-1):
                window = features[i-self.look_back:i].flatten()
                X_all.append(window)
                # Target: next day's log return
                y_all.append(np.log(prices[i+1]/prices[i]))

        if not X_all:
            return np.array([]), np.array([])

        X_all = np.array(X_all)
        y_all = np.array(y_all)
        X_all_scaled = self.scaler.fit_transform(X_all)
        return X_all_scaled, y_all

    # -----------------------------
    # Train model
    # -----------------------------
    async def train(self):
        """
        Trains the XGBoost model using the global dataset.
        Uses walk-forward validation and prints validation MAE.
        """
        X, y = await self._build_global_dataset()
        if len(X) == 0:
            return

        split = self._walk_forward_split(X, y)
        if not split:
            return

        X_train, y_train, X_val, y_val = split

        self.model.fit(X_train, y_train)
        self.trained = True
        self.save_artifacts()

        preds = self.model.predict(X_val)
        error = np.mean(np.abs(preds - y_val))
        print(f"📊 Validation MAE (log-return): {error:.5f}")

    async def backtest(self, val_size=200):
        """
        Run a walk-forward style backtest and compare to a naive baseline.
        Baseline predicts zero log-return (i.e., price stays flat).
        Returns:
            dict: metrics for model vs baseline
        """
        X, y = await self._build_global_dataset()
        if len(X) == 0:
            return {}

        split = self._walk_forward_split(X, y, val_size=val_size)
        if not split:
            return {}

        X_train, y_train, X_val, y_val = split
        self.model.fit(X_train, y_train)
        self.trained = True

        preds = self.model.predict(X_val)
        mae_model = float(np.mean(np.abs(preds - y_val)))

        baseline = np.zeros_like(y_val)
        mae_baseline = float(np.mean(np.abs(baseline - y_val)))

        direction_model = float(np.mean(np.sign(preds) == np.sign(y_val)))
        direction_baseline = float(np.mean(np.sign(baseline) == np.sign(y_val)))

        return {
            "mae_model": mae_model,
            "mae_baseline": mae_baseline,
            "directional_accuracy_model": direction_model,
            "directional_accuracy_baseline": direction_baseline,
            "validation_size": len(y_val),
        }

    # -----------------------------
    # Walk-forward split for validation
    # -----------------------------
    def _walk_forward_split(self, X, y, val_size=200):
        """
        Splits data into training and validation sets.
        Validation set is the last `val_size` samples.
        """
        if len(X) <= val_size:
            return None

        X_train = X[:-val_size]
        y_train = y[:-val_size]
        X_val = X[-val_size:]
        y_val = y[-val_size:]

        return X_train, y_train, X_val, y_val

    # -----------------------------
    # Recursive multi-step prediction
    # -----------------------------
    def predict(self, prices, volumes=None, steps=10, dates=None):
        """
        Predict next `steps` future prices recursively.
        Returns:
            list[float]: predicted prices
        """
        if not self.trained or volumes is None:
            return []

        prices = list(prices)
        volumes = list(volumes)
        if dates:
            timestamps = list(pd.to_datetime(pd.Series(dates), errors="coerce"))
        else:
            timestamps = [pd.Timestamp.utcnow()] * len(prices)
        preds = []

        for _ in range(steps):
            window_prices = prices[-self.look_back:]
            window_volumes = volumes[-self.look_back:]
            window_dates = timestamps[-self.look_back:]

            market_columns = []
            for market_symbol in self.market_indices:
                market_slice = self.market_returns.get(market_symbol, np.zeros(1))[-self.look_back:]
                if len(market_slice) < self.look_back:
                    market_slice = np.pad(market_slice, (self.look_back-len(market_slice), 0))
                market_columns.append(market_slice)
            market_features = np.column_stack(market_columns) if market_columns else np.zeros((self.look_back, 0))

            features = self._make_features_for_symbol(
                window_prices,
                window_volumes,
                window_dates,
                market_features,
            )
            window = self.scaler.transform(features.flatten().reshape(1, -1))
            pred_ret = float(self.model.predict(window)[0])

            next_price = prices[-1] * np.exp(pred_ret)
            preds.append(round(next_price, 2))

            # Append predicted price and carry last volume forward
            prices.append(next_price)
            volumes.append(volumes[-1])
            timestamps.append(timestamps[-1] + pd.Timedelta(hours=1))

        return preds

    # -----------------------------
    # Generate high/low price bands
    # -----------------------------
    def predict_high_low(self, prices, volumes=None, steps=10, dates=None):
        """
        Computes upper and lower bands for predicted prices for visualization.
        """
        preds = self.predict(prices, volumes, steps, dates=dates)
        high = [p * (1 + 0.01 + i * 0.002) for i, p in enumerate(preds)]
        low = [p * (1 - 0.01 - i * 0.002) for i, p in enumerate(preds)]
        return high, low


# -----------------------------
# Factory function & global predictor
# -----------------------------
def get_predictor(model_type="xgb"):
    if model_type == "xgb":
        return XGBoostPredictor()

# Global predictor instance used across the app
predictor = get_predictor("xgb")
