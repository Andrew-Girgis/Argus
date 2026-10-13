from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.config import settings
from app.models.schemas import FeedbackRequest, PropertyAnalysis, ServiceResult
from app.observability import analysis_trace_id, score_feedback, traced_call
from app.utils import redact_secrets
from tests.test_analysis import PROPERTY_ID, _ok, _vision

KEYED_URL = "https://maps.googleapis.com/maps/api/streetview/metadata?location=x&key=SECRET_TEST_KEY"


@pytest.fixture
def langfuse_client(monkeypatch):
    """Replace the Langfuse client with a mock that records spans and scores."""
    client = MagicMock()
    spans = []

    @contextmanager
    def start_as_current_observation(**kwargs):
        span = MagicMock(name=kwargs["name"])
        spans.append((kwargs, span))
        yield span

    client.start_as_current_observation.side_effect = start_as_current_observation
    client.spans = spans
    monkeypatch.setattr("langfuse.get_client", lambda: client)
    return client


@pytest.fixture
def tracing_enabled(monkeypatch):
    monkeypatch.setattr(settings, "LANGFUSE_TRACING_ENABLED", True)
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk")


def test_redact_secrets_masks_keys_in_urls():
    message = f"Client error '403 Forbidden' for url '{KEYED_URL}'"

    redacted = redact_secrets(message)

    assert "SECRET_TEST_KEY" not in redacted
    assert "key=<redacted>" in redacted


def test_analysis_trace_id_is_deterministic_and_valid():
    trace_id = analysis_trace_id("analysis-1")

    assert trace_id == analysis_trace_id("analysis-1")
    assert trace_id != analysis_trace_id("analysis-2")
    assert len(trace_id) == 32
    int(trace_id, 16)


async def test_traced_call_records_redacted_error(langfuse_client):
    async def failing():
        return ServiceResult(data=None, error=f"failed for {KEYED_URL}", source="google")

    result = await traced_call("fetch-street-view", failing())

    assert result.error.startswith("failed for")
    kwargs, span = langfuse_client.spans[0]
    assert kwargs["name"] == "fetch-street-view"
    update = span.update.call_args.kwargs
    assert update["level"] == "ERROR"
    assert "SECRET_TEST_KEY" not in update["status_message"]


async def test_traced_call_records_only_the_summary(langfuse_client):
    async def ok():
        return ServiceResult(data={"url": KEYED_URL}, error=None, source="google")

    await traced_call("fetch-satellite", ok(), summarize=lambda d: {"available": True})

    _, span = langfuse_client.spans[0]
    assert span.update.call_args.kwargs["output"] == {
        "source": "google",
        "available": True,
    }


async def test_property_trace_uses_the_saved_analysis_id(
    client: AsyncClient, langfuse_client, monkeypatch
):
    traced = {}

    @contextmanager
    def fake_trace_analysis(analysis_id, *, input, metadata):
        traced["analysis_id"] = analysis_id
        traced["metadata"] = metadata
        root = MagicMock()
        traced["root"] = root
        yield root

    monkeypatch.setattr("app.routes.property.trace_analysis", fake_trace_analysis)
    save_analysis = AsyncMock(return_value=ServiceResult(data={}, error=None, source="test"))

    services = {
        "google_maps.reverse_geocode": _ok({"address": "1 Main St"}),
        "supabase.save_property": _ok({"id": PROPERTY_ID, "address": "1 Main St", "lat": 1, "lon": 2}),
        "google_maps.fetch_street_view": _ok({"url": KEYED_URL}),
        "google_maps.fetch_satellite": _ok({"url": KEYED_URL}),
        "supabase.save_images": _ok([]),
        "vision.analyze_property": _ok(_vision(PropertyAnalysis())),
        "segmentation.segment_image": _ok({}),
        "pois.get_pois": _ok([]),
        "supabase.save_geospatial": _ok({}),
    }
    for name, result in services.items():
        monkeypatch.setattr(
            f"app.routes.property.{name}", AsyncMock(return_value=result)
        )
    monkeypatch.setattr("app.routes.property.supabase.save_analysis", save_analysis)

    resp = await client.post("/api/v1/property", json={"lat": 43.65, "lon": -79.38})

    analysis_id = resp.json()["analysis"]["id"]
    assert traced["analysis_id"] == analysis_id
    assert save_analysis.await_args.args[0]["id"] == analysis_id
    assert traced["metadata"]["vision_model"] == settings.VISION_MODEL
    root_update = traced["root"].update.call_args.kwargs
    assert root_update["output"]["analysis_id"] == analysis_id
    assert root_update["metadata"] == {"property_id": PROPERTY_ID}


def _feedback(**overrides) -> FeedbackRequest:
    data = {
        "analysis_id": "analysis-1",
        "property_id": "property-1",
        "field_name": "has_pool",
        "ai_value": True,
        "ai_confidence": 0.8,
        "corrected_value": False,
        "notes": "Pool is the neighbour's",
    }
    return FeedbackRequest(**{**data, **overrides})


def test_score_feedback_attaches_correction_to_analysis_trace(langfuse_client, tracing_enabled):
    score_feedback(_feedback(), "feedback-1")

    kwargs = langfuse_client.create_score.call_args.kwargs
    assert kwargs["name"] == "correct:has_pool"
    assert kwargs["value"] == 0.0
    assert kwargs["data_type"] == "BOOLEAN"
    assert kwargs["trace_id"] == analysis_trace_id("analysis-1")
    assert kwargs["score_id"] == "feedback-1"
    assert kwargs["comment"] == "Pool is the neighbour's"
    assert kwargs["metadata"]["corrected_value"] is False


def test_score_feedback_marks_confirmed_values_correct(langfuse_client, tracing_enabled):
    score_feedback(_feedback(corrected_value=True), "feedback-1")

    assert langfuse_client.create_score.call_args.kwargs["value"] == 1.0


def test_score_feedback_skipped_when_tracing_disabled(langfuse_client, monkeypatch):
    monkeypatch.setattr(settings, "LANGFUSE_TRACING_ENABLED", False)

    score_feedback(_feedback(), "feedback-1")

    langfuse_client.create_score.assert_not_called()


def test_score_feedback_skipped_without_analysis_id(langfuse_client, tracing_enabled):
    score_feedback(_feedback(analysis_id=None), "feedback-1")

    langfuse_client.create_score.assert_not_called()


def test_score_feedback_never_raises(langfuse_client, tracing_enabled):
    langfuse_client.create_score.side_effect = RuntimeError("Langfuse is down")

    score_feedback(_feedback(), "feedback-1")


async def test_feedback_saved_and_scored(client: AsyncClient, langfuse_client, tracing_enabled):
    stored = ServiceResult(data={"id": "feedback-1"}, error=None, source="postgres")
    with patch(
        "app.services.feedback._store_feedback", new_callable=AsyncMock, return_value=stored
    ):
        resp = await client.post(
            "/api/v1/feedback", json=_feedback().model_dump()
        )

    assert resp.json() == {"ok": True, "error": None}
    assert langfuse_client.create_score.call_args.kwargs["score_id"] == "feedback-1"


async def test_feedback_saved_when_langfuse_fails(client: AsyncClient, langfuse_client, tracing_enabled):
    langfuse_client.create_score.side_effect = RuntimeError("Langfuse is down")
    stored = ServiceResult(data={"id": "feedback-1"}, error=None, source="postgres")
    with patch(
        "app.services.feedback._store_feedback", new_callable=AsyncMock, return_value=stored
    ):
        resp = await client.post(
            "/api/v1/feedback", json=_feedback().model_dump()
        )

    assert resp.json() == {"ok": True, "error": None}


async def test_failed_feedback_save_is_not_scored(client: AsyncClient, langfuse_client, tracing_enabled):
    failed = ServiceResult(data=None, error="db down", source="postgres")
    with patch(
        "app.services.feedback._store_feedback", new_callable=AsyncMock, return_value=failed
    ):
        resp = await client.post(
            "/api/v1/feedback", json=_feedback().model_dump()
        )

    assert resp.json() == {"ok": False, "error": "db down"}
    langfuse_client.create_score.assert_not_called()
