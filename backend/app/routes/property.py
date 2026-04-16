import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    AnalyzeRequest,
    PropertyRequest,
    ServiceResult,
)
from app.services import google_maps, pois, segmentation, supabase, vision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/property", tags=["property"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("")
async def create_property(req: PropertyRequest):
    """Full property analysis pipeline."""
    errors: list[str] = []

    # 1. Reverse geocode
    geocode_result = await google_maps.reverse_geocode(req.lat, req.lon)
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
    prop_result = await supabase.save_property(address, req.lat, req.lon)
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

    # Try saving images to Supabase
    if property_id and images:
        img_result = await supabase.save_images(
            property_id,
            [{"image_type": i["image_type"], "url": i["url"]} for i in images],
        )
        if img_result.error:
            errors.append(f"Save images: {img_result.error}")
        elif img_result.data:
            images = img_result.data

    # 4. AI analysis
    analysis_data = None
    if street_view_url or satellite_url:
        vision_result = await vision.analyze_property(street_view_url, satellite_url)
        if vision_result.error:
            errors.append(f"Vision analysis: {vision_result.error}")
        if vision_result.data:
            vd = vision_result.data
            analysis_data = {
                "id": str(uuid.uuid4()),
                "property_id": property_id,
                "model_used": "gpt-4o",
                "property_type": vd.get("property_type"),
                "property_type_confidence": vd.get("property_type_confidence"),
                "home_style": vd.get("home_style"),
                "home_style_confidence": vd.get("home_style_confidence"),
                "stories": vd.get("stories"),
                "stories_confidence": vd.get("stories_confidence"),
                "exterior_material": vd.get("exterior_material"),
                "exterior_material_confidence": vd.get("exterior_material_confidence"),
                "has_pool": vd.get("has_pool", False),
                "pool_confidence": vd.get("pool_confidence"),
                "tree_count_estimate": vd.get("tree_count_estimate"),
                "tree_count_confidence": vd.get("tree_count_confidence"),
                "has_garage": vd.get("has_garage", False),
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
                "has_fenced_yard": vd.get("has_fenced_yard", False),
                "fence_confidence": vd.get("fence_confidence"),
                "has_solar_panels": vd.get("has_solar_panels", False),
                "solar_panels_confidence": vd.get("solar_panels_confidence"),
                "roof_type": vd.get("roof_type"),
                "roof_type_confidence": vd.get("roof_type_confidence"),
                "has_sidewalk": vd.get("has_sidewalk", False),
                "sidewalk_confidence": vd.get("sidewalk_confidence"),
                "driveway_material": vd.get("driveway_material"),
                "driveway_material_confidence": vd.get("driveway_material_confidence"),
                "has_chimney": vd.get("has_chimney", False),
                "chimney_confidence": vd.get("chimney_confidence"),
                "has_deck_or_patio": vd.get("has_deck_or_patio", False),
                "deck_patio_confidence": vd.get("deck_patio_confidence"),
                "has_gutters": vd.get("has_gutters", False),
                "gutters_confidence": vd.get("gutters_confidence"),
                "has_detached_structure": vd.get("has_detached_structure", False),
                "detached_structure_confidence": vd.get("detached_structure_confidence"),
                "has_ac_unit": vd.get("has_ac_unit", False),
                "ac_unit_confidence": vd.get("ac_unit_confidence"),
                "raw_response": vd,
                "analyzed_at": _now(),
            }
            if property_id:
                save_result = await supabase.save_analysis(property_id, vd)
                if save_result.error:
                    errors.append(f"Save analysis: {save_result.error}")

    # 5. SAM2 segmentation
    segmentation_data = None
    if satellite_url:
        seg_result = await segmentation.segment_image(satellite_url)
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

    # Save geospatial data to Supabase
    if property_id:
        geo_save_result = await supabase.save_geospatial(
            property_id,
            {"pois": pois_list},
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
