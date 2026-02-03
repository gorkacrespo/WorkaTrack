"""merge heads

Revision ID: 4bfb9151df65
Revises: 9a3fec23140b, acb4b2d8385e
Create Date: 2026-02-03 11:28:40.111616

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4bfb9151df65'
down_revision = ('9a3fec23140b', 'acb4b2d8385e')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
