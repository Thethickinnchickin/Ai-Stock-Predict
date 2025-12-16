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
