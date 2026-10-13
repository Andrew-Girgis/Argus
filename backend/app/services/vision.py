import logging

from langfuse.openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.models.schemas import PropertyAnalysis, ServiceResult

logger = logging.getLogger(__name__)

# Bump whenever INSTRUCTIONS or the PropertyAnalysis schema changes, so traces
# and experiment runs can be compared by prompt version.
PROMPT_VERSION = "2"

INSTRUCTIONS = """You are an expert property analyst. Analyze the provided property images
(street view and/or satellite) and fill in every field of the response schema.

Rules:
- Pair every value with a confidence score from 0.0 to 1.0 reflecting how certain you are
  based on what is visible. Use 1.0 only when the evidence is unambiguous.
- If a feature is not visible or you cannot determine it with reasonable certainty, set the
  value to null and its confidence to 0.0. Do not guess.
- Yes/no fields: true, false, or null when you cannot determine.
- Fields with listed options: use one of the options, or null.

Use the street view image for building details, exterior, garage, and condition, and the
satellite image for lot shape, pool, trees, fencing, and yard."""


class VisionResult(BaseModel):
    analysis: PropertyAnalysis
    model: str
    prompt_version: str


def _model_parameters() -> dict:
    """Request parameters, omitting optional ones that are not configured."""
    params: dict = {"max_output_tokens": settings.VISION_MAX_OUTPUT_TOKENS}
    if settings.VISION_TEMPERATURE is not None:
        params["temperature"] = settings.VISION_TEMPERATURE
    if settings.VISION_REASONING_EFFORT:
        params["reasoning"] = {"effort": settings.VISION_REASONING_EFFORT}
    return params


def _refusal(response) -> str | None:
    for item in response.output:
        if item.type != "message":
            continue
        for part in item.content:
            if part.type == "refusal":
                return part.refusal
    return None


async def analyze_property(
    street_view_url: str | None = None,
    satellite_url: str | None = None,
) -> ServiceResult:
    """Analyze property images with the configured OpenAI vision model."""
    try:
        if not street_view_url and not satellite_url:
            return ServiceResult(
                data=None,
                error="At least one image URL is required",
                source="openai_vision",
            )

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        content: list[dict] = [
            {"type": "input_text", "text": "Analyze this property."}
        ]
        for url in (street_view_url, satellite_url):
            if url:
                content.append(
                    {"type": "input_image", "image_url": url, "detail": "high"}
                )

        params = _model_parameters()
        response = await client.responses.parse(
            model=settings.VISION_MODEL,
            instructions=INSTRUCTIONS,
            input=[{"role": "user", "content": content}],
            text_format=PropertyAnalysis,
            **params,
            name="analyze-property-images",
            metadata={
                "workflow": "property_vision_analysis",
                "workflow_version": settings.APP_VERSION,
                "environment": settings.OBSERVABILITY_ENV,
                "prompt_version": PROMPT_VERSION,
                "model": settings.VISION_MODEL,
                "model_parameters": params,
            },
        )

        if response.status == "incomplete":
            reason = getattr(response.incomplete_details, "reason", None)
            return ServiceResult(
                data=None,
                error=f"Vision response incomplete: {reason}",
                source="openai_vision",
            )

        refusal = _refusal(response)
        if refusal:
            return ServiceResult(
                data=None, error=f"Model refused: {refusal}", source="openai_vision"
            )

        if response.output_parsed is None:
            return ServiceResult(
                data=None, error="Model returned no analysis", source="openai_vision"
            )

        return ServiceResult(
            data=VisionResult(
                analysis=response.output_parsed,
                model=response.model,
                prompt_version=PROMPT_VERSION,
            ),
            error=None,
            source="openai_vision",
        )

    except ValidationError as exc:
        # Structured Outputs guarantees the schema unless the output was cut off.
        logger.exception("Vision output did not match the analysis schema")
        return ServiceResult(
            data=None,
            error=(
                "Vision output did not match the analysis schema (it may have been "
                f"truncated; check VISION_MAX_OUTPUT_TOKENS): {exc}"
            ),
            source="openai_vision",
        )
    except Exception as exc:
        logger.exception("Error during property analysis")
        return ServiceResult(data=None, error=str(exc), source="openai_vision")
