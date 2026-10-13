import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.models.schemas import (
    AnalyzeRequest,
    PropertyRequest,
    ServiceResult,
)
from app.observability import trace_analysis, traced_call
from app.services import google_maps, pois, segmentation, supabase, vision
from app.utils import redact_secrets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/property", tags=["property"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _available(data) -> dict:
    # Image results hold keyed URLs; record only that an image was found.
    return {"available": True}


@router.post("")
async def create_property(req: PropertyRequest):
    """Full property analysis pipeline, traced as one Langfuse trace."""
    analysis_id = str(uuid.uuid4())
    with trace_analysis(
        analysis_id,
        input={"lat": req.lat, "lon": req.lon},
        metadata={
            "vision_model": settings.VISION_MODEL,
            "prompt_version": vision.PROMPT_VERSION,
            "workflow_version": settings.APP_VERSION,
        },
    ) as root:
        response = await _run_pipeline(req, analysis_id)
        root.update(
            output={
                "property_id": response["property"]["id"],
                "analysis_id": analysis_id if response["analysis"] else None,
                "errors": [redact_secrets(e) for e in response["errors"]],
            },
            metadata={"property_id": response["property"]["id"]},
        )
    return response


async def _run_pipeline(req: PropertyRequest, analysis_id: str) -> dict:
    errors: list[str] = []

    # 1. Reverse geocode
    geocode_result = await traced_call(
        "reverse-geocode",
        google_maps.reverse_geocode(req.lat, req.lon),
        input={"lat": req.lat, "lon": req.lon},
        summarize=lambda d: {"address": d.get("address")},
    )
    address = "Unknown"
    neighborhood = None
    cross_streets = None
    if geocode_result.error:
        errors.append(f"Geocoding: {geocode_result.error}")
    elif geocode_result.data:
        address = geocode_result.data["address"]
        neighborhood = geocode_result.data.get("neighborhood")
        cross_streets = geocode_result.data.get("cross_streets")

    # 2. Build property object (try Supabase, fall back to local)
    prop_result = await traced_call(
        "save-property", supabase.save_property(address, req.lat, req.lon)
    )
    if prop_result.error:
        errors.append(f"Save property: {prop_result.error}")
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
    else:
        property_data = prop_result.data
        property_id = property_data["id"]
        property_data["neighborhood"] = neighborhood
        property_data["cross_streets"] = cross_streets

    # 3. Fetch images
    sv_result = await traced_call(
        "fetch-street-view",
        google_maps.fetch_street_view(req.lat, req.lon, address=address),
        summarize=_available,
    )
    sat_result = await traced_call(
        "fetch-satellite",
        google_maps.fetch_satellite(req.lat, req.lon),
        summarize=_available,
    )

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

    # Try saving images to Supabase
    if property_id and images:
        img_result = await traced_call(
            "save-images",
            supabase.save_images(
                property_id,
                [{"image_type": i["image_type"], "url": i["url"]} for i in images],
            ),
        )
        if img_result.error:
            errors.append(f"Save images: {img_result.error}")
        elif img_result.data:
            images = img_result.data

    # 4. AI analysis
    analysis_data = None
    if street_view_url or satellite_url:
        vision_result = await traced_call(
            "vision-analysis",
            vision.analyze_property(street_view_url, satellite_url),
            summarize=lambda d: {"model": d.model, "image_sha256": d.image_sha256},
        )
        if vision_result.error:
            errors.append(f"Vision analysis: {vision_result.error}")
        elif vision_result.data:
            analysis_data = vision_result.data.analysis.to_record(
                analysis_id=analysis_id,
                property_id=property_id,
                model_used=vision_result.data.model,
                analyzed_at=_now(),
            )
            save_result = await traced_call(
                "save-analysis", supabase.save_analysis(analysis_data)
            )
            if save_result.error:
                errors.append(f"Save analysis: {save_result.error}")

    # 5. SAM2 segmentation
    segmentation_data = None
    if satellite_url:
        seg_result = await traced_call(
            "segmentation", segmentation.segment_image(satellite_url)
        )
        if seg_result.error:
            errors.append(f"Segmentation: {seg_result.error}")
        else:
            segmentation_data = seg_result.data

    # 6. POIs
    pois_result = await traced_call(
        "fetch-pois",
        pois.get_pois(req.lat, req.lon),
        summarize=lambda d: {"count": len(d)},
    )
    pois_list = []
    if pois_result.error:
        errors.append(f"POIs: {pois_result.error}")
    elif pois_result.data:
        pois_list = pois_result.data

    # Save geospatial data to Supabase
    if property_id:
        geo_save_result = await traced_call(
            "save-geospatial",
            supabase.save_geospatial(property_id, {"pois": pois_list}),
        )
        if geo_save_result.error:
            errors.append(f"Save geospatial: {geo_save_result.error}")

    # Build geospatial response
    geospatial_data = {
        "id": str(uuid.uuid4()),
        "property_id": property_id,
        "pois": pois_list,
        "fetched_at": _now(),
    }

    return {
        "property": property_data,
        "images": images,
        "analysis": analysis_data,
        "segmentation": segmentation_data,
        "geospatial": geospatial_data,
        "errors": errors,
    }


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
async def analyze(req: AnalyzeRequest):
    """Run AI Vision analysis and SAM2 segmentation on provided image URLs."""
    vision_result = await vision.analyze_property(
        req.street_view_url, req.satellite_url
    )
    seg_result = await segmentation.segment_image(req.satellite_url)

    return {
        "analysis": vision_result.model_dump(),
        "segmentation": seg_result.model_dump(),
    }


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
