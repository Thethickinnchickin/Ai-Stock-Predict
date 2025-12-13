# app/models/predictor.py

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense


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
            LSTM(64, input_shape=(look_back, 1)),
            Dense(1)
        ])
        self.model.compile(optimizer="adam", loss="mse")

    def _make_dataset(self, series):
        X, y = [], []
        for i in range(len(series) - self.look_back):
            X.append(series[i:i + self.look_back])
            y.append(series[i + self.look_back])
        X = np.array(X).reshape(-1, self.look_back, 1)
        return X, np.array(y)

    def train(self, prices):
        if len(prices) < self.look_back + 10:
            return

        returns = np.diff(np.log(prices))
        X, y = self._make_dataset(returns)

        if len(X) == 0:
            return

        self.model.fit(X, y, epochs=5, batch_size=32, verbose=0)
        self.trained = True

    def predict(self, prices, steps=5):
        if not self.trained:
            return []

        returns = np.diff(np.log(prices))
        seq = returns[-self.look_back:].tolist()

        preds = []
        for _ in range(steps):
            x = np.array(seq).reshape(1, self.look_back, 1)
            r = float(self.model.predict(x, verbose=0)[0, 0])
            preds.append(r)
            seq = seq[1:] + [r]

        # convert returns → prices
        price = prices[-1]
        out = []
        for r in preds:
            price *= np.exp(r)
            out.append(round(float(price), 2))

        return out
    
    def probability_target(self, history, target_price, days_ahead=5, simulations=100, noise_std=1.0):
        """
        Estimate probability of hitting target_price within `days_ahead`.
        Handles targets above or below current price.
        """
        import random

        last_price = history[-1]
        hits = 0

        # scale noise relative to current price
        noise_std = last_price * 0.02  # 2% daily volatility

        # predict next `days_ahead` prices
        predicted_prices = self.predict(history, steps=days_ahead)
        predicted_returns = [(predicted_prices[i] - last_price) for i, last_price in enumerate([last_price]+predicted_prices[:-1])]

        for _ in range(simulations):
            price = last_price
            for i in range(days_ahead):
                # apply predicted trend + noise
                price = price * (1 + predicted_returns[i]/last_price) + random.gauss(0, noise_std)

                # check hit depending on target relation
                if (target_price >= last_price and price >= target_price) or \
                (target_price < last_price and price <= target_price):
                    hits += 1
                    break  # stop once target is reached

        return hits / simulations




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


def get_predictor(model_type: str):
    if model_type == "lstm":
        return LSTMPredictor()
    elif model_type == "arima":
        return ARIMAPredictor()
    else:
        return LinearPredictor()
