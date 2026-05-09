import os
import shutil
import socket
import tempfile
import threading
import time
from contextlib import closing
from pathlib import Path

from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

from app import app
from models import db, User, Post, Interest, Category


TEST_DB_PATH = Path(tempfile.gettempdir()) / 'uwa_skill_swap_test.db'
UPLOAD_TEST_DIR = Path(tempfile.gettempdir()) / 'uwa_skill_swap_test_uploads'


DEFAULT_CATEGORIES = [
    ('coding', 'Coding'),
    ('language', 'Language'),
    ('music', 'Music'),
    ('sports', 'Sports'),
]


_CONFIGURED = False


def configure_app_for_tests():
    global _CONFIGURED
    if _CONFIGURED:
        return

    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{TEST_DB_PATH}",
        MAX_CONTENT_LENGTH=3 * 1024 * 1024,
    )
    UPLOAD_TEST_DIR.mkdir(parents=True, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = str(UPLOAD_TEST_DIR)
    _CONFIGURED = True


def reset_database():
    db.session.remove()
    db.drop_all()
    db.create_all()
    for idx, (slug, label) in enumerate(DEFAULT_CATEGORIES, start=1):
        db.session.add(Category(slug=slug, label=label, sort_order=idx))
    db.session.commit()


def cleanup_test_artifacts():
    with app.app_context():
        db.session.remove()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if UPLOAD_TEST_DIR.exists():
        shutil.rmtree(UPLOAD_TEST_DIR, ignore_errors=True)


def create_user(username, email=None, password='password123'):
    email = email or f'{username}@student.uwa.edu.au'
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()
    return user


def get_category(slug='coding'):
    category = Category.query.filter_by(slug=slug).first()
    if category is None:
        category = Category(slug=slug, label=slug.title(), sort_order=99)
        db.session.add(category)
        db.session.commit()
    return category


def create_post(author, title='Python tutoring', description='I can teach Python basics.', category_slug='coding'):
    category = get_category(category_slug)
    post = Post(
        title=title,
        description=description,
        user_id=author.id,
        category_id=category.id,
    )
    db.session.add(post)
    db.session.commit()
    return post


def create_interest(sender, post):
    interest = Interest(sender_id=sender.id, post_id=post.id)
    db.session.add(interest)
    db.session.commit()
    return interest


def login(client, email, password='password123', follow_redirects=True):
    return client.post(
        '/login',
        data={
            'email': email,
            'password': password,
            'submit': 'Login',
        },
        follow_redirects=follow_redirects,
    )


class LiveServerThread(threading.Thread):
    def __init__(self, flask_app):
        super().__init__(daemon=True)
        self.flask_app = flask_app
        self.server = make_server('127.0.0.1', 0, flask_app)
        self.port = self.server.server_port
        self.ctx = flask_app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.ctx.pop()


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for_server(base_url, timeout=5.0):
    import urllib.request

    deadline = time.time() + timeout
    last_exc = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base_url) as resp:
                if resp.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - best effort startup wait
            last_exc = exc
            time.sleep(0.1)
    raise RuntimeError(f'Live test server did not start in time: {last_exc}')
