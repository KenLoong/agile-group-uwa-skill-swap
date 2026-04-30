# =============================================================================
# Tests — taxonomy bootstrap and category lookups (_posts & discovery baseline)
# =============================================================================
from __future__ import annotations

import unittest

from api.app_factory import create_app
from api.tags_models import (
    CATEGORY_SLUG_GENERAL,
    Category,
    Post,
    User,
    category_id_for_slug,
    db,
)
from sqlalchemy import select


class TestBootstrapAndCategoryLookup(unittest.TestCase):
    """Exercises ``ensure_default_taxonomy`` (via factory) plus ``category_id_for_slug``."""

    def test_general_slug_resolves_after_app_factory(self) -> None:
        app = create_app(testing=True)
        with app.app_context():
            cid = category_id_for_slug(CATEGORY_SLUG_GENERAL)
            self.assertIsInstance(cid, int)
            slug = db.session.scalar(
                select(Category.slug).where(Category.id == cid)
            )
            self.assertEqual(slug, CATEGORY_SLUG_GENERAL)

    def test_unknown_slug_returns_none(self) -> None:
        app = create_app(testing=True)
        with app.app_context():
            self.assertIsNone(category_id_for_slug("no-category-with-this-slug-xyz"))

    def test_model_repr_readable(self) -> None:
        app = create_app(testing=True)
        with app.app_context():
            cat = db.session.scalar(
                select(Category).where(Category.slug == CATEGORY_SLUG_GENERAL)
            )
            self.assertIn("general", repr(cat))

            user = User(id=9001, email="x@test")
            cid = category_id_for_slug(CATEGORY_SLUG_GENERAL)
            assert cid is not None
            post = Post(
                title="t",
                description="",
                category_id=int(cid),
                owner_id=user.id,
            )
            db.session.add_all([user, post])
            db.session.flush()
            self.assertIn("Post id=", repr(post))


if __name__ == "__main__":
    unittest.main()
