-include .env
export

.PHONY: dev backend frontend install test build check docker-up docker-down docker-check observability observability-down observability-check dev-full benchmark

# Start both backend and frontend in one command
dev: install env
	@echo "Starting Argus..."
	@trap 'kill 0' EXIT; \
	cd backend && uv run uvicorn app.main:app --reload & \
	cd frontend && ~/.vite-plus/bin/vp dev & \
	wait

# Generate frontend .env from root .env
env:
	@echo "VITE_GOOGLE_MAPS_API_KEY=$(GOOGLE_MAPS_API_KEY)" > frontend/.env
	@echo "VITE_MAPBOX_API_KEY=$(MAPBOX_API_KEY)" >> frontend/.env
	@echo "VITE_API_URL=http://localhost:8000" >> frontend/.env

# Install all dependencies
install:
	@cd backend && uv sync
	@cd frontend && ~/.vite-plus/bin/vp install

# Run backend only
backend:
	cd backend && uv run uvicorn app.main:app --reload

# Run frontend only
frontend: env
	cd frontend && ~/.vite-plus/bin/vp dev

# Run backend tests
test:
	cd backend && uv run pytest -v

# Production build
build:
	cd frontend && ~/.vite-plus/bin/vp build

# Lint + format + typecheck frontend
check:
	cd frontend && ~/.vite-plus/bin/vp check

# Portable container workflows for macOS and Linux
docker-up:
	docker compose up --build --wait

docker-down:
	docker compose down

docker-check:
	docker compose config --quiet
	docker compose -f docker-compose.observability.yml config --quiet

# MLflow + Langfuse and their backing stores
observability:
	docker compose -p argus-observability -f docker-compose.observability.yml up --build --wait

observability-down:
	docker compose -p argus-observability -f docker-compose.observability.yml down

observability-check: observability
	cd backend && \
		MLFLOW_EVAL_ENABLED=true \
		MLFLOW_TRACKING_URI=http://localhost:$${MLFLOW_PORT:-5001} \
		MLFLOW_S3_ENDPOINT_URL=http://localhost:$${MINIO_API_PORT:-9000} \
		AWS_ACCESS_KEY_ID=$${MINIO_ROOT_USER:-argus_minio} \
		AWS_SECRET_ACCESS_KEY=$${MINIO_ROOT_PASSWORD:-argus_minio_local_password} \
		LANGFUSE_BASE_URL=http://localhost:$${LANGFUSE_PORT:-3000} \
		LANGFUSE_PUBLIC_KEY=$${LANGFUSE_PUBLIC_KEY:-lf_pk_argus_local_testing_only} \
		LANGFUSE_SECRET_KEY=$${LANGFUSE_SECRET_KEY:-lf_sk_argus_local_testing_only} \
		uv run python ../benchmarks/smoke_observability.py

dev-full:
	docker compose -p argus-full -f docker-compose.yml -f docker-compose.observability.yml up --build --wait

benchmark: observability-check
