# Observability Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local observability stack where Langfuse captures runtime LLM traces and MLflow owns benchmark/evaluation workflows.

**Architecture:** Docker Compose gets an observability profile with self-hosted Langfuse, MLflow, Postgres, and MinIO-compatible artifact storage. Backend observability moves into a focused module, normal app traffic traces to Langfuse, and MLflow is used only by benchmark/evaluation entrypoints.

**Tech Stack:** Python 3.13+, FastAPI, uv, OpenAI Python SDK, Langfuse Python SDK, MLflow 3.14+, Docker Compose, Postgres, MinIO, ClickHouse, Redis/Valkey, React/Vite-plus frontend.

## Global Constraints

- Do not use Supabase for MLflow metadata, Langfuse metadata, traces, benchmark results, or artifacts.
- Do not add Supabase migrations in this milestone.
- Normal backend LLM traffic goes to Langfuse, not MLflow.
- MLflow reviewed labels are canonical for benchmark truth.
- `make dev` must remain app-only and must not require observability services.
- Add `make observability`, `make dev-full`, and `make benchmark`.
- Remove hardcoded MLflow tracking URI `http://127.0.0.1:5001` from app startup.
- Do not commit real secrets.
- Use root `.env` as the local source of truth; never edit `frontend/.env` directly.
- Use `uv` for backend dependency and Python commands.

---

## File Map

- Modify: `backend/pyproject.toml` — add Langfuse SDK dependency and any lightweight benchmark dependencies.
- Modify: `backend/uv.lock` — lock backend dependency changes via `uv sync`.
- Modify: `backend/app/config.py` — add observability settings with safe defaults.
- Create: `backend/app/observability.py` — central runtime observability setup and MLflow evaluation setup helpers.
- Modify: `backend/app/main.py` — load observability setup without MLflow runtime autologging.
- Modify: `backend/app/services/vision.py` — use Langfuse-wrapped `AsyncOpenAI` and attach trace metadata for runtime OpenAI calls.
- Modify: `backend/app/routes/property.py` — remove runtime `@mlflow.trace` decorators from API routes.
- Create: `backend/tests/test_observability.py` — verify observability config behavior without external services.
- Modify: `backend/tests/test_endpoints.py` — keep endpoint tests passing after decorator removals if import behavior changes.
- Modify: `.env.example` — document observability environment variables without secrets.
- Read: `docker-compose.yml` — verify app services stay app-only.
- Create: `docker-compose.observability.yml` — define the separate observability stack.
- Modify: `Makefile` — add observability, dev-full, benchmark, and helper targets.
- Create: `benchmarks/README.md` — document benchmark conventions.
- Create: `benchmarks/smoke_mlflow.py` — sample MLflow runner that logs a smoke run and artifact.
- Create: `benchmarks/fixtures/smoke_cases.jsonl` — non-secret synthetic smoke case metadata.
- Modify: `README.md` — document local observability commands and service URLs.

---

### Task 1: Environment-Driven Observability Configuration

**Files:**
- Modify: `backend/app/config.py`
- Create: `backend/app/observability.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_observability.py`

**Interfaces:**
- Produces: `setup_runtime_observability() -> None`
- Produces: `setup_mlflow_evaluation() -> None`
- Produces: `runtime_observability_enabled() -> bool`
- Consumes: `app.config.settings`

- [ ] **Step 1: Write failing tests for observability defaults and MLflow setup**

Create `backend/tests/test_observability.py`:

```python
from unittest.mock import patch

from app import observability
from app.config import Settings


def test_runtime_observability_disabled_without_langfuse_keys():
    settings = Settings(
        LANGFUSE_TRACING_ENABLED=True,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )

    assert observability.runtime_observability_enabled(settings) is False


def test_runtime_observability_enabled_with_langfuse_keys():
    settings = Settings(
        LANGFUSE_TRACING_ENABLED=True,
        LANGFUSE_PUBLIC_KEY="pk-lf-test",
        LANGFUSE_SECRET_KEY="sk-lf-test",
    )

    assert observability.runtime_observability_enabled(settings) is True


def test_setup_runtime_observability_sets_env_for_langfuse(monkeypatch):
    settings = Settings(
        OBSERVABILITY_ENV="test",
        LANGFUSE_TRACING_ENABLED=True,
        LANGFUSE_PUBLIC_KEY="pk-lf-test",
        LANGFUSE_SECRET_KEY="sk-lf-test",
        LANGFUSE_HOST="http://langfuse.example.test",
    )

    observability.setup_runtime_observability(settings)

    assert monkeypatch.context is not None
    import os

    assert os.environ["LANGFUSE_PUBLIC_KEY"] == "pk-lf-test"
    assert os.environ["LANGFUSE_SECRET_KEY"] == "sk-lf-test"
    assert os.environ["LANGFUSE_BASE_URL"] == "http://langfuse.example.test"
    assert os.environ["LANGFUSE_TRACING_ENABLED"] == "true"
    assert os.environ["LANGFUSE_RELEASE"] == "local"
    assert os.environ["LANGFUSE_ENVIRONMENT"] == "test"


def test_setup_runtime_observability_disables_langfuse_without_keys():
    settings = Settings(
        LANGFUSE_TRACING_ENABLED=True,
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
    )

    observability.setup_runtime_observability(settings)

    import os

    assert os.environ["LANGFUSE_TRACING_ENABLED"] == "false"


def test_setup_mlflow_evaluation_configures_tracking_uri_and_experiment():
    settings = Settings(
        MLFLOW_EVAL_ENABLED=True,
        MLFLOW_TRACKING_URI="http://mlflow.example.test:5000",
        MLFLOW_EXPERIMENT_NAME="argus-test",
        MLFLOW_S3_ENDPOINT_URL="http://minio.example.test:9000",
        AWS_ACCESS_KEY_ID="minio",
        AWS_SECRET_ACCESS_KEY="minio-secret",
    )

    with (
        patch("mlflow.set_tracking_uri") as set_tracking_uri,
        patch("mlflow.set_experiment") as set_experiment,
    ):
        observability.setup_mlflow_evaluation(settings)

    set_tracking_uri.assert_called_once_with("http://mlflow.example.test:5000")
    set_experiment.assert_called_once_with("argus-test")
```

- [ ] **Step 2: Run tests and verify they fail because `app.observability` does not exist**

Run: `cd backend && uv run pytest tests/test_observability.py -v`

Expected: FAIL with `ImportError: cannot import name 'observability' from 'app'` or `ModuleNotFoundError`.

- [ ] **Step 3: Add observability settings**

Modify `backend/app/config.py` so `Settings` includes these fields:

```python
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    GOOGLE_MAPS_API_KEY: str = ""
    MAPBOX_ACCESS_TOKEN: str = Field(default="", validation_alias="MAPBOX_API_KEY")
    OPENAI_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""

    OBSERVABILITY_ENV: str = "local"
    APP_VERSION: str = "local"

    LANGFUSE_TRACING_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"

    MLFLOW_EVAL_ENABLED: bool = False
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "argus-property-analysis"
    MLFLOW_S3_ENDPOINT_URL: str = "http://localhost:9000"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
```

- [ ] **Step 4: Create the observability module**

Create `backend/app/observability.py`:

```python
import os

import mlflow

from app.config import Settings, settings


def runtime_observability_enabled(config: Settings = settings) -> bool:
    """Return whether Langfuse runtime tracing has enough config to run."""
    return bool(
        config.LANGFUSE_TRACING_ENABLED
        and config.LANGFUSE_PUBLIC_KEY
        and config.LANGFUSE_SECRET_KEY
    )


def setup_runtime_observability(config: Settings = settings) -> None:
    """Configure runtime observability for normal app traffic."""
    if not runtime_observability_enabled(config):
        os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
        return

    os.environ["LANGFUSE_PUBLIC_KEY"] = config.LANGFUSE_PUBLIC_KEY
    os.environ["LANGFUSE_SECRET_KEY"] = config.LANGFUSE_SECRET_KEY
    os.environ["LANGFUSE_BASE_URL"] = config.LANGFUSE_HOST
    os.environ["LANGFUSE_TRACING_ENABLED"] = "true"
    os.environ["LANGFUSE_RELEASE"] = config.APP_VERSION
    os.environ["LANGFUSE_ENVIRONMENT"] = config.OBSERVABILITY_ENV


def setup_mlflow_evaluation(config: Settings = settings) -> None:
    """Configure MLflow for benchmark/evaluation scripts only."""
    if not config.MLFLOW_EVAL_ENABLED:
        return

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = config.MLFLOW_S3_ENDPOINT_URL
    if config.AWS_ACCESS_KEY_ID:
        os.environ["AWS_ACCESS_KEY_ID"] = config.AWS_ACCESS_KEY_ID
    if config.AWS_SECRET_ACCESS_KEY:
        os.environ["AWS_SECRET_ACCESS_KEY"] = config.AWS_SECRET_ACCESS_KEY

    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(config.MLFLOW_EXPERIMENT_NAME)
```

- [ ] **Step 5: Replace runtime MLflow setup in app startup**

Modify `backend/app/main.py` to remove `import mlflow`, `mlflow.set_tracking_uri(...)`, and `mlflow.autolog()`. Add runtime observability setup after `.env` loading and before route imports:

```python
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.observability import setup_runtime_observability
from app.utils import setup_logging

# Load .env from parent directory (project root)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

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
```

- [ ] **Step 6: Run observability tests**

Run: `cd backend && uv run pytest tests/test_observability.py -v`

Expected: PASS for all tests in `tests/test_observability.py`.

- [ ] **Step 7: Run existing backend tests**

Run: `cd backend && uv run pytest -v`

Expected: PASS. If the command fails, stop and diagnose the failing test output before continuing.

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/app/observability.py backend/app/main.py backend/tests/test_observability.py
git commit -m "feat: add observability configuration"
```

---

### Task 2: Langfuse Runtime OpenAI Tracing

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `backend/app/services/vision.py`
- Modify: `backend/app/routes/property.py`
- Test: `backend/tests/test_observability.py`
- Test: `backend/tests/test_endpoints.py`

**Interfaces:**
- Consumes: `runtime_observability_enabled(config: Settings = settings) -> bool`
- Produces: `vision.analyze_property(street_view_url: str | None, satellite_url: str | None) -> ServiceResult` with Langfuse tracing when enabled.

- [ ] **Step 1: Write failing test that normal property routes have no MLflow trace decorators**

Append to `backend/tests/test_observability.py`:

```python
from app.routes import property as property_routes


def test_property_routes_are_not_mlflow_traced_by_default():
    route_handlers = [
        property_routes.create_property,
        property_routes.get_images,
        property_routes.analyze,
        property_routes.get_pois_route,
    ]

    for handler in route_handlers:
        assert not hasattr(handler, "__wrapped__")
```

- [ ] **Step 2: Run test and verify it fails while route handlers are still MLflow-decorated**

Run: `cd backend && uv run pytest tests/test_observability.py::test_property_routes_are_not_mlflow_traced_by_default -v`

Expected: FAIL because at least one handler has `__wrapped__` from the decorator.

- [ ] **Step 3: Add Langfuse dependency**

Modify `backend/pyproject.toml` dependencies so the list includes `langfuse`:

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "httpx>=0.28.0",
    "supabase>=2.0.0",
    "openai>=1.60.0",
    "pydantic-settings>=2.7.0",
    "python-dotenv>=1.0.0",
    "huggingface-hub>=1.7.2",
    "mlflow>=3.14.0",
    "langfuse>=3.0.0",
]
```

Run: `cd backend && uv sync`

Expected: dependency resolution succeeds and `backend/uv.lock` updates.

- [ ] **Step 4: Switch OpenAI client import to Langfuse wrapper**

Modify the import in `backend/app/services/vision.py`:

```python
from langfuse import get_client, propagate_attributes
from langfuse.openai import AsyncOpenAI
```

Keep existing imports for `json`, `logging`, `re`, `settings`, and `ServiceResult`.

- [ ] **Step 5: Add Langfuse trace metadata around the OpenAI call**

In `backend/app/services/vision.py`, update the OpenAI call area inside `analyze_property()` to use the Langfuse client and propagated attributes:

```python
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        langfuse = get_client()

        content: list[dict] = [{"type": "text", "text": ANALYSIS_PROMPT}]

        if street_view_url:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": street_view_url, "detail": "high"},
                }
            )

        if satellite_url:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": satellite_url, "detail": "high"},
                }
            )

        with langfuse.start_as_current_observation(
            as_type="span",
            name="property-vision-analysis",
            input={
                "has_street_view": bool(street_view_url),
                "has_satellite": bool(satellite_url),
            },
        ) as span:
            with propagate_attributes(
                trace_name="property-vision-analysis",
                tags=["runtime", "property-analysis", settings.OBSERVABILITY_ENV],
                metadata={
                    "workflow": "property_vision_analysis",
                    "workflow_version": settings.APP_VERSION,
                    "model": "gpt-4o",
                    "environment": settings.OBSERVABILITY_ENV,
                },
                version=settings.APP_VERSION,
            ):
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": content}],
                    max_tokens=1500,
                    temperature=0.2,
                    name="openai-vision-analysis",
                    metadata={
                        "workflow": "property_vision_analysis",
                        "environment": settings.OBSERVABILITY_ENV,
                    },
                )
            span.update(output={"model": "gpt-4o"})
```

Keep the existing `raw_text`, JSON extraction, and error handling after this block.

- [ ] **Step 6: Remove runtime MLflow route decorators**

Modify `backend/app/routes/property.py`:

```python
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
```

Remove `import mlflow` and remove these decorators:

```python
@mlflow.trace(name="create_property")
@mlflow.trace(name="get_property_images")
@mlflow.trace(name="analyze_property_images")
@mlflow.trace(name="get_property_pois")
```

- [ ] **Step 7: Run route decorator test**

Run: `cd backend && uv run pytest tests/test_observability.py::test_property_routes_are_not_mlflow_traced_by_default -v`

Expected: PASS.

- [ ] **Step 8: Run backend tests**

Run: `cd backend && uv run pytest -v`

Expected: PASS. If the command fails, stop and diagnose the failing test output before continuing.

- [ ] **Step 9: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/app/services/vision.py backend/app/routes/property.py backend/tests/test_observability.py
git commit -m "feat: route runtime llm tracing to langfuse"
```

---

### Task 3: Docker Compose Observability Stack And Make Targets

**Files:**
- Read: `docker-compose.yml`
- Create: `docker-compose.observability.yml`
- Modify: `Makefile`
- Modify: `.env.example`
- Modify: `README.md`

**Interfaces:**
- Produces: `make observability`
- Produces: `make dev-full`
- Produces: `make benchmark`
- Produces: local service URLs `http://localhost:5000` for MLflow, `http://localhost:9001` for MinIO console, `http://localhost:3000` for Langfuse.

- [ ] **Step 1: Add observability env examples**

Append to `.env.example`:

```bash

# Observability
OBSERVABILITY_ENV=local
APP_VERSION=local

# Langfuse runtime tracing
LANGFUSE_TRACING_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=http://localhost:3000

# MLflow benchmark/evaluation tracking
MLFLOW_EVAL_ENABLED=false
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=argus-property-analysis
MLFLOW_S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=argus_minio
AWS_SECRET_ACCESS_KEY=argus_minio_password

# Local observability infrastructure defaults
MLFLOW_POSTGRES_USER=mlflow
MLFLOW_POSTGRES_PASSWORD=mlflow_password
MLFLOW_POSTGRES_DB=mlflow
MINIO_ROOT_USER=argus_minio
MINIO_ROOT_PASSWORD=argus_minio_password
LANGFUSE_POSTGRES_USER=langfuse
LANGFUSE_POSTGRES_PASSWORD=langfuse_password
LANGFUSE_POSTGRES_DB=langfuse
LANGFUSE_NEXTAUTH_SECRET=replace-with-a-long-random-string
LANGFUSE_SALT=replace-with-a-long-random-string
CLICKHOUSE_USER=clickhouse
CLICKHOUSE_PASSWORD=clickhouse_password
CLICKHOUSE_DB=langfuse
REDIS_PASSWORD=redis_password
```

- [ ] **Step 2: Create observability compose file**

Create `docker-compose.observability.yml`:

```yaml
services:
  mlflow-postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${MLFLOW_POSTGRES_USER:-mlflow}
      POSTGRES_PASSWORD: ${MLFLOW_POSTGRES_PASSWORD:-mlflow_password}
      POSTGRES_DB: ${MLFLOW_POSTGRES_DB:-mlflow}
    volumes:
      - mlflow-postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${MLFLOW_POSTGRES_USER:-mlflow} -d ${MLFLOW_POSTGRES_DB:-mlflow}"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-argus_minio}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-argus_minio_password}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data

  minio-init:
    image: minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      sleep 5;
      mc alias set local http://minio:9000 ${MINIO_ROOT_USER:-argus_minio} ${MINIO_ROOT_PASSWORD:-argus_minio_password};
      mc mb --ignore-existing local/mlflow;
      exit 0;
      "

  mlflow:
    image: ghcr.io/mlflow/mlflow:v3.14.0
    depends_on:
      mlflow-postgres:
        condition: service_healthy
      minio-init:
        condition: service_completed_successfully
    ports:
      - "5000:5000"
    environment:
      AWS_ACCESS_KEY_ID: ${MINIO_ROOT_USER:-argus_minio}
      AWS_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD:-argus_minio_password}
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
    command: >
      mlflow server
      --host 0.0.0.0
      --port 5000
      --backend-store-uri postgresql://${MLFLOW_POSTGRES_USER:-mlflow}:${MLFLOW_POSTGRES_PASSWORD:-mlflow_password}@mlflow-postgres:5432/${MLFLOW_POSTGRES_DB:-mlflow}
      --default-artifact-root s3://mlflow/artifacts

  langfuse-postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${LANGFUSE_POSTGRES_USER:-langfuse}
      POSTGRES_PASSWORD: ${LANGFUSE_POSTGRES_PASSWORD:-langfuse_password}
      POSTGRES_DB: ${LANGFUSE_POSTGRES_DB:-langfuse}
    volumes:
      - langfuse-postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${LANGFUSE_POSTGRES_USER:-langfuse} -d ${LANGFUSE_POSTGRES_DB:-langfuse}"]
      interval: 10s
      timeout: 5s
      retries: 5

  clickhouse:
    image: clickhouse/clickhouse-server:24.8
    environment:
      CLICKHOUSE_DB: ${CLICKHOUSE_DB:-langfuse}
      CLICKHOUSE_USER: ${CLICKHOUSE_USER:-clickhouse}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-clickhouse_password}
    volumes:
      - clickhouse-data:/var/lib/clickhouse

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD:-redis_password}
    volumes:
      - redis-data:/data

  langfuse-worker:
    image: langfuse/langfuse-worker:3
    depends_on:
      langfuse-postgres:
        condition: service_healthy
      clickhouse:
        condition: service_started
      redis:
        condition: service_started
    environment: &langfuse-env
      DATABASE_URL: postgresql://${LANGFUSE_POSTGRES_USER:-langfuse}:${LANGFUSE_POSTGRES_PASSWORD:-langfuse_password}@langfuse-postgres:5432/${LANGFUSE_POSTGRES_DB:-langfuse}
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET:-replace-with-a-long-random-string}
      SALT: ${LANGFUSE_SALT:-replace-with-a-long-random-string}
      ENCRYPTION_KEY: ${LANGFUSE_ENCRYPTION_KEY:-0000000000000000000000000000000000000000000000000000000000000000}
      CLICKHOUSE_URL: http://clickhouse:8123
      CLICKHOUSE_USER: ${CLICKHOUSE_USER:-clickhouse}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-clickhouse_password}
      CLICKHOUSE_DB: ${CLICKHOUSE_DB:-langfuse}
      REDIS_CONNECTION_STRING: redis://:${REDIS_PASSWORD:-redis_password}@redis:6379/0
      LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES: "true"

  langfuse-web:
    image: langfuse/langfuse:3
    depends_on:
      langfuse-postgres:
        condition: service_healthy
      clickhouse:
        condition: service_started
      redis:
        condition: service_started
    ports:
      - "3000:3000"
    environment:
      <<: *langfuse-env
      NEXTAUTH_URL: http://localhost:3000

volumes:
  mlflow-postgres-data:
  minio-data:
  langfuse-postgres-data:
  clickhouse-data:
  redis-data:
```

- [ ] **Step 3: Keep app compose app-only**

Verify `docker-compose.yml` still contains only the app services by default:

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./backend:/app
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
      - VITE_MAPBOX_API_KEY=${MAPBOX_API_KEY}
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
    restart: unless-stopped
```

- [ ] **Step 4: Add Make targets**

Modify `Makefile` `.PHONY` and add targets:

```make
.PHONY: dev backend frontend install test build check observability observability-down dev-full benchmark

observability:
	docker compose --env-file .env -f docker-compose.observability.yml up

observability-down:
	docker compose --env-file .env -f docker-compose.observability.yml down

dev-full:
	@trap 'kill 0' EXIT; \
	docker compose --env-file .env -f docker-compose.observability.yml up & \
	$(MAKE) dev & \
	wait

benchmark:
	docker compose --env-file .env -f docker-compose.observability.yml up -d
	cd backend && MLFLOW_EVAL_ENABLED=true uv run python ../benchmarks/smoke_mlflow.py
```

- [ ] **Step 5: Validate compose config renders**

Run: `docker compose --env-file .env -f docker-compose.observability.yml config`

Expected: exit 0 and rendered YAML output. If `.env` does not exist locally, run `cp .env.example .env` first and replace only non-secret local dummy values required by Compose.

- [ ] **Step 6: Document service URLs in README**

Add this section to `README.md` after Docker Compose:

```markdown
## Observability Stack

Argus uses Langfuse for runtime LLM observability and MLflow for benchmark/evaluation workflows.

| Command | Description |
|---------|-------------|
| `make dev` | Start the app only |
| `make observability` | Start Langfuse, MLflow, MinIO, and backing stores |
| `make dev-full` | Start app + observability stack |
| `make benchmark` | Start observability stack and run the benchmark smoke runner |

| Service | URL |
|---------|-----|
| Langfuse | http://localhost:3000 |
| MLflow | http://localhost:5000 |
| MinIO Console | http://localhost:9001 |

Runtime app traces go to Langfuse. Benchmark and evaluation runs go to MLflow. Supabase is not used as storage for either observability platform.
```

- [ ] **Step 7: Commit**

```bash
git add .env.example docker-compose.yml docker-compose.observability.yml Makefile README.md
git commit -m "feat: add local observability stack"
```

---

### Task 4: MLflow Benchmark Smoke Runner

**Files:**
- Create: `benchmarks/README.md`
- Create: `benchmarks/fixtures/smoke_cases.jsonl`
- Create: `benchmarks/smoke_mlflow.py`
- Test: run `make benchmark`

**Interfaces:**
- Consumes: `setup_mlflow_evaluation()` from `backend/app/observability.py`
- Produces: `benchmarks/smoke_mlflow.py` script that logs one MLflow run and one artifact to MinIO-backed artifact storage.

- [ ] **Step 1: Create benchmark fixture**

Create `benchmarks/fixtures/smoke_cases.jsonl`:

```jsonl
{"case_id":"smoke-001","lat":43.6532,"lon":-79.3832,"expected_property_type":"unknown","notes":"Synthetic smoke case for MLflow connectivity only."}
```

- [ ] **Step 2: Create benchmark README**

Create `benchmarks/README.md`:

```markdown
# Argus Benchmarks

MLflow is the canonical benchmark and evaluation system for Argus.

Runtime app traffic is traced in Langfuse. Benchmark scripts in this directory configure MLflow explicitly and log runs, metrics, parameters, and artifacts to the MLflow tracking server.

Run the smoke benchmark with:

```bash
make benchmark
```

The smoke runner does not measure model quality. It verifies that MLflow can connect to the tracking server and write artifacts to MinIO.
```

- [ ] **Step 3: Create failing smoke script test by running missing file**

Run: `cd backend && uv run python ../benchmarks/smoke_mlflow.py`

Expected: FAIL with `No such file or directory` before the script exists.

- [ ] **Step 4: Create MLflow smoke runner**

Create `benchmarks/smoke_mlflow.py`:

```python
import json
from pathlib import Path

import mlflow

from app.config import settings
from app.observability import setup_mlflow_evaluation


ROOT = Path(__file__).resolve().parent
FIXTURE_PATH = ROOT / "fixtures" / "smoke_cases.jsonl"
REPORT_PATH = ROOT / "smoke_report.json"


def load_cases() -> list[dict]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    if not settings.MLFLOW_EVAL_ENABLED:
        raise RuntimeError(
            "MLFLOW_EVAL_ENABLED must be true for benchmark runs. "
            "Use `make benchmark` or set MLFLOW_EVAL_ENABLED=true."
        )

    setup_mlflow_evaluation()
    cases = load_cases()

    report = {
        "runner": "smoke_mlflow",
        "case_count": len(cases),
        "case_ids": [case["case_id"] for case in cases],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with mlflow.start_run(run_name="argus-observability-smoke"):
        mlflow.log_param("runner", "smoke_mlflow")
        mlflow.log_param("dataset", "benchmarks/fixtures/smoke_cases.jsonl")
        mlflow.log_metric("case_count", len(cases))
        mlflow.log_artifact(str(REPORT_PATH))

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run smoke runner with MLflow evaluation disabled and verify clear failure**

Run: `cd backend && uv run python ../benchmarks/smoke_mlflow.py`

Expected: FAIL with `RuntimeError: MLFLOW_EVAL_ENABLED must be true for benchmark runs.`

- [ ] **Step 6: Run benchmark target against local stack**

Run: `make benchmark`

Expected: Docker Compose starts observability services, the smoke runner prints JSON containing `"runner": "smoke_mlflow"`, and an MLflow run appears at `http://localhost:5000` with `smoke_report.json` as an artifact.

- [ ] **Step 7: Remove generated smoke report from version control if present**

If `benchmarks/smoke_report.json` exists after the run, add this line to `.gitignore`:

```gitignore
benchmarks/smoke_report.json
```

- [ ] **Step 8: Commit**

```bash
git add benchmarks/README.md benchmarks/fixtures/smoke_cases.jsonl benchmarks/smoke_mlflow.py .gitignore
git commit -m "feat: add mlflow benchmark smoke runner"
```

---

### Task 5: End-To-End Verification And Documentation Tightening

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-06-25-observability-platform-design.md` only if implementation reveals a design correction.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: verified local commands and final implementation notes.

- [ ] **Step 1: Verify app-only development still works without observability**

Run: `make test`

Expected: backend tests pass with no Langfuse or MLflow services running.

- [ ] **Step 2: Verify frontend check still works**

Run: `make check`

Expected: frontend lint, format, and typecheck pass. If `~/.vite-plus/bin/vp` is missing, install vite-plus according to project notes before rerunning.

- [ ] **Step 3: Verify observability compose config**

Run: `docker compose --env-file .env -f docker-compose.observability.yml config`

Expected: exit 0.

- [ ] **Step 4: Verify observability services start**

Run: `docker compose --env-file .env -f docker-compose.observability.yml up -d`

Expected: services start and `docker compose --env-file .env -f docker-compose.observability.yml ps` shows running containers for MLflow, MinIO, Langfuse, Postgres, ClickHouse, and Redis.

- [ ] **Step 5: Verify MLflow smoke benchmark**

Run: `make benchmark`

Expected: smoke JSON prints to the terminal and an MLflow run appears at `http://localhost:5000`.

- [ ] **Step 6: Verify runtime Langfuse tracing manually**

Set these in `.env` using credentials created in the local Langfuse UI:

```bash
LANGFUSE_TRACING_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-local-project-key
LANGFUSE_SECRET_KEY=sk-lf-local-project-key
LANGFUSE_HOST=http://localhost:3000
```

Run: `make dev-full`

In another terminal, trigger an analysis request:

```bash
curl -X POST http://localhost:8000/api/v1/property/analyze \
  -H 'Content-Type: application/json' \
  -d '{"street_view_url":"https://example.com/street.jpg","satellite_url":"https://example.com/satellite.jpg"}'
```

Expected: if `OPENAI_API_KEY` is valid and image URLs are accepted by OpenAI, a runtime trace appears in Langfuse. If OpenAI rejects the example URLs, use real Google image URLs from the app and repeat the request.

- [ ] **Step 7: Confirm normal app traffic does not create MLflow eval records by default**

After Step 6, open `http://localhost:5000` and verify no new benchmark run named `property-vision-analysis` was created by the normal API request. MLflow should only show runs created by `make benchmark` or explicit benchmark scripts.

- [ ] **Step 8: Update README with any operational corrections**

If verification revealed a required startup delay, port change, or credential step, update `README.md` with exact working commands and URLs. Keep this section concise and do not add secrets.

- [ ] **Step 9: Commit verification/documentation updates**

```bash
git add README.md docs/superpowers/specs/2026-06-25-observability-platform-design.md
git commit -m "docs: document observability verification"
```

Only include the spec file if a real design correction was needed. If no documentation changes were needed, skip this commit.
