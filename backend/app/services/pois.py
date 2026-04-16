import logging

import httpx

from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


async def get_pois(
    lat: float, lon: float, radius_meters: int = 1000
) -> ServiceResult:
    """Fetch points of interest near coordinates using Overpass API (OpenStreetMap).

    Queries for amenities, shops, schools, restaurants, parks, and transit stops.
    No API key required.
    """
    try:
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"](around:{radius_meters},{lat},{lon});
          node["shop"](around:{radius_meters},{lat},{lon});
          node["leisure"="park"](around:{radius_meters},{lat},{lon});
          node["public_transport"="stop_position"](around:{radius_meters},{lat},{lon});
          node["highway"="bus_stop"](around:{radius_meters},{lat},{lon});
          node["railway"="station"](around:{radius_meters},{lat},{lon});
          node["railway"="halt"](around:{radius_meters},{lat},{lon});
        );
        out body;
        """

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                OVERPASS_URL,
                data={"data": query},
            )

        if resp.status_code != 200:
            return ServiceResult(
                data=None,
                error=f"Overpass API returned status {resp.status_code}",
                source="overpass",
            )

        raw = resp.json()
        elements = raw.get("elements", [])

        pois = []
        for el in elements:
            tags = el.get("tags", {})
            poi = {
                "id": el.get("id"),
                "lat": el.get("lat"),
                "lon": el.get("lon"),
                "name": tags.get("name", ""),
                "category": _categorize(tags),
                "tags": tags,
            }
            pois.append(poi)

        return ServiceResult(data=pois, error=None, source="overpass")

    except Exception as exc:
        logger.exception("Error fetching POIs from Overpass API")
        return ServiceResult(data=None, error=str(exc), source="overpass")


def _categorize(tags: dict) -> str:
    """Determine a human-readable category from OSM tags."""
    if "amenity" in tags:
        amenity = tags["amenity"]
        if amenity in ("school", "kindergarten", "university", "college"):
            return "education"
        if amenity in ("restaurant", "cafe", "fast_food", "bar", "pub"):
            return "food_drink"
        if amenity in ("hospital", "clinic", "doctors", "dentist", "pharmacy"):
            return "health"
        if amenity in ("bank", "atm"):
            return "finance"
        if amenity in ("library", "community_centre", "place_of_worship"):
            return "community"
        return f"amenity:{amenity}"
    if "shop" in tags:
        return f"shop:{tags['shop']}"
    if "leisure" in tags:
        return f"leisure:{tags['leisure']}"
    if tags.get("public_transport") or tags.get("highway") == "bus_stop":
        return "transit"
    if "railway" in tags:
        return "transit"
    return "other"
