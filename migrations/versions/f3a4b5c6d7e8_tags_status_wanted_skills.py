"""Tags, post status, and wanted-skills (user↔category)

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7

"""
from alembic import op
import sqlalchemy as sa

revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    # Tag lookup table
    op.create_table(
        'tag',
        sa.Column('id',    sa.Integer(),    nullable=False),
        sa.Column('slug',  sa.String(50),   nullable=False),
        sa.Column('label', sa.String(80),   nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    # post <-> tag many-to-many
    op.create_table(
        'post_tags',
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('tag_id',  sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['post.id']),
        sa.ForeignKeyConstraint(['tag_id'],  ['tag.id']),
        sa.PrimaryKeyConstraint('post_id', 'tag_id'),
    )

    # user <-> category many-to-many (wanted skills)
    op.create_table(
        'user_wanted_categories',
        sa.Column('user_id',     sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'],     ['user.id']),
        sa.ForeignKeyConstraint(['category_id'], ['category.id']),
        sa.PrimaryKeyConstraint('user_id', 'category_id'),
    )

    # Add lifecycle status to post
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('status', sa.String(20), nullable=False, server_default='open')
        )


def downgrade():
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_column('status')
    op.drop_table('user_wanted_categories')
    op.drop_table('post_tags')
    op.drop_table('tag')
