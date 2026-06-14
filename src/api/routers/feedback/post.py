"""POST /feedback"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    tags=["feedback"],
    summary="Feedback",
    description="Feedback를 기록합니다.",
)
def feedback(
    req: FeedbackRequest,
    container: AppContainer = Depends(get_app_container),
) -> FeedbackResponse:
    result = container.feedback_recorder.record(
        arm_id=req.arm_id,
        context_key=req.user_id,
        action=req.action,
        dwell_seconds=req.dwell_seconds,
    )
    return FeedbackResponse(arm_id=result.arm_id, reward=result.reward)
