# Argus — Agent Notes

## Project Overview

Full-stack property intelligence app. Backend (Python/FastAPI) takes lat/lon, fetches Google Maps imagery, runs OpenAI Vision analysis, computes geospatial data, and returns a property profile. Frontend (React/Vite) displays results with Mapbox maps.

## Commands

```bash
make dev          # Install deps + start both servers (backend :8000, frontend :5173)
make backend      # Backend only: cd backend && uv run uvicorn app.main:app --reload
make frontend     # Frontend only: generates frontend/.env, then cd frontend && vp dev
make test         # cd backend && uv run pytest -v
make check        # cd frontend && vp check  (lint + format + typecheck)
make build        # cd frontend && vp build
```

## Architecture

- **Backend** (`backend/app/`): FastAPI app, entrypoint `app.main:app`
  - Routes at `/api/v1/property` and `/api/v1/feedback`
  - Services in `app/services/`: each returns `ServiceResult(data, error, source)` — never raises, always returns a result
  - Config via `pydantic_settings` in `app/config.py`, reads from `../.env` (project root)
  - SAM2 segmentation is optional (conditional import — stubs gracefully when missing)

- **Frontend** (`frontend/src/`): React + Vite-plus + shadcn/ui (base-nova style) + Tailwind v4
  - Path alias: `@` → `./src`
  - API client in `src/lib/api.ts`, types in `src/lib/types.ts`
  - shadcn components in `src/components/ui/`, app components alongside

## Critical Details

- **vite-plus, not vite**: Frontend uses `vite-plus` (a Vite fork). Commands go through `~/.vite-plus/bin/vp`, not `npx vite`. The `vp` binary must be installed before `make dev` / `make frontend` / `make check` / `make build` will work.
- **Environment**: Root `.env` is the single source of truth. `make dev` and `make frontend` auto-generate `frontend/.env` from it. Never edit `frontend/.env` directly — it's gitignored and overwritten.
- **Backend env loading**: `app/main.py` explicitly loads root `.env` via `python-dotenv` (`Path(__file__).resolve().parent.parent.parent / ".env"`). The pydantic Settings class also reads `../.env`.
- **MAPBOX_API_KEY vs MAPBOX_ACCESS_TOKEN**: The env var is `MAPBOX_API_KEY` everywhere. `app/config.py` aliases it to `MAPBOX_ACCESS_TOKEN` via `validation_alias`.
- **SUPABASE_SECRET_KEY** (env var) maps to `SUPABASE_SECRET_KEY` in Settings — note the `.env.example` also says `SUPABASE_SECRET_KEY`, but Docker compose and config use this same name.
- **Python 3.13+ required**, Node 20+ required.
- **async tests**: Uses `pytest-asyncio` with `asyncio_mode = "auto"`. Test services by patching `app.routes.<route>.<module>.<func>` with `AsyncMock`.

## Testing

```bash
cd backend && uv run pytest -v              # all tests
cd backend && uv run pytest tests/test_endpoints.py::test_health_check  # single test
```

No frontend tests exist currently.

## Frontend Lint/Typecheck

```bash
cd frontend && ~/.vite-plus/bin/vp check    # runs oxc + typescript + unicorn + react lints
```

The lint config is in `vite.config.ts` under `defineConfig({ lint: ... })`. `src/components/ui/**` files have relaxed `react/only-export-components` rule.