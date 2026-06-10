from app.models.schemas import FeedbackRequest, ServiceResult
from app.services import property_store


async def save_feedback(req: FeedbackRequest) -> ServiceResult:
    """Save a user correction to Postgres."""
    return await property_store.save_feedback(req)
