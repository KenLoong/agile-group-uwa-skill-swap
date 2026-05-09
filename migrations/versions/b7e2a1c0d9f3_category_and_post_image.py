"""Category table and optional post cover image

Revision ID: b7e2a1c0d9f3
Revises: 4ff919df183e
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'b7e2a1c0d9f3'
down_revision = '4ff919df183e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=40), nullable=False),
        sa.Column('label', sa.String(length=80), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    cat = sa.table(
        'category',
        sa.column('slug', sa.String),
        sa.column('label', sa.String),
        sa.column('sort_order', sa.Integer),
    )
    op.bulk_insert(
        cat,
        [
            {'slug': 'coding', 'label': 'Coding / IT', 'sort_order': 10},
            {'slug': 'language', 'label': 'Languages', 'sort_order': 20},
            {'slug': 'music', 'label': 'Music / Arts', 'sort_order': 30},
            {'slug': 'sports', 'label': 'Sports / Fitness', 'sort_order': 40},
            {'slug': 'other', 'label': 'Other', 'sort_order': 50},
        ],
    )

    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('image_filename', sa.String(length=120), nullable=True))
        batch_op.create_foreign_key('fk_post_category_id', 'category', ['category_id'], ['id'])

    op.add_column('user', sa.Column('avatar_filename', sa.String(length=120), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE post SET category_id = (
                SELECT id FROM category WHERE slug = CASE post.category
                    WHEN 'Coding' THEN 'coding'
                    WHEN 'Music' THEN 'music'
                    WHEN 'Language' THEN 'language'
                    WHEN 'Sports' THEN 'sports'
                    ELSE 'other'
                END
            )
            """
        )
    )

    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.alter_column('category_id', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column('category')


def downgrade():
    raise NotImplementedError(
        'Downgrade from Category/images is not supported; restore database.db from backup if needed.'
    )
