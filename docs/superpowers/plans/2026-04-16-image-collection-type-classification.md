# Image Collection & Property Type Classification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current 2-image property fetch with 13 multi-angle images (8 street view headings + 1 satellite + 4 oblique aerial tiles), add a lightweight property type classifier, and pass the type through the vision prompt so irrelevant AI analysis fields return null and are hidden in the UI.

**Architecture:** Two new functions in `google_maps.py` collect additional angles; a new `property_type.py` service makes a quick GPT-4o classification from the satellite image; `routes/property.py` orchestrates the expanded pipeline; schema changes propagate through Supabase, Pydantic models, and TypeScript types. The frontend already hides null-value AI cards — no extra frontend card logic is needed beyond a TypeScript type update.

**Tech Stack:** Python 3.13, FastAPI, httpx, OpenAI GPT-4o, Supabase, Google Maps Static API, Google Street View Static API, React/TypeScript, uv, pytest + pytest-asyncio (asyncio_mode=auto already set in pyproject.toml).

---

## File Map

| Action | Path |
|--------|------|
| Create | `backend/tests/__init__.py` |
| Create | `backend/tests/conftest.py` |
| Create | `backend/tests/test_google_maps.py` |
| Create | `backend/tests/test_property_type.py` |
| Create | `backend/app/services/property_type.py` |
| Modify | `backend/app/services/google_maps.py` |
| Modify | `backend/app/services/supabase.py` |
| Modify | `backend/app/services/vision.py` |
| Modify | `backend/app/models/schemas.py` |
| Modify | `backend/app/routes/property.py` |
| Modify | `frontend/src/lib/types.ts` |

---

### Task 1: Test infrastructure

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create the tests package**

```bash
mkdir -p backend/tests
touch backend/tests/__init__.py
```

- [ ] **Step 2: Create conftest.py**

```python
# backend/tests/conftest.py
# pytest-asyncio is configured in pyproject.toml with asyncio_mode = "auto"
# All async test functions run as coroutines automatically — no @pytest.mark.asyncio needed.
```

- [ ] **Step 3: Verify test runner works**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: `no tests ran` (exit 5 or 0, no errors)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/
git commit -m "test: add tests package and conftest"
```

---

### Task 2: DB schema migration

**Files:** None (SQL run in Supabase Dashboard)

- [ ] **Step 1: Open Supabase Dashboard → SQL Editor**

Run this SQL:

```sql
-- Add property type classification column to properties
ALTER TABLE properties
  ADD COLUMN IF NOT EXISTS property_type_class TEXT;

-- Add heading column to property_images for angle tracking
ALTER TABLE property_images
  ADD COLUMN IF NOT EXISTS heading INTEGER;

-- Remove the image_type check constraint if it restricts to only street_view/satellite
-- First check whether it exists:
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_name = 'property_images'
  AND constraint_type = 'CHECK';

-- If a check constraint exists on image_type, drop it (replace constraint_name below):
-- ALTER TABLE property_images DROP CONSTRAINT IF EXISTS property_images_image_type_check;
```

- [ ] **Step 2: Verify columns exist**

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('properties', 'property_images')
  AND column_name IN ('property_type_class', 'heading');
```

Expected: 2 rows returned (`property_type_class TEXT` and `heading INTEGER`).

- [ ] **Step 3: Commit note**

```bash
git commit --allow-empty -m "chore: applied DB migration — property_type_class + heading columns"
```

---

### Task 3: Update schemas.py

**Files:**
- Modify: `backend/app/models/schemas.py`

- [ ] **Step 1: Write the failing test (verifies schema structure)**

```python
# backend/tests/test_schemas.py
from app.models.schemas import Property, PropertyImage
from datetime import datetime, timezone
from uuid import uuid4

def test_property_has_type_class_field():
    p = Property(
        id=uuid4(),
        address="123 Main St",
        lat=43.0,
        lon=-79.0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        property_type_class="residential",
    )
    assert p.property_type_class == "residential"

def test_property_type_class_optional():
    p = Property(
        id=uuid4(),
        address="123 Main St",
        lat=43.0,
        lon=-79.0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert p.property_type_class is None

def test_property_image_has_heading_field():
    img = PropertyImage(
        id=uuid4(),
        property_id=uuid4(),
        image_type="street_view",
        url="http://example.com/img.jpg",
        fetched_at=datetime.now(timezone.utc),
        heading=90,
    )
    assert img.heading == 90

def test_property_image_heading_optional():
    img = PropertyImage(
        id=uuid4(),
        property_id=uuid4(),
        image_type="satellite",
        url="http://example.com/img.jpg",
        fetched_at=datetime.now(timezone.utc),
    )
    assert img.heading is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_schemas.py -v
```

Expected: FAIL — `Property` has no field `property_type_class`, `PropertyImage` has no field `heading`.

- [ ] **Step 3: Update schemas.py**

Change the `ImageType` enum to include `OBLIQUE`, change `PropertyImage.image_type` to `str` (removes the strict enum restriction), and add the two new fields:

```python
class ImageType(str, Enum):
    STREET_VIEW = "street_view"
    SATELLITE = "satellite"
    OBLIQUE = "oblique"


class Property(BaseModel):
    id: UUID
    address: str
    lat: float
    lon: float
    neighborhood: str | None = None
    cross_streets: str | None = None
    property_type_class: str | None = None   # NEW
    created_at: datetime
    updated_at: datetime


class PropertyImage(BaseModel):
    id: UUID
    property_id: UUID
    image_type: str          # Changed from ImageType enum to str to allow future values
    url: str
    heading: int | None = None   # NEW
    fetched_at: datetime
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_schemas.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add property_type_class and heading fields to schemas"
```

---

### Task 4: Multi-angle image collection in google_maps.py

**Files:**
- Modify: `backend/app/services/google_maps.py`
- Create: `backend/tests/test_google_maps.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_google_maps.py
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.services.google_maps import fetch_multi_angle_street_view, fetch_oblique_tiles


async def test_fetch_multi_angle_returns_8_images_on_ok():
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "OK"}

    with patch("app.services.google_maps.httpx.AsyncClient") as MockClient:
        mock_cm = AsyncMock()
        mock_cm.get = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_cm)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await fetch_multi_angle_street_view(43.0, -79.0, "123 Main St, Toronto")

    assert result.error is None
    assert result.data is not None
    assert len(result.data) == 8
    headings = [img["heading"] for img in result.data]
    assert headings == [0, 45, 90, 135, 180, 225, 270, 315]
    for img in result.data:
        assert "url" in img
        assert "streetview" in img["url"].lower() or "maps.googleapis.com" in img["url"]


async def test_fetch_multi_angle_returns_error_when_no_coverage():
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ZERO_RESULTS"}

    with patch("app.services.google_maps.httpx.AsyncClient") as MockClient:
        mock_cm = AsyncMock()
        mock_cm.get = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_cm)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await fetch_multi_angle_street_view(0.0, 0.0)

    assert result.data is None
    assert result.error is not None
    assert "ZERO_RESULTS" in result.error


async def test_fetch_oblique_tiles_returns_4_images():
    # fetch_oblique_tiles constructs URLs without any HTTP call
    result = await fetch_oblique_tiles(43.651, -79.347)

    assert result.error is None
    assert result.data is not None
    assert len(result.data) == 4
    headings = [img["heading"] for img in result.data]
    assert headings == [0, 90, 180, 270]
    for img in result.data:
        assert "url" in img
        assert "staticmap" in img["url"].lower() or "maps.googleapis.com" in img["url"]
        assert "tilt" not in img["url"]   # Static Maps uses heading, not tilt param


async def test_fetch_oblique_tiles_all_urls_contain_satellite():
    result = await fetch_oblique_tiles(43.0, -79.0)

    for img in result.data:
        assert "satellite" in img["url"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_google_maps.py -v
```

Expected: FAIL — `fetch_multi_angle_street_view` and `fetch_oblique_tiles` not defined.

- [ ] **Step 3: Add the two functions to google_maps.py**

Add after the existing `fetch_satellite` function:

```python
async def fetch_multi_angle_street_view(
    lat: float, lon: float, address: str | None = None
) -> ServiceResult:
    """Fetch 8 Street View image URLs at 45° increments (0°–315°)."""
    try:
        location = address if address else f"{lat},{lon}"

        # Single metadata check to verify Street View coverage exists
        meta_params = {
            "location": location,
            "key": settings.GOOGLE_MAPS_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            meta_resp = await client.get(
                f"{STREET_VIEW_BASE}/metadata", params=meta_params
            )
            meta_data = meta_resp.json()

        if meta_data.get("status") != "OK":
            return ServiceResult(
                data=None,
                error=f"Street View not available: {meta_data.get('status')}",
                source="google_street_view",
            )

        images = []
        for heading in range(0, 360, 45):
            params = {
                "size": "640x480",
                "location": location,
                "heading": str(heading),
                "pitch": "0",
                "fov": "90",
                "key": settings.GOOGLE_MAPS_API_KEY,
                "return_error_code": "true",
            }
            url = f"{STREET_VIEW_BASE}?{urlencode(params)}"
            images.append({"url": url, "heading": heading})

        return ServiceResult(data=images, error=None, source="google_street_view")

    except Exception as exc:
        logger.exception("Error fetching multi-angle Street View")
        return ServiceResult(data=None, error=str(exc), source="google_street_view")


async def fetch_oblique_tiles(lat: float, lon: float) -> ServiceResult:
    """Build 4 Google Maps satellite URLs at 45° heading increments (oblique aerial)."""
    try:
        images = []
        for heading in [0, 90, 180, 270]:
            params = {
                "center": f"{lat},{lon}",
                "zoom": "18",
                "size": "640x640",
                "maptype": "satellite",
                "heading": str(heading),
                "key": settings.GOOGLE_MAPS_API_KEY,
            }
            url = f"{STATIC_MAP_BASE}?{urlencode(params)}"
            images.append({"url": url, "heading": heading})

        return ServiceResult(data=images, error=None, source="google_satellite")

    except Exception as exc:
        logger.exception("Error building oblique tile URLs")
        return ServiceResult(data=None, error=str(exc), source="google_satellite")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_google_maps.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/google_maps.py backend/tests/test_google_maps.py
git commit -m "feat: add multi-angle street view and oblique tile collection"
```

---

### Task 5: Property type classifier service

**Files:**
- Create: `backend/app/services/property_type.py`
- Create: `backend/tests/test_property_type.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_property_type.py
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.services.property_type import classify


async def test_classify_returns_residential():
    mock_choice = MagicMock()
    mock_choice.message.content = '{"class": "residential", "confidence": 0.95}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.services.property_type.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_client

        result = await classify(satellite_url="http://example.com/sat.jpg")

    assert result.error is None
    assert result.data["class"] == "residential"
    assert result.data["confidence"] == 0.95


async def test_classify_returns_commercial():
    mock_choice = MagicMock()
    mock_choice.message.content = '{"class": "commercial", "confidence": 0.88}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.services.property_type.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_client

        result = await classify(satellite_url="http://example.com/sat.jpg")

    assert result.data["class"] == "commercial"


async def test_classify_sanitizes_invalid_class():
    mock_choice = MagicMock()
    mock_choice.message.content = '{"class": "unknown_garbage", "confidence": 0.5}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.services.property_type.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_client

        result = await classify(satellite_url="http://example.com/sat.jpg")

    assert result.data["class"] == "residential"


async def test_classify_no_images_returns_default():
    result = await classify()

    assert result.data["class"] == "residential"
    assert result.error is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_property_type.py -v
```

Expected: FAIL — `property_type` module not found.

- [ ] **Step 3: Create property_type.py**

```python
# backend/app/services/property_type.py
import json
import logging

from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)

_VALID_CLASSES = {"residential", "commercial", "industrial", "poi"}

CLASSIFY_PROMPT = """Look at this property image and classify the property type.

Return ONLY a JSON object — no markdown, no other text:
{
  "class": "residential" | "commercial" | "industrial" | "poi",
  "confidence": 0.0 to 1.0
}

Definitions:
- residential: single-family homes, duplexes, townhouses, condos, apartments
- commercial: retail stores, offices, restaurants, hotels, mixed-use buildings
- industrial: warehouses, factories, storage facilities, logistics centres
- poi: parks, monuments, government buildings, schools, hospitals, places of worship"""


async def classify(
    street_view_url: str | None = None,
    satellite_url: str | None = None,
) -> ServiceResult:
    """Classify property type (residential/commercial/industrial/poi) via GPT-4o."""
    if not street_view_url and not satellite_url:
        return ServiceResult(
            data={"class": "residential", "confidence": 0.0},
            error="No images provided; defaulting to residential",
            source="property_type_classifier",
        )

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        content: list[dict] = [{"type": "text", "text": CLASSIFY_PROMPT}]

        # Prefer satellite for classification — better top-down context
        img_url = satellite_url or street_view_url
        content.append({
            "type": "image_url",
            "image_url": {"url": img_url, "detail": "low"},
        })

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=60,
            temperature=0.1,
        )

        raw = response.choices[0].message.content or ""
        result = json.loads(raw.strip())

        if result.get("class") not in _VALID_CLASSES:
            result["class"] = "residential"

        return ServiceResult(data=result, error=None, source="property_type_classifier")

    except Exception as exc:
        logger.exception("Error classifying property type; defaulting to residential")
        return ServiceResult(
            data={"class": "residential", "confidence": 0.0},
            error=str(exc),
            source="property_type_classifier",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_property_type.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/property_type.py backend/tests/test_property_type.py
git commit -m "feat: add property type classifier service"
```

---

### Task 6: Update supabase.py for heading and property_type_class

**Files:**
- Modify: `backend/app/services/supabase.py`

- [ ] **Step 1: Update save_images() to store heading**

Find the current `save_images` function and replace the record-building loop:

```python
async def save_images(
    property_id: str, images: list[dict[str, Any]]
) -> ServiceResult:
    """Save property image records to Supabase."""
    try:
        client = _get_client()
        now = datetime.now(timezone.utc).isoformat()
        records = []
        for img in images:
            record: dict[str, Any] = {
                "id": str(uuid4()),
                "property_id": property_id,
                "image_type": img["image_type"],
                "url": img["url"],
                "fetched_at": now,
            }
            if img.get("heading") is not None:
                record["heading"] = img["heading"]
            records.append(record)
        result = client.table("property_images").insert(records).execute()
        return ServiceResult(
            data=result.data if result.data else records,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving images to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 2: Update save_property() to accept property_type_class**

Replace the existing `save_property` function signature and record dict:

```python
async def save_property(
    address: str,
    lat: float,
    lon: float,
    property_type_class: str | None = None,
) -> ServiceResult:
    """Insert a new property record into Supabase."""
    try:
        client = _get_client()
        now = datetime.now(timezone.utc).isoformat()
        record: dict[str, Any] = {
            "id": str(uuid4()),
            "address": address,
            "lat": lat,
            "lon": lon,
            "created_at": now,
            "updated_at": now,
        }
        if property_type_class is not None:
            record["property_type_class"] = property_type_class
        result = client.table("properties").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving property to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 3: Run all tests to confirm nothing broke**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All existing tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/supabase.py
git commit -m "feat: save heading and property_type_class to Supabase"
```

---

### Task 7: Update vision.py to accept property type context

**Files:**
- Modify: `backend/app/services/vision.py`

- [ ] **Step 1: Add property_type_class parameter and prefix the prompt when set**

Change the `analyze_property` function signature and the content-building block:

```python
async def analyze_property(
    street_view_url: str | None = None,
    satellite_url: str | None = None,
    property_type_class: str | None = None,   # NEW parameter
) -> ServiceResult:
    """Analyze property images using OpenAI Vision API (gpt-4o)."""
    try:
        if not street_view_url and not satellite_url:
            return ServiceResult(
                data=None,
                error="At least one image URL is required",
                source="openai_vision",
            )

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Build type-aware prompt prefix
        type_prefix = ""
        if property_type_class:
            type_prefix = (
                f"This is a {property_type_class} property. "
                "Only analyze fields that are relevant to this property type. "
                "Return null (with confidence 0.0) for fields that do not apply "
                "(e.g., has_fenced_yard or has_deck_or_patio for a commercial building).\n\n"
            )

        content: list[dict] = [{"type": "text", "text": type_prefix + ANALYSIS_PROMPT}]

        # ... rest of the function is unchanged (image appending, API call, parsing)
```

Keep everything after `content: list[dict] = ...` identical to the current code.

- [ ] **Step 2: Run all tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests PASS (function signature change is backward-compatible).

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/vision.py
git commit -m "feat: pass property type class to vision prompt for type-aware analysis"
```

---

### Task 8: Rewrite image collection in routes/property.py

**Files:**
- Modify: `backend/app/routes/property.py`

- [ ] **Step 1: Add property_type import and restructure the pipeline**

Replace the imports block at the top:

```python
from app.services import google_maps, pois, segmentation, supabase, vision, property_type
```

- [ ] **Step 2: Replace the image-fetching section (steps 2–4 of the current pipeline)**

The current pipeline steps 2–4 (save property → fetch images → AI analysis) become the following. Replace from the `# 2. Build property object` comment through the end of the AI analysis block:

```python
    # 2. Get satellite URL (URL construction only — no HTTP call)
    sat_result = await google_maps.fetch_satellite(req.lat, req.lon)
    satellite_url = sat_result.data["url"] if sat_result.data else None

    # 3. Classify property type using satellite image
    property_type_class = None
    if satellite_url:
        type_result = await property_type.classify(satellite_url=satellite_url)
        if type_result.data:
            property_type_class = type_result.data.get("class")
        if type_result.error:
            errors.append(f"Property type classification: {type_result.error}")

    # 4. Save property with type class
    prop_result = await supabase.save_property(
        address, req.lat, req.lon, property_type_class=property_type_class
    )
    if prop_result.error:
        errors.append(f"Save property: {prop_result.error}")
        property_id = str(uuid.uuid4())
        property_data = {
            "id": property_id,
            "address": address,
            "lat": req.lat,
            "lon": req.lon,
            "neighborhood": neighborhood,
            "cross_streets": cross_streets,
            "property_type_class": property_type_class,
            "created_at": _now(),
            "updated_at": _now(),
        }
    else:
        property_data = prop_result.data
        property_id = property_data["id"]
        property_data["neighborhood"] = neighborhood
        property_data["cross_streets"] = cross_streets
        property_data["property_type_class"] = property_type_class

    # 5. Fetch all images
    sv_result = await google_maps.fetch_multi_angle_street_view(req.lat, req.lon, address=address)
    oblique_result = await google_maps.fetch_oblique_tiles(req.lat, req.lon)

    street_view_url = None   # heading=0 used for AI analysis (most likely front-facing)
    images = []

    if sv_result.error:
        errors.append(f"Street View: {sv_result.error}")
    elif sv_result.data:
        for sv in sv_result.data:
            if sv["heading"] == 0:
                street_view_url = sv["url"]
            images.append({
                "image_type": "street_view",
                "url": sv["url"],
                "heading": sv["heading"],
            })

    if satellite_url:
        images.append({
            "image_type": "satellite",
            "url": satellite_url,
            "heading": None,
        })

    if oblique_result.error:
        errors.append(f"Oblique tiles: {oblique_result.error}")
    elif oblique_result.data:
        for obl in oblique_result.data:
            images.append({
                "image_type": "oblique",
                "url": obl["url"],
                "heading": obl["heading"],
            })

    # Save all images
    if property_id and images:
        img_result = await supabase.save_images(
            property_id,
            images,
        )
        if img_result.error:
            errors.append(f"Save images: {img_result.error}")
        elif img_result.data:
            images = img_result.data

    # 6. AI analysis (type-aware, uses heading=0 street view + satellite)
    analysis_data = None
    if street_view_url or satellite_url:
        vision_result = await vision.analyze_property(
            street_view_url, satellite_url, property_type_class=property_type_class
        )
```

Everything after `vision_result = await vision.analyze_property(...)` through the end of the route function remains unchanged (the `if vision_result.error:` block, SAM2, POIs, geospatial, return statement).

- [ ] **Step 3: Start the backend and do a manual smoke test**

```bash
cd backend && uv run uvicorn app.main:app --reload
```

In another terminal:
```bash
curl -s -X POST http://localhost:8000/api/v1/property \
  -H "Content-Type: application/json" \
  -d '{"lat": 43.6532, "lon": -79.3832}' \
  | python3 -m json.tool | grep -E '"image_type"|"heading"|"property_type_class"'
```

Expected: Output shows `street_view` images with headings 0–315, `satellite` with no heading, `oblique` images with headings 0/90/180/270, and `property_type_class` set on the property.

- [ ] **Step 4: Run all tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/property.py
git commit -m "feat: expand property pipeline to 13 images with type classification"
```

---

### Task 9: Update frontend TypeScript types

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add the new fields**

In `types.ts`, update the `Property` interface and `PropertyImage` interface:

```typescript
export interface Property {
  id: string;
  address: string;
  lat: number;
  lon: number;
  neighborhood: string | null;
  cross_streets: string | null;
  property_type_class: "residential" | "commercial" | "industrial" | "poi" | null;  // NEW
  created_at: string;
  updated_at: string;
}

export interface PropertyImage {
  id: string;
  property_id: string;
  image_type: "street_view" | "satellite" | "oblique";  // added "oblique"
  url: string;
  heading: number | null;  // NEW
  fetched_at: string;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && ~/.vite-plus/bin/vp check
```

Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat: add property_type_class and heading to frontend types"
```

---

### Task 10: End-to-end verification

- [ ] **Step 1: Start the full dev stack**

```bash
make dev
```

- [ ] **Step 2: Search for a property in the UI**

Open `http://localhost:5173`. Search a Canadian address (e.g., `43.6532, -79.3832` for downtown Toronto).

- [ ] **Step 3: Verify in browser network tab**

Open DevTools → Network. Find the `POST /api/v1/property` response. Verify:
- `property.property_type_class` is `"residential"`, `"commercial"`, etc. (not null)
- `images` array has 13 entries (8 `street_view` + 1 `satellite` + 4 `oblique`)
- `street_view` images each have a `heading` value (0, 45, 90, … 315)
- `oblique` images each have a `heading` (0, 90, 180, 270)

- [ ] **Step 4: Verify type-aware analysis**

For a commercial address, check that cards like "Pool", "Fenced Yard", "Deck / Patio" show null/hidden (the AI returned null because the type context instructed it to).

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete image collection and property type classification pipeline"
```
