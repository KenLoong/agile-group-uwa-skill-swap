"""Add notification table for @mention feature

Revision ID: g4b5c6d7e8f9
Revises: f3a4b5c6d7e8

"""
from alembic import op
import sqlalchemy as sa

revision = 'g4b5c6d7e8f9'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notification',
        sa.Column('id',         sa.Integer(),    nullable=False),
        sa.Column('user_id',    sa.Integer(),    nullable=False),
        sa.Column('actor_id',   sa.Integer(),    nullable=False),
        sa.Column('post_id',    sa.Integer(),    nullable=False),
        sa.Column('comment_id', sa.Integer(),    nullable=True),
        sa.Column('notif_type', sa.String(20),   nullable=False, server_default='mention'),
        sa.Column('read',       sa.Boolean(),    nullable=False, server_default='0'),
        sa.Column('timestamp',  sa.DateTime(),   nullable=True),
        sa.ForeignKeyConstraint(['user_id'],    ['user.id']),
        sa.ForeignKeyConstraint(['actor_id'],   ['user.id']),
        sa.ForeignKeyConstraint(['post_id'],    ['post.id']),
        sa.ForeignKeyConstraint(['comment_id'], ['comment.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_user_id', 'notification', ['user_id'])
    op.create_index('ix_notification_read',    'notification', ['user_id', 'read'])


def downgrade():
    op.drop_index('ix_notification_read',    table_name='notification')
    op.drop_index('ix_notification_user_id', table_name='notification')
    op.drop_table('notification')
