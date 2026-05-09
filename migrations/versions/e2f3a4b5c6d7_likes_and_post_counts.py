"""Post likes and denormalized comment/like counts

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6

"""
from alembic import op
import sqlalchemy as sa

revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'post_like',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['post.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'post_id', name='uq_post_like_user_post'),
    )
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE post SET comment_count = (
                SELECT COUNT(*) FROM comment WHERE comment.post_id = post.id
            )
            """
        )
    )


def downgrade():
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_column('like_count')
        batch_op.drop_column('comment_count')
    op.drop_table('post_like')
