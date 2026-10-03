from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_llm_provider, get_pdf_service
from app.models.schemas import ExplainRequest, ExplainResponse
from app.services.llm.base import LLMProvider
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api", tags=["tutor"])


@router.post("/explain", response_model=ExplainResponse)
async def explain(
    payload: ExplainRequest,
    pdf_service: PDFService = Depends(get_pdf_service),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> ExplainResponse:
    page_texts = pdf_service.get_pages_text(payload.document_id, payload.pages)
    explanation = await llm_provider.explain(
        question=payload.question, pages=payload.pages, page_texts=page_texts
    )
    return ExplainResponse(
        answer=explanation.answer,
        pages_used=explanation.pages_used,
        provider=explanation.provider,
        input_tokens=explanation.input_tokens,
        output_tokens=explanation.output_tokens,
        estimated_cost_usd=explanation.estimated_cost_usd,
    )
