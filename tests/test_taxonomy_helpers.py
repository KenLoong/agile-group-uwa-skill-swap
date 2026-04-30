# =============================================================================
# Unit tests — api/taxonomy_helpers (pure string / status predicates)
# =============================================================================
from __future__ import annotations

import unittest

from api import taxonomy_helpers as th


class TestNormalizeTagSlug(unittest.TestCase):
    def test_lowercase_and_hyphen(self) -> None:
        self.assertEqual(th.normalize_tag_slug("  Hello   World "), "hello-world")

    def test_strips_unsafe_chars(self) -> None:
        self.assertEqual(th.normalize_tag_slug("café!?"), "caf")

    def test_empty_and_non_string(self) -> None:
        self.assertEqual(th.normalize_tag_slug(""), "")
        self.assertEqual(th.normalize_tag_slug("   "), "")
        self.assertEqual(th.normalize_tag_slug(None), "")  # type: ignore[arg-type]

    def test_max_len_truncates(self) -> None:
        long = "a" * 100
        self.assertEqual(len(th.normalize_tag_slug(long, max_len=12)), 12)

    def test_collapses_hyphen_runs(self) -> None:
        self.assertEqual(th.normalize_tag_slug("a---b"), "a-b")

    def test_category_slug_matches_tag_rules_but_shorter(self) -> None:
        raw = "  Creative Arts  Studio "
        self.assertEqual(th.normalize_category_slug(raw), "creative-arts-studio")
        self.assertLessEqual(len(th.normalize_category_slug(raw, max_len=12)), 12)


class TestDisplayHelpers(unittest.TestCase):
    def test_display_prefers_label(self) -> None:
        self.assertEqual(th.display_label_or_slug("  Python  ", "python"), "Python")

    def test_display_falls_back_to_slug(self) -> None:
        self.assertEqual(th.display_label_or_slug("", "python"), "python")


class TestStatusHelpers(unittest.TestCase):
    def test_explain_returns_three_ordered_pairs(self) -> None:
        rows = th.explain_post_status_choices()
        self.assertEqual(len(rows), 3)
        keys = {r[0] for r in rows}
        self.assertEqual(keys, {"open", "matched", "closed"})

    def test_is_allowed_matches_case_insensitive(self) -> None:
        self.assertTrue(th.is_allowed_post_status("OPEN"))
        self.assertTrue(th.is_allowed_post_status("  closed  "))
        self.assertFalse(th.is_allowed_post_status("idle"))
        self.assertFalse(th.is_allowed_post_status(404))


if __name__ == "__main__":
    unittest.main()
