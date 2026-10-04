from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_hv1_service
from app.models.hv1_schemas import (
    Hv1ProgressResponse,
    Hv1RatingSubmitRequest,
    Hv1RatingSubmitResponse,
    Hv1SessionStartRequest,
    Hv1SessionStartResponse,
    Hv1TaskResponse,
)
from app.services.hv1_service import HV1Service

router = APIRouter(prefix="/api/research/hv1", tags=["research-hv1"])


@router.post("/session/start", response_model=Hv1SessionStartResponse)
async def start_hv1_session(
    payload: Hv1SessionStartRequest,
    hv1_service: HV1Service = Depends(get_hv1_service),
) -> Hv1SessionStartResponse:
    return hv1_service.start_session(payload)


@router.get("/session/{participant_session_id}/task", response_model=Hv1TaskResponse)
async def get_hv1_task(
    participant_session_id: str,
    hv1_service: HV1Service = Depends(get_hv1_service),
) -> Hv1TaskResponse:
    return hv1_service.get_next_task(participant_session_id)


@router.get("/session/{participant_session_id}/progress", response_model=Hv1ProgressResponse)
async def get_hv1_progress(
    participant_session_id: str,
    hv1_service: HV1Service = Depends(get_hv1_service),
) -> Hv1ProgressResponse:
    return hv1_service.get_progress(participant_session_id)


@router.post("/session/{participant_session_id}/rating", response_model=Hv1RatingSubmitResponse)
async def submit_hv1_rating(
    participant_session_id: str,
    payload: Hv1RatingSubmitRequest,
    hv1_service: HV1Service = Depends(get_hv1_service),
) -> Hv1RatingSubmitResponse:
    return hv1_service.submit_rating(participant_session_id, payload)
