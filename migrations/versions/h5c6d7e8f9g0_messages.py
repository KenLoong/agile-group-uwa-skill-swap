"""Add message table for private messaging

Revision ID: h5c6d7e8f9g0
Revises: g4b5c6d7e8f9

"""
from alembic import op
import sqlalchemy as sa

revision = 'h5c6d7e8f9g0'
down_revision = 'g4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'message',
        sa.Column('id',           sa.Integer(),  nullable=False),
        sa.Column('sender_id',    sa.Integer(),  nullable=False),
        sa.Column('recipient_id', sa.Integer(),  nullable=False),
        sa.Column('content',      sa.Text(),     nullable=False),
        sa.Column('read',         sa.Boolean(),  nullable=False, server_default='0'),
        sa.Column('timestamp',    sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'],    ['user.id']),
        sa.ForeignKeyConstraint(['recipient_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_message_recipient', 'message', ['recipient_id', 'read'])
    op.create_index('ix_message_convo',     'message', ['sender_id', 'recipient_id'])


def downgrade():
    op.drop_index('ix_message_convo',     table_name='message')
    op.drop_index('ix_message_recipient', table_name='message')
    op.drop_table('message')
