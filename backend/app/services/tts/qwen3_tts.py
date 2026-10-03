from __future__ import annotations

from app.services.tts.base import TTSProvider, TTSResult


class Qwen3TTSProvider(TTSProvider):
    def __init__(self, checkpoint: str | None = None) -> None:
        self.checkpoint = checkpoint

    async def synthesize(self, *, text: str) -> TTSResult:
        raise NotImplementedError(
            "Qwen3TTSProvider is a placeholder. Connect a Qwen3-TTS inference pipeline to enable audio synthesis."
        )

