# Evaluation Specs

This folder stores preregistered, versioned experiment methodology for evaluation runs.

## Files

- [e2_multimodal_v1.yaml](./e2_multimodal_v1.yaml): E2 experiment preregistration (case set, pairing strategy, condition definitions, metadata plan, and analysis alignment).
- [e2_scoring_rubric_v1.yaml](./e2_scoring_rubric_v1.yaml): frozen rubric definitions used to score E2 outputs.

## Conventions

- **Immutability after execution starts:** Once outputs are generated for a spec version, do not mutate that version in place.
- **Version bumps for methodology changes:** Create `*_v2.yaml`, `*_v3.yaml`, etc. for any methodological changes.
- **Prompt isolation:** Design metadata (rationale, expected limitations, hypotheses, scoring notes) must not be injected into model prompts.
- **No secrets:** Specs must not contain credentials, tokens, private keys, or environment-specific secrets.

## PostgreSQL scoring table proposal

The current schema persists experiments in `evaluation_experiments` and `evaluation_cases`.
For rubric scoring, add a separate table (future migration), not a replacement:

```sql
CREATE TABLE evaluation_scores (
  id BIGSERIAL PRIMARY KEY,
  experiment_id INTEGER NOT NULL REFERENCES evaluation_experiments(id) ON DELETE CASCADE,
  evaluation_case_id INTEGER NOT NULL REFERENCES evaluation_cases(id) ON DELETE CASCADE,
  condition VARCHAR(40) NOT NULL, -- text | text_image
  rubric_version VARCHAR(80) NOT NULL,
  scorer_type VARCHAR(40) NOT NULL, -- human | model | hybrid
  scorer_identifier VARCHAR(120) NULL, -- anonymized rater id
  factual_correctness SMALLINT NOT NULL CHECK (factual_correctness BETWEEN 0 AND 4),
  document_grounding SMALLINT NOT NULL CHECK (document_grounding BETWEEN 0 AND 4),
  completeness SMALLINT NOT NULL CHECK (completeness BETWEEN 0 AND 4),
  teaching_clarity SMALLINT NOT NULL CHECK (teaching_clarity BETWEEN 0 AND 4),
  visual_grounding SMALLINT NULL CHECK (visual_grounding BETWEEN 0 AND 4),
  visual_detail_accuracy SMALLINT NULL CHECK (visual_detail_accuracy BETWEEN 0 AND 4),
  notes TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Keep dimensions separate in storage; compute aggregate quality scores in queries/reports.
