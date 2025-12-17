# app/models/model_store.py

class ModelStore:
    """Simple in-memory store for symbol-specific models."""
    def __init__(self):
        self._store = {}

    def get(self, symbol: str):
        return self._store.get(symbol)

    def set(self, symbol: str, model):
        self._store[symbol] = model

    def clear(self):
        self._store.clear()

# global instance
model_store = ModelStore()
