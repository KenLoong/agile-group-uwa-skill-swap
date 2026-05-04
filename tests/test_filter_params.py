# =============================================================================
# Tests — api.filter_params (search alias precedence, no Flask app required)
# =============================================================================
from __future__ import annotations

import unittest

from werkzeug.datastructures import ImmutableMultiDict

from api.filter_params import normalized_search_expression


class _FakeRequest:
    __slots__ = ("args",)

    def __init__(self, mapping: dict[str, str] | list[tuple[str, str]]) -> None:
        self.args = ImmutableMultiDict(mapping)


class TestFilterParams(unittest.TestCase):
    def test_blank_query_key_wins_over_legacy_q(self):
        req = _FakeRequest([("category", "coding"), ("q", "should-not-apply"), ("query", "")])
        self.assertEqual(normalized_search_expression(req), "")

    def test_search_alias_used_when_query_omitted(self):
        req = _FakeRequest([("q", "  hello  ")])
        self.assertEqual(normalized_search_expression(req), "hello")

    def test_q_used_before_search_when_both_present_without_query(self):
        req = _FakeRequest([("search", "beta"), ("q", "alpha")])
        # First among q/search when query absent: q then search in loop
        self.assertEqual(normalized_search_expression(req), "alpha")


if __name__ == "__main__":
    unittest.main()
