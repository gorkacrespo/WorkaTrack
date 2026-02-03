from alembic import op
import sqlalchemy as sa

revision = 'e1063c9ea043'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'work_sessions',
        sa.Column('started_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'work_sessions',
        sa.Column('ended_at', sa.DateTime(), nullable=True)
    )


def downgrade():
    op.drop_column('work_sessions', 'ended_at')
    op.drop_column('work_sessions', 'started_at')
