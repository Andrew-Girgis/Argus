# 3D Model Generation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an on-demand "Generate 3D Model" button to the property results page. Clicking it triggers a backend pipeline that feeds the 13 collected property images through Gemini (multi-view synthesis) and then a self-hosted Trellis GPU service (3D reconstruction), uploads the resulting GLB file to Supabase Storage, and displays it in an in-app `<model-viewer>` with a download button.

**Architecture:** A new async FastAPI route (`POST /api/v1/property/{id}/generate-3d`) starts a `BackgroundTask` and returns immediately. The background task runs: image fetch → Gemini synthesis (6 sequential calls, one per view angle) → Trellis HTTP call → Supabase Storage upload → status update to `ready`. The frontend polls `GET /api/v1/property/{id}/3d-model` every 3 seconds until `status === "ready"`, then renders `<model-viewer>`. Trellis runs as a separate thin FastAPI service on a GPU machine.

**Pre-requisite:** Plan 1 (image collection + property type classification) must be complete — this plan depends on `property_type_class`, the 13-image collection, and the `get_property_images` Supabase function defined here.

**Tech Stack:** Python 3.13, FastAPI BackgroundTasks, `google-genai` SDK, httpx, Supabase Storage, Trellis (microsoft/TRELLIS — self-hosted on CUDA GPU), `<model-viewer>` web component (Google), React/TypeScript.

---

## File Map

| Action | Path |
|--------|------|
| Create | `backend/app/services/synthesis.py` |
| Create | `backend/app/services/model_3d.py` |
| Create | `backend/app/routes/model3d.py` |
| Create | `backend/trellis_service/main.py` |
| Create | `backend/tests/test_synthesis.py` |
| Create | `backend/tests/test_model_3d.py` |
| Create | `frontend/src/components/ModelViewer.tsx` |
| Create | `frontend/src/components/Generate3DButton.tsx` |
| Modify | `backend/app/config.py` |
| Modify | `backend/pyproject.toml` |
| Modify | `backend/app/models/schemas.py` |
| Modify | `backend/app/services/supabase.py` |
| Modify | `backend/app/main.py` |
| Modify | `frontend/src/lib/api.ts` |
| Modify | `frontend/src/lib/types.ts` |
| Modify | `frontend/src/components/PropertyHero.tsx` |
| Modify | `frontend/src/App.tsx` |
| Modify | `frontend/index.html` |

---

### Task 1: Add dependencies and config vars

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`
- Modify: `/.env.example` (project root)

- [ ] **Step 1: Add google-genai to backend dependencies**

In `backend/pyproject.toml`, add to the `dependencies` list:

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
    "google-genai>=1.0.0",       # NEW — Gemini SDK
]
```

- [ ] **Step 2: Install the new dependency**

```bash
cd backend && uv sync
```

Expected: `google-genai` package installed, no errors.

- [ ] **Step 3: Add GEMINI_API_KEY and TRELLIS_API_URL to config.py**

```python
# backend/app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_MAPS_API_KEY: str = ""
    MAPBOX_ACCESS_TOKEN: str = Field(default="", validation_alias="MAPBOX_API_KEY")
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""                          # NEW
    TRELLIS_API_URL: str = "http://localhost:8001"    # NEW — GPU service URL
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
```

- [ ] **Step 4: Add vars to .env.example**

In the project root `.env.example`, add:

```bash
# Gemini (multi-view synthesis)
GEMINI_API_KEY=

# Trellis GPU service (3D model generation)
# Set to the URL of your GPU machine running trellis_service/main.py
TRELLIS_API_URL=http://localhost:8001
```

Also add `GEMINI_API_KEY=your_key_here` to the root `.env` file (never commit this).

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/config.py .env.example
git commit -m "feat: add google-genai dep and GEMINI_API_KEY/TRELLIS_API_URL config"
```

---

### Task 2: DB migration and Supabase Storage setup

**Files:** None (SQL + Supabase Dashboard UI)

- [ ] **Step 1: Create model_3d table**

In Supabase Dashboard → SQL Editor:

```sql
CREATE TABLE IF NOT EXISTS model_3d (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'generating',  -- generating | ready | failed
    glb_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_model_3d_property_id ON model_3d(property_id);
```

- [ ] **Step 2: Create Supabase Storage bucket**

In Supabase Dashboard → Storage → New bucket:
- Name: `models`
- Public: **Yes** (GLB files need to be publicly readable by the browser)
- Allowed MIME types: `model/gltf-binary`

- [ ] **Step 3: Verify**

```sql
SELECT table_name FROM information_schema.tables WHERE table_name = 'model_3d';
```

Expected: 1 row.

- [ ] **Step 4: Commit note**

```bash
git commit --allow-empty -m "chore: applied model_3d table migration and created models storage bucket"
```

---

### Task 3: Add Model3D schema to schemas.py

**Files:**
- Modify: `backend/app/models/schemas.py`

- [ ] **Step 1: Add the Model3D model at the end of the database models section**

```python
class Model3D(BaseModel):
    id: UUID
    property_id: UUID
    status: str   # generating | ready | failed
    glb_url: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
```

- [ ] **Step 2: Run all tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: add Model3D schema"
```

---

### Task 4: Add model_3d Supabase functions

**Files:**
- Modify: `backend/app/services/supabase.py`

- [ ] **Step 1: Add get_property_images()**

```python
async def get_property_images(property_id: str) -> ServiceResult:
    """Fetch all image records for a property, ordered by image_type then heading."""
    try:
        client = _get_client()
        result = (
            client.table("property_images")
            .select("*")
            .eq("property_id", property_id)
            .order("image_type")
            .execute()
        )
        return ServiceResult(data=result.data or [], error=None, source="supabase")
    except Exception as exc:
        logger.exception("Error fetching property images")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 2: Add get_property_analysis()**

```python
async def get_property_analysis(property_id: str) -> ServiceResult:
    """Fetch the most recent AI analysis record for a property."""
    try:
        client = _get_client()
        result = (
            client.table("ai_analysis")
            .select("*")
            .eq("property_id", property_id)
            .order("analyzed_at", desc=True)
            .limit(1)
            .execute()
        )
        data = result.data[0] if result.data else {}
        return ServiceResult(data=data, error=None, source="supabase")
    except Exception as exc:
        logger.exception("Error fetching property analysis")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 3: Add save_model_3d()**

```python
async def save_model_3d(job_id: str, property_id: str) -> ServiceResult:
    """Create a model_3d record with status=generating."""
    try:
        client = _get_client()
        record = {
            "id": job_id,
            "property_id": property_id,
            "status": "generating",
        }
        result = client.table("model_3d").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving model_3d record")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 4: Add update_model_3d_status()**

```python
async def update_model_3d_status(
    job_id: str,
    status: str,
    glb_url: str | None = None,
) -> ServiceResult:
    """Update model_3d status. Sets completed_at when status is ready or failed."""
    try:
        client = _get_client()
        updates: dict[str, Any] = {"status": status}
        if status in ("ready", "failed"):
            updates["completed_at"] = datetime.now(timezone.utc).isoformat()
        if glb_url:
            updates["glb_url"] = glb_url
        result = (
            client.table("model_3d")
            .update(updates)
            .eq("id", job_id)
            .execute()
        )
        return ServiceResult(
            data=result.data[0] if result.data else None,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error updating model_3d status")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 5: Add get_model_3d()**

```python
async def get_model_3d(property_id: str) -> ServiceResult:
    """Fetch the most recent model_3d record for a property."""
    try:
        client = _get_client()
        result = (
            client.table("model_3d")
            .select("*")
            .eq("property_id", property_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        data = result.data[0] if result.data else None
        return ServiceResult(data=data, error=None, source="supabase")
    except Exception as exc:
        logger.exception("Error fetching model_3d")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 6: Add upload_model_glb()**

```python
async def upload_model_glb(property_id: str, glb_bytes: bytes) -> ServiceResult:
    """Upload a GLB file to the 'models' Supabase Storage bucket."""
    try:
        client = _get_client()
        path = f"{property_id}/model.glb"
        client.storage.from_("models").upload(
            path,
            glb_bytes,
            file_options={"content-type": "model/gltf-binary", "upsert": "true"},
        )
        url = client.storage.from_("models").get_public_url(path)
        return ServiceResult(data={"url": url}, error=None, source="supabase")
    except Exception as exc:
        logger.exception("Error uploading GLB to Supabase Storage")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 7: Run all tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/supabase.py
git commit -m "feat: add model_3d Supabase functions (get images, save/update/get model, upload GLB)"
```

---

### Task 5: Gemini synthesis service

**Files:**
- Create: `backend/app/services/synthesis.py`
- Create: `backend/tests/test_synthesis.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_synthesis.py
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.services.synthesis import synthesize_views, _build_metadata_text


def test_build_metadata_text_includes_known_fields():
    analysis = {
        "stories": "2",
        "exterior_material": "Brick",
        "roof_type": "Gable",
        "home_style": "Colonial",
    }
    text = _build_metadata_text(analysis, "residential")
    assert "residential" in text
    assert "2" in text
    assert "Brick" in text
    assert "Gable" in text
    assert "Colonial" in text


def test_build_metadata_text_skips_none_fields():
    analysis = {"stories": None, "exterior_material": "Stone"}
    text = _build_metadata_text(analysis, "residential")
    assert "None" not in text
    assert "Stone" in text


async def test_synthesize_views_returns_error_when_images_unfetchable():
    with patch("app.services.synthesis.httpx.AsyncClient") as MockClient:
        mock_cm = AsyncMock()
        mock_cm.get = AsyncMock(side_effect=Exception("connection refused"))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_cm)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await synthesize_views(
            image_urls=["http://example.com/img.jpg"],
            analysis={},
            property_type_class="residential",
        )

    assert result.data is None
    assert result.error is not None
    assert "No images" in result.error


async def test_synthesize_views_returns_6_images_on_success():
    # Mock image fetch
    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.content = b"fakejpegbytes"

    # Mock Gemini response part with inline image data
    mock_part = MagicMock()
    mock_part.inline_data = MagicMock()
    mock_part.inline_data.data = b"fakeimagebytes"

    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]

    mock_gemini_response = MagicMock()
    mock_gemini_response.candidates = [mock_candidate]

    with (
        patch("app.services.synthesis.httpx.AsyncClient") as MockClient,
        patch("app.services.synthesis.genai.Client") as MockGenai,
    ):
        mock_cm = AsyncMock()
        mock_cm.get = AsyncMock(return_value=mock_http_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_cm)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content = MagicMock(return_value=mock_gemini_response)
        MockGenai.return_value = mock_genai_client

        result = await synthesize_views(
            image_urls=["http://example.com/img.jpg"],
            analysis={"stories": "2", "exterior_material": "Brick"},
            property_type_class="residential",
        )

    assert result.error is None
    assert result.data is not None
    assert len(result.data) == 6
    views = [img["view"] for img in result.data]
    assert "front" in views
    assert "rear" in views
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_synthesis.py -v
```

Expected: FAIL — `synthesis` module not found.

- [ ] **Step 3: Create synthesis.py**

```python
# backend/app/services/synthesis.py
import logging

import httpx
from google import genai
from google.genai import types

from app.config import settings
from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)

# Six architectural views to synthesize — one Gemini call each
_VIEW_PROMPTS = [
    ("front",      "Generate a photorealistic front elevation view of this building. Show the full front facade, entrance, and street-facing features. Consistent daylight, neutral background."),
    ("rear",       "Generate a photorealistic rear elevation view of this building. Show the full back of the building, including any yard features, decks, or rear-facing elements."),
    ("left_side",  "Generate a photorealistic left side elevation view of this building as seen from the street."),
    ("right_side", "Generate a photorealistic right side elevation view of this building as seen from the street."),
    ("corner",     "Generate a photorealistic corner perspective of this building showing both the front-left corner, capturing both the front and left side facades simultaneously."),
    ("aerial",     "Generate a photorealistic bird's-eye aerial perspective of this building from a 45-degree angle, showing the roof, lot boundaries, driveway, and surrounding yard."),
]

_SYSTEM_CONTEXT = """You are an architectural visualization expert.
Use the provided reference photos to understand the building's form, materials, and features.
Produce a single photorealistic architectural rendering per request.
The building must be the primary subject. Use neutral/white background.
Maintain architectural accuracy — do not invent features not present in the reference photos."""


def _build_metadata_text(analysis: dict, property_type_class: str) -> str:
    lines = [f"Property type: {property_type_class}"]
    field_labels = [
        ("stories",           "Stories"),
        ("exterior_material", "Exterior material"),
        ("roof_type",         "Roof type"),
        ("home_style",        "Architectural style"),
        ("approximate_age",   "Approximate age"),
        ("condition_estimate","Condition"),
    ]
    for field, label in field_labels:
        val = analysis.get(field)
        if val is not None:
            lines.append(f"{label}: {val}")
    if analysis.get("has_garage"):
        lines.append("Has garage: Yes")
    if analysis.get("has_pool"):
        lines.append("Has pool: Yes")
    return "\n".join(lines)


async def _fetch_bytes(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.content
    except Exception:
        pass
    return None


async def synthesize_views(
    image_urls: list[str],
    analysis: dict,
    property_type_class: str,
) -> ServiceResult:
    """Use Gemini to synthesize 6 consistent architectural renders from property images.

    Makes 6 sequential Gemini API calls — one per view angle.
    Returns a list of {"view": str, "bytes": bytes} dicts.
    """
    try:
        # Fetch up to 9 images (best quality within Gemini's context limit)
        image_bytes_list: list[bytes] = []
        for url in image_urls[:9]:
            b = await _fetch_bytes(url)
            if b:
                image_bytes_list.append(b)

        if not image_bytes_list:
            return ServiceResult(
                data=None,
                error="No images could be fetched for synthesis",
                source="gemini_synthesis",
            )

        metadata = _build_metadata_text(analysis, property_type_class)
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        synthesis_images: list[dict] = []

        for view_name, view_prompt in _VIEW_PROMPTS:
            prompt_text = f"{_SYSTEM_CONTEXT}\n\nKnown characteristics:\n{metadata}\n\nTask: {view_prompt}"

            # Build content parts: all reference images + the prompt text
            parts: list[types.Part] = [
                types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img))
                for img in image_bytes_list
            ]
            parts.append(types.Part(text=prompt_text))

            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[types.Content(parts=parts)],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )

            # Extract the first image part from the response
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    synthesis_images.append({
                        "view": view_name,
                        "bytes": part.inline_data.data,
                    })
                    break

        if not synthesis_images:
            return ServiceResult(
                data=None,
                error="Gemini returned no image content",
                source="gemini_synthesis",
            )

        return ServiceResult(data=synthesis_images, error=None, source="gemini_synthesis")

    except Exception as exc:
        logger.exception("Error during Gemini multi-view synthesis")
        return ServiceResult(data=None, error=str(exc), source="gemini_synthesis")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_synthesis.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/synthesis.py backend/tests/test_synthesis.py
git commit -m "feat: add Gemini multi-view synthesis service"
```

---

### Task 6: Trellis client service

**Files:**
- Create: `backend/app/services/model_3d.py`
- Create: `backend/tests/test_model_3d.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_model_3d.py
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.services.model_3d import generate


async def test_generate_returns_glb_bytes_on_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"GLB_BINARY_DATA"
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.model_3d.httpx.AsyncClient") as MockClient:
        mock_cm = AsyncMock()
        mock_cm.post = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_cm)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await generate([b"img1bytes", b"img2bytes"])

    assert result.error is None
    assert result.data is not None
    assert result.data["glb_bytes"] == b"GLB_BINARY_DATA"


async def test_generate_returns_error_on_timeout():
    import httpx as _httpx

    with patch("app.services.model_3d.httpx.AsyncClient") as MockClient:
        mock_cm = AsyncMock()
        mock_cm.post = AsyncMock(side_effect=_httpx.TimeoutException("timeout"))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_cm)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await generate([b"img1bytes"])

    assert result.data is None
    assert result.error is not None
    assert "timed out" in result.error.lower()


async def test_generate_returns_error_on_empty_input():
    result = await generate([])

    assert result.data is None
    assert result.error is not None
    assert "No synthesis images" in result.error
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_model_3d.py -v
```

Expected: FAIL — `model_3d` module not found.

- [ ] **Step 3: Create model_3d.py**

```python
# backend/app/services/model_3d.py
import logging

import httpx

from app.config import settings
from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)


async def generate(synthesis_images: list[bytes]) -> ServiceResult:
    """Send synthesized view images to the Trellis GPU service; receive a GLB file.

    The Trellis service must be running at settings.TRELLIS_API_URL.
    It exposes POST /generate accepting multipart image files and returning GLB binary.
    See trellis_service/main.py for the GPU-side wrapper.
    """
    if not synthesis_images:
        return ServiceResult(
            data=None,
            error="No synthesis images provided to 3D generator",
            source="trellis",
        )

    try:
        # Send all synthesis images; Trellis will use the first (front view) if
        # its pipeline only supports single-image input in the installed version.
        files = [
            ("images", (f"view_{i}.jpg", img_bytes, "image/jpeg"))
            for i, img_bytes in enumerate(synthesis_images)
        ]

        async with httpx.AsyncClient(timeout=300.0) as client:  # 5-min timeout for GPU inference
            response = await client.post(
                f"{settings.TRELLIS_API_URL}/generate",
                files=files,
            )
            response.raise_for_status()

        return ServiceResult(
            data={"glb_bytes": response.content},
            error=None,
            source="trellis",
        )

    except httpx.TimeoutException:
        return ServiceResult(
            data=None,
            error="Trellis service timed out (>300s) — check GPU availability",
            source="trellis",
        )
    except Exception as exc:
        logger.exception("Error calling Trellis 3D generation service")
        return ServiceResult(data=None, error=str(exc), source="trellis")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_model_3d.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/model_3d.py backend/tests/test_model_3d.py
git commit -m "feat: add Trellis 3D generation client service"
```

---

### Task 7: Trellis GPU-side wrapper service

**Files:**
- Create: `backend/trellis_service/main.py`

This file lives in the repo for reference but runs on a separate GPU machine, not on the main backend server.

- [ ] **Step 1: Create the wrapper**

```python
# backend/trellis_service/main.py
"""
Thin FastAPI wrapper around Microsoft TRELLIS for 3D model generation.

Run this on a GPU machine (NOT the main backend server):
  Requirements: CUDA GPU with ≥16GB VRAM, CUDA 11.8+, Python 3.10+
  
  Setup:
    git clone https://github.com/microsoft/TRELLIS /opt/trellis
    cd /opt/trellis
    pip install -e ".[all]"
    pip install fastapi uvicorn python-multipart
  
  Run:
    cd /opt/trellis
    uvicorn trellis_service.main:app --host 0.0.0.0 --port 8001

  On the main backend, set: TRELLIS_API_URL=http://<gpu-machine-ip>:8001

GPU hosting options (for production):
  - RunPod (runpod.io) — RTX 3090 ~$0.44/hr, A100 ~$1.64/hr
  - Lambda Labs — A10 ~$0.60/hr
  - Vast.ai — cheapest spot pricing

VRAM requirements:
  - JeffreyXiang/TRELLIS-image-large: ~16GB (RTX 3090 / A100 minimum)
  - JeffreyXiang/TRELLIS-image-500M-v0.1: ~8GB (RTX 3080 OK)
"""
import io
import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

logger = logging.getLogger(__name__)

app = FastAPI(title="Trellis 3D Service")

# Load model once at startup (takes ~30-60s on first load)
try:
    from trellis.pipelines import TrellisImageTo3DPipeline
    from trellis.utils import postprocessing_utils

    _pipeline = TrellisImageTo3DPipeline.from_pretrained(
        "JeffreyXiang/TRELLIS-image-large"
    )
    _pipeline.cuda()
    logger.info("Trellis pipeline loaded successfully")
except Exception as e:
    logger.error("Failed to load Trellis pipeline: %s", e)
    _pipeline = None


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": _pipeline is not None}


@app.post("/generate")
async def generate(images: list[UploadFile] = File(...)):
    """Accept 1+ images, return a textured GLB file.

    Uses the first image as the primary input (front elevation for best results).
    Additional images improve reconstruction quality if the Trellis version supports
    multi-image input — this wrapper handles both gracefully.
    """
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Trellis model not loaded")

    if not images:
        raise HTTPException(status_code=400, detail="No images provided")

    try:
        pil_images = []
        for upload in images:
            raw = await upload.read()
            pil_images.append(Image.open(io.BytesIO(raw)).convert("RGB"))

        # Use first image as primary input (front elevation)
        primary_image = pil_images[0]

        outputs = _pipeline.run(primary_image, seed=42)

        buf = io.BytesIO()
        glb = postprocessing_utils.to_glb(
            outputs["gaussian"][0],
            outputs["mesh"][0],
            simplify=0.95,
            texture_size=1024,
        )
        glb.export(buf, file_type="glb")
        buf.seek(0)

        return Response(
            content=buf.getvalue(),
            media_type="model/gltf-binary",
            headers={"Content-Disposition": "attachment; filename=model.glb"},
        )

    except Exception as exc:
        logger.exception("Trellis generation failed")
        raise HTTPException(status_code=500, detail=str(exc))
```

- [ ] **Step 2: Create trellis_service __init__.py**

```bash
touch backend/trellis_service/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add backend/trellis_service/
git commit -m "feat: add Trellis GPU wrapper service (run on separate GPU machine)"
```

---

### Task 8: model3d route and background pipeline

**Files:**
- Create: `backend/app/routes/model3d.py`

- [ ] **Step 1: Create the route file**

```python
# backend/app/routes/model3d.py
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.services import model_3d as model_3d_service
from app.services import supabase, synthesis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/property", tags=["model3d"])


async def _run_pipeline(job_id: str, property_id: str) -> None:
    """Background task: fetch images → Gemini synthesis → Trellis → upload GLB → mark ready."""
    try:
        # 1. Load all images for this property
        images_result = await supabase.get_property_images(property_id)
        if images_result.error or not images_result.data:
            logger.error("No images found for property %s", property_id)
            await supabase.update_model_3d_status(job_id, "failed")
            return

        # 2. Load analysis metadata
        analysis_result = await supabase.get_property_analysis(property_id)
        analysis = analysis_result.data or {}

        # 3. Get property type class
        property_result = await supabase.get_property(property_id)
        property_type_class = "residential"
        if property_result.data:
            property_type_class = property_result.data.get("property_type_class") or "residential"

        # 4. Build ordered image URL list:
        #    street_view heading=0 first, then other street views, satellite, oblique
        images = images_result.data
        ordered: list[dict] = []
        # Front view first (most important for Trellis primary image)
        ordered += [i for i in images if i["image_type"] == "street_view" and i.get("heading") == 0]
        ordered += [i for i in images if i["image_type"] == "satellite"]
        ordered += [i for i in images if i["image_type"] == "oblique"]
        ordered += [i for i in images if i["image_type"] == "street_view" and i.get("heading") != 0]
        image_urls = [i["url"] for i in ordered]

        # 5. Gemini synthesis
        synth_result = await synthesis.synthesize_views(
            image_urls=image_urls[:9],
            analysis=analysis,
            property_type_class=property_type_class,
        )
        if synth_result.error or not synth_result.data:
            logger.error("Synthesis failed for job %s: %s", job_id, synth_result.error)
            await supabase.update_model_3d_status(job_id, "failed")
            return

        # 6. 3D generation via Trellis
        synthesis_image_bytes = [img["bytes"] for img in synth_result.data]
        gen_result = await model_3d_service.generate(synthesis_image_bytes)
        if gen_result.error or not gen_result.data:
            logger.error("Trellis generation failed for job %s: %s", job_id, gen_result.error)
            await supabase.update_model_3d_status(job_id, "failed")
            return

        # 7. Upload GLB to Supabase Storage
        upload_result = await supabase.upload_model_glb(
            property_id, gen_result.data["glb_bytes"]
        )
        if upload_result.error:
            logger.error("GLB upload failed for job %s: %s", job_id, upload_result.error)
            await supabase.update_model_3d_status(job_id, "failed")
            return

        # 8. Mark complete
        await supabase.update_model_3d_status(
            job_id, "ready", glb_url=upload_result.data["url"]
        )
        logger.info("3D model generation complete for job %s", job_id)

    except Exception as exc:
        logger.exception("Unhandled error in 3D pipeline for job %s", job_id)
        await supabase.update_model_3d_status(job_id, "failed")


@router.post("/{property_id}/generate-3d")
async def start_generation(property_id: str, background_tasks: BackgroundTasks):
    """Start 3D model generation. Returns immediately with job_id and status=generating."""
    job_id = str(uuid.uuid4())
    save_result = await supabase.save_model_3d(job_id, property_id)
    if save_result.error:
        raise HTTPException(status_code=500, detail="Failed to create generation job")

    background_tasks.add_task(_run_pipeline, job_id, property_id)
    return {"job_id": job_id, "status": "generating"}


@router.get("/{property_id}/3d-model")
async def get_model_status(property_id: str):
    """Poll for 3D model status. Returns status and glb_url when ready."""
    result = await supabase.get_model_3d(property_id)
    if result.error or not result.data:
        return {"job_id": None, "status": "not_started", "glb_url": None}

    model = result.data
    return {
        "job_id": model.get("id"),
        "status": model.get("status"),
        "glb_url": model.get("glb_url"),
    }
```

- [ ] **Step 2: Run all tests to confirm imports are clean**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/model3d.py
git commit -m "feat: add model3d route with async background pipeline"
```

---

### Task 9: Register model3d router in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Import and register the router**

```python
from app.routes.feedback import router as feedback_router
from app.routes.model3d import router as model3d_router   # NEW
from app.routes.property import router as property_router

# ...

app.include_router(property_router)
app.include_router(feedback_router)
app.include_router(model3d_router)   # NEW
```

- [ ] **Step 2: Verify the routes are registered**

```bash
cd backend && uv run uvicorn app.main:app --reload &
sleep 2
curl -s http://localhost:8000/openapi.json | python3 -c "import sys,json; d=json.load(sys.stdin); [print(p) for p in d['paths'] if '3d' in p]"
kill %1
```

Expected: `/api/v1/property/{property_id}/generate-3d` and `/api/v1/property/{property_id}/3d-model` printed.

- [ ] **Step 3: Run all tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register model3d router"
```

---

### Task 10: Frontend API functions

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add two new functions**

```typescript
export async function generate3DModel(propertyId: string): Promise<{ job_id: string; status: string }> {
  const { data } = await api.post(`/api/v1/property/${propertyId}/generate-3d`);
  return data;
}

export async function get3DModelStatus(propertyId: string): Promise<{
  job_id: string | null;
  status: "not_started" | "generating" | "ready" | "failed";
  glb_url: string | null;
}> {
  const { data } = await api.get(`/api/v1/property/${propertyId}/3d-model`);
  return data;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add generate3DModel and get3DModelStatus API functions"
```

---

### Task 11: Frontend TypeScript types

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add Model3DStatus interface**

```typescript
export interface Model3DStatus {
  job_id: string | null;
  status: "not_started" | "generating" | "ready" | "failed";
  glb_url: string | null;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat: add Model3DStatus type"
```

---

### Task 12: Add model-viewer script to index.html

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add the script tag before </body>**

```html
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
    <!-- Google model-viewer web component for 3D GLB display -->
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js"></script>
  </body>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add model-viewer web component script"
```

---

### Task 13: ModelViewer component

**Files:**
- Create: `frontend/src/components/ModelViewer.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/ModelViewer.tsx
import { Download } from "lucide-react";

// TypeScript declaration for the <model-viewer> custom element
declare global {
  namespace JSX {
    interface IntrinsicElements {
      "model-viewer": React.HTMLAttributes<HTMLElement> & {
        src?: string;
        alt?: string;
        "camera-controls"?: boolean | "";
        "auto-rotate"?: boolean | "";
        "shadow-intensity"?: string;
        style?: React.CSSProperties;
      };
    }
  }
}

interface ModelViewerProps {
  glbUrl: string;
}

export default function ModelViewer({ glbUrl }: ModelViewerProps) {
  return (
    <div className="relative w-full overflow-hidden rounded-2xl shadow-[var(--neu-elevated)]">
      <model-viewer
        src={glbUrl}
        alt="3D model of the property"
        camera-controls=""
        auto-rotate=""
        shadow-intensity="1"
        style={{
          width: "100%",
          height: "500px",
          background: "var(--card)",
        }}
      />
      <div className="absolute bottom-3 right-3">
        <a
          href={glbUrl}
          download="property-model.glb"
          className="inline-flex items-center gap-2 rounded-lg bg-card/90 backdrop-blur-xl px-3 py-1.5 text-xs font-medium text-foreground shadow-[var(--neu-flat)] hover:bg-card transition-colors border border-border"
        >
          <Download className="size-3" />
          Download GLB
        </a>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && ~/.vite-plus/bin/vp check
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ModelViewer.tsx
git commit -m "feat: add ModelViewer component with download button"
```

---

### Task 14: Generate3DButton component

**Files:**
- Create: `frontend/src/components/Generate3DButton.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/Generate3DButton.tsx
import { useEffect, useRef, useState } from "react";
import { Box, Loader2 } from "lucide-react";
import { generate3DModel, get3DModelStatus } from "@/lib/api";
import ModelViewer from "@/components/ModelViewer";

interface Generate3DButtonProps {
  propertyId: string;
}

type Status = "idle" | "generating" | "ready" | "failed";

export default function Generate3DButton({ propertyId }: Generate3DButtonProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [glbUrl, setGlbUrl] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clean up polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function handleGenerate() {
    setStatus("generating");
    try {
      await generate3DModel(propertyId);

      pollRef.current = setInterval(async () => {
        try {
          const result = await get3DModelStatus(propertyId);
          if (result.status === "ready" && result.glb_url) {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setGlbUrl(result.glb_url);
            setStatus("ready");
          } else if (result.status === "failed") {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setStatus("failed");
          }
        } catch {
          // Polling error — keep retrying
        }
      }, 3000);
    } catch {
      setStatus("failed");
    }
  }

  if (status === "ready" && glbUrl) {
    return <ModelViewer glbUrl={glbUrl} />;
  }

  if (status === "generating") {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
        <Loader2 className="size-4 animate-spin text-primary" />
        Generating 3D model… (~90s)
      </div>
    );
  }

  if (status === "failed") {
    return (
      <button
        type="button"
        onClick={handleGenerate}
        className="flex items-center gap-2 rounded-lg border border-destructive/40 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/5 transition-colors"
      >
        Generation failed — retry
      </button>
    );
  }

  // idle
  return (
    <button
      type="button"
      onClick={handleGenerate}
      className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors shadow-[var(--neu-flat)]"
    >
      <Box className="size-4" />
      Generate 3D Model
    </button>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && ~/.vite-plus/bin/vp check
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Generate3DButton.tsx
git commit -m "feat: add Generate3DButton with polling and inline ModelViewer on ready"
```

---

### Task 15: Update PropertyHero and App.tsx

**Files:**
- Modify: `frontend/src/components/PropertyHero.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update PropertyHero to accept propertyId and render the button**

```tsx
// frontend/src/components/PropertyHero.tsx
import DataBadge from "@/components/ui/data-badge";
import Generate3DButton from "@/components/Generate3DButton";

interface PropertyHeroProps {
  streetViewUrl: string | null;
  satelliteUrl: string | null;
  address: string;
  propertyId: string | null;    // NEW
}

function ImageSkeleton() {
  return <div className="aspect-video w-full animate-pulse rounded-2xl bg-surface-raised" />;
}

export default function PropertyHero({ streetViewUrl, satelliteUrl, address, propertyId }: PropertyHeroProps) {
  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2
          className="font-heading text-xl font-semibold text-foreground truncate tracking-tight"
          title={address}
        >
          {address}
        </h2>
        {propertyId && <Generate3DButton propertyId={propertyId} />}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="relative overflow-hidden rounded-2xl shadow-[var(--neu-flat)]">
          {streetViewUrl ? (
            <img
              src={streetViewUrl}
              alt={`Street view of ${address}`}
              className="aspect-video w-full object-cover"
            />
          ) : (
            <ImageSkeleton />
          )}
          <DataBadge className="absolute bottom-3 left-3 bg-card/80 backdrop-blur-sm">
            Street View
          </DataBadge>
        </div>

        <div className="relative overflow-hidden rounded-2xl shadow-[var(--neu-flat)]">
          {satelliteUrl ? (
            <img
              src={satelliteUrl}
              alt={`Satellite view of ${address}`}
              className="aspect-video w-full object-cover"
            />
          ) : (
            <ImageSkeleton />
          )}
          <DataBadge className="absolute bottom-3 left-3 bg-card/80 backdrop-blur-sm">
            Satellite
          </DataBadge>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Update App.tsx to pass propertyId to PropertyHero**

Find the `<PropertyHero ... />` call in `App.tsx` and add the `propertyId` prop:

```tsx
<PropertyHero
  streetViewUrl={streetViewUrl}
  satelliteUrl={satelliteUrl}
  address={address}
  propertyId={property.property.id}
/>
```

(`property.property.id` is already a `string` in the TypeScript type.)

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && ~/.vite-plus/bin/vp check
```

Expected: No errors.

- [ ] **Step 4: Run all backend tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PropertyHero.tsx frontend/src/App.tsx
git commit -m "feat: wire Generate3DButton into PropertyHero via propertyId prop"
```

---

### Task 16: End-to-end verification

- [ ] **Step 1: Set up environment variables**

In the root `.env`, verify these are set:
```bash
GEMINI_API_KEY=your_gemini_api_key
TRELLIS_API_URL=http://localhost:8001   # or your GPU machine IP
```

- [ ] **Step 2: Start the Trellis service on the GPU machine**

On the GPU machine (RTX 3090+ recommended):
```bash
cd /opt/trellis
uvicorn trellis_service.main:app --host 0.0.0.0 --port 8001
```

Wait for: `INFO: Trellis pipeline loaded successfully` in the logs.

Verify health: `curl http://<gpu-ip>:8001/health` → `{"status":"ok","model_loaded":true}`

- [ ] **Step 3: Start the full dev stack**

On the main dev machine:
```bash
make dev
```

- [ ] **Step 4: Search a property and trigger 3D generation**

Open `http://localhost:5173`. Search a Canadian residential address. After results load, click "Generate 3D Model".

- [ ] **Step 5: Monitor backend logs**

Watch for:
- `INFO: 3D model generation complete for job <uuid>`
- No `ERROR` lines in the pipeline

- [ ] **Step 6: Verify in-app viewer**

After ~90–120s:
- The button is replaced by a `<model-viewer>` panel showing the 3D model
- The model can be orbited/rotated with the mouse
- "Download GLB" link downloads a valid `.glb` file (open in Blender or `gltf.report` to verify)

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: complete 3D model generation pipeline — Gemini synthesis + Trellis + model-viewer"
```
