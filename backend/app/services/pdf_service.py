from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

import fitz
from fastapi import HTTPException, UploadFile, status


@dataclass(slots=True)
class StoredDocument:
    document_id: str
    file_name: str
    file_path: Path
    page_count: int


@dataclass(slots=True)
class PagePayload:
    page_number: int
    text: str
    page_count: int
    file_name: str


class PDFService:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._documents: dict[str, StoredDocument] = {}

    async def store_pdf(self, upload: UploadFile) -> StoredDocument:
        if upload.content_type not in {"application/pdf", "application/octet-stream"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF uploads are supported.",
            )
        if not upload.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Missing upload filename."
            )

        document_id = str(uuid.uuid4())
        file_name = Path(upload.filename).name
        destination = self.storage_dir / f"{document_id}_{file_name}"

        with destination.open("wb") as target:
            shutil.copyfileobj(upload.file, target)

        try:
            with fitz.open(destination) as pdf:
                page_count = pdf.page_count
        except Exception as exc:  # pragma: no cover - fitz exception types are broad
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid PDF.",
            ) from exc

        stored = StoredDocument(
            document_id=document_id, file_name=file_name, file_path=destination, page_count=page_count
        )
        self._documents[document_id] = stored
        return stored

    def get_document(self, document_id: str) -> StoredDocument:
        document = self._documents.get(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
            )
        return document

    def get_page(self, document_id: str, page_number: int) -> PagePayload:
        document = self.get_document(document_id)
        if page_number < 1 or page_number > document.page_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Page {page_number} out of range. Valid range: 1..{document.page_count}.",
            )

        with fitz.open(document.file_path) as pdf:
            page = pdf.load_page(page_number - 1)
            text = page.get_text("text")

        return PagePayload(
            page_number=page_number,
            text=text,
            page_count=document.page_count,
            file_name=document.file_name,
        )

    def get_pages_text(self, document_id: str, pages: list[int]) -> dict[int, str]:
        document = self.get_document(document_id)
        invalid = [page for page in pages if page < 1 or page > document.page_count]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid pages {invalid}. Valid range: 1..{document.page_count} for this document."
                ),
            )

        page_texts: dict[int, str] = {}
        with fitz.open(document.file_path) as pdf:
            for page_number in pages:
                page_texts[page_number] = pdf.load_page(page_number - 1).get_text("text")
        return page_texts

