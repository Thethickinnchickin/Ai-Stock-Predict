from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional

class Settings(BaseSettings):
    """
    Global application settings loaded from environment variables.
    Automatically loads values from a .env file if present.
    """

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # allow extra env vars without crashing
    )

    # App
    ENV: str = Field("development", description="Environment: development, production")
    DEBUG: bool = Field(True, description="Debug mode enabled/disabled")

    # Market Symbols
    SYMBOLS: List[str] = Field(
        default=["AAPL", "TSLA", "BTC-USD", "ETH-USD", "NVDA"],
        description="Default symbols to track"
    )

    # Fetching Intervals (seconds)
    FETCH_INTERVAL: int = Field(120, description="Seconds between live price fetches (free tier safe)")
    PREDICT_INTERVAL: int = Field(10, description="Seconds between AI predictions")
    ALERT_INTERVAL: int = Field(15, description="Seconds between alert checks (match fetch interval)")
    HOURLY_HISTORY_PERIOD: str = Field("60d", description="Period of hourly history to preload")
    HOURLY_REFRESH_INTERVAL: int = Field(3600, description="Seconds between hourly history refreshes")
    HOURLY_DATA_MAX_AGE_SECONDS: int = Field(10800, description="Max acceptable age for hourly data")
    BACKTEST_RUN_HOUR: int = Field(2, description="Local hour (0-23) to run nightly backtest")
    BACKTEST_VAL_SIZE: int = Field(200, description="Validation size for backtest")
    BACKTEST_LOG_PATH: str = Field("logs/backtest.log", description="Relative path for backtest log")
    ALERT_WEBHOOK_URL: Optional[str] = Field(None, description="Webhook URL for alert delivery")
    ALERT_WEBHOOK_TIMEOUT: int = Field(5, description="Webhook timeout seconds")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(60, description="Rate limit window in seconds")
    RATE_LIMIT_MAX: int = Field(120, description="Max requests per window per IP")
    FEATURE_IMPORTANCE_LOG_PATH: str = Field("logs/feature_importance.jsonl", description="Feature importance log path")
    FEATURE_IMPORTANCE_TOP_K: int = Field(8, description="Number of feature importance entries to log")
    MODEL_DIR: str = Field("models", description="Directory for saved model artifacts")
    MODEL_FILE: str = Field("xgb_model.json", description="XGBoost model filename")
    SCALER_FILE: str = Field("scaler.joblib", description="Scaler filename")
    MODEL_META_FILE: str = Field("model_meta.json", description="Model metadata filename")

    # Redis
    REDIS_HOST: str = Field("localhost", description="Redis host")
    REDIS_PORT: int = Field(6379, description="Redis port")
    REDIS_DB: int = Field(0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(None, description="Redis password (optional)")

    # External APIs
    POLYGON_API_KEY: Optional[str] = Field(None, description="Polygon.io API key (required for live prices)")
    ALPHA_VANTAGE_KEY: Optional[str] = None
    BINANCE_KEY: Optional[str] = None
    BINANCE_SECRET: Optional[str] = None

    # Websocket
    WEBSOCKET_BROADCAST_INTERVAL: int = Field(1, description="Seconds between websocket broadcast pushes")


# Global instance
settings = Settings()
