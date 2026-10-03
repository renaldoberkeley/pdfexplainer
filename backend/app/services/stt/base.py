from __future__ import annotations

from abc import ABC, abstractmethod


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, *, audio_bytes: bytes, mime_type: str) -> str:
        raise NotImplementedError

