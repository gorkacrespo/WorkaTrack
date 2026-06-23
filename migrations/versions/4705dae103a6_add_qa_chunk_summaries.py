"""add qa_chunk_summaries

Revision ID: 4705dae103a6
Revises: 67b5a287831e
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4705dae103a6'
down_revision = '67b5a287831e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'qa_chunk_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('week_end', sa.Date(), nullable=False),
        sa.Column('scope', sa.String(length=32), nullable=False, server_default='all'),
        sa.Column('algo_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('meta_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'user_id', 'scope', 'algo_version', 'week_start', name='uq_qa_chunk_summary'),
    )
    op.create_index(op.f('ix_qa_chunk_summaries_algo_version'), 'qa_chunk_summaries', ['algo_version'], unique=False)
    op.create_index(op.f('ix_qa_chunk_summaries_project_id'), 'qa_chunk_summaries', ['project_id'], unique=False)
    op.create_index(op.f('ix_qa_chunk_summaries_scope'), 'qa_chunk_summaries', ['scope'], unique=False)
    op.create_index(op.f('ix_qa_chunk_summaries_user_id'), 'qa_chunk_summaries', ['user_id'], unique=False)
    op.create_index(op.f('ix_qa_chunk_summaries_week_end'), 'qa_chunk_summaries', ['week_end'], unique=False)
    op.create_index(op.f('ix_qa_chunk_summaries_week_start'), 'qa_chunk_summaries', ['week_start'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_qa_chunk_summaries_week_start'), table_name='qa_chunk_summaries')
    op.drop_index(op.f('ix_qa_chunk_summaries_week_end'), table_name='qa_chunk_summaries')
    op.drop_index(op.f('ix_qa_chunk_summaries_user_id'), table_name='qa_chunk_summaries')
    op.drop_index(op.f('ix_qa_chunk_summaries_scope'), table_name='qa_chunk_summaries')
    op.drop_index(op.f('ix_qa_chunk_summaries_project_id'), table_name='qa_chunk_summaries')
    op.drop_index(op.f('ix_qa_chunk_summaries_algo_version'), table_name='qa_chunk_summaries')
    op.drop_table('qa_chunk_summaries')
