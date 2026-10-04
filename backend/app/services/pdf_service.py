from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

import fitz
from fastapi import HTTPException, UploadFile, status

from app.services.llm.base import PageContext, PageImage

DEFAULT_RENDER_DPI = 200
DEFAULT_RENDER_FORMAT = "png"


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


@dataclass(slots=True)
class PageImagePayload:
    page_number: int
    image_bytes: bytes
    image_format: str
    width: int
    height: int
    rendered_dpi: int
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
        self._validate_pages(pages, document.page_count)

        page_texts: dict[int, str] = {}
        with fitz.open(document.file_path) as pdf:
            for page_number in pages:
                page_texts[page_number] = pdf.load_page(page_number - 1).get_text("text")
        return page_texts

    def render_page_image(
        self,
        document_id: str,
        page_number: int,
        *,
        rendered_dpi: int = DEFAULT_RENDER_DPI,
        image_format: str = DEFAULT_RENDER_FORMAT,
    ) -> PageImagePayload:
        document = self.get_document(document_id)
        self._validate_pages([page_number], document.page_count)
        self._validate_render_params(rendered_dpi=rendered_dpi, image_format=image_format)

        with fitz.open(document.file_path) as pdf:
            page = pdf.load_page(page_number - 1)
            pixmap = page.get_pixmap(dpi=rendered_dpi, alpha=False)
            image_bytes = pixmap.tobytes(image_format)
            width = int(pixmap.width)
            height = int(pixmap.height)

        return PageImagePayload(
            page_number=page_number,
            image_bytes=image_bytes,
            image_format=image_format,
            width=width,
            height=height,
            rendered_dpi=rendered_dpi,
            page_count=document.page_count,
            file_name=document.file_name,
        )

    def get_page_contexts(
        self,
        document_id: str,
        pages: list[int],
        *,
        include_images: bool,
        rendered_dpi: int = DEFAULT_RENDER_DPI,
        image_format: str = DEFAULT_RENDER_FORMAT,
    ) -> list[PageContext]:
        document = self.get_document(document_id)
        self._validate_pages(pages, document.page_count)
        self._validate_render_params(rendered_dpi=rendered_dpi, image_format=image_format)

        contexts: list[PageContext] = []
        with fitz.open(document.file_path) as pdf:
            for page_number in pages:
                page = pdf.load_page(page_number - 1)
                page_text = page.get_text("text")
                image: PageImage | None = None
                if include_images:
                    pixmap = page.get_pixmap(dpi=rendered_dpi, alpha=False)
                    image = PageImage(
                        data=pixmap.tobytes(image_format),
                        image_format=image_format,
                        width=int(pixmap.width),
                        height=int(pixmap.height),
                        rendered_dpi=rendered_dpi,
                    )
                contexts.append(PageContext(page_number=page_number, text=page_text, image=image))
        return contexts

    @staticmethod
    def _validate_render_params(*, rendered_dpi: int, image_format: str) -> None:
        if rendered_dpi < 72 or rendered_dpi > 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rendered_dpi must be between 72 and 400.",
            )
        if image_format.lower() not in {"png", "jpeg", "jpg"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="image_format must be one of: png, jpeg, jpg.",
            )

    @staticmethod
    def _validate_pages(pages: list[int], page_count: int) -> None:
        invalid = [page for page in pages if page < 1 or page > page_count]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pages {invalid}. Valid range: 1..{page_count} for this document.",
            )
