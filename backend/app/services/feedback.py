import logging
from datetime import datetime, timezone
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.models.schemas import FeedbackRequest, ServiceResult

logger = logging.getLogger(__name__)


async def save_feedback(req: FeedbackRequest) -> ServiceResult:
    """Save a user correction to the ai_feedback table."""
    try:
        from app.config import settings
        from app.services.supabase import _ensure_postgres_schema, _get_client, _get_conn

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
        if settings.DATABASE_URL:
            _ensure_postgres_schema()
            postgres_record = {
                **record,
                "ai_value": Jsonb(record["ai_value"]),
                "corrected_value": Jsonb(record["corrected_value"]),
            }
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ai_feedback (
                            id, analysis_id, property_id, field_name, ai_value,
                            ai_confidence, corrected_value, notes, submitted_at
                        ) VALUES (
                            %(id)s, %(analysis_id)s, %(property_id)s, %(field_name)s,
                            %(ai_value)s::jsonb, %(ai_confidence)s,
                            %(corrected_value)s::jsonb, %(notes)s, %(submitted_at)s
                        )
                        RETURNING *
                        """,
                        postgres_record,
                    )
                    return ServiceResult(data=cur.fetchone(), error=None, source="postgres")

        client = _get_client()
        result = client.table("ai_feedback").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving feedback to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")
