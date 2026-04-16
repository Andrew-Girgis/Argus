import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.config import settings
from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)


def _get_client():
    """Create and return a Supabase client."""
    from supabase import create_client

    url = settings.SUPABASE_URL
    # Accept bare project ref or full URL
    if url and not url.startswith("http"):
        url = f"https://{url}.supabase.co"

    return create_client(url, settings.SUPABASE_SECRET_KEY)


async def save_property(
    address: str, lat: float, lon: float
) -> ServiceResult:
    """Insert a new property record into Supabase."""
    try:
        client = _get_client()
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": str(uuid4()),
            "address": address,
            "lat": lat,
            "lon": lon,
            "created_at": now,
            "updated_at": now,
        }
        result = client.table("properties").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving property to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")


async def get_property(property_id: str) -> ServiceResult:
    """Fetch a property by ID from Supabase."""
    try:
        client = _get_client()
        result = (
            client.table("properties")
            .select("*")
            .eq("id", property_id)
            .execute()
        )
        if not result.data:
            return ServiceResult(
                data=None, error="Property not found", source="supabase"
            )
        return ServiceResult(data=result.data[0], error=None, source="supabase")
    except Exception as exc:
        logger.exception("Error fetching property from Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")


async def save_images(
    property_id: str, images: list[dict[str, Any]]
) -> ServiceResult:
    """Save property image records to Supabase."""
    try:
        client = _get_client()
        now = datetime.now(timezone.utc).isoformat()
        records = []
        for img in images:
            records.append(
                {
                    "id": str(uuid4()),
                    "property_id": property_id,
                    "image_type": img["image_type"],
                    "url": img["url"],
                    "fetched_at": now,
                }
            )
        result = client.table("property_images").insert(records).execute()
        return ServiceResult(
            data=result.data if result.data else records,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving images to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")


async def save_analysis(
    property_id: str, analysis: dict[str, Any]
) -> ServiceResult:
    """Save AI analysis results to Supabase."""
    try:
        client = _get_client()
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": str(uuid4()),
            "property_id": property_id,
            "model_used": "gpt-4o",
            "home_style": analysis.get("home_style"),
            "has_pool": analysis.get("has_pool"),
            "pool_confidence": analysis.get("pool_confidence"),
            "tree_count_estimate": analysis.get("tree_count_estimate"),
            "has_garage": analysis.get("has_garage"),
            "condition_estimate": analysis.get("condition_estimate"),
            "approximate_age": analysis.get("approximate_age"),
            "raw_response": analysis,
            "analyzed_at": now,
        }
        result = client.table("ai_analysis").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving analysis to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")


async def save_geospatial(
    property_id: str, geo_data: dict[str, Any]
) -> ServiceResult:
    """Save geospatial data (isochrones, POIs) to Supabase."""
    try:
        client = _get_client()
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": str(uuid4()),
            "property_id": property_id,
            "isochrone_geojson": geo_data.get("isochrone_geojson", {}),
            "pois": geo_data.get("pois", []),
            "fetched_at": now,
        }
        result = client.table("geospatial_data").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving geospatial data to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")
