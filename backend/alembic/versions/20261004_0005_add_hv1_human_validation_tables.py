"""add hv1 human validation tables

Revision ID: 20261004_0005
Revises: 20261003_0004
Create Date: 2026-10-04 15:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20261004_0005"
down_revision: Union[str, Sequence[str], None] = "20261003_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "human_studies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("study_id", sa.String(length=120), nullable=False, unique=True),
        sa.Column("protocol_version", sa.String(length=80), nullable=False),
        sa.Column("rubric_version", sa.String(length=80), nullable=False),
        sa.Column("source_results_commit", sa.String(length=80), nullable=False),
        sa.Column("source_experiment", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("participant_source", sa.String(length=80), nullable=False),
        sa.Column("responses", sa.Integer(), nullable=False),
        sa.Column("ratings_per_response", sa.Integer(), nullable=False),
        sa.Column("target_total_ratings", sa.Integer(), nullable=False),
        sa.Column("assignment_version", sa.String(length=80), nullable=False),
        sa.Column("randomization_seed", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "human_participants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=120), nullable=False),
        sa.Column("external_provider", sa.String(length=40), nullable=False),
        sa.Column("external_participant_hash", sa.String(length=128), nullable=True),
        sa.Column("external_study_hash", sa.String(length=128), nullable=True),
        sa.Column("external_session_hash", sa.String(length=128), nullable=True),
        sa.Column("assignment_slot", sa.Integer(), nullable=False),
        sa.Column("assignment_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["human_studies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("study_id", "public_id", name="uq_human_participant_public_id"),
    )

    op.create_table(
        "human_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("hv1_response_id", sa.String(length=40), nullable=False),
        sa.Column("family_id", sa.String(length=20), nullable=False),
        sa.Column("task_order", sa.Integer(), nullable=False),
        sa.Column("assignment_version", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["human_studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["human_participants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("participant_id", "task_order", name="uq_human_assignment_task_order"),
        sa.UniqueConstraint("participant_id", "hv1_response_id", name="uq_human_assignment_response"),
    )

    op.create_table(
        "human_ratings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("hv1_response_id", sa.String(length=40), nullable=False),
        sa.Column("rubric_version", sa.String(length=80), nullable=False),
        sa.Column("factual_correctness", sa.Integer(), nullable=False),
        sa.Column("document_grounding", sa.Integer(), nullable=False),
        sa.Column("completeness", sa.Integer(), nullable=False),
        sa.Column("teaching_clarity", sa.Integer(), nullable=False),
        sa.Column("visual_grounding", sa.Integer(), nullable=True),
        sa.Column("visual_detail_accuracy", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_test_data", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["human_studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["human_participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["human_assignments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("participant_id", "hv1_response_id", name="uq_human_rating_once"),
        sa.CheckConstraint("factual_correctness BETWEEN 0 AND 4", name="ck_human_rating_fact"),
        sa.CheckConstraint("document_grounding BETWEEN 0 AND 4", name="ck_human_rating_ground"),
        sa.CheckConstraint("completeness BETWEEN 0 AND 4", name="ck_human_rating_complete"),
        sa.CheckConstraint("teaching_clarity BETWEEN 0 AND 4", name="ck_human_rating_clarity"),
        sa.CheckConstraint(
            "visual_grounding IS NULL OR visual_grounding BETWEEN 0 AND 4",
            name="ck_human_rating_visual_ground",
        ),
        sa.CheckConstraint(
            "visual_detail_accuracy IS NULL OR visual_detail_accuracy BETWEEN 0 AND 4",
            name="ck_human_rating_visual_detail",
        ),
    )


def downgrade() -> None:
    op.drop_table("human_ratings")
    op.drop_table("human_assignments")
    op.drop_table("human_participants")
    op.drop_table("human_studies")
