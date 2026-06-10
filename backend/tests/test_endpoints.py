from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.schemas import ServiceResult


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_get_images(client: AsyncClient):
    mock_sv = ServiceResult(
        data={"url": "https://maps.example.com/streetview?lat=43&lon=-79"},
        error=None,
        source="google_street_view",
    )
    mock_sat = ServiceResult(
        data={"url": "https://maps.example.com/satellite?lat=43&lon=-79"},
        error=None,
        source="google_satellite",
    )

    with (
        patch(
            "app.routes.property.google_maps.fetch_street_view",
            new_callable=AsyncMock,
            return_value=mock_sv,
        ),
        patch(
            "app.routes.property.google_maps.fetch_satellite",
            new_callable=AsyncMock,
            return_value=mock_sat,
        ),
    ):
        resp = await client.get("/api/v1/property/images?lat=43.65&lon=-79.38")

    assert resp.status_code == 200
    data = resp.json()
    assert data["street_view"]["data"]["url"].startswith("https://")
    assert data["satellite"]["data"]["url"].startswith("https://")
    assert data["street_view"]["error"] is None
    assert data["satellite"]["error"] is None


@pytest.mark.asyncio
async def test_analyze(client: AsyncClient):
    mock_vision = ServiceResult(
        data={
            "home_style": "Colonial",
            "has_pool": False,
            "pool_confidence": 0.1,
            "tree_count_estimate": 3,
            "has_garage": True,
            "condition_estimate": "Good",
            "approximate_age": "20-30 years",
        },
        error=None,
        source="openai_vision",
    )
    mock_seg = ServiceResult(
        data={"status": "sam_unavailable", "message": "SAM service URL is not configured"},
        error=None,
        source="sam3",
    )

    with (
        patch(
            "app.routes.property.vision.analyze_property",
            new_callable=AsyncMock,
            return_value=mock_vision,
        ),
        patch(
            "app.routes.property.segmentation.segment_image",
            new_callable=AsyncMock,
            return_value=mock_seg,
        ),
    ):
        resp = await client.post(
            "/api/v1/property/analyze",
            json={
                "street_view_url": "https://example.com/sv.jpg",
                "satellite_url": "https://example.com/sat.jpg",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis"]["data"]["home_style"] == "Colonial"
    assert data["analysis"]["data"]["has_garage"] is True
    assert data["segmentation"]["data"]["status"] == "sam_unavailable"


@pytest.mark.asyncio
async def test_segment_only_does_not_call_vision(client: AsyncClient):
    mock_seg = ServiceResult(
        data={"status": "sam_unavailable", "segments": []},
        error=None,
        source="sam3",
    )

    with (
        patch(
            "app.routes.property.segmentation.segment_image",
            new_callable=AsyncMock,
            return_value=mock_seg,
        ) as mock_segment,
        patch("app.routes.property.vision.analyze_property", new_callable=AsyncMock) as mock_vision,
    ):
        resp = await client.post(
            "/api/v1/property/segment",
            json={
                "image_url": "https://example.com/sat.jpg",
                "image_type": "satellite",
                "targets": [{"type": "aerial_roof", "prompt": "the roof"}],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["status"] == "sam_unavailable"
    mock_segment.assert_awaited_once()
    mock_vision.assert_not_called()


@pytest.mark.asyncio
async def test_get_pois(client: AsyncClient):
    mock_pois = ServiceResult(
        data=[
            {
                "id": 12345,
                "lat": 43.651,
                "lon": -79.381,
                "name": "Tim Hortons",
                "category": "food_drink",
                "tags": {"amenity": "cafe", "name": "Tim Hortons"},
            },
            {
                "id": 12346,
                "lat": 43.652,
                "lon": -79.382,
                "name": "Central Park",
                "category": "leisure:park",
                "tags": {"leisure": "park", "name": "Central Park"},
            },
        ],
        error=None,
        source="overpass",
    )

    with patch(
        "app.routes.property.pois.get_pois",
        new_callable=AsyncMock,
        return_value=mock_pois,
    ):
        resp = await client.get("/api/v1/property/pois?lat=43.65&lon=-79.38")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2
    assert data["data"][0]["name"] == "Tim Hortons"


@pytest.mark.asyncio
async def test_create_property(client: AsyncClient):
    mock_geocode = ServiceResult(
        data={
            "address": "123 Main St, Toronto, ON",
            "neighborhood": "Downtown",
            "cross_streets": "Main St",
            "city": "Toronto",
        },
        error=None,
        source="google_geocode",
    )
    mock_sv = ServiceResult(
        data={"url": "https://maps.example.com/sv"},
        error=None,
        source="google_street_view",
    )
    mock_sat = ServiceResult(
        data={"url": "https://maps.example.com/sat"},
        error=None,
        source="google_satellite",
    )
    mock_vision = ServiceResult(
        data={
            "home_style": "Victorian",
            "has_pool": False,
            "pool_confidence": 0.05,
            "tree_count_estimate": 5,
            "has_garage": False,
            "condition_estimate": "Good",
            "approximate_age": "50+ years",
        },
        error=None,
        source="openai_vision",
    )
    mock_seg = ServiceResult(
        data={"status": "sam_unavailable", "message": "SAM service URL is not configured"},
        error=None,
        source="sam3",
    )
    mock_pois_result = ServiceResult(
        data=[{"id": 1, "name": "Cafe", "category": "food_drink"}],
        error=None,
        source="overpass",
    )
    mock_cache = ServiceResult(data=None, error=None, source="postgres")
    mock_search = ServiceResult(
        data={"id": "11111111-2222-3333-4444-555555555555"},
        error=None,
        source="postgres",
    )
    mock_saved_profile = ServiceResult(
        data={
            "property": {
                "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "address": "123 Main St, Toronto, ON",
                "lat": 43.65,
                "lon": -79.38,
                "neighborhood": "Downtown",
                "cross_streets": "Main St",
                "created_at": "2026-03-20T00:00:00+00:00",
                "updated_at": "2026-03-20T00:00:00+00:00",
            },
            "images": [],
            "analysis": {"id": "analysis-1", "home_style": "Victorian"},
            "segmentation": {"status": "sam_unavailable"},
            "geospatial": {"id": "geo-1", "property_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "pois": []},
            "errors": [],
            "cache": {"status": "miss"},
        },
        error=None,
        source="postgres",
    )

    with (
        patch(
            "app.routes.property.google_maps.reverse_geocode",
            new_callable=AsyncMock,
            return_value=mock_geocode,
        ),
        patch("app.routes.property.property_store.get_cached_profile", new_callable=AsyncMock, return_value=mock_cache),
        patch("app.routes.property.property_store.create_search", new_callable=AsyncMock, return_value=mock_search),
        patch(
            "app.routes.property.google_maps.fetch_street_view",
            new_callable=AsyncMock,
            return_value=mock_sv,
        ),
        patch(
            "app.routes.property.google_maps.fetch_satellite",
            new_callable=AsyncMock,
            return_value=mock_sat,
        ),
        patch(
            "app.routes.property.vision.analyze_property",
            new_callable=AsyncMock,
            return_value=mock_vision,
        ),
        patch(
            "app.routes.property.segmentation.segment_image",
            new_callable=AsyncMock,
            return_value=mock_seg,
        ),
        patch(
            "app.routes.property.pois.get_pois",
            new_callable=AsyncMock,
            return_value=mock_pois_result,
        ),
        patch("app.routes.property.property_store.save_profile", new_callable=AsyncMock, return_value=mock_saved_profile),
    ):
        resp = await client.post(
            "/api/v1/property",
            json={"lat": 43.65, "lon": -79.38},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["property"]["address"] == "123 Main St, Toronto, ON"
    assert data["property"]["id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert data["analysis"]["home_style"] == "Victorian"
    assert data["segmentation"]["status"] == "sam_unavailable"
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_create_property_cache_hit(client: AsyncClient):
    mock_geocode = ServiceResult(
        data={"address": "123 Main St, Toronto, ON", "city": "Toronto"},
        error=None,
        source="google_geocode",
    )
    mock_cached = ServiceResult(
        data={
            "property": {"id": "cached", "address": "123 Main St, Toronto, ON"},
            "images": [],
            "analysis": {"home_style": "Cached"},
            "segmentation": None,
            "geospatial": None,
            "errors": [],
            "cache": {"status": "hit"},
        },
        error=None,
        source="postgres",
    )

    with (
        patch("app.routes.property.google_maps.reverse_geocode", new_callable=AsyncMock, return_value=mock_geocode),
        patch("app.routes.property.property_store.get_cached_profile", new_callable=AsyncMock, return_value=mock_cached),
        patch("app.routes.property.vision.analyze_property", new_callable=AsyncMock) as mock_vision,
    ):
        resp = await client.post("/api/v1/property", json={"lat": 43.65, "lon": -79.38})

    assert resp.status_code == 200
    data = resp.json()
    assert data["cache"]["status"] == "hit"
    assert data["analysis"]["home_style"] == "Cached"
    mock_vision.assert_not_called()
