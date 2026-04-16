import logging

from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)


async def segment_image(image_url: str) -> ServiceResult:
    """Segment a property image using SAM2.

    If SAM2 is not installed, returns a stub result indicating unavailability.
    """
    try:
        import sam2  # noqa: F401

        # SAM2 is available — run segmentation
        # Placeholder for actual SAM2 pipeline integration
        logger.info("SAM2 module found, but full pipeline is not yet implemented")
        return ServiceResult(
            data={
                "status": "sam2_available",
                "message": "SAM2 pipeline not yet integrated",
                "image_url": image_url,
            },
            error=None,
            source="sam2",
        )

    except ImportError:
        logger.info("SAM2 module not installed — returning stub result")
        return ServiceResult(
            data={
                "status": "sam2_not_available",
                "message": "SAM2 module not installed",
            },
            error=None,
            source="sam2",
        )

    except Exception as exc:
        logger.exception("Error during SAM2 segmentation")
        return ServiceResult(data=None, error=str(exc), source="sam2")
