# HV1 Human Validation Package

This folder contains preregistered methodology and implementation artifacts for **HV1**, the human validation layer over frozen E2 responses.

## Files

- [hv1_study_protocol.md](./hv1_study_protocol.md): narrative protocol and ethics/copyright checkpoints.
- [hv1_study_spec.yaml](./hv1_study_spec.yaml): machine-readable study specification.
- [human_e2_rubric_v1.yaml](./human_e2_rubric_v1.yaml): human rubric with explicit abstention policy.
- [data/hv1_response_pool_public.json](./data/hv1_response_pool_public.json): participant-safe response pool (no condition labels).
- [data/hv1_private_mapping.secure.json](./data/hv1_private_mapping.secure.json): private response mapping (condition-bearing; do not expose to participants).
- [data/hv1_calibration_fixture.json](./data/hv1_calibration_fixture.json): synthetic calibration example.

## Local architecture

- Backend APIs are implemented under `/api/research/hv1/*` (FastAPI).
- Frontend evaluator UI is isolated at `/research/hv1`.
- Persistent storage uses dedicated human-validation tables, separate from historical automated scoring rows.

## Local development/testing

1. Ensure backend migrations are up to date.
2. Start backend and frontend locally.
3. Open `/research/hv1`.
4. Run through synthetic local sessions only.

No real participant traffic or Prolific integration is enabled in this phase.

## Planned Prolific launch concept (not implemented yet)

The UI can accept optional query parameters for future study routing:

- `PROLIFIC_PID`
- `STUDY_ID`
- `SESSION_ID`

Local mode does not require them. Before launch:

- finalize ethics/IRB decision and consent language,
- finalize Prolific study configuration and completion workflow,
- confirm source-material distribution constraints.
