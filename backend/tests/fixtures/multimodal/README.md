# Multimodal Development Fixtures

This folder is reserved for development-only multimodal fixtures used for rendering,
serialization, and contract tests.

These fixtures are **not** benchmark cases and must not be added to:

- `evaluation/specs/e2_multimodal_v1.yaml`
- `evaluation/specs/e2_scoring_rubric_v1.yaml`

The test suite generates synthetic visuals at runtime (for example simple
shape-and-arrow diagrams) to validate multimodal plumbing without touching
frozen E2 benchmark prompts.
