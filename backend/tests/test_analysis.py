from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.schemas import PropertyAnalysis, ServiceResult
from app.services import vision

PROPERTY_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _ok(data, source="test"):
    return ServiceResult(data=data, error=None, source=source)


@pytest.fixture
def pipeline_mocks():
    """Patch every service the property pipeline calls with passing defaults."""
    mocks = {
        "google_maps.reverse_geocode": _ok({"address": "123 Main St, Toronto, ON"}),
        "supabase.save_property": _ok(
            {
                "id": PROPERTY_ID,
                "address": "123 Main St, Toronto, ON",
                "lat": 43.65,
                "lon": -79.38,
            }
        ),
        "google_maps.fetch_street_view": _ok({"url": "https://maps.example.com/sv"}),
        "google_maps.fetch_satellite": _ok({"url": "https://maps.example.com/sat"}),
        "supabase.save_images": _ok([]),
        "vision.analyze_property": _ok(PropertyAnalysis()),
        "supabase.save_analysis": _ok({}),
        "segmentation.segment_image": _ok({"status": "sam2_not_available"}),
        "pois.get_pois": _ok([]),
        "supabase.save_geospatial": _ok({}),
    }
    with ExitStack() as stack:
        patched = {
            name: stack.enter_context(
                patch(
                    f"app.routes.property.{name}",
                    new_callable=AsyncMock,
                    return_value=result,
                )
            )
            for name, result in mocks.items()
        }
        yield patched


async def test_unknown_values_stay_null(client: AsyncClient, pipeline_mocks):
    pipeline_mocks["vision.analyze_property"].return_value = _ok(
        PropertyAnalysis(has_pool=None, pool_confidence=0.0, has_garage=True)
    )

    resp = await client.post("/api/v1/property", json={"lat": 43.65, "lon": -79.38})

    analysis = resp.json()["analysis"]
    assert analysis["has_pool"] is None
    assert analysis["has_chimney"] is None
    assert analysis["has_garage"] is True

    saved = pipeline_mocks["supabase.save_analysis"].await_args.args[0]
    assert saved["has_pool"] is None
    assert saved["has_chimney"] is None


async def test_response_analysis_id_matches_saved_row(client: AsyncClient, pipeline_mocks):
    resp = await client.post("/api/v1/property", json={"lat": 43.65, "lon": -79.38})

    analysis = resp.json()["analysis"]
    saved = pipeline_mocks["supabase.save_analysis"].await_args.args[0]
    assert analysis["id"] == saved["id"]
    assert saved["property_id"] == PROPERTY_ID
    assert saved["model_used"] == vision.MODEL


async def test_vision_error_skips_analysis(client: AsyncClient, pipeline_mocks):
    pipeline_mocks["vision.analyze_property"].return_value = ServiceResult(
        data={"raw_text": "not json"},
        error="JSON parse error: no JSON",
        source="openai_vision",
    )

    resp = await client.post("/api/v1/property", json={"lat": 43.65, "lon": -79.38})

    data = resp.json()
    assert data["analysis"] is None
    assert any(e.startswith("Vision analysis:") for e in data["errors"])
    pipeline_mocks["supabase.save_analysis"].assert_not_awaited()


def test_to_record_keeps_model_extras_in_raw_response():
    analysis = PropertyAnalysis.model_validate({"has_pool": None, "unexpected_field": "kept"})

    record = analysis.to_record(
        analysis_id="analysis-1",
        property_id=PROPERTY_ID,
        model_used="test-model",
        analyzed_at="2026-01-01T00:00:00+00:00",
    )

    assert "unexpected_field" not in record
    assert record["raw_response"]["unexpected_field"] == "kept"
    assert record["has_pool"] is None


def _mock_openai(text: str) -> MagicMock:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return MagicMock(return_value=client)


async def test_vision_validates_model_output():
    text = '```json\n{"has_pool": null, "stories": 2, "tree_count_estimate": 4}\n```'
    with patch("app.services.vision.AsyncOpenAI", _mock_openai(text)):
        result = await vision.analyze_property("https://example.com/sv.jpg")

    assert result.error is None
    assert isinstance(result.data, PropertyAnalysis)
    assert result.data.has_pool is None
    assert result.data.stories == "2"
    assert result.data.tree_count_estimate == 4


async def test_vision_rejects_output_that_does_not_match_schema():
    text = '{"tree_count_estimate": "lots"}'
    with patch("app.services.vision.AsyncOpenAI", _mock_openai(text)):
        result = await vision.analyze_property("https://example.com/sv.jpg")

    assert result.error.startswith("Schema validation error")
    assert result.data == {"raw_text": text}
