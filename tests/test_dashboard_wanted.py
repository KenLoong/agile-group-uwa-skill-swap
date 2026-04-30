# =============================================================================
# Smoke tests — dashboard wanted categories (GET/POST /api/dashboard/wanted)
# =============================================================================
from __future__ import annotations

import json
import unittest

from api.app_factory import create_app
from api.tags_models import Category, User, db


class TestDashboardWantedApi(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_get_wanted_requires_identity(self) -> None:
        r = self.client.get("/api/dashboard/wanted")
        self.assertEqual(r.status_code, 401)

    def test_post_round_trip_with_x_user_id(self) -> None:
        with self.app.app_context():
            u = User(id=1, email="a@student.uwa.edu.au")
            db.session.add(u)
            db.session.commit()
            cid = Category.query.filter_by(slug="coding").first()
            assert cid is not None

        hdr = {"X-User-Id": "1"}
        r0 = self.client.get("/api/dashboard/wanted", headers=hdr)
        self.assertEqual(r0.status_code, 200)
        data0 = json.loads(r0.get_data(as_text=True))
        self.assertIn("wanted_ids", data0)
        self.assertEqual(data0["wanted_ids"], [])

        r1 = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [cid.id]}),
            content_type="application/json",
            headers=hdr,
        )
        self.assertEqual(r1.status_code, 200)
        self.assertTrue(json.loads(r1.get_data(as_text=True)).get("ok"))

        r2 = self.client.get("/api/dashboard/wanted", headers=hdr)
        ids = json.loads(r2.get_data(as_text=True))["wanted_ids"]
        self.assertIn(cid.id, ids)


if __name__ == "__main__":
    unittest.main()
