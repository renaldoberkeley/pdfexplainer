from __future__ import annotations

import os
import time
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    model: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    max_new_tokens: int = Field(default=750, ge=1, le=4096)


class GenerateResponse(BaseModel):
    text: str
    model: str
    device: str
    input_tokens: int
    output_tokens: int
    generation_seconds: float
    loaded: bool


class ModelStatus(BaseModel):
    model: str
    device: str
    loaded: bool
    cuda_available: bool
    gpu_name: str | None = None


class GemmaRuntime:
    def __init__(self) -> None:
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._torch: Any | None = None
        self._model_id = os.getenv("GEMMA_MODEL_ID", "").strip()
        if not self._model_id:
            raise ValueError("GEMMA_MODEL_ID is required for runpod inference service.")
        self._device = "cpu"
        self._loaded = False

    def _select_device(self, torch_module: Any) -> str:
        if torch_module.cuda.is_available():
            return "cuda"
        if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
            return "mps"
        return "cpu"

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._torch = torch
        self._device = self._select_device(torch)
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_id)
        self._model = AutoModelForCausalLM.from_pretrained(self._model_id, low_cpu_mem_usage=True)
        self._model.to(self._device)
        self._model.eval()
        self._loaded = True

    def generate(self, prompt: str, max_new_tokens: int) -> GenerateResponse:
        self.ensure_loaded()
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._torch is not None
        start = time.monotonic()
        tokens = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        with self._torch.inference_mode():
            output_ids = self._model.generate(
                **tokens, max_new_tokens=max_new_tokens, do_sample=False
            )
        prompt_token_count = tokens["input_ids"].shape[1]
        generated = output_ids[0][prompt_token_count:]
        text = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
        generation_seconds = round(time.monotonic() - start, 2)
        return GenerateResponse(
            text=text,
            model=self._model_id,
            device=self._device,
            input_tokens=int(prompt_token_count),
            output_tokens=int(generated.shape[0]),
            generation_seconds=generation_seconds,
            loaded=self._loaded,
        )

    def status(self) -> ModelStatus:
        cuda_available = False
        gpu_name = None
        if self._torch is not None:
            cuda_available = bool(self._torch.cuda.is_available())
            if cuda_available:
                gpu_name = str(self._torch.cuda.get_device_name(0))
        return ModelStatus(
            model=self._model_id,
            device=self._device,
            loaded=self._loaded,
            cuda_available=cuda_available,
            gpu_name=gpu_name,
        )


app = FastAPI(title="RunPod Gemma Inference Service", version="0.1.0")
runtime = GemmaRuntime()


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("RUNPOD_API_KEY", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RUNPOD_API_KEY is not configured.",
        )
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/model/status", response_model=ModelStatus, dependencies=[Depends(verify_api_key)])
async def model_status() -> ModelStatus:
    return runtime.status()


@app.post("/generate", response_model=GenerateResponse, dependencies=[Depends(verify_api_key)])
async def generate(payload: GenerateRequest) -> GenerateResponse:
    if payload.model.strip() != runtime.status().model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configured model is {runtime.status().model}; got {payload.model}.",
        )
    return runtime.generate(prompt=payload.prompt, max_new_tokens=payload.max_new_tokens)

