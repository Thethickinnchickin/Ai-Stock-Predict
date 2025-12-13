# app/models/model_store.py

class ModelStore:
    def __init__(self):
        self.models = {}

    def get(self, symbol: str):
        return self.models.get(symbol)

    def set(self, symbol: str, model):
        self.models[symbol] = model


model_store = ModelStore()
