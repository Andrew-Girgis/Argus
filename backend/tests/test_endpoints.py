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
        data={"status": "sam2_not_available", "message": "SAM2 module not installed"},
        error=None,
        source="sam2",
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
    assert data["segmentation"]["data"]["status"] == "sam2_not_available"


@pytest.mark.asyncio
async def test_get_isochrone(client: AsyncClient):
    mock_iso = ServiceResult(
        data={
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"value": 300, "profile": "foot-walking"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-79.38, 43.65], [-79.37, 43.66], [-79.38, 43.65]]
                        ],
                    },
                }
            ],
        },
        error=None,
        source="openrouteservice",
    )

    with patch(
        "app.routes.property.isochrone.get_isochrone",
        new_callable=AsyncMock,
        return_value=mock_iso,
    ):
        resp = await client.get("/api/v1/property/isochrone?lat=43.65&lon=-79.38")

    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["type"] == "FeatureCollection"
    assert len(data["data"]["features"]) == 1


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
    mock_save_property = ServiceResult(
        data={
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "address": "123 Main St, Toronto, ON",
            "lat": 43.65,
            "lon": -79.38,
            "created_at": "2026-03-20T00:00:00+00:00",
            "updated_at": "2026-03-20T00:00:00+00:00",
        },
        error=None,
        source="supabase",
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
    mock_save_images = ServiceResult(
        data=[
            {
                "id": "img-1",
                "property_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "image_type": "street_view",
                "url": "https://maps.example.com/sv",
                "fetched_at": "2026-03-20T00:00:00+00:00",
            }
        ],
        error=None,
        source="supabase",
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
    mock_save_analysis = ServiceResult(
        data={"id": "analysis-1", "home_style": "Victorian"},
        error=None,
        source="supabase",
    )
    mock_seg = ServiceResult(
        data={"status": "sam2_not_available", "message": "SAM2 module not installed"},
        error=None,
        source="sam2",
    )
    mock_iso = ServiceResult(
        data={"type": "FeatureCollection", "features": []},
        error=None,
        source="openrouteservice",
    )
    mock_pois_result = ServiceResult(
        data=[{"id": 1, "name": "Cafe", "category": "food_drink"}],
        error=None,
        source="overpass",
    )
    mock_save_geo = ServiceResult(
        data={"id": "geo-1", "isochrone_geojson": {}, "pois": []},
        error=None,
        source="supabase",
    )

    with (
        patch(
            "app.routes.property.google_maps.reverse_geocode",
            new_callable=AsyncMock,
            return_value=mock_geocode,
        ),
        patch(
            "app.routes.property.supabase.save_property",
            new_callable=AsyncMock,
            return_value=mock_save_property,
        ),
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
            "app.routes.property.supabase.save_images",
            new_callable=AsyncMock,
            return_value=mock_save_images,
        ),
        patch(
            "app.routes.property.vision.analyze_property",
            new_callable=AsyncMock,
            return_value=mock_vision,
        ),
        patch(
            "app.routes.property.supabase.save_analysis",
            new_callable=AsyncMock,
            return_value=mock_save_analysis,
        ),
        patch(
            "app.routes.property.segmentation.segment_image",
            new_callable=AsyncMock,
            return_value=mock_seg,
        ),
        patch(
            "app.routes.property.isochrone.get_isochrone",
            new_callable=AsyncMock,
            return_value=mock_iso,
        ),
        patch(
            "app.routes.property.pois.get_pois",
            new_callable=AsyncMock,
            return_value=mock_pois_result,
        ),
        patch(
            "app.routes.property.supabase.save_geospatial",
            new_callable=AsyncMock,
            return_value=mock_save_geo,
        ),
        patch(
            "app.routes.property.scoring.compute_scores",
            return_value=ServiceResult(
                data={
                    "walk_score": 72,
                    "walk_description": "Very Walkable",
                    "transit_score": 55,
                    "transit_description": "Good Transit",
                    "bike_score": 60,
                    "bike_description": "Bikeable",
                    "drive_score": 85,
                    "amenity_score": 65,
                    "amenity_breakdown": {"grocery": 15, "education": 10},
                },
                error=None,
                source="scoring",
            ),
        ),
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
    assert data["segmentation"]["status"] == "sam2_not_available"
    assert data["errors"] == []
