# HV1 — Human Validation of E2 (Preregistered, Not Launched)

## Study identity

- **Study ID:** `hv1_e2_human_validation`
- **Status:** `preregistered_not_launched`
- **Source E2 results commit:** `f7e2d562f30b3bad9c899eecba8568079e9ac4bf`
- **Participant source (planned):** Prolific

## Purpose

HV1 independently evaluates the 24 frozen E2 responses with blinded human raters to assess:

1. alignment with automated quality conclusions,
2. possible automated ceiling/leniency effects,
3. visual-grounding differences between text and text+image conditions,
4. treatment of appropriate insufficient-information refusals (notably A_H1),
5. inter-rater agreement.

## Fixed scope

- Responses: **24** (12 text, 12 text+image)
- Ratings per response: **3**
- Target completed ratings: **72**
- No reruns of E2 inference.
- No reruns of automated scoring.
- No changes to frozen E2 specs or historical result artifacts.

## Blinding requirements

Participant-facing materials must not reveal:

- condition labels (`text` vs `text_image`)
- case IDs (`A_*`, `V*`)
- experiment keys (`E2a`, `E2b`)
- latency/token/cost metadata
- prior automated scores
- hypotheses or expected outcomes

## Assignment design

- Balanced slot design with **minimum 6 participants**.
- Each participant rates **12 tasks**.
- For each case family (two condition variants), a participant sees **exactly one** variant.
- Across 6 slots, each response receives 3 ratings and each case family receives 3 text + 3 text+image ratings.
- Task order is deterministic per slot using `assignment_version` + `randomization_seed`.

## Participant qualifications (planned for Prolific)

Recommended inclusion criteria:

- English proficiency sufficient for technical reading and writing tasks.
- Background in at least one relevant area (self-reported): computer science, data science, statistics, mathematics, engineering, machine learning, or related quantitative field.
- Prior experience interpreting technical explanations, charts, equations, or code snippets.

Recommended non-excessive exclusions:

- Fail comprehension check on rubric/task instructions.
- Incomplete submissions (substantial missing ratings).

Do not exclude based on disagreement with the research hypothesis.

## Ethics and human-subjects checkpoint (required before launch)

**UNRESOLVED PRE-LAUNCH REQUIREMENT**

Before any recruitment or data collection:

- determine whether IRB review, exemption determination, or other institutional approval is required,
- finalize participant consent language and study information sheet,
- verify privacy/data-handling requirements.

No ethics determination is claimed in this protocol.

## Copyright/content-distribution checkpoint (required before launch)

**UNRESOLVED PRE-LAUNCH REQUIREMENT**

The source PDFs include UC Berkeley course material. Before public deployment:

- confirm permissible distribution pattern for page rendering,
- keep full PDFs server-side/local,
- serve only the minimal task-required pages.

No legal determination is claimed in this protocol.

## Data handling and privacy

- Do not collect names/emails or unnecessary PII.
- Accept optional provider identifiers (`PROLIFIC_PID`, `STUDY_ID`, `SESSION_ID`) but store hashed forms where practical.
- Separate private mapping from participant-facing payloads.
- Do not expose filesystem paths, secrets, or internal experiment metadata in participant APIs.

## Instrument workflow

1. Intro/consent placeholder screen (draft-only, not final consent).
2. Synthetic calibration example (not E2 content).
3. Repeated blinded rating tasks with rubric help accessible.
4. Submit-and-next progression until assigned tasks complete.

## Analysis preregistration (post-collection)

### Primary analyses

For each rubric dimension:

- compare text vs text+image human ratings,
- report mean, median, distribution, and condition deltas.

### Inter-rater agreement

- Krippendorff’s alpha (ordinal) per dimension.
- Optional: weighted pairwise Cohen’s kappa.

### Ceiling analysis

- compare proportion of maximum scores (4/4) between human and automated ratings,
- evaluate whether human scores provide finer discrimination.

### H1 diagnostic analysis

- analyze A_H1 separately post-collection to test whether humans reward correct evidence-limited refusal.
- do not reveal this diagnostic target to participants.

### Visual-case analysis

- treat human ratings as authoritative evidence for V1–V6 visual dimensions.
- comparisons against automated visual metrics must acknowledge E2 provenance caveats.

## Quality checks

Transparent checks only:

- instruction comprehension confirmation,
- required-field validation,
- duplicate submission prevention,
- incomplete-response exclusion rules predefined.

No deceptive trap questions.

## Launch status

- Prolific study creation: **not done**
- Recruitment: **not done**
- Human participants: **0**
- Real human ratings: **0**
