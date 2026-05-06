"""Smoke-test the discover preview route (non-Selenium)."""
from __future__ import annotations

import unittest

from app import create_app


class TestDiscoverPreviewRoute(unittest.TestCase):
    def test_discover_renders_grid_shell(self) -> None:
        app = create_app(testing=True)
        with app.test_client() as c:
            r = c.get("/discover")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'id="post-grid"', r.data)


if __name__ == "__main__":
    unittest.main()
