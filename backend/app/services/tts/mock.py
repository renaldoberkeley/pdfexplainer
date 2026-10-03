from __future__ import annotations

import base64
import io
import math
import struct
import wave

from app.services.tts.base import TTSProvider, TTSResult


class MockTTSProvider(TTSProvider):
    async def synthesize(self, *, text: str) -> TTSResult:
        buffer = io.BytesIO()
        sample_rate = 22050
        duration_seconds = 0.8
        frequency = 330.0
        frames = int(sample_rate * duration_seconds)

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for index in range(frames):
                amplitude = int(
                    32767 * 0.15 * math.sin((2.0 * math.pi * frequency * index) / sample_rate)
                )
                wav_file.writeframes(struct.pack("<h", amplitude))

        audio_bytes = buffer.getvalue()
        return TTSResult(
            audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
            mime_type="audio/wav",
            provider="mock-tts",
        )

