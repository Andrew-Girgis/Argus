import logging
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)

STREET_VIEW_BASE = "https://maps.googleapis.com/maps/api/streetview"
STATIC_MAP_BASE = "https://maps.googleapis.com/maps/api/staticmap"
GEOCODE_BASE = "https://maps.googleapis.com/maps/api/geocode/json"


async def fetch_street_view(
    lat: float, lon: float, address: str | None = None
) -> ServiceResult:
    """Fetch a Google Street View image URL for the given address or coordinates."""
    try:
        location = address if address else f"{lat},{lon}"
        params = {
            "size": "640x480",
            "location": location,
            "key": settings.GOOGLE_MAPS_API_KEY,
            "return_error_code": "true",
        }
        url = f"{STREET_VIEW_BASE}?{urlencode(params)}"

        # Verify the image exists via metadata endpoint
        meta_params = {
            "location": location,
            "key": settings.GOOGLE_MAPS_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            meta_resp = await client.get(
                f"{STREET_VIEW_BASE}/metadata", params=meta_params
            )
            meta_data = meta_resp.json()

        if meta_data.get("status") != "OK":
            return ServiceResult(
                data=None,
                error=f"Street View not available: {meta_data.get('status')}",
                source="google_street_view",
            )

        return ServiceResult(data={"url": url}, error=None, source="google_street_view")

    except Exception as exc:
        logger.exception("Error fetching Street View image")
        return ServiceResult(
            data=None, error=str(exc), source="google_street_view"
        )


async def fetch_satellite(lat: float, lon: float) -> ServiceResult:
    """Fetch a Google Static Maps satellite image URL for the given coordinates."""
    try:
        params = {
            "center": f"{lat},{lon}",
            "zoom": "19",
            "size": "640x640",
            "maptype": "satellite",
            "key": settings.GOOGLE_MAPS_API_KEY,
        }
        url = f"{STATIC_MAP_BASE}?{urlencode(params)}"

        return ServiceResult(
            data={"url": url}, error=None, source="google_satellite"
        )

    except Exception as exc:
        logger.exception("Error fetching satellite image")
        return ServiceResult(data=None, error=str(exc), source="google_satellite")


def _extract_component(result: dict, component_type: str) -> str | None:
    """Extract a specific address component from a geocode result."""
    for component in result.get("address_components", []):
        if component_type in component.get("types", []):
            return component.get("long_name")
    return None


def _extract_neighborhood(results: list[dict]) -> str | None:
    """Extract neighborhood from geocode results, trying multiple strategies."""
    # First try the primary result's components
    for result in results:
        neighborhood = _extract_component(result, "neighborhood")
        if neighborhood:
            return neighborhood
        # Fall back to sublocality
        sublocality = _extract_component(result, "sublocality_level_1")
        if sublocality:
            return sublocality
        sublocality = _extract_component(result, "sublocality")
        if sublocality:
            return sublocality

    # Try looking for a result with type "neighborhood"
    for result in results:
        if "neighborhood" in result.get("types", []):
            return result.get("formatted_address", "").split(",")[0]

    return None


def _extract_cross_streets(results: list[dict]) -> str | None:
    """Try to extract cross street info from geocode results."""
    for result in results:
        if "intersection" in result.get("types", []):
            return result.get("formatted_address", "").split(",")[0]
        # Look for route components
        route = _extract_component(result, "route")
        if route:
            return route
    return None


async def reverse_geocode(lat: float, lon: float) -> ServiceResult:
    """Reverse geocode coordinates to an address with neighborhood and cross street info."""
    try:
        params = {
            "latlng": f"{lat},{lon}",
            "key": settings.GOOGLE_MAPS_API_KEY,
            "result_type": "street_address|neighborhood|intersection",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(GEOCODE_BASE, params=params)
            data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            # Retry without result_type filter
            params.pop("result_type", None)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(GEOCODE_BASE, params=params)
                data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            return ServiceResult(
                data=None,
                error=f"Geocoding failed: {data.get('status')}",
                source="google_geocode",
            )

        results = data["results"]
        primary = results[0]

        address = primary.get("formatted_address", "Unknown")
        neighborhood = _extract_neighborhood(results)
        cross_streets = _extract_cross_streets(results)

        # Also extract city/municipality
        city = _extract_component(primary, "locality")

        return ServiceResult(
            data={
                "address": address,
                "neighborhood": neighborhood,
                "cross_streets": cross_streets,
                "city": city,
            },
            error=None,
            source="google_geocode",
        )

    except Exception as exc:
        logger.exception("Error during reverse geocoding")
        return ServiceResult(data=None, error=str(exc), source="google_geocode")
