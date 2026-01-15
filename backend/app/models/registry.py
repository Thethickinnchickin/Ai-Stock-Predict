import asyncio
from .predictor import get_predictor

class ModelRegistry:
    def __init__(self):
        self.model = None
        self.lock = asyncio.Lock()
        self.ready = False

    async def load(self):
        async with self.lock:
            self.model = get_predictor("xgb")
            if not self.model.load_artifacts():
                await self.model.train()
            self.ready = True

    def get(self):
        return self.model

model_registry = ModelRegistry()
