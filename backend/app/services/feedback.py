import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.models.schemas import FeedbackRequest, ServiceResult

logger = logging.getLogger(__name__)


async def save_feedback(req: FeedbackRequest) -> ServiceResult:
    """Save a user correction to the ai_feedback table."""
    try:
        from app.services.supabase import _get_client
        client = _get_client()
        record = {
            "id": str(uuid4()),
            "analysis_id": req.analysis_id,
            "property_id": req.property_id,
            "field_name": req.field_name,
            "ai_value": req.ai_value,
            "ai_confidence": req.ai_confidence,
            "corrected_value": req.corrected_value,
            "notes": req.notes,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        result = client.table("ai_feedback").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving feedback to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")
