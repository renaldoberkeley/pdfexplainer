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
    page_contexts = pdf_service.get_page_contexts(
        payload.document_id,
        payload.pages,
        include_images=payload.input_mode == "text_image",
        rendered_dpi=payload.rendered_dpi,
        image_format=payload.image_format,
    )
    explanation = await llm_provider.explain(
        question=payload.question,
        pages=page_contexts,
        input_mode=payload.input_mode,
    )
    return ExplainResponse(
        answer=explanation.answer,
        pages_used=explanation.pages_used,
        provider=explanation.provider,
        input_tokens=explanation.input_tokens,
        output_tokens=explanation.output_tokens,
        estimated_cost_usd=explanation.estimated_cost_usd,
        input_mode=payload.input_mode,
        image_count=explanation.image_count,
        request_payload_bytes=explanation.request_payload_bytes,
        image_preprocessing_seconds=explanation.image_preprocessing_seconds,
        server_generation_seconds=explanation.server_generation_seconds,
        approximate_tokens_per_second=explanation.approximate_tokens_per_second,
    )
