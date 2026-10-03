from __future__ import annotations

from fastapi import Request

from app.services.llm.base import LLMProvider
from app.services.pdf_service import PDFService
from app.services.tts.base import TTSProvider


def get_pdf_service(request: Request) -> PDFService:
    return request.app.state.pdf_service


def get_llm_provider(request: Request) -> LLMProvider:
    return request.app.state.llm_provider


def get_tts_provider(request: Request) -> TTSProvider:
    return request.app.state.tts_provider

