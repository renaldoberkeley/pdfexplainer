from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.models.schemas import DocumentUploadResponse, PageResponse
from app.dependencies import get_pdf_service
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...), pdf_service: PDFService = Depends(get_pdf_service)
) -> DocumentUploadResponse:
    stored = await pdf_service.store_pdf(file)
    return DocumentUploadResponse(
        document_id=stored.document_id, filename=stored.file_name, page_count=stored.page_count
    )


@router.get("/{document_id}/pages/{page_number}", response_model=PageResponse)
async def get_page(
    document_id: str, page_number: int, pdf_service: PDFService = Depends(get_pdf_service)
) -> PageResponse:
    page = pdf_service.get_page(document_id, page_number)
    return PageResponse(
        document_id=document_id,
        page_number=page.page_number,
        page_count=page.page_count,
        filename=page.file_name,
        text=page.text,
    )
