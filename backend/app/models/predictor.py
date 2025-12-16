import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler


class LinearPredictor:
    def train(self, prices):
        pass

    def predict(self, prices, steps=1):
        if not prices:
            return []
        return [prices[-1]] * steps


class LSTMPredictor:
    def __init__(self, look_back=20):
        self.look_back = look_back
        self.trained = False

        self.model = Sequential([
            LSTM(64, input_shape=(look_back, 6)),
            Dense(1)
        ])
        self.model.compile(optimizer="adam", loss="mse")

    def _make_dataset(self, features):
        X, y = [], []
        for i in range(len(features) - self.look_back):
            X.append(features[i:i + self.look_back])
            y.append(features[i + self.look_back][0])
        return np.array(X), np.array(y)

    def _make_features(self, prices, volumes=None, market_returns=None):
        prices = np.array(prices)
        returns = np.diff(np.log(prices))
        vol = np.array([np.std(returns[max(0, i-20):i+1]) for i in range(len(returns))])
        momentum = np.array([(prices[i+1]/prices[max(0,i+1-20)] - 1) for i in range(len(returns))])

        vol_change = np.zeros(len(returns))
        if volumes is not None and len(volumes) > 1:
            vols = np.array(volumes[1:])
            vol_change = np.diff(vols)/(vols[:-1] + 1e-8)

        market_ret = np.zeros(len(returns))
        if market_returns is not None:
            market_ret = np.array(market_returns[:len(returns)])

        # RSI
        def compute_rsi(prices, window=14):
            deltas = np.diff(prices)
            seed = deltas[:window]
            up = seed[seed > 0].sum()/window
            down = -seed[seed < 0].sum()/window
            rs = up/(down + 1e-8)
            rsi = np.zeros(len(prices)-1)
            rsi[:window] = 100 - 100/(1+rs)
            for i in range(window, len(prices)-1):
                delta = deltas[i]
                upval = max(delta,0)
                downval = -min(delta,0)
                up = (up*(window-1)+upval)/window
                down = (down*(window-1)+downval)/window
                rs = up/(down+1e-8)
                rsi[i] = 100 - 100/(1+rs)
            return rsi

        rsi = compute_rsi(prices)

        # Trim all to the minimum length
        min_len = min(len(returns), len(vol), len(momentum), len(vol_change), len(market_ret), len(rsi))
        returns, vol, momentum, vol_change, market_ret, rsi = [arr[-min_len:] for arr in [returns, vol, momentum, vol_change, market_ret, rsi]]

        features = np.column_stack([returns, vol, momentum, vol_change, market_ret, rsi])
        return (features - features.mean(axis=0))/(features.std(axis=0)+1e-8)


    def train(self, prices, volumes=None, market_returns=None):
        if len(prices) < self.look_back + 30:
            return
        features = self._make_features(prices, volumes, market_returns)
        X, y = self._make_dataset(features)
        if len(X) == 0:
            return
        self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
        self.trained = True

    def predict(self, prices, volumes=None, market_returns=None, steps=5):
        if not self.trained:
            return []

        features = self._make_features(prices, volumes, market_returns)
        seq = features[-self.look_back:].tolist()
        preds = []
        last_price = prices[-1]

        for _ in range(steps):
            x = np.array(seq).reshape(1, self.look_back, 6)
            r = float(self.model.predict(x, verbose=0)[0,0])
            preds.append(r)

            next_vol = np.std([f[0] for f in seq[-20:]])
            next_momentum = seq[-1][2]
            next_vol_change = seq[-1][3]
            next_market = seq[-1][4]
            next_rsi = seq[-1][5]

            noise = np.random.normal(0, 1e-4)
            seq = seq[1:] + [[r+noise, next_vol, next_momentum, next_vol_change, next_market, next_rsi]]

        price = last_price
        out = []
        for r in preds:
            price *= np.exp(r)
            out.append(round(float(price),2))
        return out

    def predict_high_low(self, prices, volumes=None, market_returns=None, steps=5):
        """
        Return predicted high and low ranges (±1% volatility) for each step.
        """
        preds = self.predict(prices, volumes, market_returns, steps)
        high = [p * 1.01 for p in preds]
        low = [p * 0.99 for p in preds]
        return high, low

class ARIMAPredictor:
    def __init__(self):
        self.model_fit = None

    def train(self, prices):
        if len(prices) < 20:
            return
        returns = np.diff(np.log(prices))
        model = ARIMA(returns, order=(2, 0, 2))
        self.model_fit = model.fit()

    def predict(self, prices, steps=5):
        if not self.model_fit:
            return []
        forecast = self.model_fit.forecast(steps)
        price = prices[-1]
        out = []
        for r in forecast:
            price *= np.exp(r)
            out.append(round(float(price), 2))
        return out

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler


class XGBoostPredictor:
    """
    XGBoost regressor that predicts LOG RETURNS instead of prices.
    This prevents flat-line collapse during long recursive forecasts.
    """

    def __init__(self, look_back=20):
        self.look_back = look_back
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

    # --------------------------------------------------
    # Feature engineering
    # --------------------------------------------------
    def _make_features(self, prices, volumes):
        prices = np.array(prices, dtype=float)
        volumes = np.array(volumes, dtype=float)

        log_returns = np.diff(np.log(prices), prepend=np.log(prices[0]))

        rolling_mean = (
            pd.Series(prices).rolling(5).mean().bfill().values
        )
        rolling_std = (
            pd.Series(prices).rolling(5).std().fillna(0).values
        )

        features = np.column_stack([
            prices,
            log_returns,
            rolling_mean,
            rolling_std,
            volumes,
        ])

        return features

    # --------------------------------------------------
    # Dataset builder
    # --------------------------------------------------
    def _make_dataset(self, prices, volumes):
        features = self._make_features(prices, volumes)

        X, y = [], []
        for i in range(len(prices) - self.look_back):
            window = features[i:i + self.look_back].flatten()
            X.append(window)

            # TARGET = next-day log return
            next_ret = np.log(
                prices[i + self.look_back] /
                prices[i + self.look_back - 1]
            )
            y.append(next_ret)

        X = np.array(X)
        y = np.array(y)

        X = self.scaler.fit_transform(X)
        return X, y

    # --------------------------------------------------
    # Training
    # --------------------------------------------------
    def train(self, prices, volumes=None):
        if volumes is None:
            volumes = [0] * len(prices)

        if len(prices) < self.look_back + 30:
            return

        X, y = self._make_dataset(prices, volumes)
        self.model.fit(X, y)
        self.trained = True

    # --------------------------------------------------
    # Recursive prediction
    # --------------------------------------------------
    def predict(self, prices, volumes=None, steps=10):
        if not self.trained:
            return []

        if volumes is None:
            volumes = [0] * len(prices)

        prices = list(prices)
        volumes = list(volumes)

        preds = []
        current_price = prices[-1]

        for _ in range(steps):
            features = self._make_features(prices, volumes)
            window = features[-self.look_back:].flatten().reshape(1, -1)
            window = self.scaler.transform(window)

            pred_ret = float(self.model.predict(window)[0])

            # Convert return → price
            current_price *= np.exp(pred_ret)
            preds.append(round(current_price, 2))

            # roll window forward
            prices.append(current_price)
            volumes.append(volumes[-1])

        return preds

    # --------------------------------------------------
    # High / Low bands
    # --------------------------------------------------
    def predict_high_low(self, prices, volumes=None, steps=10):
        preds = self.predict(prices, volumes, steps)

        # widening confidence band
        high = [p * (1 + 0.01 + i * 0.002) for i, p in enumerate(preds)]
        low = [p * (1 - 0.01 - i * 0.002) for i, p in enumerate(preds)]

        return high, low



def get_predictor(model_type: str):
    if model_type == "lstm":
        return LSTMPredictor()
    elif model_type == "arima":
        return ARIMAPredictor()
    elif model_type == "xgb":
        return XGBoostPredictor()
    else:
        return LinearPredictor()