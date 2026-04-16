# Argus -- Address Intelligence

Full-stack application that takes a street address or lat/long and returns a comprehensive property profile using Google Maps imagery, AI vision analysis, and geospatial data.

## Tech Stack

- **Frontend:** React + Vite, shadcn/ui, Tailwind CSS, react-map-gl, Recharts, TanStack Query
- **Backend:** Python FastAPI, OpenAI Vision (gpt-4o), SAM2 segmentation, Supabase
- **Infrastructure:** Docker Compose

## Local Setup

### Prerequisites

- Node.js 20+
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker (optional)

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

## Environment Variables

| Variable                    | Purpose                                      | Where to get it                                      |
|-----------------------------|----------------------------------------------|------------------------------------------------------|
| `GOOGLE_MAPS_API_KEY`       | Street View, Satellite imagery, Geocoding    | [Google Cloud Console](https://console.cloud.google.com/) |
| `MAPBOX_API_KEY`            | Map display and geocoding in the frontend    | [Mapbox Account](https://account.mapbox.com/)        |
| `OPENAI_API_KEY`            | GPT-4o Vision for property image analysis    | [OpenAI Platform](https://platform.openai.com/)     |
| `SUPABASE_URL`              | PostgreSQL database URL                      | [Supabase Dashboard](https://supabase.com/dashboard) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key (server-side only) | [Supabase Dashboard](https://supabase.com/dashboard) |

## API Reference

### `POST /api/v1/property`

Full property analysis pipeline. Fetches imagery, runs AI analysis, computes isochrones, and finds nearby POIs.

**Request:**
```json
{
  "address": "123 Main St, Toronto, ON",
  "lat": 43.6532,
  "lng": -79.3832
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
| OpenAI Vision API | Property image analysis (gpt-4o) | Yes |
| SAM2 | Image segmentation | No (runs locally) |
| Overpass API / OpenStreetMap | Nearby POIs | No |
| Supabase | PostgreSQL persistence | Yes |

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
├── frontend/               # React + Vite app (to be scaffolded)
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```
