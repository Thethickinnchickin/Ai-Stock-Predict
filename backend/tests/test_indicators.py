import numpy as np
from app.models.predictor import XGBoostPredictor


def test_rsi_constant_series():
    predictor = XGBoostPredictor()
    prices = [100.0] * 30
    rsi = predictor._calc_rsi(prices)
    assert len(rsi) == len(prices)
    assert np.allclose(rsi, 50.0)


def test_rsi_trending_up():
    predictor = XGBoostPredictor()
    prices = list(range(1, 31))
    rsi = predictor._calc_rsi(prices)
    assert rsi[-1] > 50.0


def test_feature_matrix_shape():
    predictor = XGBoostPredictor()
    prices = [float(x) for x in range(1, 41)]
    volumes = [1000.0 + x for x in range(40)]
    dates = [f"2026-01-01 {x % 24:02d}:00" for x in range(40)]
    market_features = np.zeros((len(prices), 3))

    features = predictor._make_features_for_symbol(prices, volumes, dates, market_features)
    assert features.shape[0] == len(prices)
    assert features.shape[1] == 11 + market_features.shape[1]
