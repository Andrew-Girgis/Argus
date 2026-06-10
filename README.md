# Argus -- Address Intelligence

Full-stack application that takes a street address or lat/long and returns a comprehensive property profile using Google Maps imagery, AI vision analysis, and geospatial data.

## Tech Stack

- **Frontend:** React + Vite, shadcn/ui, Tailwind CSS, react-map-gl, Recharts, TanStack Query
- **Backend:** Python FastAPI, OpenAI Vision, Postgres cache/persistence, optional SAM 3.1 segmentation
- **Infrastructure:** Docker Compose with Postgres and pgAdmin

## Local Setup

### Prerequisites

- Node.js 20+
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker (required for Postgres/pgAdmin; optional for local-only frontend/backend)

### 1. Clone the repo

```bash
git clone <repo-url>
cd Argus
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Fill in your API keys in .env
```

For secrets, prefer runtime injection with `s env` instead of committing local values:

```bash
s env OPENAI_API_KEY LANGFUSE_PUBLIC_KEY LANGFUSE_SECRET_KEY LANGFUSE_BASE_URL -- make backend
```

### 3. Run the app

```bash
make dev
```

This installs all dependencies and starts both the backend (http://localhost:8000) and frontend (http://localhost:5173) in parallel.

Other commands:

| Command       | Description                        |
|---------------|------------------------------------|
| `make dev`    | Install deps + start both servers  |
| `make test`   | Run backend integration tests      |
| `make check`  | Lint, format, typecheck frontend   |
| `make build`  | Production build frontend          |

## Docker Compose

```bash
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:5173         |
| Backend  | http://localhost:8000         |
| API Docs | http://localhost:8000/docs    |
| pgAdmin  | http://localhost:5050         |

SAM 3.1 is behind a Compose profile because it requires gated Hugging Face checkpoint access and CUDA-capable hardware:

```bash
make sam
```

When running the backend locally with `make backend`, use the local SAM URL:

```bash
make backend-sam
```

When running the backend inside Docker Compose, use the Docker service URL:

```bash
SAM_SERVICE_URL=http://sam:8100 s HF_TOKEN -- docker compose --profile sam up --build
```

## Environment Variables

| Variable                    | Purpose                                      | Where to get it                                      |
|-----------------------------|----------------------------------------------|------------------------------------------------------|
| `GOOGLE_MAPS_API_KEY`       | Street View, Satellite imagery, Geocoding    | [Google Cloud Console](https://console.cloud.google.com/) |
| `MAPBOX_API_KEY`            | Map display and geocoding in the frontend    | [Mapbox Account](https://account.mapbox.com/)        |
| `OPENAI_API_KEY`            | Vision/property intelligence analysis        | [OpenAI Platform](https://platform.openai.com/)      |
| `OPENAI_VISION_MODEL`       | Configurable OpenAI model for image analysis | OpenAI model name                                    |
| `DATABASE_URL`              | Backend Postgres connection URL              | Local/Docker Postgres                                |
| `LANGFUSE_*`                | External Langfuse Cloud tracing              | Langfuse project settings                            |
| `HF_TOKEN`                  | Gated SAM 3.1 checkpoint access              | Hugging Face settings                                |

## API Reference

### `POST /api/v1/property`

Full property analysis pipeline. Reverse geocodes coordinates, checks the Postgres cache by normalized address, fetches imagery on cache miss/stale, runs AI analysis, optionally calls SAM segmentation, and finds nearby POIs.

**Request:**
```json
{
  "lat": 43.6532,
  "lon": -79.3832
}
```

**Response:** Complete property profile including images, AI analysis, and nearby points of interest.

---

### `GET /api/v1/property/images`

Fetch Street View and Satellite images for a location.

**Query parameters:** `lat`, `lng`, `address`

**Response:** URLs or base64-encoded images for the requested location.

---

### `POST /api/v1/property/analyze`

Run AI vision analysis on property images.

**Request:**
```json
{
  "images": ["<base64 or URL>"],
  "lat": 43.6532,
  "lng": -79.3832
}
```

**Response:** Structured AI analysis of the property (building type, condition, features, etc.).

---

### `GET /api/v1/property/pois`

Find nearby points of interest via OpenStreetMap/Overpass.

**Query parameters:** `lat`, `lng`, `radius` (metres), `category`

**Response:** List of nearby POIs with name, category, and distance.

---

### `GET /health`

Health check endpoint.

**Response:**
```json
{ "status": "ok" }
```

## Data Sources

| Source | Purpose | Key required? |
|--------|---------|---------------|
| Google Maps Static API | Street View + Satellite imagery | Yes |
| OpenAI Vision API | Property image analysis | Yes |
| SAM 3.1 | Optional text-prompted segmentation | HF token + local GPU for full service |
| Overpass API / OpenStreetMap | Nearby POIs | No |
| Postgres | Cache and persistence | Docker/local DB |

## Project Structure

```
Argus/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   └── services/
│   │       └── __init__.py
│   ├── Dockerfile
│   └── pyproject.toml
├── sam-service/             # Optional SAM 3.1 service contract
├── frontend/               # React + Vite app (to be scaffolded)
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```
