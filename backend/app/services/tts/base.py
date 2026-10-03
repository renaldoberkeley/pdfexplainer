from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class TTSResult:
    audio_base64: str
    mime_type: str
    provider: str


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, *, text: str) -> TTSResult:
        raise NotImplementedError

