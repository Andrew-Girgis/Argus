import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.utils import setup_logging

# Load .env from parent directory (project root)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

from app.observability import langfuse  # noqa: E402
from app.db.pool import close_pool, init_db  # noqa: E402
from app.routes.feedback import router as feedback_router  # noqa: E402
from app.routes.property import router as property_router  # noqa: E402

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_pool()
    langfuse.flush()

app = FastAPI(
    title="Argus",
    description="Property intelligence API",
    version="0.1.0",
    lifespan=lifespan,
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


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    with langfuse.start_as_current_observation(
        as_type="span",
        name=f"{request.method} {request.url.path}",
        input={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
        },
    ) as span:
        try:
            response = await call_next(request)
        except Exception as exc:
            span.update(output={"error": type(exc).__name__})
            raise

        span.update(output={"status_code": response.status_code})

    langfuse.flush()
    return response


@app.get("/health")
async def health_check():
    return {"status": "ok"}
