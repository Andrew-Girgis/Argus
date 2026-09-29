import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from parent directory (project root)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

from app.observability import setup_runtime_observability
from app.utils import setup_logging

setup_runtime_observability()

from app.routes.feedback import router as feedback_router
from app.routes.property import router as property_router

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Argus",
    description="Property intelligence API",
    version="0.1.0",
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(property_router)
app.include_router(feedback_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
