from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.services.llm.base import LLMProvider
from app.services.pdf_service import PDFService
from app.services.tts.base import TTSProvider
from app.services.hv1_service import HV1Service


def get_pdf_service(request: Request) -> PDFService:
    return request.app.state.pdf_service


def get_llm_provider(request: Request) -> LLMProvider:
    return request.app.state.llm_provider


def get_tts_provider(request: Request) -> TTSProvider:
    return request.app.state.tts_provider


def get_hv1_service(request: Request) -> HV1Service:
    service = getattr(request.app.state, "hv1_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HV1 service is not configured. Set DATABASE_URL and HV1 files for local research mode.",
        )
    return service
