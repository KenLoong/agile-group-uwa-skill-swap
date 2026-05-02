# =============================================================================
# Unit tests — api.discover_ordering (deterministic ORDER BY helpers)
# =============================================================================
# Validates the standalone ordering module used by GET /api/filter (Issue #5).
# Heavy behaviour remains in tests/test_discover_filter.py (integration).
# =============================================================================
from __future__ import annotations

import unittest

from api.discover_ordering import (
    likes_order_columns,
    newest_order_columns,
    ordering_spec_human_readable,
    popular_order_columns,
)


class TestDiscoverOrderingModule(unittest.TestCase):
    """Lightweight assertions on tuples + spec helper (no Flask app boot)."""

    def test_every_mode_has_terminal_id_tiebreak_in_docs(self):
        """Human-readable chains end with explicit id wording for likes/popular/newest."""
        spec = ordering_spec_human_readable()
        self.assertEqual(set(spec.keys()), {"likes", "newest", "popular"})
        for mode, clauses in spec.items():
            self.assertGreaterEqual(len(clauses), 2, mode)
            self.assertTrue(
                any("(tie-break)" in c or "tie-break" in c for c in clauses),
                f"{mode} missing id tie-break string: {clauses}",
            )

    def test_column_tuple_arity_matches_documented_modes(self):
        self.assertEqual(len(tuple(newest_order_columns())), 2)
        self.assertEqual(len(tuple(likes_order_columns())), 3)
        self.assertEqual(len(tuple(popular_order_columns())), 3)


if __name__ == "__main__":
    unittest.main()
