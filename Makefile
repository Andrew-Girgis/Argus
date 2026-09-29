include .env
export

.PHONY: dev backend backend-sam sam frontend install test build check

# Start both backend and frontend in one command
dev: install env
	@echo "Starting Argus..."
	@trap 'kill 0' EXIT; \
	cd backend && uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 & \
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
	cd backend && uv run python -m uvicorn app.main:app --reload --host 0.0.0.0

# Run backend with local Docker SAM service enabled
backend-sam:
	cd backend && SAM_SERVICE_URL=http://localhost:8100 uv run python -m uvicorn app.main:app --reload --host 0.0.0.0

# Run optional SAM service only. Requires HF_TOKEN in .env.
sam:
	docker compose --profile sam build sam
	docker compose --profile sam up --force-recreate sam

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
