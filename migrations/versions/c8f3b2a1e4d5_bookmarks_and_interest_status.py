"""Bookmarks and interest exchange status

Revision ID: c8f3b2a1e4d5
Revises: b7e2a1c0d9f3

"""
from alembic import op
import sqlalchemy as sa

revision = 'c8f3b2a1e4d5'
down_revision = 'b7e2a1c0d9f3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('interest', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending')
        )
    op.create_table(
        'bookmark',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['post.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'post_id', name='uq_bookmark_user_post'),
    )


def downgrade():
    op.drop_table('bookmark')
    with op.batch_alter_table('interest', schema=None) as batch_op:
        batch_op.drop_column('status')
