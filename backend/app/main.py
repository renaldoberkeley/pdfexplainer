from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.explain import router as explain_router
from app.api.providers import router as providers_router
from app.api.speech import router as speech_router
from app.services.pdf_service import PDFService
from app.services.provider_factory import build_llm_provider, build_tts_provider


def create_app() -> FastAPI:
    app = FastAPI(title="AI PDF Tutor API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    upload_dir = Path(os.getenv("PDF_UPLOAD_DIR", "backend/uploads"))
    app.state.pdf_service = PDFService(storage_dir=upload_dir)
    app.state.llm_provider = build_llm_provider()
    app.state.tts_provider = build_tts_provider()

    app.include_router(documents_router)
    app.include_router(explain_router)
    app.include_router(speech_router)
    app.include_router(providers_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
