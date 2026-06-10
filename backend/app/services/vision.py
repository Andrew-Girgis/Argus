import json
import logging
import re

from langfuse import observe
from langfuse.openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import ServiceResult
from app.observability import langfuse

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are a Canadian residential property intelligence extraction engine.
Analyze the provided property images (street view and/or satellite) and return a JSON object.

IMPORTANT RULES:
- For every field include a paired confidence score (0.0 to 1.0) reflecting how certain you are
  based on what is visible in the images. Use 1.0 only when the evidence is unambiguous.
- If a feature is not visible or you cannot determine it with reasonable certainty, set the
  value to null and the confidence to 0.0. Do not guess.
- For boolean fields: use true, false, or null (cannot determine).
- For string fields: use the listed options, or null if you cannot determine.
- For numeric fields: use an integer, or null if you cannot determine.
- Use Canadian residential conventions. Ontario-specific assumptions are allowed where the
  address/context supports them, but mark those values as inferred or assumed.
- Distinguish observed visual evidence from inferred or regional assumptions.
- Use this reasoning hierarchy when exact data is unavailable: exact visible evidence,
  satellite/street imagery inference, same-street/subdivision patterns if evident, then
  regional construction conventions.

{
  "property_type": "one of: Detached, Semi-Detached, Townhouse, Condo, Duplex, Triplex, Other — or null if unclear",
  "property_type_confidence": 0.0 to 1.0,

  "home_style": "architectural style (e.g., Colonial, Ranch, Tudor, Split-level, Modern, Victorian, Bungalow, Contemporary) — or null if unclear",
  "home_style_confidence": 0.0 to 1.0,

  "stories": "one of: 1, 1.5, 2, 2.5, 3, Split-level — or null if unclear",
  "stories_confidence": 0.0 to 1.0,

  "exterior_material": "primary material (e.g., Brick, Vinyl Siding, Stone, Stucco, Wood, Aluminum, Mixed) — or null if unclear",
  "exterior_material_confidence": 0.0 to 1.0,

  "has_pool": true/false/null,
  "pool_confidence": 0.0 to 1.0,

  "tree_count_estimate": integer or null,
  "tree_count_confidence": 0.0 to 1.0,

  "has_garage": true/false/null,
  "garage_confidence": 0.0 to 1.0,

  "parking_type": "one of: Attached Garage, Detached Garage, Carport, Driveway Only, Street, None visible — or null if unclear",
  "parking_type_confidence": 0.0 to 1.0,

  "parking_spaces_estimate": integer or null,
  "parking_spaces_confidence": 0.0 to 1.0,

  "condition_estimate": "one of: Excellent, Good, Fair, Poor — or null if unclear",
  "condition_confidence": 0.0 to 1.0,

  "approximate_age": "estimated age range (e.g., '0-5 years', '5-15 years', '16-30 years', '30-50 years', '50+ years') — or null if unclear",
  "approximate_age_confidence": 0.0 to 1.0,

  "lot_shape": "one of: Regular, Pie-Shaped, Corner, Irregular, Cul-de-sac — or null if unclear",
  "lot_shape_confidence": 0.0 to 1.0,

  "has_fenced_yard": true/false/null,
  "fence_confidence": 0.0 to 1.0,

  "has_solar_panels": true/false/null,
  "solar_panels_confidence": 0.0 to 1.0,

  "roof_type": "one of: Gable, Clipped Gable, Dutch Gable, Gambrel, Hip, Mansard, Shed, Flat — or null if unclear",
  "roof_type_confidence": 0.0 to 1.0,

  "has_sidewalk": true/false/null,
  "sidewalk_confidence": 0.0 to 1.0,

  "driveway_material": "one of: Concrete, Asphalt, Interlock/Paving Stone, Gravel, None visible — or null if unclear",
  "driveway_material_confidence": 0.0 to 1.0,

  "has_chimney": true/false/null,
  "chimney_confidence": 0.0 to 1.0,

  "has_deck_or_patio": true/false/null,
  "deck_patio_confidence": 0.0 to 1.0,

  "has_gutters": true/false/null,
  "gutters_confidence": 0.0 to 1.0,

  "has_detached_structure": true/false/null - sheds, workshops, or secondary structures excluding the main garage,
  "detached_structure_confidence": 0.0 to 1.0,

  "has_ac_unit": true/false/null,
  "ac_unit_confidence": 0.0 to 1.0,

  "data_quality_note": "short note about image quality, uncertainty, and inference limits",
  "sources_used": ["street_view", "satellite", "sam_segmentation", "regional_convention"],
  "enhanced_intelligence": {
    "property_subtype": {"value": "string|null", "confidence": 0.0, "evidence_kind": "observed|inferred|assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "bedrooms_estimated_main_above_grade": {"value": "number|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "bedrooms_possible_total_with_basement": {"value": "number|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "bathrooms_estimated": {"value": "number|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "construction_year_estimated": {"value": "number|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "heating_system_exists": {"value": "boolean|null", "confidence": 0.0, "evidence_kind": "assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "heating_system_type": {"value": ["string"], "confidence": 0.0, "evidence_kind": "assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "cooling_system_exists": {"value": "boolean|null", "confidence": 0.0, "evidence_kind": "observed|inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "water_heater_ownership": {"value": "Owned|Rental|Unknown", "confidence": 0.0, "evidence_kind": "assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "fireplace_exists": {"value": "boolean|null", "confidence": 0.0, "evidence_kind": "observed|inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "hot_tub_exists": {"value": "boolean|null", "confidence": 0.0, "evidence_kind": "observed|unknown", "basis": "string", "sources_used": ["string"]},
    "sump_pump_exists": {"value": "boolean|null", "confidence": 0.0, "evidence_kind": "assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "roof_tree_canopy_above_roof": {"value": "boolean|null", "confidence": 0.0, "evidence_kind": "observed|unknown", "basis": "string", "sources_used": ["string"]},
    "garage_type": {"value": "string|null", "confidence": 0.0, "evidence_kind": "observed|inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "garage_spaces_estimated": {"value": "number|null", "confidence": 0.0, "evidence_kind": "observed|inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "driveway_parking_spaces_estimated": {"value": "number|null", "confidence": 0.0, "evidence_kind": "observed|inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "total_parking_spaces_estimated": {"value": "number|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "basement_exists": {"value": "boolean|null", "confidence": 0.0, "evidence_kind": "inferred|assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "basement_type": {"value": "string|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "foundation_type": {"value": "string|null", "confidence": 0.0, "evidence_kind": "inferred|assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "water_supply": {"value": "string|null", "confidence": 0.0, "evidence_kind": "assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "sewer": {"value": "string|null", "confidence": 0.0, "evidence_kind": "assumed|unknown", "basis": "string", "sources_used": ["string"]},
    "lot_frontage_ft_estimated": {"value": "number|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "lot_depth_ft_estimated": {"value": "number|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "estimated_finished_area_sqft_range": {"value": "string|null", "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "community_features": {"value": ["string"], "confidence": 0.0, "evidence_kind": "observed|inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "likely_interior_features": {"value": ["string"], "confidence": 0.0, "evidence_kind": "inferred|unknown", "basis": "string", "sources_used": ["string"]},
    "additional_features": {"value": {}, "confidence": 0.0, "evidence_kind": "observed|inferred|unknown", "basis": "string", "sources_used": ["string"]}
  }
}

Analyze both the street view image (for building details, exterior, garage, condition) and
the satellite image (for lot shape, pool, trees, fencing, yard). If the satellite image
has a map marker, focus the satellite analysis on the property directly under that marker.
Return ONLY valid JSON with no additional text or markdown formatting."""


def _extract_json(text: str) -> dict:
    """Extract JSON from text that may contain markdown fences or other wrapping."""
    cleaned = text.strip()

    # Remove markdown code fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Try direct parse
    if cleaned:
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Try finding JSON object in the text
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return json.loads(brace_match.group(0))

    raise json.JSONDecodeError("No JSON found in response", text, 0)


def _completion_options() -> dict:
    model = settings.OPENAI_SEGMENTED_REASONING_MODEL or settings.OPENAI_VISION_MODEL
    options = {
        "model": model,
        "messages": [],
        "metadata": {"feature": "property-analysis", "configured_model": model},
    }
    if model.startswith("gpt-5"):
        options["max_completion_tokens"] = 1500
        options["reasoning_effort"] = "none"
    else:
        options["max_tokens"] = 1500
        options["temperature"] = 0.2
    return options


@observe(name="property-vision", capture_input=False, capture_output=False)
async def analyze_property(
    street_view_url: str | None = None,
    satellite_url: str | None = None,
) -> ServiceResult:
    """Analyze property images using OpenAI Vision API."""
    langfuse.update_current_span(
        input={
            "has_street_view": street_view_url is not None,
            "has_satellite": satellite_url is not None,
        },
        metadata={"service": "openai_vision"},
    )
    raw_text = ""
    try:
        if not street_view_url and not satellite_url:
            return ServiceResult(
                data=None,
                error="At least one image URL is required",
                source="openai_vision",
            )

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        content: list[dict] = [{"type": "text", "text": ANALYSIS_PROMPT}]

        if street_view_url:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": street_view_url, "detail": "high"},
                }
            )

        if satellite_url:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": satellite_url, "detail": "high"},
                }
            )

        response = await client.chat.completions.create(
            name="property-vision-analysis",
            **{
                **_completion_options(),
                "messages": [{"role": "user", "content": content}],
            },
        )

        raw_text = response.choices[0].message.content or ""
        logger.info("Vision API raw response: %s", raw_text[:500])

        analysis = _extract_json(raw_text)

        langfuse.update_current_span(
            output={
                "property_type": analysis.get("property_type"),
                "home_style": analysis.get("home_style"),
                "condition_estimate": analysis.get("condition_estimate"),
            }
        )

        return ServiceResult(data=analysis, error=None, source="openai_vision")

    except json.JSONDecodeError as exc:
        logger.exception("Failed to parse Vision API response as JSON")
        return ServiceResult(
            data={"raw_text": raw_text},
            error=f"JSON parse error: {exc}",
            source="openai_vision",
        )
    except Exception as exc:
        logger.exception("Error during property analysis")
        return ServiceResult(data=None, error=str(exc), source="openai_vision")
