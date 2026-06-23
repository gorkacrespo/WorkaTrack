"""add started_at ended_at to work_sessions

Revision ID: 67b5a287831e
Revises: b336f32fd92b
Create Date: 2026-02-06 10:08:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "67b5a287831e"
down_revision = "b336f32fd92b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "work_sessions",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "work_sessions",
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("work_sessions", "ended_at")
    op.drop_column("work_sessions", "started_at")
