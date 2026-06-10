import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from langfuse import observe

from app.config import settings
from app.models.schemas import (
    AnalyzeRequest,
    PropertyRequest,
    SegmentRequest,
)
from app.observability import langfuse
from app.services import google_maps, pois, property_store, segmentation, vision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/property", tags=["property"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _analysis_response(vd: dict[str, Any], property_id: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "property_id": property_id,
        "model_used": settings.OPENAI_VISION_MODEL,
        "property_type": vd.get("property_type"),
        "property_type_confidence": vd.get("property_type_confidence"),
        "home_style": vd.get("home_style"),
        "home_style_confidence": vd.get("home_style_confidence"),
        "stories": vd.get("stories"),
        "stories_confidence": vd.get("stories_confidence"),
        "exterior_material": vd.get("exterior_material"),
        "exterior_material_confidence": vd.get("exterior_material_confidence"),
        "has_pool": vd.get("has_pool"),
        "pool_confidence": vd.get("pool_confidence"),
        "tree_count_estimate": vd.get("tree_count_estimate"),
        "tree_count_confidence": vd.get("tree_count_confidence"),
        "has_garage": vd.get("has_garage"),
        "garage_confidence": vd.get("garage_confidence"),
        "parking_type": vd.get("parking_type"),
        "parking_type_confidence": vd.get("parking_type_confidence"),
        "parking_spaces_estimate": vd.get("parking_spaces_estimate"),
        "parking_spaces_confidence": vd.get("parking_spaces_confidence"),
        "condition_estimate": vd.get("condition_estimate"),
        "condition_confidence": vd.get("condition_confidence"),
        "approximate_age": vd.get("approximate_age"),
        "approximate_age_confidence": vd.get("approximate_age_confidence"),
        "lot_shape": vd.get("lot_shape"),
        "lot_shape_confidence": vd.get("lot_shape_confidence"),
        "has_fenced_yard": vd.get("has_fenced_yard"),
        "fence_confidence": vd.get("fence_confidence"),
        "has_solar_panels": vd.get("has_solar_panels"),
        "solar_panels_confidence": vd.get("solar_panels_confidence"),
        "roof_type": vd.get("roof_type"),
        "roof_type_confidence": vd.get("roof_type_confidence"),
        "has_sidewalk": vd.get("has_sidewalk"),
        "sidewalk_confidence": vd.get("sidewalk_confidence"),
        "driveway_material": vd.get("driveway_material"),
        "driveway_material_confidence": vd.get("driveway_material_confidence"),
        "has_chimney": vd.get("has_chimney"),
        "chimney_confidence": vd.get("chimney_confidence"),
        "has_deck_or_patio": vd.get("has_deck_or_patio"),
        "deck_patio_confidence": vd.get("deck_patio_confidence"),
        "has_gutters": vd.get("has_gutters"),
        "gutters_confidence": vd.get("gutters_confidence"),
        "has_detached_structure": vd.get("has_detached_structure"),
        "detached_structure_confidence": vd.get("detached_structure_confidence"),
        "has_ac_unit": vd.get("has_ac_unit"),
        "ac_unit_confidence": vd.get("ac_unit_confidence"),
        "raw_response": vd,
        "analyzed_at": _now(),
    }


@router.post("")
@observe(name="property-create", capture_input=False, capture_output=False)
async def create_property(req: PropertyRequest):
    """Full property analysis pipeline."""
    langfuse.update_current_span(
        input={"lat": req.lat, "lon": req.lon},
        metadata={"feature": "property-analysis", "endpoint": "create_property"},
    )
    errors: list[str] = []

    # 1. Reverse geocode
    geocode_result = await google_maps.reverse_geocode(req.lat, req.lon)
    address = "Unknown"
    neighborhood = None
    cross_streets = None
    if geocode_result.error:
        errors.append(f"Geocoding: {geocode_result.error}")
        address = f"Unknown ({req.lat},{req.lon})"
    elif geocode_result.data:
        address = geocode_result.data["address"]
        neighborhood = geocode_result.data.get("neighborhood")
        cross_streets = geocode_result.data.get("cross_streets")
    city = geocode_result.data.get("city") if geocode_result.data else None

    cached = await property_store.get_cached_profile(address)
    if cached.error:
        errors.append(f"Cache lookup: {cached.error}")
    elif cached.data:
        langfuse.update_current_span(output={"cache_status": "hit"})
        return cached.data

    search_result = await property_store.create_search(
        req.lat, req.lon, address, "miss", errors=errors
    )
    if search_result.error:
        errors.append(f"Create search: {search_result.error}")
        search_id = None
    else:
        search_id = search_result.data["id"]

    property_id = str(uuid.uuid4())
    property_data = {
        "id": property_id,
        "address": address,
        "lat": req.lat,
        "lon": req.lon,
        "neighborhood": neighborhood,
        "cross_streets": cross_streets,
        "created_at": _now(),
        "updated_at": _now(),
    }

    # 3. Fetch images
    sv_result = await google_maps.fetch_street_view(req.lat, req.lon, address=address)
    sat_result = await google_maps.fetch_satellite(req.lat, req.lon)

    street_view_url = None
    satellite_url = None
    images = []

    if sv_result.error:
        errors.append(f"Street View: {sv_result.error}")
    elif sv_result.data:
        street_view_url = sv_result.data["url"]
        images.append({
            "id": str(uuid.uuid4()),
            "property_id": property_id,
            "image_type": "street_view",
            "url": street_view_url,
            "fetched_at": _now(),
        })

    if sat_result.error:
        errors.append(f"Satellite: {sat_result.error}")
    elif sat_result.data:
        satellite_url = sat_result.data["url"]
        images.append({
            "id": str(uuid.uuid4()),
            "property_id": property_id,
            "image_type": "satellite",
            "url": satellite_url,
            "fetched_at": _now(),
        })

    # 4. AI analysis
    analysis_data = None
    if street_view_url or satellite_url:
        vision_result = await vision.analyze_property(
            street_view_url, satellite_url
        )
        if vision_result.error:
            errors.append(f"Vision analysis: {vision_result.error}")
        if vision_result.data:
            analysis_data = _analysis_response(vision_result.data, property_id)

    # 5. SAM 3.1 segmentation, if configured
    segmentation_data = None
    if satellite_url:
        seg_result = await segmentation.segment_image(
            satellite_url,
            image_type="satellite",
        )
        if seg_result.error:
            errors.append(f"Segmentation: {seg_result.error}")
        else:
            segmentation_data = seg_result.data

    # 6. POIs
    pois_result = await pois.get_pois(req.lat, req.lon)
    pois_list = []
    if pois_result.error:
        errors.append(f"POIs: {pois_result.error}")
    elif pois_result.data:
        pois_list = pois_result.data

    # Build geospatial response
    geospatial_data = {
        "id": str(uuid.uuid4()),
        "property_id": property_id,
        "pois": pois_list,
        "fetched_at": _now(),
    }

    response = {
        "property": property_data,
        "images": images,
        "analysis": analysis_data,
        "segmentation": segmentation_data,
        "geospatial": geospatial_data,
        "errors": errors,
        "cache": {"status": "miss"},
    }

    save_result = await property_store.save_profile(
        address=address,
        lat=req.lat,
        lon=req.lon,
        neighborhood=neighborhood,
        cross_streets=cross_streets,
        city=city,
        search_id=search_id,
        images=[{"image_type": i["image_type"], "url": i["url"]} for i in images],
        analysis=analysis_data["raw_response"] if analysis_data else None,
        segmentation=segmentation_data,
        pois=pois_list,
        errors=errors,
    )
    if save_result.error:
        response["errors"].append(f"Save profile: {save_result.error}")
    elif save_result.data:
        response = save_result.data

    langfuse.update_current_span(
        output={
            "property_id": property_id,
            "has_analysis": analysis_data is not None,
            "has_segmentation": segmentation_data is not None,
            "poi_count": len(pois_list),
            "error_count": len(errors),
            "cache_status": response.get("cache", {}).get("status"),
        }
    )

    return response


@router.get("/images")
async def get_images(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """Fetch Street View and Satellite image URLs for given coordinates."""
    sv_result = await google_maps.fetch_street_view(lat, lon)
    sat_result = await google_maps.fetch_satellite(lat, lon)

    return {
        "street_view": sv_result.model_dump(),
        "satellite": sat_result.model_dump(),
    }


@router.post("/analyze")
@observe(name="property-analyze", capture_input=False, capture_output=False)
async def analyze(req: AnalyzeRequest):
    """Run AI Vision analysis and SAM segmentation on provided image URLs."""
    langfuse.update_current_span(
        input={
            "has_street_view": bool(req.street_view_url),
            "has_satellite": bool(req.satellite_url),
        },
        metadata={"feature": "property-analysis", "endpoint": "analyze"},
    )
    vision_result = await vision.analyze_property(
        req.street_view_url, req.satellite_url
    )
    seg_result = await segmentation.segment_image(req.satellite_url)

    response = {
        "analysis": vision_result.model_dump(),
        "segmentation": seg_result.model_dump(),
    }

    langfuse.update_current_span(
        output={
            "vision_error": vision_result.error,
            "segmentation_error": seg_result.error,
        }
    )

    return response


@router.post("/segment")
@observe(name="property-segment", capture_input=False, capture_output=False)
async def segment(req: SegmentRequest):
    """Run SAM segmentation only, without any OpenAI/GPT calls."""
    langfuse.update_current_span(
        input={
            "image_type": req.image_type,
            "target_count": len(req.targets or []),
        },
        metadata={"feature": "sam-segmentation", "endpoint": "segment"},
    )
    result = await segmentation.segment_image(
        req.image_url,
        image_type=req.image_type,
        targets=[target.model_dump() for target in req.targets] if req.targets else None,
    )
    langfuse.update_current_span(
        output={
            "source": result.source,
            "error": result.error,
            "status": result.data.get("status") if isinstance(result.data, dict) else None,
        }
    )
    return result.model_dump()


@router.get("/pois")
async def get_pois_route(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(1000, description="Search radius in meters"),
):
    """Return POIs near the given coordinates."""
    result = await pois.get_pois(lat, lon, radius_meters=radius)
    if result.error and not result.data:
        raise HTTPException(status_code=502, detail=result.error)
    return result.model_dump()
