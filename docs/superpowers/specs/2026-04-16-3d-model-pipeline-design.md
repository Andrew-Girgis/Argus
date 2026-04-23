# 3D Model Generation Pipeline — Design Spec

**Goal:** Given any searched address, collect multi-angle imagery, classify the property type, synthesize architecturally consistent views via Gemini, and generate a downloadable + in-app viewable 3D model using a self-hosted Trellis GPU service.

**Architecture:** Two new sub-pipelines bolt onto the existing Argus property search flow. Sub-pipeline 1 (image collection + type classification) runs on every search. Sub-pipeline 2 (synthesis + 3D generation) runs on-demand via a "Generate 3D Model" button.

**Tech Stack:** FastAPI, Google Maps Static API (multi-angle + oblique), Gemini 2.0 Flash (image generation), Trellis (Microsoft MSRA, self-hosted on GPU), Supabase Storage (GLB files), `<model-viewer>` web component (Three.js-backed, Google), React/TypeScript frontend.

---

## Sub-pipeline 1: Image Collection + Property Type Classification

### Image Collection (replaces current 2-image fetch)

All 13 images are collected on every property search and saved to the `property_images` table with an extended `image_type` value and a `heading` column.

**Street View — 8 angles**
- API: Google Street View Static API
- Headings: 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°
- Params: `size=640x480`, `pitch=0`, `fov=90`
- `image_type`: `street_view`, `heading`: the degree value
- Only saved if Street View metadata returns `status: OK` for that heading

**Satellite top-down — 1 image**
- API: Google Maps Static API
- Params: `maptype=satellite`, `zoom=19`, `size=640x640`, `tilt=0`
- `image_type`: `satellite`, `heading`: null

**Oblique aerial — 4 images**
- API: Google Maps Static API
- Params: `maptype=satellite`, `zoom=18`, `size=640x640`, `tilt=45`
- Headings: 0°, 90°, 180°, 270°
- `image_type`: `oblique`, `heading`: the degree value

**New functions in `backend/app/services/google_maps.py`:**
- `fetch_multi_angle_street_view(lat, lon, address) -> ServiceResult` — returns list of `{url, heading}`, skips headings with no Street View coverage
- `fetch_oblique_tiles(lat, lon) -> ServiceResult` — returns list of `{url, heading}`

### Property Type Classification

A lightweight first-pass classification runs immediately after images are collected, before the full AI analysis. It uses GPT-4o with the street view 0° image + satellite image.

**New service: `backend/app/services/property_type.py`**
- `classify(street_view_url, satellite_url) -> ServiceResult`
- Returns: `{"class": "residential" | "commercial" | "industrial" | "poi", "confidence": float}`
- Result stored in `properties.property_type_class` column (new)

**Effect on AI analysis cards (frontend):**
Rather than maintaining hard-coded field sets per type, the property type class is passed as context to the GPT-4o vision prompt. The model returns `null` for fields that don't apply (e.g., `has_fenced_yard` for a commercial property). The frontend already hides null-value cards — no additional frontend logic needed.

**Effect on 3D synthesis:**
The property type class is passed to Gemini so it generates appropriate view angles (e.g., more oblique angles for a commercial/industrial building, street-level elevations for residential).

---

## Sub-pipeline 2: On-Demand 3D Model Generation

Triggered by a "Generate 3D Model" button that appears in `PropertyHero` after a successful search. The full round-trip takes ~90–120 seconds.

### Stage 1 — Gemini Multi-View Synthesis

**New service: `backend/app/services/synthesis.py`**
- `synthesize_views(images: list[dict], analysis: dict, property_type_class: str) -> ServiceResult`

**Inputs sent to Gemini:**
- Up to 9 real images: street view 0°, 90°, 180°, 270° + satellite + 4 oblique tiles
- Property metadata as text: address, property type, stories, exterior material, roof type, approximate age, condition
- Requested outputs: front elevation, rear elevation, left side elevation, right side elevation, corner perspective, aerial perspective (6 total)

**Gemini call:**
- Model: `gemini-2.0-flash-exp` with `response_modalities=["TEXT", "IMAGE"]`
- Prompt directs Gemini to produce photorealistic architectural renders — consistent lighting, no obstructions, full building visible, white background
- Returns 6 image bytes (base64-decoded) passed directly to Trellis; not stored permanently

### Stage 2 — Trellis 3D Reconstruction

**New service: `backend/app/services/model_3d.py`**
- `generate(synthesis_images: list[bytes], property_id: str) -> ServiceResult`
- Posts the 6 synthetic view images to the Trellis HTTP API
- Trellis returns a GLB file (textured mesh)
- GLB uploaded to Supabase Storage: `models/{property_id}/model.glb`
- Returns: `{"glb_url": "...", "status": "ready"}`

**Trellis setup:**
- Repo: `github.com/microsoft/TRELLIS`
- Requires: CUDA GPU with ≥16GB VRAM (RTX 3090 / A100 / etc.), CUDA 11.8+, Python 3.10
- Run as a FastAPI wrapper (thin service on the same GPU machine) exposing `POST /generate` accepting multipart image upload, returning GLB binary
- Config: `TRELLIS_API_URL` env var (e.g., `http://localhost:8001` during dev, GPU instance URL in prod)
- GPU hosting options for prod: RunPod, Lambda Labs, Vast.ai (~$0.50–$1.50/hr, spin up on demand)

### Async Job Flow

Generation is too slow for a synchronous HTTP response. Flow:

1. `POST /api/v1/property/{property_id}/generate-3d` — creates a record in `model_3d` table with `status: "generating"`, starts a FastAPI `BackgroundTask`, returns `{job_id, status: "generating"}` immediately
2. Background task runs synthesis → Trellis → uploads GLB → updates `model_3d` row to `status: "ready"` + `glb_url`
3. `GET /api/v1/property/{property_id}/3d-model` — returns current `{status, glb_url}`. Frontend polls every 3s until `status === "ready"`

**New route file: `backend/app/routes/model3d.py`**
- `POST /api/v1/property/{property_id}/generate-3d`
- `GET /api/v1/property/{property_id}/3d-model`

---

## Frontend Changes

### New Components

**`ModelViewer.tsx`**
- Wraps the `<model-viewer>` web component (Google, Three.js-backed, no extra dependencies beyond the script tag)
- Props: `glbUrl: string`
- Features: orbit/rotate/zoom controls, environment lighting, "Download GLB" anchor button
- Renders in a `h-[500px]` panel below `PropertyHero`, only visible when model is ready

**`Generate3DButton.tsx`**
- Placed inside `PropertyHero` bottom-right
- States:
  - `idle`: "Generate 3D Model" button (primary outlined)
  - `generating`: spinner + "Generating model… (~90s)"
  - `ready`: hidden (model viewer takes over)
  - `error`: "Generation failed — retry"
- On click: POST to generate endpoint, then polls GET every 3s

### Modified Components

**`PropertyHero.tsx`** — receives `propertyId` prop, renders `<Generate3DButton>` and conditionally `<ModelViewer>`

**`AIInsights.tsx`** — already hides null-value cards; no change needed once the vision prompt is type-aware

**`App.tsx`** — passes `propertyId` to `PropertyHero`

---

## Data / Storage Changes

### Supabase Table Changes

**`properties` table** — add column:
```sql
ALTER TABLE properties ADD COLUMN property_type_class TEXT;
```

**`property_images` table** — add column:
```sql
ALTER TABLE property_images ADD COLUMN heading INTEGER;
```
Existing `image_type` values (`street_view`, `satellite`) are kept; new values `oblique` added.

**New `model_3d` table:**
```sql
CREATE TABLE model_3d (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID REFERENCES properties(id),
  status TEXT NOT NULL DEFAULT 'generating', -- generating | ready | failed
  glb_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);
```

### Supabase Storage

New public bucket: `models`
- Path pattern: `models/{property_id}/model.glb`
- Public read, authenticated write

---

## Scope Note — Decomposition

This feature naturally splits into two shippable increments:

**Increment 1:** Multi-angle image collection + property type classification + type-aware analysis cards. Ships without any 3D. Standalone value: richer imagery for the existing AI analysis.

**Increment 2:** Gemini synthesis + Trellis 3D generation + model viewer. Depends on Increment 1's image collection but is otherwise independent.

The implementation plan should treat these as two separate tasks with a clear hand-off.
