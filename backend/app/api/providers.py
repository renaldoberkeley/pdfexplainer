from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_llm_provider, get_tts_provider
from app.models.schemas import ProviderConfigResponse, ProviderStatusResponse
from app.services.llm.base import LLMProvider
from app.services.provider_factory import get_provider_config, get_providers_status
from app.services.tts.base import TTSProvider

router = APIRouter(prefix="/api", tags=["providers"])


@router.get("/providers", response_model=ProviderConfigResponse)
async def provider_config() -> ProviderConfigResponse:
    config = get_provider_config()
    return ProviderConfigResponse(**config)


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def provider_status(
    llm_provider: LLMProvider = Depends(get_llm_provider),
    tts_provider: TTSProvider = Depends(get_tts_provider),
) -> ProviderStatusResponse:
    status = get_providers_status(llm_provider=llm_provider, tts_provider=tts_provider)
    return ProviderStatusResponse(**status)
