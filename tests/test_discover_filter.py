# =============================================================================
# Tests — GET /api/filter (discover JSON contract + filters + pagination)
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta

from api.app_factory import create_app
from api.tags_models import Category, Interest, Post, Tag, User, db
from sqlalchemy import select

_TS0 = datetime(2026, 3, 1, 12, 0, 0)


@contextmanager
def _session(app):
    with app.app_context():
        try:
            yield db.session
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            raise


class TestDiscoverFilterApi(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_empty_database_returns_contract_keys(self) -> None:
        r = self.client.get("/api/filter")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertEqual(
            sorted(data.keys()),
            ["has_next", "has_prev", "page", "pages", "posts", "total"],
        )
        self.assertEqual(data["posts"], [])
        self.assertEqual(data["pages"], 0)
        self.assertEqual(data["total"], 0)

    def test_category_filter_and_unknown_slug_empty(self) -> None:
        self._seed_two_posts_two_categories()

        coding = json.loads(self.client.get("/api/filter?category=coding").get_data(as_text=True))
        self.assertEqual(len(coding["posts"]), 1)
        self.assertEqual(coding["posts"][0]["category_slug"], "coding")

        music = json.loads(self.client.get("/api/filter?category=music").get_data(as_text=True))
        self.assertEqual(len(music["posts"]), 1)

        bogus = json.loads(self.client.get("/api/filter?category=missing-slug").get_data(as_text=True))
        self.assertEqual(bogus["posts"], [])
        self.assertEqual(bogus["pages"], 0)
        self.assertEqual(bogus["page"], 1)
        self.assertEqual(bogus["total"], 0)

    def test_explicit_empty_query_clears_stale_parallel_q_when_category_active(self) -> None:
        """?q= alongside blank query must not keep the q filter once query is emptied."""
        with _session(self.app) as s:
            ux = User(id=902, email="nine02@student.uwa.edu.au", username="nine02")
            s.add(ux)
            cid = s.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None
            ts = datetime(2026, 11, 1, 12, 0, 0)
            s.add(
                Post(
                    title="Broad lesson",
                    description="no token",
                    category_id=int(cid),
                    owner_id=902,
                    timestamp=ts,
                )
            )
            s.add(
                Post(
                    title="Zeta UNIQUEQTOKEN narrow",
                    description="has token",
                    category_id=int(cid),
                    owner_id=902,
                    timestamp=ts + timedelta(hours=1),
                )
            )

        narrow_only = json.loads(
            self.client.get(
                "/api/filter?category=coding&q=UNIQUEQTOKEN"
            ).get_data(as_text=True)
        )
        self.assertEqual(narrow_only["total"], 1)
        titles_narrow = [p["title"] for p in narrow_only["posts"]]
        self.assertEqual(titles_narrow, ["Zeta UNIQUEQTOKEN narrow"])

        cleared_via_query = json.loads(
            self.client.get(
                "/api/filter?category=coding&q=UNIQUEQTOKEN&query="
            ).get_data(as_text=True)
        )
        self.assertEqual(cleared_via_query["total"], 2)
        self.assertEqual(len(cleared_via_query["posts"]), 2)

    def test_tag_filter(self) -> None:
        self._seed_tagged_fixture()
        out = json.loads(self.client.get("/api/filter?tag=python").get_data(as_text=True))
        titles = sorted(p["title"] for p in out["posts"])
        self.assertEqual(titles, ["Alpha py", "Gamma py"])

    def test_query_matches_title_or_description(self) -> None:
        self._seed_tagged_fixture()
        q = json.loads(self.client.get("/api/filter?query=UNIQUE-SNIPPET-XYZ").get_data(as_text=True))
        self.assertEqual(len(q["posts"]), 1)
        self.assertEqual(q["posts"][0]["title"], "Beta other")

    def test_sort_likes_orders_desc_then_timestamp(self) -> None:
        with _session(self.app) as s:
            u = User(id=1, email="a@student.uwa.edu.au", username="poster")
            s.add(u)
            cid = s.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None
            ts = datetime(2026, 4, 1, 8, 0, 0)
            p_newer = Post(
                title="High likes newer",
                description="newer row",
                category_id=int(cid),
                owner_id=1,
                like_count=5,
                timestamp=ts + timedelta(hours=1),
            )
            p_older = Post(
                title="High likes older",
                description="older row",
                category_id=int(cid),
                owner_id=1,
                like_count=5,
                timestamp=ts,
            )
            s.add_all([p_newer, p_older])

        data = json.loads(self.client.get("/api/filter?sort=likes&category=coding").get_data(as_text=True))
        titles = [p["title"] for p in data["posts"] if p["title"].startswith("High likes")]
        self.assertEqual(titles, ["High likes newer", "High likes older"])

    def test_sort_likes_same_score_and_same_timestamp_orders_by_id_desc(self) -> None:
        """Tie on like_count + timestamp must not yield undefined order across DBs/pages."""
        with _session(self.app) as s:
            ux = User(id=701, email="tie702@student.uwa.edu.au", username="tie702")
            s.add(ux)
            cid = s.scalar(select(Category.id).where(Category.slug == "languages"))
            assert cid is not None
            ts = datetime(2026, 8, 1, 15, 0, 0)
            for suffix in ("low", "mid", "high"):
                s.add(
                    Post(
                        title=f"TIE-ID-{suffix}",
                        description="same stats",
                        category_id=int(cid),
                        owner_id=701,
                        like_count=11,
                        timestamp=ts,
                    )
                )

        data = json.loads(
            self.client.get("/api/filter?sort=likes&category=languages").get_data(as_text=True)
        )
        tie_titles = [p["title"] for p in data["posts"] if p["title"].startswith("TIE-ID-")]
        self.assertEqual(len(tie_titles), 3)
        ids = [
            next(int(p["id"]) for p in data["posts"] if p["title"] == t) for t in tie_titles
        ]
        self.assertEqual(ids, sorted(ids, reverse=True), "Higher post id must rank first when counts and timestamps match")

    def test_sort_popular_by_interest_count(self) -> None:
        with _session(self.app) as s:
            ua = User(id=10, email="a10@student.uwa.edu.au", username="poster10")
            ub = User(id=11, email="b11@student.uwa.edu.au", username="u11")
            uc = User(id=12, email="c12@student.uwa.edu.au", username="u12")
            ud = User(id=13, email="d13@student.uwa.edu.au", username="u13")
            s.add_all([ua, ub, uc, ud])
            cid = s.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None

            ts = datetime(2026, 5, 1, 12, 0, 0)
            p_hot = Post(
                title="Hot interest",
                description="many interests",
                category_id=int(cid),
                owner_id=10,
                timestamp=ts,
            )
            p_cool = Post(
                title="Cool interest",
                description="few",
                category_id=int(cid),
                owner_id=10,
                timestamp=ts + timedelta(days=1),
            )
            s.add_all([p_hot, p_cool])
            s.flush()

            for uid in (11, 12, 13):
                s.add(Interest(sender_id=uid, post_id=p_hot.id))
            s.add(Interest(sender_id=11, post_id=p_cool.id))

        data = json.loads(self.client.get("/api/filter?sort=popular&category=coding").get_data(as_text=True))
        top = [p["title"] for p in data["posts"] if p["title"].endswith("interest")]
        self.assertEqual(top[0], "Hot interest")

    def test_sort_popular_equal_interests_same_timestamp_orders_by_id_desc(self) -> None:
        """Equal Interest counts + same timestamp rely on Post.id descending."""
        with _session(self.app) as s:
            ua = User(id=820, email="o820@student.uwa.edu.au", username="o820")
            for idx, uid in enumerate((821, 822, 823, 824), start=1):
                s.add(User(id=uid, email=f"u{idx}81@student.uwa.edu.au", username=f"i{uid}"))
            s.add(ua)
            cid = s.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None
            ts = datetime(2026, 10, 1, 14, 0, 0)
            p_early = Post(
                title="POP-EARLY",
                description="popular tie",
                category_id=int(cid),
                owner_id=820,
                timestamp=ts,
            )
            p_late = Post(
                title="POP-LATE",
                description="popular tie",
                category_id=int(cid),
                owner_id=820,
                timestamp=ts,
            )
            s.add_all([p_early, p_late])
            s.flush()
            # Two interests each so COUNT ties before timestamp/id keys apply.
            s.add_all(
                [
                    Interest(sender_id=821, post_id=p_early.id),
                    Interest(sender_id=822, post_id=p_early.id),
                    Interest(sender_id=823, post_id=p_late.id),
                    Interest(sender_id=824, post_id=p_late.id),
                ]
            )

        data = json.loads(self.client.get("/api/filter?sort=popular&category=coding").get_data(as_text=True))
        pop = [p["title"] for p in data["posts"] if p["title"].startswith("POP-")]
        self.assertGreaterEqual(len(pop), 2)
        self.assertEqual(pop[0], "POP-LATE", "Higher id wins when Interest counts and timestamps match")

    def test_invalid_sort_falls_back_newest(self) -> None:
        with _session(self.app) as s:
            u = User(id=20, email="x@student.uwa.edu.au", username="zzz")
            s.add(u)
            cid = s.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None

            ta = datetime(2026, 6, 1, 12, 0, 0)
            s.add(
                Post(
                    title="Old post",
                    description="past",
                    category_id=int(cid),
                    owner_id=20,
                    timestamp=ta,
                )
            )
            s.add(
                Post(
                    title="Brand new post",
                    description="later",
                    category_id=int(cid),
                    owner_id=20,
                    timestamp=ta + timedelta(days=30),
                )
            )

        data = json.loads(self.client.get("/api/filter?sort=wacky-unknown").get_data(as_text=True))
        titles = [p["title"] for p in data["posts"][:2]]
        self.assertEqual(titles[0], "Brand new post")

    def test_sort_newest_same_timestamp_orders_by_id_desc(self) -> None:
        with _session(self.app) as s:
            ux = User(id=800, email="n800@student.uwa.edu.au", username="n800")
            s.add(ux)
            cid = s.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None
            ts = datetime(2026, 9, 1, 11, 0, 0)
            for suf in ("a", "b", "c"):
                s.add(
                    Post(
                        title=f"NEWEST-TIE-{suf}",
                        description="collision",
                        category_id=int(cid),
                        owner_id=800,
                        timestamp=ts,
                    )
                )

        data = json.loads(self.client.get("/api/filter?sort=newest&category=coding").get_data(as_text=True))
        bloc = [p["title"] for p in data["posts"] if p["title"].startswith("NEWEST-TIE-")]
        self.assertEqual(len(bloc), 3)
        ids = [next(int(p["id"]) for p in data["posts"] if p["title"] == t) for t in bloc]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_pagination_nine_per_page(self) -> None:
        with _session(self.app) as s:
            owner = User(id=30, email="bulk@student.uwa.edu.au", username="bulk")
            s.add(owner)
            cid = s.scalar(select(Category.id).where(Category.slug == "languages"))
            assert cid is not None

            ts = datetime(2026, 7, 1, 12, 0, 0)
            for idx in range(10):
                s.add(
                    Post(
                        title=f"Lesson {idx}",
                        description=str(idx),
                        category_id=int(cid),
                        owner_id=30,
                        timestamp=ts + timedelta(minutes=idx),
                    )
                )

        pg1 = json.loads(self.client.get("/api/filter?category=languages&page=1").get_data(as_text=True))
        self.assertEqual(pg1["page"], 1)
        self.assertEqual(pg1["pages"], 2)
        self.assertTrue(pg1["has_next"])
        self.assertFalse(pg1["has_prev"])
        self.assertEqual(len(pg1["posts"]), 9)

        pg2 = json.loads(self.client.get("/api/filter?category=languages&page=2").get_data(as_text=True))
        self.assertEqual(pg2["page"], 2)
        self.assertEqual(len(pg2["posts"]), 1)
        self.assertFalse(pg2["has_next"])
        self.assertTrue(pg2["has_prev"])
        self.assertEqual(pg1["total"], 10)
        self.assertEqual(pg2["total"], 10)

        far = json.loads(self.client.get("/api/filter?category=languages&page=999").get_data(as_text=True))
        self.assertEqual(far["pages"], 2)
        self.assertEqual(far["page"], 2)
        self.assertEqual(far["total"], 10)
        self.assertEqual(len(far["posts"]), 1)

    def test_card_payload_fields(self) -> None:
        with _session(self.app) as s:
            ux = User(id=40, email="carl@student.uwa.edu.au", username="carl")
            s.add(ux)
            cid = s.scalar(select(Category.id).where(Category.slug == "sports"))
            assert cid is not None
            s.add(
                Post(
                    title="Ball skills",
                    description="Line one.\nSecond line continuation for snippet.",
                    category_id=int(cid),
                    owner_id=40,
                    like_count=0,
                    image_filename=None,
                    timestamp=_TS0,
                )
            )
            s.add(
                Post(
                    title="With jpeg",
                    description="tiny",
                    category_id=int(cid),
                    owner_id=40,
                    image_filename="demo.jpg",
                    image_alt="Cover of practice session",
                    timestamp=_TS0 + timedelta(days=1),
                )
            )

        data = json.loads(self.client.get("/api/filter?category=sports").get_data(as_text=True))
        by_title = {p["title"]: p for p in data["posts"]}
        plain = by_title["Ball skills"]
        self.assertLessEqual(len(plain["snippet"]), 121)
        self.assertEqual(plain["author"], "carl")
        self.assertEqual(plain["author_profile"], "/user/carl")
        self.assertIsNone(plain["image_url"])
        self.assertIsNone(plain["image_alt"])
        im = by_title["With jpeg"]
        self.assertIsNotNone(im["image_url"])
        self.assertIn("/static/uploads/posts/demo.jpg", im["image_url"])
        self.assertEqual(im["image_alt"], "Cover of practice session")
        keys = sorted(plain.keys())
        expected = sorted(
            [
                "author",
                "author_profile",
                "category_label",
                "category_slug",
                "comment_count",
                "id",
                "image_alt",
                "image_url",
                "like_count",
                "snippet",
                "status",
                "tags",
                "timestamp",
                "title",
            ]
        )
        self.assertEqual(keys, expected)

    def _seed_two_posts_two_categories(self) -> None:
        with _session(self.app) as s:
            ux = User(id=2, email="w@student.uwa.edu.au", username="dual")
            s.add(ux)
            cid_code = int(s.scalar(select(Category.id).where(Category.slug == "coding")) or 0)
            cid_music = int(s.scalar(select(Category.id).where(Category.slug == "music")) or 0)
            assert cid_code and cid_music
            ts = datetime(2026, 2, 1, 9, 0, 0)
            s.add(
                Post(
                    title="Coding offer",
                    description="Algorithms",
                    category_id=cid_code,
                    owner_id=2,
                    timestamp=ts,
                )
            )
            s.add(
                Post(
                    title="Violin tutoring",
                    description="Bow techniques",
                    category_id=cid_music,
                    timestamp=ts + timedelta(days=1),
                    owner_id=2,
                )
            )

    def _seed_tagged_fixture(self) -> None:
        with _session(self.app) as s:
            u = User(id=3, email="t@student.uwa.edu.au", username="tags_user")
            s.add(u)
            py_t = Tag(slug="python", label="Python")
            js_t = Tag(slug="javascript", label="JavaScript")
            s.add(py_t)
            s.add(js_t)
            cid = s.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None
            ta = datetime(2026, 2, 10, 9, 0, 0)
            p_alpha = Post(
                title="Alpha py",
                description="Uses python tutoring",
                category_id=int(cid),
                owner_id=3,
                timestamp=ta,
            )
            p_alpha.tags.append(py_t)
            p_beta = Post(
                title="Beta other",
                description="UNIQUE-SNIPPET-XYZ in body only",
                category_id=int(cid),
                owner_id=3,
                timestamp=ta + timedelta(hours=1),
            )
            p_beta.tags.append(js_t)
            p_gamma = Post(
                title="Gamma py",
                description="Different copy",
                category_id=int(cid),
                owner_id=3,
                timestamp=ta + timedelta(hours=2),
            )
            p_gamma.tags.append(py_t)
            s.add_all([p_alpha, p_beta, p_gamma])
