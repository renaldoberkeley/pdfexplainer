from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_tts_provider
from app.models.schemas import SpeechRequest, SpeechResponse
from app.services.tts.base import TTSProvider

router = APIRouter(prefix="/api", tags=["speech"])


@router.post("/speech", response_model=SpeechResponse)
async def speech(
    payload: SpeechRequest, tts_provider: TTSProvider = Depends(get_tts_provider)
) -> SpeechResponse:
    result = await tts_provider.synthesize(text=payload.text)
    return SpeechResponse(
        audio_base64=result.audio_base64, mime_type=result.mime_type, provider=result.provider
    )

