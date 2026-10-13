from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import json

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.models.schemas import PropertyAnalysis, ServiceResult
from app.config import settings
from app.services import vision
from app.services.images import DownloadedImage, ImageDownloadError
from app.services.vision import VisionResult

KEYED_SV_URL = "https://maps.googleapis.com/maps/api/streetview?location=1+Main+St&key=SECRET_TEST_KEY"
KEYED_SAT_URL = "https://maps.googleapis.com/maps/api/staticmap?center=43,-79&key=SECRET_TEST_KEY"

PROPERTY_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _ok(data, source="test"):
    return ServiceResult(data=data, error=None, source=source)


def _vision(analysis: PropertyAnalysis, model: str = "gpt-test-2026-01-01") -> VisionResult:
    return VisionResult(
        analysis=analysis, model=model, prompt_version="test", image_sha256={}
    )


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
        "vision.analyze_property": _ok(_vision(PropertyAnalysis())),
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
        _vision(PropertyAnalysis(has_pool=None, pool_confidence=0.0, has_garage=True))
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
    assert saved["model_used"] == "gpt-test-2026-01-01"
    assert analysis["model_used"] == "gpt-test-2026-01-01"


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


def _parsed_response(analysis=None, *, status="completed", refusal=None, model="gpt-4o-2024-08-06"):
    content = [SimpleNamespace(type="refusal", refusal=refusal)] if refusal else []
    return SimpleNamespace(
        status=status,
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        output=[SimpleNamespace(type="message", content=content)],
        output_parsed=analysis,
        model=model,
    )


@pytest.fixture
def openai_parse(monkeypatch):
    """Patch the OpenAI client and return the mocked ``responses.parse``."""
    parse = AsyncMock(return_value=_parsed_response(PropertyAnalysis(has_pool=None)))
    client = MagicMock()
    client.responses.parse = parse
    monkeypatch.setattr(vision, "AsyncOpenAI", MagicMock(return_value=client))
    monkeypatch.setattr(vision, "download_image", AsyncMock(side_effect=_fake_download))
    return parse


async def _fake_download(url: str, label: str) -> DownloadedImage:
    return DownloadedImage(
        data_url=f"data:image/jpeg;base64,{label}",
        sha256=f"{label}-sha",
        content_type="image/jpeg",
        size_bytes=10,
    )


async def test_vision_returns_parsed_analysis_and_reported_model(openai_parse):
    result = await vision.analyze_property(KEYED_SV_URL)

    assert result.error is None
    assert result.data.analysis.has_pool is None
    assert result.data.model == "gpt-4o-2024-08-06"
    assert result.data.prompt_version == vision.PROMPT_VERSION
    kwargs = openai_parse.await_args.kwargs
    assert kwargs["text_format"] is PropertyAnalysis
    assert kwargs["model"] == settings.VISION_MODEL


async def test_vision_omits_unset_optional_parameters(openai_parse, monkeypatch):
    monkeypatch.setattr(settings, "VISION_TEMPERATURE", None)
    monkeypatch.setattr(settings, "VISION_REASONING_EFFORT", None)

    await vision.analyze_property(KEYED_SV_URL)

    kwargs = openai_parse.await_args.kwargs
    assert "temperature" not in kwargs
    assert "reasoning" not in kwargs
    assert "max_tokens" not in kwargs
    assert kwargs["max_output_tokens"] == settings.VISION_MAX_OUTPUT_TOKENS


async def test_vision_sends_configured_parameters(openai_parse, monkeypatch):
    monkeypatch.setattr(settings, "VISION_MODEL", "some-new-model")
    monkeypatch.setattr(settings, "VISION_TEMPERATURE", 0.2)
    monkeypatch.setattr(settings, "VISION_REASONING_EFFORT", "low")

    await vision.analyze_property(KEYED_SV_URL)

    kwargs = openai_parse.await_args.kwargs
    assert kwargs["model"] == "some-new-model"
    assert kwargs["temperature"] == 0.2
    assert kwargs["reasoning"] == {"effort": "low"}
    assert kwargs["metadata"]["model"] == "some-new-model"
    assert kwargs["metadata"]["prompt_version"] == vision.PROMPT_VERSION


async def test_vision_reports_refusal(openai_parse):
    openai_parse.return_value = _parsed_response(refusal="I can't help with that.")

    result = await vision.analyze_property(KEYED_SV_URL)

    assert result.data is None
    assert result.error == "Model refused: I can't help with that."


async def test_vision_reports_incomplete_response(openai_parse):
    openai_parse.return_value = _parsed_response(status="incomplete")

    result = await vision.analyze_property(KEYED_SV_URL)

    assert result.data is None
    assert result.error == "Vision response incomplete: max_output_tokens"


async def test_vision_reports_truncated_output(openai_parse):
    # The SDK raises while parsing JSON that was cut off mid-object.
    try:
        PropertyAnalysis.model_validate_json('{"has_pool": tr')
    except ValidationError as exc:
        openai_parse.side_effect = exc

    result = await vision.analyze_property(KEYED_SV_URL)

    assert result.data is None
    assert "VISION_MAX_OUTPUT_TOKENS" in result.error


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        PropertyAnalysis(pool_confidence=1.5)


def test_categorical_fields_reject_unlisted_values():
    with pytest.raises(ValidationError):
        PropertyAnalysis(roof_type="Dome")


async def test_openai_request_contains_image_bytes_not_keyed_urls(openai_parse):
    result = await vision.analyze_property(KEYED_SV_URL, KEYED_SAT_URL)

    kwargs = openai_parse.await_args.kwargs
    sent = json.dumps(
        {k: v for k, v in kwargs.items() if k != "text_format"}, default=str
    )
    assert "SECRET_TEST_KEY" not in sent
    assert "googleapis" not in sent
    images = [p for p in kwargs["input"][0]["content"] if p["type"] == "input_image"]
    assert [p["image_url"] for p in images] == [
        "data:image/jpeg;base64,street_view",
        "data:image/jpeg;base64,satellite",
    ]
    assert kwargs["metadata"]["street_view_sha256"] == "street_view-sha"
    assert kwargs["metadata"]["satellite_sha256"] == "satellite-sha"
    assert result.data.image_sha256 == {
        "street_view": "street_view-sha",
        "satellite": "satellite-sha",
    }


async def test_download_failure_skips_openai_call(openai_parse, monkeypatch):
    monkeypatch.setattr(
        vision,
        "download_image",
        AsyncMock(side_effect=ImageDownloadError("satellite image download failed: HTTP 403")),
    )

    result = await vision.analyze_property(KEYED_SV_URL, KEYED_SAT_URL)

    assert result.data is None
    assert result.error == "satellite image download failed: HTTP 403"
    openai_parse.assert_not_awaited()


async def test_analyze_endpoint_rejects_non_google_images(client: AsyncClient, openai_parse, monkeypatch):
    # Use the real downloader so the host allowlist is exercised end to end.
    from app.services import images

    monkeypatch.setattr(vision, "download_image", images.download_image)
    with patch(
        "app.routes.property.segmentation.segment_image",
        new_callable=AsyncMock,
        return_value=_ok({"status": "sam2_not_available"}),
    ):
        resp = await client.post(
            "/api/v1/property/analyze",
            json={
                "street_view_url": "http://169.254.169.254/latest/meta-data",
                "satellite_url": "https://example.com/sat.jpg",
            },
        )

    analysis = resp.json()["analysis"]
    assert analysis["data"] is None
    assert "host is not allowed" in analysis["error"]
    openai_parse.assert_not_awaited()
