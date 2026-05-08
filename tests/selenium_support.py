# =============================================================================
# Selenium helpers — seeded demo data + optional in-process werkzeug server
# =============================================================================
from __future__ import annotations

import os
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from sqlalchemy import select
from werkzeug.serving import make_server

from api.tags_models import POST_STATUS_OPEN, Category, Post, Tag, User, db

SEED_LANGUAGE_TITLE = "Language Post Demo"
SEED_CODING_TITLE = "Coding Post Demo"
SEED_TAGGED_TITLE = "Tagged E2E Post"


def seed_selenium_demo_posts() -> int:
    """
    Insert predictable posts after categories exist (matches discover slugs).

    Returns the numeric id of ``SEED_TAGGED_TITLE`` for detail-page tests.
    """
    cid_lang = db.session.scalar(select(Category.id).where(Category.slug == "languages"))
    cid_code = db.session.scalar(select(Category.id).where(Category.slug == "coding"))
    if cid_lang is None or cid_code is None:
        raise RuntimeError("Seed categories coding/languages missing; bootstrap categories first.")

    owner = db.session.scalar(select(User).where(User.username == "selenium_seed_fixture"))
    if owner is None:
        owner = User(
            email="selenium_fixture@student.uwa.edu.au",
            username="selenium_seed_fixture",
        )
        db.session.add(owner)
        db.session.flush()

    def _ensure_post(title: str, category_id: int) -> Post:
        existing = db.session.scalar(select(Post).where(Post.title == title))
        if existing is not None:
            return existing
        row = Post(
            title=title,
            description=f"Demo copy for `{title}` (Selenium harness).",
            category_id=int(category_id),
            owner_id=int(owner.id),
            status=POST_STATUS_OPEN,
            comment_count=0,
            like_count=0,
        )
        db.session.add(row)
        db.session.flush()
        return row

    _ensure_post(SEED_LANGUAGE_TITLE, int(cid_lang))
    _ensure_post(SEED_CODING_TITLE, int(cid_code))

    tagged = _ensure_post(SEED_TAGGED_TITLE, int(cid_code))
    for slug, label in (("python", "python"), ("selenium", "selenium")):
        tag_row = db.session.scalar(select(Tag).where(Tag.slug == slug))
        if tag_row is None:
            tag_row = Tag(slug=slug, label=label[:80])
            db.session.add(tag_row)
            db.session.flush()
        if tag_row not in tagged.tags:
            tagged.tags.append(tag_row)

    db.session.commit()
    pid = db.session.scalar(select(Post.id).where(Post.title == SEED_TAGGED_TITLE))
    if pid is None:
        raise RuntimeError("Tagged seed post missing after commit.")
    return int(pid)


def spawn_bound_port() -> int:
    """Ephemeral localhost port for werkzeug.make_server."""
    import socket as _sock

    s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def wait_http_ok(base: str, path: str, *, attempts: int = 60, delay_s: float = 0.05) -> None:
    url = f"{base.rstrip('/')}{path}"
    last: BaseException | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=2.0):
                return
        except OSError as exc:
            last = exc
            time.sleep(delay_s)
    raise RuntimeError(f"Live server never became reachable at {url!r}") from last


class LiveServerContext:
    """Owns tempfile DB path + werkzeug server thread."""

    __slots__ = ("_httpd", "_thread", "_db_path", "_base")

    def __init__(self) -> None:
        self._httpd = None  # type: ignore[assignment]
        self._thread: threading.Thread | None = None
        fd, raw = tempfile.mkstemp(prefix="selenium_", suffix=".db")
        os.close(fd)
        self._db_path = Path(raw)
        self._base = ""

    @property
    def db_uri(self) -> str:
        return f"sqlite:///{self._db_path.resolve()}"

    @property
    def base_url(self) -> str:
        return self._base

    def start(self, flask_app):
        """Bind werkzeug threaded server to the configured Flask ``app`` instance."""
        from flask import Flask

        if not isinstance(flask_app, Flask):
            raise TypeError("start() expects the Flask application instance.")

        port = spawn_bound_port()
        self._httpd = make_server("127.0.0.1", port, flask_app, threaded=True)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self._base = f"http://127.0.0.1:{port}"

        wait_http_ok(self._base, "/discover")
        wait_http_ok(self._base, "/api/filter?category=all")

    def shutdown(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        try:
            self._db_path.unlink(missing_ok=True)
        except OSError:
            pass


def start_live_discover_demo():
    """Create app on file-backed SQLite, seed, return (base_url, tagged_post_id, ctx)."""
    from app import create_app

    ctx = LiveServerContext()
    app = create_app(
        testing=True,
        test_config={"SQLALCHEMY_DATABASE_URI": ctx.db_uri},
    )
    with app.app_context():
        tagged_post_id = seed_selenium_demo_posts()
    ctx.start(app)
    return ctx.base_url, tagged_post_id, ctx
