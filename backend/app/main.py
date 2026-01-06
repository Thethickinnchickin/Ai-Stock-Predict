import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from .tasks.runner import start_background_tasks
from .models.predictor import get_predictor
from .graphql.schema import schema
from .models.registry import model_registry

# -----------------------------
# Initialize FastAPI app
# -----------------------------
app = FastAPI(
    title="AI Stock Predictive Backend",
    description="Real-time GraphQL + WebSocket backend",
    version="1.0.0",
)

# -----------------------------
# Enable CORS for all origins
# This allows frontend clients from any domain to access the API
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP methods
    allow_headers=["*"],  # allow all headers
)

# -----------------------------
# Startup Event: runs when the server starts
# -----------------------------
@app.on_event("startup")
async def on_startup():
    """
    1. Launches background tasks for:
       - Fetching live prices
       - Monitoring alerts
       - Periodic model training
    2. Loads/trains the global XGBoost model via model_registry
    """
    # Start background tasks in an asyncio task (non-blocking)
    asyncio.create_task(start_background_tasks())
    print("🚀 Background tasks started")

    # NOTE: Duplicate call—should remove one to avoid running tasks twice
    asyncio.create_task(start_background_tasks())

    # Load the global model into memory (train if not already trained)
    await model_registry.load()
    print("✅ Global XGBoost model trained")

# -----------------------------
# Mount GraphQL API at /graphql
# This exposes queries like predict_stock(symbol)
# -----------------------------
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
