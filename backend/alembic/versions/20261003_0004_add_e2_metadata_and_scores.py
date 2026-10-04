"""add e2 metadata and scores

Revision ID: 20261003_0004
Revises: 20261003_0003
Create Date: 2026-10-03 23:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20261003_0004"
down_revision: Union[str, Sequence[str], None] = "20261003_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    json_type = _json_type()
    op.add_column("evaluation_cases", sa.Column("condition", sa.String(length=40), nullable=True))
    op.add_column("evaluation_cases", sa.Column("case_input_mode", sa.String(length=40), nullable=True))
    op.add_column("evaluation_cases", sa.Column("image_count", sa.Integer(), nullable=True))
    op.add_column("evaluation_cases", sa.Column("image_metadata", json_type, nullable=True))
    op.add_column("evaluation_cases", sa.Column("request_payload_bytes", sa.Integer(), nullable=True))
    op.add_column("evaluation_cases", sa.Column("image_preprocessing_seconds", sa.Float(), nullable=True))
    op.add_column("evaluation_cases", sa.Column("server_generation_seconds", sa.Float(), nullable=True))
    op.add_column("evaluation_cases", sa.Column("approximate_tokens_per_second", sa.Float(), nullable=True))
    op.add_column("evaluation_cases", sa.Column("performance_metadata", json_type, nullable=True))

    op.create_table(
        "evaluation_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_case_id", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(length=40), nullable=False),
        sa.Column("rubric_version", sa.String(length=80), nullable=False),
        sa.Column("scorer_type", sa.String(length=40), nullable=False),
        sa.Column("scorer_identifier", sa.String(length=120), nullable=True),
        sa.Column("factual_correctness", sa.Integer(), nullable=False),
        sa.Column("document_grounding", sa.Integer(), nullable=False),
        sa.Column("completeness", sa.Integer(), nullable=False),
        sa.Column("teaching_clarity", sa.Integer(), nullable=False),
        sa.Column("visual_grounding", sa.Integer(), nullable=True),
        sa.Column("visual_detail_accuracy", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["evaluation_experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_case_id"], ["evaluation_cases.id"], ondelete="CASCADE"),
        sa.CheckConstraint("factual_correctness BETWEEN 0 AND 4", name="ck_eval_scores_fact"),
        sa.CheckConstraint("document_grounding BETWEEN 0 AND 4", name="ck_eval_scores_ground"),
        sa.CheckConstraint("completeness BETWEEN 0 AND 4", name="ck_eval_scores_complete"),
        sa.CheckConstraint("teaching_clarity BETWEEN 0 AND 4", name="ck_eval_scores_clarity"),
        sa.CheckConstraint(
            "visual_grounding IS NULL OR visual_grounding BETWEEN 0 AND 4",
            name="ck_eval_scores_visual_ground",
        ),
        sa.CheckConstraint(
            "visual_detail_accuracy IS NULL OR visual_detail_accuracy BETWEEN 0 AND 4",
            name="ck_eval_scores_visual_detail",
        ),
    )


def downgrade() -> None:
    op.drop_table("evaluation_scores")
    op.drop_column("evaluation_cases", "performance_metadata")
    op.drop_column("evaluation_cases", "approximate_tokens_per_second")
    op.drop_column("evaluation_cases", "server_generation_seconds")
    op.drop_column("evaluation_cases", "image_preprocessing_seconds")
    op.drop_column("evaluation_cases", "request_payload_bytes")
    op.drop_column("evaluation_cases", "image_metadata")
    op.drop_column("evaluation_cases", "image_count")
    op.drop_column("evaluation_cases", "case_input_mode")
    op.drop_column("evaluation_cases", "condition")
