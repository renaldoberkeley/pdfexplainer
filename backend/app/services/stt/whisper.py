from __future__ import annotations

from app.services.stt.base import STTProvider


class WhisperSTTProvider(STTProvider):
    def __init__(self, checkpoint: str | None = None) -> None:
        self.checkpoint = checkpoint

    async def transcribe(self, *, audio_bytes: bytes, mime_type: str) -> str:
        raise NotImplementedError(
            "WhisperSTTProvider is a placeholder. Add Whisper model loading and inference to enable STT."
        )

