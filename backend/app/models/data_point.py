# models/data_point.py

from pydantic import BaseModel, Field
from datetime import datetime

class DataPoint(BaseModel):
    symbol: str = Field(..., description="Ticker symbol, e.g., AAPL")
    price: float = Field(..., description="Current or historical price")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "price": 189.42,
                "timestamp": "2025-01-12T18:25:43.511Z"
            }
        }
