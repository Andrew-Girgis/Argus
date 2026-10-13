import logging
import os
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from typing import Any

from app.config import Settings, settings
from app.models.schemas import FeedbackRequest, ServiceResult
from app.utils import redact_secrets

logger = logging.getLogger(__name__)


def runtime_observability_enabled(config: Settings = settings) -> bool:
    """Return whether runtime tracing has all required configuration."""
    return bool(
        config.LANGFUSE_TRACING_ENABLED
        and config.LANGFUSE_PUBLIC_KEY
        and config.LANGFUSE_SECRET_KEY
    )


def setup_runtime_observability(config: Settings = settings) -> None:
    """Configure Langfuse before its OpenAI wrapper is imported."""
    enabled = runtime_observability_enabled(config)
    os.environ["LANGFUSE_TRACING_ENABLED"] = str(enabled).lower()
    os.environ["LANGFUSE_BASE_URL"] = config.LANGFUSE_BASE_URL
    os.environ["LANGFUSE_TRACING_ENVIRONMENT"] = config.OBSERVABILITY_ENV
    os.environ["LANGFUSE_RELEASE"] = config.APP_VERSION

    if enabled:
        os.environ["LANGFUSE_PUBLIC_KEY"] = config.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = config.LANGFUSE_SECRET_KEY


def setup_mlflow_evaluation(config: Settings = settings) -> None:
    """Configure MLflow only for explicit benchmark and evaluation commands."""
    if not config.MLFLOW_EVAL_ENABLED:
        raise RuntimeError("MLFLOW_EVAL_ENABLED must be true for evaluation runs")

    import mlflow

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = config.MLFLOW_S3_ENDPOINT_URL
    if config.AWS_ACCESS_KEY_ID:
        os.environ["AWS_ACCESS_KEY_ID"] = config.AWS_ACCESS_KEY_ID
    if config.AWS_SECRET_ACCESS_KEY:
        os.environ["AWS_SECRET_ACCESS_KEY"] = config.AWS_SECRET_ACCESS_KEY

    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(config.MLFLOW_EXPERIMENT_NAME)


def analysis_trace_id(analysis_id: str) -> str:
    """Deterministic Langfuse trace ID for a property analysis.

    Feedback carries only the analysis ID, so deriving the trace ID from it lets
    scores be attached without storing the trace ID in the database.
    """
    from langfuse import Langfuse

    return Langfuse.create_trace_id(seed=analysis_id)


@contextmanager
def trace_analysis(analysis_id: str, *, input: dict, metadata: dict[str, str]):
    """Root span for one property analysis; a no-op when tracing is disabled."""
    from langfuse import get_client, propagate_attributes

    with (
        get_client().start_as_current_observation(
            name="analyze-property",
            as_type="span",
            trace_context={"trace_id": analysis_trace_id(analysis_id)},
            input=input,
        ) as root,
        propagate_attributes(
            trace_name="analyze-property",
            metadata={"analysis_id": analysis_id, **metadata},
        ),
    ):
        yield root


async def traced_call(
    name: str,
    call: Awaitable[ServiceResult],
    *,
    input: dict | None = None,
    summarize: Callable[[Any], dict] | None = None,
) -> ServiceResult:
    """Await a service call inside a child span and record its outcome.

    Only ``summarize(data)`` is recorded as output, never the raw data, because
    some results (e.g. image URLs) contain credentials.
    """
    from langfuse import get_client

    with get_client().start_as_current_observation(
        name=name, as_type="span", input=input
    ) as span:
        result = await call
        if result.error:
            span.update(
                level="ERROR",
                status_message=redact_secrets(result.error),
                output={"source": result.source},
            )
        else:
            output = summarize(result.data) if summarize and result.data else {}
            span.update(output={"source": result.source, **output})
        return result


def score_feedback(req: FeedbackRequest, feedback_id: str) -> None:
    """Attach a reviewer's verdict to the analysis trace as a Langfuse score.

    Never raises: feedback is already saved, and the score is best effort.
    """
    if not req.analysis_id or not runtime_observability_enabled():
        return
    try:
        from langfuse import get_client

        get_client().create_score(
            name=f"correct:{req.field_name}",
            value=1.0 if req.corrected_value == req.ai_value else 0.0,
            data_type="BOOLEAN",
            trace_id=analysis_trace_id(req.analysis_id),
            score_id=feedback_id,
            comment=req.notes,
            metadata={
                "feedback_id": feedback_id,
                "property_id": req.property_id,
                "ai_value": req.ai_value,
                "ai_confidence": req.ai_confidence,
                "corrected_value": req.corrected_value,
            },
        )
    except Exception:
        logger.warning("Could not send feedback score to Langfuse", exc_info=True)
