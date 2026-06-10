import logging
from typing import Any

import httpx

from app.config import settings
from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)


SATELLITE_TARGETS = [
    {
        "type": "aerial_home_boundary",
        "prompt": "the residential home directly under the map marker, including the full visible building footprint",
    },
    {
        "type": "aerial_pool",
        "prompt": "the swimming pool on the same residential property as the map marker",
    },
    {
        "type": "aerial_driveway",
        "prompt": "the driveway belonging to the residential home directly under the map marker",
    },
    {
        "type": "aerial_roof",
        "prompt": "the roof of the residential home directly under the map marker",
    },
]

STREET_VIEW_TARGETS = [
    {
        "type": "street_garage",
        "prompt": "the garage door or garage structure of the home in focus only",
    }
]


async def segment_image(
    image_url: str,
    image_type: str = "satellite",
    targets: list[dict[str, str]] | None = None,
) -> ServiceResult:
    """Segment a property image using the local SAM 3.1 service if configured."""
    if not settings.SAM_SERVICE_URL:
        return ServiceResult(
            data={
                "status": "sam_unavailable",
                "message": "SAM service URL is not configured",
                "model": settings.SAM_MODEL_ID,
            },
            error=None,
            source="sam3",
        )

    selected_targets = targets or _default_targets(image_type)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.SAM_SERVICE_URL.rstrip('/')}/segment",
                json={
                    "image_url": image_url,
                    "image_type": image_type,
                    "targets": selected_targets,
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        return ServiceResult(
            data=data,
            error=None,
            source="sam3",
        )
    except Exception as exc:
        logger.warning("SAM service unavailable: %s", exc)
        return ServiceResult(
            data={
                "status": "sam_unavailable",
                "message": str(exc),
                "model": settings.SAM_MODEL_ID,
                "image_url": image_url,
                "targets": selected_targets,
            },
            error=None,
            source="sam3",
        )


def _default_targets(image_type: str) -> list[dict[str, str]]:
    if image_type == "street_view":
        return STREET_VIEW_TARGETS
    return SATELLITE_TARGETS
