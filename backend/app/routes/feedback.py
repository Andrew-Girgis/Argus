import logging

from fastapi import APIRouter

from app.models.schemas import FeedbackRequest
from app.services import feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("")
async def submit_feedback(req: FeedbackRequest):
    """Save a user correction for an AI-generated field."""
    result = await feedback.save_feedback(req)
    if result.error:
        logger.warning("Feedback save failed: %s", result.error)
    return {"ok": result.error is None, "error": result.error}
