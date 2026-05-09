"""Remove interest exchange status column

Revision ID: d1e2f3a4b5c6
Revises: c8f3b2a1e4d5

"""
from alembic import op
import sqlalchemy as sa

revision = 'd1e2f3a4b5c6'
down_revision = 'c8f3b2a1e4d5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('interest', schema=None) as batch_op:
        batch_op.drop_column('status')


def downgrade():
    with op.batch_alter_table('interest', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending')
        )
