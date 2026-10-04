from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.explain import router as explain_router
from app.api.hv1 import router as hv1_router
from app.api.providers import router as providers_router
from app.api.speech import router as speech_router
from app.evaluation.database import create_session_factory
from app.services.pdf_service import PDFService
from app.services.hv1_service import HV1Service
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
    app.state.hv1_service = _build_hv1_service()

    app.include_router(documents_router)
    app.include_router(explain_router)
    app.include_router(speech_router)
    app.include_router(providers_router)
    app.include_router(hv1_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

def _build_hv1_service() -> HV1Service | None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return None

    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "evaluation" / "human_validation" / "data"
    study_spec = project_root / "evaluation" / "human_validation" / "hv1_study_spec.yaml"
    rubric_file = project_root / "evaluation" / "human_validation" / "human_e2_rubric_v1.yaml"
    documents_dir = project_root / "evaluation" / "documents"

    required = [data_dir, study_spec, rubric_file, documents_dir]
    if any(not path.exists() for path in required):
        return None

    return HV1Service(
        session_factory=create_session_factory(database_url),
        data_dir=data_dir,
        document_dir=documents_dir,
        rubric_file=rubric_file,
        study_spec_file=study_spec,
    )


app = create_app()
