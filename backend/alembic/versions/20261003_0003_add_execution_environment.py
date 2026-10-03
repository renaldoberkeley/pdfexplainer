from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20261003_0003"
down_revision = "20261003_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluation_experiments",
        sa.Column(
            "execution_environment",
            sa.String(length=100),
            nullable=False,
            server_default=sa.text("'local'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("evaluation_experiments", "execution_environment")

