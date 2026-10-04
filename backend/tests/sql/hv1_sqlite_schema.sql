CREATE TABLE IF NOT EXISTS human_studies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  study_id VARCHAR(120) NOT NULL UNIQUE,
  protocol_version VARCHAR(80) NOT NULL,
  rubric_version VARCHAR(80) NOT NULL,
  source_results_commit VARCHAR(80) NOT NULL,
  source_experiment VARCHAR(40) NOT NULL,
  status VARCHAR(80) NOT NULL,
  participant_source VARCHAR(80) NOT NULL,
  responses INTEGER NOT NULL,
  ratings_per_response INTEGER NOT NULL,
  target_total_ratings INTEGER NOT NULL,
  assignment_version VARCHAR(80) NOT NULL,
  randomization_seed VARCHAR(120) NOT NULL,
  metadata_json TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS human_participants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  study_id INTEGER NOT NULL,
  public_id VARCHAR(120) NOT NULL,
  external_provider VARCHAR(40) NOT NULL,
  external_participant_hash VARCHAR(128) NULL,
  external_study_hash VARCHAR(128) NULL,
  external_session_hash VARCHAR(128) NULL,
  assignment_slot INTEGER NOT NULL,
  assignment_version VARCHAR(80) NOT NULL,
  status VARCHAR(40) NOT NULL,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(study_id) REFERENCES human_studies(id) ON DELETE CASCADE,
  UNIQUE(study_id, public_id)
);

CREATE TABLE IF NOT EXISTS human_assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  study_id INTEGER NOT NULL,
  participant_id INTEGER NOT NULL,
  hv1_response_id VARCHAR(40) NOT NULL,
  family_id VARCHAR(20) NOT NULL,
  task_order INTEGER NOT NULL,
  assignment_version VARCHAR(80) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(study_id) REFERENCES human_studies(id) ON DELETE CASCADE,
  FOREIGN KEY(participant_id) REFERENCES human_participants(id) ON DELETE CASCADE,
  UNIQUE(participant_id, task_order),
  UNIQUE(participant_id, hv1_response_id)
);

CREATE TABLE IF NOT EXISTS human_ratings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  study_id INTEGER NOT NULL,
  participant_id INTEGER NOT NULL,
  assignment_id INTEGER NOT NULL,
  hv1_response_id VARCHAR(40) NOT NULL,
  rubric_version VARCHAR(80) NOT NULL,
  factual_correctness INTEGER NOT NULL CHECK (factual_correctness BETWEEN 0 AND 4),
  document_grounding INTEGER NOT NULL CHECK (document_grounding BETWEEN 0 AND 4),
  completeness INTEGER NOT NULL CHECK (completeness BETWEEN 0 AND 4),
  teaching_clarity INTEGER NOT NULL CHECK (teaching_clarity BETWEEN 0 AND 4),
  visual_grounding INTEGER NULL CHECK (visual_grounding IS NULL OR visual_grounding BETWEEN 0 AND 4),
  visual_detail_accuracy INTEGER NULL CHECK (visual_detail_accuracy IS NULL OR visual_detail_accuracy BETWEEN 0 AND 4),
  comment TEXT NULL,
  is_test_data BOOLEAN NOT NULL DEFAULT 1,
  submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(study_id) REFERENCES human_studies(id) ON DELETE CASCADE,
  FOREIGN KEY(participant_id) REFERENCES human_participants(id) ON DELETE CASCADE,
  FOREIGN KEY(assignment_id) REFERENCES human_assignments(id) ON DELETE CASCADE,
  UNIQUE(participant_id, hv1_response_id)
);
