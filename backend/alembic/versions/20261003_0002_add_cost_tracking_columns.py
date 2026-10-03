from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20261003_0002"
down_revision = "20261003_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluation_experiments",
        sa.Column(
            "total_estimated_cost_usd",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "evaluation_cases",
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evaluation_cases", "estimated_cost_usd")
    op.drop_column("evaluation_experiments", "total_estimated_cost_usd")

