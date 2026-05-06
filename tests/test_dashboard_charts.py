# =============================================================================
# GET /api/dashboard/charts — authenticated personal chart JSON
# =============================================================================
# Run:
#   PYTHONPATH=. python -m unittest tests.test_dashboard_charts -v
# =============================================================================
from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timedelta, timezone

from api.app_factory import create_app
from api.tags_models import Category, Interest, Post, User, db
from services.stats_service import dashboard_charts_payload
from sqlalchemy import select


class TestDashboardChartsAuth(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_charts_401_without_identity(self) -> None:
        r = self.client.get("/api/dashboard/charts")
        self.assertEqual(r.status_code, 401)


class TestDashboardChartsPayload(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_charts_200_and_shape(self) -> None:
        with self.app.app_context():
            db.session.add(User(id=1, email="o1@uwa.edu.au", username="owner1"))
            cid = int(
                db.session.scalar(select(Category.id).where(Category.slug == "coding")) or 0
            )
            db.session.add(
                Post(
                    title="mine",
                    description="d",
                    owner_id=1,
                    category_id=cid,
                    like_count=3,
                )
            )
            db.session.commit()

        r = self.client.get("/api/dashboard/charts", headers={"X-User-Id": "1"})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertIn("category_distribution", data)
        self.assertIn("daily_activity", data)
        self.assertEqual(len(data["daily_activity"]), 30)
        self.assertTrue(any(x["label"] == "Coding" for x in data["category_distribution"]))
        self.assertTrue(all("likes" in d and "interests" in d for d in data["daily_activity"]))

    def test_interests_bucketed_by_utc_date(self) -> None:
        fixed_end = date(2026, 5, 15)
        window_start = fixed_end - timedelta(days=29)

        with self.app.app_context():
            db.session.add(User(id=10, email="a@uwa.edu.au", username="a10"))
            db.session.add(User(id=11, email="b@uwa.edu.au", username="b11"))
            cid = int(db.session.scalar(select(Category.id).where(Category.slug == "music")) or 0)
            p = Post(title="p", description="d", owner_id=10, category_id=cid)
            db.session.add(p)
            db.session.flush()
            day_in_window = window_start + timedelta(days=5)
            ts = datetime(
                day_in_window.year,
                day_in_window.month,
                day_in_window.day,
                12,
                0,
                0,
                tzinfo=timezone.utc,
            )
            db.session.add(
                Interest(
                    sender_id=11,
                    post_id=p.id,
                    timestamp=ts.replace(tzinfo=None),
                )
            )
            db.session.commit()

        with self.app.app_context():
            payload = dashboard_charts_payload(10, end_day=fixed_end)

        key = day_in_window.isoformat()
        bucket = next(d for d in payload["daily_activity"] if d["date"] == key)
        self.assertEqual(bucket["interests"], 1)
        self.assertEqual(bucket["likes"], 0)


if __name__ == "__main__":
    unittest.main()
