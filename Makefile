include .env
export

.PHONY: dev backend frontend install test build check

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
