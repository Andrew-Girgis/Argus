# Observability Platform Design

## Goal

Make Argus ready for evaluation-driven AI development by adding a local observability stack that can later move to a shared hosted VM. The stack must support runtime LLM debugging, token/cost monitoring, human review, benchmark datasets, prompt/workflow experiments, and repeatable evaluation runs.

This design intentionally separates application data from observability data. Supabase remains the Argus domain database. MLflow and Langfuse own their own persistence layers.

## Current State

The backend is a FastAPI app that fetches Google imagery, runs LLM Vision analysis, computes geospatial data, and writes selected results to Supabase. The frontend displays property results and maps.

Observability is currently partial and informal:

- `backend/pyproject.toml` already includes `mlflow>=3.14.0`.
- `backend/app/main.py` hardcodes `mlflow.set_tracking_uri("http://127.0.0.1:5001")` and calls broad `mlflow.autolog()`.
- Several property routes use `@mlflow.trace` today.
- `docker-compose.yml` only starts the backend and frontend.
- Supabase calls are implemented, but the repository has no authoritative migration files for the implied schema.

The current MLflow integration should be replaced with explicit, environment-driven observability aligned to the responsibilities below.

## Tool Responsibilities

Argus will use both MLflow and Langfuse, but not as duplicate sources of truth.

### Langfuse

Langfuse is the runtime LLM observability platform.

It owns:

- Backend LLM traces from normal app traffic.
- Token, cost, latency, and model usage monitoring.
- Trace debugging and comments.
- Runtime prompt review.
- Annotation queues and corrected outputs for trace-level review.
- User or reviewer feedback attached to runtime traces.

Normal backend LLM traffic should be sent to Langfuse, not MLflow.

### MLflow

MLflow is the benchmark and evaluation platform.

It owns:

- Canonical human-reviewed benchmark datasets.
- Ground-truth labels and expectations for evaluations.
- Experiment runs.
- Prompt, model, and workflow comparisons.
- Scorers and yardsticks.
- Evaluation reports and artifacts.
- Future CI regression gates.

MLflow reviewed labels are canonical. Supabase can supply candidate records later, but MLflow datasets are the source of truth for benchmark labels once labels exist.

### Supabase

Supabase remains the Argus application and domain database.

It owns:

- Property records and enriched property metadata.
- Persisted AI outputs that the app needs to display or reuse.
- Future geographic zone entities and property-zone mappings.
- Future product workflow state, if needed.

Supabase must not be used as the backend database for MLflow or Langfuse internals.

## Trace And Feedback Routing

Runtime traces go to Langfuse. Benchmark and evaluation runs go to MLflow.

When a reviewer sees an incorrect runtime output, the first-line workflow should use Langfuse scores, comments, annotation queues, or corrected outputs. When a reviewed result becomes durable benchmark truth, it should be promoted into an MLflow dataset.

Argus should avoid duplicating every trace into both systems. If correlation is needed, use shared metadata such as:

- `property_id`
- `analysis_id`
- `workflow_version`
- `prompt_name`
- `prompt_version`
- `model`
- `environment`
- `langfuse_trace_id`
- `mlflow_run_id` or `mlflow_trace_id` for benchmark runs

This keeps Langfuse as the operational record and MLflow as the evaluation record.

## Local Infrastructure

The first milestone targets local Docker now and shared VM later.

The observability stack should run separately from the normal app by default. The intended developer commands are:

```bash
make dev             # app only
make observability   # Langfuse + MLflow + storage
make dev-full        # app + observability
make benchmark       # app + observability + benchmark runner
```

Docker Compose should use a separate observability profile or equivalent composition so normal development stays lightweight.

### MLflow Services

MLflow should run with production-like local persistence:

- `mlflow` tracking server
- `mlflow-postgres` for tracking metadata
- `minio` for S3-compatible artifact storage

MLflow should expose a local UI and API. The backend and benchmark scripts should use environment variables for the tracking URI and artifact settings rather than hardcoded localhost values.

### Langfuse Services

Langfuse should be self-hosted.

The local stack should follow the current Langfuse self-hosting requirements, expected to include:

- `langfuse-web`
- `langfuse-worker`
- `langfuse-postgres`
- `clickhouse`
- `redis` or `valkey`
- Blob/object storage if required by the selected Langfuse deployment path

The local Compose structure should be designed so service URLs, secrets, and persistent volumes can be moved to a shared hosted VM later.

## Backend Instrumentation

Add a focused observability module, for example `backend/app/observability.py`, to configure observability at startup.

The module should:

- Read all observability settings from environment variables.
- Enable Langfuse runtime tracing when configured.
- Avoid sending normal app traffic to MLflow by default.
- Configure MLflow only for benchmark/evaluation entrypoints.
- Attach consistent metadata to traces and runs.

The current broad MLflow setup in `backend/app/main.py` should be removed or replaced. In particular:

- Remove the hardcoded `http://127.0.0.1:5001` tracking URI.
- Avoid broad `mlflow.autolog()` for normal app startup.
- Remove or relocate route-level `@mlflow.trace` decorators if they cause normal runtime traffic to be logged to MLflow.
- Use explicit OpenAI/Langfuse instrumentation for runtime traces.
- Keep MLflow tracing and logging inside benchmark/evaluation scripts or controlled evaluation entrypoints.

Suggested environment variables:

```bash
OBSERVABILITY_ENV=local

LANGFUSE_TRACING_ENABLED=true
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=http://localhost:3000

MLFLOW_EVAL_ENABLED=true
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=argus-property-analysis
MLFLOW_S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

Exact variable names may be adjusted during implementation to match SDK requirements, but code must remain environment-driven.

## Benchmark Workflow

Benchmarks should live outside the normal API request path.

Add a `benchmarks/` or `experiments/` area for:

- Dataset management scripts.
- Evaluation runners.
- Scorer definitions.
- Prompt/workflow version metadata.
- Generated evaluation reports.

Benchmark scripts should call the same underlying property-analysis functions where possible, but with controlled inputs and explicit metadata.

Each MLflow evaluation run should log:

- Dataset name and version.
- Prompt name and version.
- Workflow version.
- Model and model parameters.
- Image/source metadata used for the run.
- Scorer names and versions.
- Aggregate metrics.
- Per-case outputs where appropriate.
- Artifacts such as reports or failure analyses.

The first infrastructure milestone does not need to create fake benchmark data. It should create the hosting, configuration, and project conventions needed to build real benchmarks from human-reviewed data later.

## Supabase Boundary

Supabase exists today and is used by the app, but schema management is informal. The repo does not currently include authoritative Supabase migrations.

The current code implies these app tables:

- `properties`
- `property_images`
- `ai_analysis`
- `geospatial_data`
- `ai_feedback`

For this observability milestone:

- Do not use Supabase for MLflow metadata.
- Do not use Supabase for Langfuse metadata.
- Do not use Supabase for traces, benchmark results, or artifacts.
- Do not add Supabase migrations as part of the observability setup.
- Document that proper Supabase migrations are needed before reviewed benchmark data depends on Supabase-derived records.

Future Supabase direction:

- Keep and expand `properties` with richer Google-derived metadata such as neighborhood, city/locality, administrative areas, postal code, address components, place ID, geocode precision, and source metadata.
- Reconsider `property_images`; storing full images or many image URLs may become heavy. The app may dynamically load imagery from APIs and persist only metadata or request parameters when reproducibility requires it.
- Persist AI analysis outputs because they are important app/domain artifacts. Link them to `property_id` and include metadata that can correlate to Langfuse traces and MLflow prompt/evaluation context.
- Pivot geospatial persistence toward canonical StatCan geographic zones such as CSD, CD, CT, DA, and related boundaries.
- Add property-to-zone mapping tables later so properties can be grouped by shared zones for future ML/data science work.
- De-emphasize or remove `ai_feedback` unless Argus needs a native correction UI independent of Langfuse and MLflow.

## Error Handling And Operational Behavior

Observability must not make the app unusable during local development.

- If Langfuse is disabled or unreachable, normal app requests should still run.
- If MLflow is disabled or unreachable, normal app requests should still run.
- Benchmark commands should fail clearly when MLflow is unavailable, because benchmark results require MLflow.
- Service startup should document required ports and persistent volumes.
- Secrets should remain in local environment files or secret tooling, not committed files.

## Testing And Verification

Initial verification should cover infrastructure and instrumentation, not benchmark quality.

Required checks:

- `make dev` starts the app without requiring observability services.
- `make observability` starts MLflow, MinIO, and Langfuse services.
- `make dev-full` starts the app and observability services together.
- A normal backend OpenAI call appears in Langfuse.
- A normal backend OpenAI call does not create an MLflow evaluation record by default.
- A sample benchmark runner can connect to MLflow and log a run/artifact to MinIO.
- Existing backend tests still pass.

Later checks:

- Human review in Langfuse can flag incorrect runtime outputs.
- Human-reviewed MLflow labels can be used in repeatable evaluation runs.
- Benchmark results can compare prompt/model/workflow versions.
- Future CI can gate regressions using MLflow evaluation outputs.

## Non-Goals For This Milestone

- Designing or migrating the full Supabase schema.
- Building a custom Argus human-review UI.
- Creating fake benchmark datasets.
- Hosting the shared VM deployment immediately.
- Adding Supabase local hosting.
- Making Supabase the storage backend for MLflow or Langfuse.
- Sending all runtime traces to both Langfuse and MLflow.

## Open Follow-Ups

These are intentionally deferred beyond the first observability milestone:

- Design formal Supabase migrations for the current app schema.
- Decide whether `property_images` should store URLs, metadata, request parameters, or nothing.
- Design StatCan zone ingestion and property-zone mapping.
- Define the first human-reviewed benchmark dataset schema in MLflow.
- Define the first evaluation scorers for property analysis accuracy.
- Decide whether an Argus-native review UI is ever needed in addition to Langfuse and MLflow review tools.
