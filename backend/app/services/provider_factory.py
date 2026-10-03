from __future__ import annotations

import os
from typing import Any

from app.services.llm.base import LLMProvider
from app.services.llm.gemma import LocalGemmaProvider
from app.services.llm.mock import MockLLMProvider
from app.services.llm.remote_gemma import RemoteGemmaProvider
from app.services.tts.base import TTSProvider
from app.services.tts.mock import MockTTSProvider
from app.services.tts.qwen3_tts import Qwen3TTSProvider

LLM_PROVIDER_OPTIONS = ("mock", "gemma_local", "gemma_remote", "gemma")
TTS_PROVIDER_OPTIONS = ("mock", "qwen3")


def build_llm_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name in {"gemma", "gemma_local"}:
        model_id = os.getenv("GEMMA_MODEL_ID", "").strip()
        max_new_tokens = int(os.getenv("GEMMA_MAX_NEW_TOKENS", "1000"))
        return LocalGemmaProvider(model_id=model_id, max_new_tokens=max_new_tokens)
    if provider_name == "gemma_remote":
        model_id = os.getenv("GEMMA_MODEL_ID", "").strip()
        max_new_tokens = int(os.getenv("GEMMA_MAX_NEW_TOKENS", "1000"))
        remote_url = os.getenv("GEMMA_REMOTE_URL", "").strip()
        remote_api_key = os.getenv("GEMMA_REMOTE_API_KEY", "").strip()
        timeout_seconds = float(os.getenv("GEMMA_REMOTE_TIMEOUT_SECONDS", "120"))
        return RemoteGemmaProvider(
            model_id=model_id,
            base_url=remote_url,
            api_key=remote_api_key,
            max_new_tokens=max_new_tokens,
            timeout_seconds=timeout_seconds,
        )
    raise ValueError(f"Unsupported LLM provider: {provider_name}")


def build_tts_provider() -> TTSProvider:
    provider_name = os.getenv("TTS_PROVIDER", "mock").lower()
    if provider_name == "mock":
        return MockTTSProvider()
    if provider_name == "qwen3":
        return Qwen3TTSProvider(checkpoint=os.getenv("QWEN3_TTS_CHECKPOINT"))
    raise ValueError(f"Unsupported TTS provider: {provider_name}")


def get_provider_config() -> dict[str, str | list[str]]:
    return {
        "llm_provider": os.getenv("LLM_PROVIDER", "mock").lower(),
        "gemma_model_id": os.getenv("GEMMA_MODEL_ID", "").strip(),
        "gemma_max_new_tokens": os.getenv("GEMMA_MAX_NEW_TOKENS", "1000"),
        "gemma_remote_url": os.getenv("GEMMA_REMOTE_URL", "").strip(),
        "tts_provider": os.getenv("TTS_PROVIDER", "mock").lower(),
        "stt_provider": os.getenv("STT_PROVIDER", "whisper").lower(),
        "available_llm_providers": list(LLM_PROVIDER_OPTIONS),
        "available_tts_providers": list(TTS_PROVIDER_OPTIONS),
        "available_stt_providers": ["whisper"],
    }


def get_providers_status(llm_provider: LLMProvider, tts_provider: TTSProvider) -> dict[str, Any]:
    if hasattr(llm_provider, "status"):
        llm_status = llm_provider.status()
    else:
        llm_status = {"provider": llm_provider.__class__.__name__.lower()}

    if isinstance(tts_provider, MockTTSProvider):
        tts_status = {"provider": "mock"}
    elif isinstance(tts_provider, Qwen3TTSProvider):
        tts_status = {"provider": "qwen3"}
    else:
        tts_status = {"provider": tts_provider.__class__.__name__.lower()}

    return {"llm": llm_status, "tts": tts_status}
