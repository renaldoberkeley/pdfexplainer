from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationCaseDef:
    case_id: str
    document: str
    pages: list[int]
    question: str
    label: str


E1_CASES: list[EvaluationCaseDef] = [
    EvaluationCaseDef(
        case_id="S1",
        document="synthetic_e1_smoke.pdf",
        pages=[1],
        question="What is the main point of this document?",
        label="Basic comprehension",
    ),
    EvaluationCaseDef(
        case_id="S2",
        document="synthetic_e1_smoke.pdf",
        pages=[1],
        question="What are weights and how are they used according to this document?",
        label="Technical detail",
    ),
    EvaluationCaseDef(
        case_id="S3",
        document="synthetic_e1_smoke.pdf",
        pages=[1],
        question="What optimizer and learning rate schedule were used in this experiment?",
        label="Insufficient information",
    ),
    EvaluationCaseDef(
        case_id="N1",
        document="notebook_lecture3.pdf",
        pages=[3, 4, 5],
        question="Explain why PCA is useful for the congressional voting example. Why can't we simply select two of the original roll-call columns? Explain it as if I'm learning PCA for the first time.",
        label="PCA motivation",
    ),
    EvaluationCaseDef(
        case_id="N2",
        document="notebook_lecture3.pdf",
        pages=[10],
        question="How much of the variation is captured by the first principal component, and how much is captured by the first two together? Explain what those numbers mean intuitively.",
        label="Quantitative grounding",
    ),
    EvaluationCaseDef(
        case_id="N3",
        document="notebook_lecture3.pdf",
        pages=[12],
        question="What is model.components_ and why does taking a dot product with w1 produce a legislator's first PCA coordinate? Explain the intuition first, then the mathematics.",
        label="Technical explanation",
    ),
    EvaluationCaseDef(
        case_id="L1",
        document="lecture_03_dimensionality_reduction.pdf",
        pages=[20, 21],
        question="Explain X ≈ ZW. What do X, Z, and W represent? Explain the dimensions of each matrix and give me an intuitive explanation of what the factorization is doing.",
        label="Matrix factorization",
    ),
    EvaluationCaseDef(
        case_id="L2",
        document="lecture_03_dimensionality_reduction.pdf",
        pages=[25, 26, 27, 28],
        question="Explain how PCA is being formulated as an optimization problem. What exactly are we minimizing? Why is the data centered? Why do we require the rows of W to be orthonormal? Explain the intuition before the mathematics.",
        label="Optimization formulation",
    ),
    EvaluationCaseDef(
        case_id="L3",
        document="lecture_03_dimensionality_reduction.pdf",
        pages=[30, 31, 32, 33, 34, 35, 36, 37, 38, 39],
        question="Walk me through the derivation that leads to the eigenvector equation. Explain each major step intuitively before explaining the mathematics. Why does the first principal component end up being the eigenvector associated with the largest eigenvalue?",
        label="Derivation walkthrough",
    ),
    EvaluationCaseDef(
        case_id="H1",
        document="lecture_03_dimensionality_reduction.pdf",
        pages=[3, 4],
        question="Using this document, derive the full Lagrangian eigenvector equation presented later in the derivation section and give the final eigenvalue equation.",
        label="Hallucination / grounding",
    ),
]


EXPERIMENT_DEFS: dict[str, dict[str, str | int]] = {
    "e1a_gemma3_4b_text_m1_mps": {
        "name": "E1a — Gemma 3 4B Text Baseline — M1 MPS",
        "model_id": "google/gemma-3-4b-it",
        "provider": "gemma_local",
        "input_mode": "text",
        "hardware_backend": "mps",
        "execution_environment": "local",
        "device": "mps",
        "prompt_version": "v1",
        "max_new_tokens": 750,
    },
    "phase_b_remote_contract_validation": {
        "name": "Phase B — Remote Gemma Contract Validation",
        "model_id": "google/gemma-3-4b-it",
        "provider": "gemma_remote",
        "input_mode": "text",
        "hardware_backend": "stub",
        "execution_environment": "remote_stub",
        "device": "simulated_cuda",
        "prompt_version": "v1",
        "max_new_tokens": 750,
    },
    "e1b_gemma3_4b_text_runpod_cuda": {
        "name": "E1b — Gemma 3 4B Text Baseline — RunPod CUDA",
        "model_id": "google/gemma-3-4b-it",
        "provider": "gemma_remote",
        "input_mode": "text",
        "hardware_backend": "runpod_cuda",
        "execution_environment": "runpod",
        "device": "cuda",
        "prompt_version": "v1",
        "max_new_tokens": 750,
    },
    "e2a_gemma3_4b_text_control_runpod_cuda": {
        "name": "E2a — Gemma 3 4B Text Control — RunPod CUDA",
        "model_id": "google/gemma-3-4b-it",
        "provider": "gemma_remote",
        "input_mode": "text",
        "hardware_backend": "runpod_cuda",
        "execution_environment": "runpod",
        "device": "cuda",
        "prompt_version": "v1",
        "max_new_tokens": 750,
    },
    "e2b_gemma3_4b_multimodal_runpod_cuda": {
        "name": "E2b — Gemma 3 4B Multimodal — RunPod CUDA",
        "model_id": "google/gemma-3-4b-it",
        "provider": "gemma_remote",
        "input_mode": "text_image",
        "hardware_backend": "runpod_cuda",
        "execution_environment": "runpod",
        "device": "cuda",
        "prompt_version": "v1",
        "max_new_tokens": 750,
    },
}
