import os
import re
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Post, Comment, Interest, Category, Bookmark, PostLike, Tag, Notification, Message, post_tags
from forms import RegistrationForm, LoginForm, PostForm, CommentForm, AccountForm
from uploads_util import save_post_image, delete_post_image, save_avatar_image, delete_avatar_image
from md_format import render_post_markdown, markdown_plain_snippet

load_dotenv()
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-only-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Total request body limit (file uploads)
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024
app.config.setdefault('AVATAR_UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads', 'avatars'))

db.init_app(app)
csrf = CSRFProtect(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


@app.context_processor
def inject_globals():
    """Inject unread notification + message counts into every template."""
    unread_notifs = 0
    unread_msgs   = 0
    if current_user.is_authenticated:
        unread_notifs = Notification.query.filter_by(user_id=current_user.id, read=False).count()
        unread_msgs   = Message.query.filter_by(recipient_id=current_user.id, read=False).count()
    return {
        'unread_notif_count': unread_notifs,
        'unread_msg_count':   unread_msgs,
    }


@app.template_filter('post_markdown')
def post_markdown_filter(text):
    return render_post_markdown(text)


@app.template_filter('render_mentions')
def render_mentions_filter(text):
    """Convert @username in comment text to clickable profile links (HTML-safe)."""
    import markupsafe
    safe = str(markupsafe.escape(text))
    linked = re.sub(
        r'@(\w+)',
        r'<a href="/user/\1" class="mention-link">@\1</a>',
        safe,
    )
    return markupsafe.Markup(linked)


@app.template_filter('markdown_snippet')
def markdown_snippet_filter(text, max_len=120):
    try:
        n = int(max_len)
    except (TypeError, ValueError):
        n = 120
    return markdown_plain_snippet(text, n)


def post_upload_dir():
    return os.path.join(app.root_path, 'static', 'uploads', 'posts')


def avatar_upload_dir():
    return app.config.get('AVATAR_UPLOAD_FOLDER')


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

def fill_post_category_choices(form):
    form.category_id.choices = [
        (c.id, c.label) for c in Category.query.order_by(Category.sort_order, Category.id).all()
    ]


def post_list_base_query(sort):
    if sort == 'popular':
        return (
            Post.query.outerjoin(Interest)
            .group_by(Post.id)
            .order_by(func.count(Interest.id).desc(), Post.timestamp.desc())
        )
    if sort == 'likes':
        return Post.query.order_by(Post.like_count.desc(), Post.timestamp.desc())
    return Post.query.order_by(Post.timestamp.desc())


def post_to_json(p):
    return {
        'id':             p.id,
        'title':          p.title,
        'category_slug':  p.category.slug,
        'category_label': p.category.label,
        'author':         p.author.username,
        'author_profile': url_for('user_profile', username=p.author.username),
        'snippet':        markdown_plain_snippet(p.description, 120),
        'timestamp':      p.timestamp.strftime('%Y-%m-%d'),
        'comment_count':  p.comment_count,
        'like_count':     p.like_count,
        'status':         p.status,
        'tags':           [{'slug': t.slug, 'label': t.label} for t in p.tags],
        'image_url': (
            url_for('static', filename=f'uploads/posts/{p.image_filename}')
            if p.image_filename else None
        ),
    }


def save_post_tags(post, tags_csv):
    """Parse a comma-separated tag string, upsert Tag rows, link to post."""
    post.tags = []
    if not tags_csv or not tags_csv.strip():
        return
    seen = set()
    for raw in tags_csv.split(','):
        raw = raw.strip()
        if not raw:
            continue
        slug = re.sub(r'[^a-z0-9\-]', '', raw.lower().replace(' ', '-'))[:50]
        if not slug or slug in seen:
            continue
        seen.add(slug)
        tag = Tag.query.filter_by(slug=slug).first()
        if not tag:
            tag = Tag(slug=slug, label=raw[:80])
            db.session.add(tag)
        post.tags.append(tag)


def recommended_posts_for_user(user, limit=6):
    """Categories inferred from the user's listings + posts they clicked *Interested* on."""
    if not user.is_authenticated:
        return []
    owned_cats = {
        r[0]
        for r in db.session.query(Post.category_id).filter(Post.user_id == user.id).distinct()
    }
    interest_cats = {
        r[0]
        for r in db.session.query(Post.category_id)
        .join(Interest, Interest.post_id == Post.id)
        .filter(Interest.sender_id == user.id)
        .distinct()
    }
    category_ids = list(owned_cats | interest_cats)
    if not category_ids:
        return []

    interested_post_ids = [
        r[0]
        for r in db.session.query(Interest.post_id).filter(Interest.sender_id == user.id).all()
    ]
    q = Post.query.filter(Post.category_id.in_(category_ids), Post.user_id != user.id)
    if interested_post_ids:
        q = q.filter(~Post.id.in_(interested_post_ids))
    return q.order_by(Post.timestamp.desc()).limit(limit).all()


def find_matches_for_user(user):
    """
    Bidirectional skill-swap matching.

    A match between current_user and other_user exists when:
      - other_user has an open post in a category that current_user *wants to learn*
      - other_user *wants to learn* a category that current_user offers (has open post in)

    Returns a list of dicts:
      { 'user': <User>, 'their_posts': [<Post>, ...] }
    """
    my_offer_cats = {
        r[0] for r in db.session.query(Post.category_id)
        .filter(Post.user_id == user.id, Post.status == 'open').all()
    }
    my_want_cats = {c.id for c in user.wanted_categories}

    if not my_offer_cats or not my_want_cats:
        return []

    # Other users who have open posts in categories I want
    candidate_ids = {
        r[0] for r in db.session.query(Post.user_id)
        .filter(
            Post.category_id.in_(my_want_cats),
            Post.status == 'open',
            Post.user_id != user.id,
        ).all()
    }

    matches = []
    for uid in candidate_ids:
        other = db.session.get(User, uid)
        if not other:
            continue
        other_want_ids = {c.id for c in other.wanted_categories}
        # Only a match if other also wants something I offer
        if not (other_want_ids & my_offer_cats):
            continue
        # Collect their relevant open posts (in cats I want)
        overlap_cats = my_want_cats & {
            r[0] for r in db.session.query(Post.category_id)
            .filter(Post.user_id == uid, Post.status == 'open').all()
        }
        their_posts = Post.query.filter(
            Post.user_id == uid,
            Post.category_id.in_(overlap_cats),
            Post.status == 'open',
        ).all()
        matches.append({'user': other, 'their_posts': their_posts})

    return matches


# ------------------------------------------------------------------
# 1. Authentication routes
# ------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_pw)
        if form.avatar.data:
            try:
                user.avatar_filename = save_avatar_image(form.avatar.data, avatar_upload_dir())
            except ValueError as exc:
                form.avatar.errors.append(str(exc))
                return render_template('register.html', title='Register', form=form)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = AccountForm()
    if form.validate_on_submit():
        if form.remove_avatar.data and current_user.avatar_filename:
            delete_avatar_image(avatar_upload_dir(), current_user.avatar_filename)
            current_user.avatar_filename = None
        if form.avatar.data:
            if current_user.avatar_filename:
                delete_avatar_image(avatar_upload_dir(), current_user.avatar_filename)
            try:
                current_user.avatar_filename = save_avatar_image(form.avatar.data, avatar_upload_dir())
            except ValueError as exc:
                form.avatar.errors.append(str(exc))
                return render_template('account.html', title='Account', form=form)
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('account'))
    return render_template('account.html', title='Account', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


# ------------------------------------------------------------------
# 2. Discovery page, filter API, public user profile
# ------------------------------------------------------------------

@app.route('/')
def index():
    page  = request.args.get('page', 1, type=int)
    sort  = request.args.get('sort', 'newest')
    if sort not in ('newest', 'popular', 'likes'):
        sort = 'newest'
    per_page   = 9
    q          = request.args.get('q', '').strip()
    categories = Category.query.order_by(Category.sort_order, Category.id).all()

    # Popular tags for the tag bar (top 12 by usage)
    popular_tags = (
        Tag.query
        .join(post_tags)
        .group_by(Tag.id)
        .order_by(func.count().desc())
        .limit(12)
        .all()
    )

    query = post_list_base_query(sort)
    if q:
        query = query.filter(Post.title.contains(q) | Post.description.contains(q))
    pagination  = query.paginate(page=page, per_page=per_page, error_out=False)
    recommended = recommended_posts_for_user(current_user, limit=6) if current_user.is_authenticated else []
    return render_template(
        'index.html',
        posts=pagination.items,
        pagination=pagination,
        categories=categories,
        popular_tags=popular_tags,
        sort=sort,
        recommended_posts=recommended,
    )


@app.route('/api/filter')
def filter_posts():
    category_slug = request.args.get('category')
    search_query  = request.args.get('query', '')
    tag_slug      = request.args.get('tag', '')
    sort          = request.args.get('sort', 'newest')
    if sort not in ('newest', 'popular', 'likes'):
        sort = 'newest'
    page     = request.args.get('page', 1, type=int)
    per_page = 9

    query = post_list_base_query(sort)
    if category_slug and category_slug != 'all':
        query = query.join(Category).filter(Category.slug == category_slug)
    if tag_slug:
        query = query.join(post_tags).join(Tag).filter(Tag.slug == tag_slug)
    if search_query:
        query = query.filter(
            Post.title.contains(search_query) | Post.description.contains(search_query)
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'posts':    [post_to_json(p) for p in pagination.items],
        'page':     pagination.page,
        'pages':    pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })


@app.route('/api/tags')
def api_tags():
    """Autocomplete endpoint: returns tags whose slug contains the query."""
    q    = request.args.get('q', '').strip().lower()
    tags = Tag.query.filter(Tag.slug.contains(q)).order_by(Tag.slug).limit(10).all()
    return jsonify([{'slug': t.slug, 'label': t.label} for t in tags])


@app.route('/user/<username>')
def user_profile(username):
    profile_user = User.query.filter_by(username=username).first_or_404()
    posts = (
        Post.query.filter_by(user_id=profile_user.id)
        .order_by(Post.timestamp.desc())
        .all()
    )
    # Extra context for the owner: enable in-page wanted-skill editing
    all_cats   = []
    wanted_ids = set()
    is_owner   = current_user.is_authenticated and current_user.id == profile_user.id
    if is_owner:
        all_cats   = Category.query.order_by(Category.sort_order, Category.id).all()
        wanted_ids = {c.id for c in current_user.wanted_categories}
    return render_template(
        'user_profile.html',
        profile_user=profile_user,
        posts=posts,
        is_owner=is_owner,
        all_cats=all_cats,
        wanted_ids=wanted_ids,
    )


# ------------------------------------------------------------------
# 3. Skill posts (CRUD)
# ------------------------------------------------------------------

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    fill_post_category_choices(form)
    if form.validate_on_submit():
        up_dir = post_upload_dir()
        try:
            image_name = save_post_image(form.image.data, up_dir)
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('create_post.html', title='New Skill', form=form, editing=False, post=None)
        post = Post(
            title=form.title.data,
            description=form.description.data,
            category_id=form.category_id.data,
            user_id=current_user.id,
            image_filename=image_name,
            status=form.status.data,
        )
        db.session.add(post)
        db.session.flush()  # get post.id before commit
        save_post_tags(post, form.tags.data)
        db.session.commit()
        flash('Your skill has been posted!', 'success')
        return redirect(url_for('index'))
    return render_template('create_post.html', title='New Skill', form=form, editing=False, post=None)


@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post            = Post.query.get_or_404(post_id)
    form            = CommentForm()
    interest_count  = Interest.query.filter_by(post_id=post_id).count()
    already_interested = False
    is_saved = False
    liked    = False
    if current_user.is_authenticated:
        already_interested = (
            Interest.query.filter_by(sender_id=current_user.id, post_id=post_id).first()
            is not None
        )
        is_saved = (
            Bookmark.query.filter_by(user_id=current_user.id, post_id=post_id).first()
            is not None
        )
        if post.user_id != current_user.id:
            liked = (
                PostLike.query.filter_by(user_id=current_user.id, post_id=post_id).first()
                is not None
            )
    return render_template(
        'post_detail.html',
        title=post.title,
        post=post,
        form=form,
        interest_count=interest_count,
        already_interested=already_interested,
        is_saved=is_saved,
        liked=liked,
    )


@app.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    fill_post_category_choices(form)
    if form.validate_on_submit():
        up_dir = post_upload_dir()
        if form.remove_image.data:
            delete_post_image(up_dir, post.image_filename)
            post.image_filename = None
        try:
            if form.image.data and getattr(form.image.data, 'filename', None):
                delete_post_image(up_dir, post.image_filename)
                post.image_filename = save_post_image(form.image.data, up_dir)
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('create_post.html', title='Update Skill', form=form, editing=True, post=post)
        post.title       = form.title.data
        post.description = form.description.data
        post.category_id = form.category_id.data
        post.status      = form.status.data
        save_post_tags(post, form.tags.data)
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post_detail', post_id=post.id))
    if request.method == 'GET':
        form.title.data       = post.title
        form.description.data = post.description
        form.category_id.data = post.category_id
        form.status.data      = post.status
        form.tags.data        = ','.join(t.slug for t in post.tags)
    return render_template('create_post.html', title='Update Skill', form=form, editing=True, post=post)


@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    delete_post_image(post_upload_dir(), post.image_filename)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('index'))


@app.route('/post/<int:post_id>/set-status', methods=['POST'])
@login_required
def set_post_status(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        return jsonify({'ok': False}), 403
    data       = request.get_json(silent=True, force=True) or request.form
    new_status = data.get('status')
    if new_status not in ('open', 'matched', 'closed'):
        return jsonify({'ok': False, 'message': 'Invalid status.'}), 400
    post.status = new_status
    db.session.commit()
    return jsonify({'ok': True, 'status': post.status})


# ------------------------------------------------------------------
# 4. Interactions
# ------------------------------------------------------------------

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def post_comment(post_id):
    post       = Post.query.get_or_404(post_id)
    form       = CommentForm()
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, user_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        post.comment_count = (post.comment_count or 0) + 1
        db.session.flush()                               # get comment.id before commit
        parse_mentions(form.content.data, current_user, post, comment.id)
        db.session.commit()
        if wants_json:
            return jsonify({
                'ok':            True,
                'username':      current_user.username,
                'timestamp':     comment.timestamp.strftime('%Y-%m-%d %H:%M'),
                'content':       comment.content,
                'comment_count': post.comment_count,
            })
        flash('Your comment has been added!', 'success')
    else:
        if wants_json:
            msg = form.content.errors[0] if form.content.errors else 'Could not post comment.'
            return jsonify({'ok': False, 'message': msg}), 400
        for err in form.content.errors:
            flash(err, 'danger')
    return redirect(url_for('post_detail', post_id=post_id))


@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_post_like(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id == current_user.id:
        return jsonify({'ok': False, 'message': 'You cannot like your own skill.'}), 400
    existing = PostLike.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        db.session.delete(existing)
        post.like_count = max(0, (post.like_count or 0) - 1)
        db.session.commit()
        return jsonify({'ok': True, 'liked': False, 'like_count': post.like_count})
    db.session.add(PostLike(user_id=current_user.id, post_id=post_id))
    post.like_count = (post.like_count or 0) + 1
    db.session.commit()
    return jsonify({'ok': True, 'liked': True, 'like_count': post.like_count})


@app.route('/interest/<int:post_id>', methods=['POST'])
@login_required
def express_interest(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author == current_user:
        return jsonify({'status': 'error', 'message': 'You cannot request your own skill.'}), 400

    existing = Interest.query.filter_by(sender_id=current_user.id, post_id=post_id).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'Already sent a request.'}), 400

    new_interest = Interest(sender_id=current_user.id, post_id=post_id)
    db.session.add(new_interest)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Request sent successfully!'})


@app.route('/post/<int:post_id>/bookmark', methods=['POST'])
@login_required
def toggle_bookmark(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id == current_user.id:
        return jsonify({'ok': False, 'message': 'You cannot bookmark your own skill.'}), 400
    existing = Bookmark.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'ok': True, 'saved': False})
    db.session.add(Bookmark(user_id=current_user.id, post_id=post_id))
    db.session.commit()
    return jsonify({'ok': True, 'saved': True})


# ------------------------------------------------------------------
# 5. Dashboard
# ------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    my_posts = Post.query.filter_by(user_id=current_user.id).all()

    incoming_interests = (
        Interest.query.join(Post)
        .filter(Post.user_id == current_user.id)
        .order_by(Interest.timestamp.desc())
        .all()
    )
    my_sent_requests = (
        Interest.query.filter_by(sender_id=current_user.id)
        .order_by(Interest.timestamp.desc())
        .all()
    )
    saved = (
        Bookmark.query.filter_by(user_id=current_user.id)
        .order_by(Bookmark.timestamp.desc())
        .all()
    )
    matches       = find_matches_for_user(current_user)
    all_cats      = Category.query.order_by(Category.sort_order, Category.id).all()
    wanted_ids    = {c.id for c in current_user.wanted_categories}
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.timestamp.desc())
        .limit(50)
        .all()
    )
    return render_template(
        'dashboard.html',
        title='Dashboard',
        my_posts=my_posts,
        incoming=incoming_interests,
        sent=my_sent_requests,
        saved=saved,
        matches=matches,
        all_cats=all_cats,
        wanted_ids=wanted_ids,
        notifications=notifications,
    )


@app.route('/dashboard/wanted-skills', methods=['POST'])
@login_required
def save_wanted_skills():
    """AJAX endpoint to persist the user's wanted category list."""
    data    = request.get_json(silent=True, force=True) or {}
    cat_ids = data.get('category_ids', [])
    cats    = Category.query.filter(Category.id.in_(cat_ids)).all()
    current_user.wanted_categories = cats
    db.session.commit()
    return jsonify({'ok': True, 'count': len(cats)})


# ------------------------------------------------------------------
# 6. @mention: user autocomplete + notifications
# ------------------------------------------------------------------

def parse_mentions(text, actor, post, comment_id=None):
    """
    Scan `text` for @username patterns, create Notification records for
    each mentioned user (excluding the actor themselves).
    Must be called inside a db.session context before commit.
    """
    usernames = set(re.findall(r'@(\w+)', text))
    for username in usernames:
        if username.lower() == actor.username.lower():
            continue
        target = User.query.filter_by(username=username).first()
        if target:
            db.session.add(Notification(
                user_id=target.id,
                actor_id=actor.id,
                post_id=post.id,
                comment_id=comment_id,
                notif_type='mention',
            ))


@app.route('/api/users')
def api_users():
    """Username autocomplete for the @mention dropdown (max 8 results)."""
    q     = request.args.get('q', '').strip()
    query = User.query
    if q:
        query = query.filter(User.username.ilike(f'{q}%'))
    users = query.order_by(User.username).limit(8).all()
    return jsonify([{'username': u.username} for u in users])


@app.route('/api/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Mark all of the current user's unread notifications as read."""
    Notification.query.filter_by(user_id=current_user.id, read=False).update({'read': True})
    db.session.commit()
    return jsonify({'ok': True})


# ------------------------------------------------------------------
# 7. Public stats page + data APIs
# ------------------------------------------------------------------

@app.route('/stats')
def stats():
    return render_template('stats.html', title='Platform Stats')


@app.route('/api/stats')
def api_stats():
    """JSON feed for the public stats page (Chart.js)."""
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()

    # --- Category post counts ---
    cat_counts = (
        db.session.query(Category.label, func.count(Post.id).label('cnt'))
        .outerjoin(Post, Post.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.sort_order, Category.id)
        .all()
    )

    # --- 30-day new-post trend (fill zeros for missing days) ---
    thirty_days_ago = datetime.utcnow() - timedelta(days=29)
    raw_daily = (
        db.session.query(
            func.date(Post.timestamp).label('d'),
            func.count(Post.id).label('cnt'),
        )
        .filter(Post.timestamp >= thirty_days_ago)
        .group_by(func.date(Post.timestamp))
        .all()
    )
    daily_map = {str(r.d): r.cnt for r in raw_daily}
    trend_30 = [
        {'date': str(today - timedelta(days=i)), 'count': daily_map.get(str(today - timedelta(days=i)), 0)}
        for i in range(29, -1, -1)
    ]

    # --- Top 5 users (by post count, then total likes) ---
    top_rows = (
        db.session.query(
            User.username,
            func.count(Post.id).label('post_count'),
            func.coalesce(func.sum(Post.like_count), 0).label('total_likes'),
        )
        .join(Post, Post.user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(Post.id).desc(), func.sum(Post.like_count).desc())
        .limit(5)
        .all()
    )

    return jsonify({
        'totals': {
            'posts':    Post.query.count(),
            'users':    User.query.count(),
            'comments': Comment.query.count(),
            'tags':     Tag.query.count(),
        },
        'category_counts': [{'label': r.label, 'count': r.cnt} for r in cat_counts],
        'trend_30':         trend_30,
        'top_users':        [
            {'username': r.username, 'post_count': r.post_count, 'total_likes': int(r.total_likes)}
            for r in top_rows
        ],
    })


@app.route('/api/dashboard/charts')
@login_required
def api_dashboard_charts():
    """JSON feed for the personal dashboard chart tab."""
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    thirty_days_ago = datetime.utcnow() - timedelta(days=29)

    # My category distribution (doughnut chart)
    cat_dist = (
        db.session.query(Category.label, func.count(Post.id).label('cnt'))
        .join(Post, Post.category_id == Category.id)
        .filter(Post.user_id == current_user.id)
        .group_by(Category.id)
        .all()
    )

    # Daily likes + interests on MY posts for last 30 days
    my_post_ids = [
        r[0] for r in db.session.query(Post.id).filter(Post.user_id == current_user.id).all()
    ]

    daily_likes     = {}
    daily_interests = {}

    if my_post_ids:
        for r in (
            db.session.query(
                func.date(PostLike.timestamp).label('d'),
                func.count(PostLike.id).label('cnt'),
            )
            .filter(PostLike.post_id.in_(my_post_ids), PostLike.timestamp >= thirty_days_ago)
            .group_by(func.date(PostLike.timestamp))
            .all()
        ):
            daily_likes[str(r.d)] = r.cnt

        for r in (
            db.session.query(
                func.date(Interest.timestamp).label('d'),
                func.count(Interest.id).label('cnt'),
            )
            .filter(Interest.post_id.in_(my_post_ids), Interest.timestamp >= thirty_days_ago)
            .group_by(func.date(Interest.timestamp))
            .all()
        ):
            daily_interests[str(r.d)] = r.cnt

    daily_activity = [
        {
            'date':      str(today - timedelta(days=i)),
            'likes':     daily_likes.get(str(today - timedelta(days=i)), 0),
            'interests': daily_interests.get(str(today - timedelta(days=i)), 0),
        }
        for i in range(29, -1, -1)
    ]

    return jsonify({
        'category_distribution': [{'label': r.label, 'count': r.cnt} for r in cat_dist],
        'daily_activity':        daily_activity,
    })


# ------------------------------------------------------------------
# 8. Private messaging
# ------------------------------------------------------------------

def _inbox_conversations(user):
    """
    Return a list of dicts, one per unique conversation partner,
    ordered by the most recent message descending.
    Each dict: { partner, last_message, unread_count }
    """
    from sqlalchemy import or_
    all_msgs = (
        Message.query
        .filter(or_(Message.sender_id == user.id, Message.recipient_id == user.id))
        .order_by(Message.timestamp.desc())
        .all()
    )
    seen      = set()
    convos    = []
    for msg in all_msgs:
        pid = msg.recipient_id if msg.sender_id == user.id else msg.sender_id
        if pid in seen:
            continue
        seen.add(pid)
        partner      = db.session.get(User, pid)
        unread_count = Message.query.filter_by(
            sender_id=pid, recipient_id=user.id, read=False
        ).count()
        convos.append({'partner': partner, 'last_message': msg, 'unread_count': unread_count})
    return convos


@app.route('/messages')
@login_required
def messages_inbox():
    convos = _inbox_conversations(current_user)
    return render_template('messages.html', title='Messages', convos=convos)


@app.route('/messages/<username>')
@login_required
def conversation(username):
    from sqlalchemy import or_, and_
    partner = User.query.filter_by(username=username).first_or_404()
    if partner.id == current_user.id:
        return redirect(url_for('messages_inbox'))

    msgs = (
        Message.query
        .filter(or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == partner.id),
            and_(Message.sender_id == partner.id,      Message.recipient_id == current_user.id),
        ))
        .order_by(Message.timestamp)
        .all()
    )
    # Mark received messages as read
    Message.query.filter_by(
        sender_id=partner.id, recipient_id=current_user.id, read=False
    ).update({'read': True})
    db.session.commit()

    last_id = msgs[-1].id if msgs else 0
    return render_template(
        'conversation.html',
        title=f'Chat with {partner.username}',
        partner=partner,
        messages=msgs,
        last_id=last_id,
    )


@app.route('/api/messages/<username>', methods=['POST'])
@login_required
def send_message(username):
    from sqlalchemy import or_, and_
    partner = User.query.filter_by(username=username).first_or_404()
    if partner.id == current_user.id:
        return jsonify({'ok': False, 'message': 'Cannot message yourself.'}), 400

    data    = request.get_json(silent=True, force=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'ok': False, 'message': 'Message cannot be empty.'}), 400
    if len(content) > 2000:
        return jsonify({'ok': False, 'message': 'Message too long (max 2000 chars).'}), 400

    msg = Message(sender_id=current_user.id, recipient_id=partner.id, content=content)
    db.session.add(msg)
    db.session.commit()
    return jsonify({
        'ok':        True,
        'id':        msg.id,
        'content':   msg.content,
        'timestamp': msg.timestamp.strftime('%H:%M'),
        'is_mine':   True,
    })


@app.route('/api/messages/poll/<username>')
@login_required
def poll_messages(username):
    from sqlalchemy import or_, and_
    partner  = User.query.filter_by(username=username).first_or_404()
    after_id = request.args.get('after', 0, type=int)

    msgs = (
        Message.query
        .filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.recipient_id == partner.id),
                and_(Message.sender_id == partner.id,      Message.recipient_id == current_user.id),
            ),
            Message.id > after_id,
        )
        .order_by(Message.timestamp)
        .all()
    )
    # Mark any newly received messages as read
    for m in msgs:
        if m.recipient_id == current_user.id and not m.read:
            m.read = True
    if msgs:
        db.session.commit()

    return jsonify([{
        'id':        m.id,
        'content':   m.content,
        'sender':    m.sender.username,
        'timestamp': m.timestamp.strftime('%H:%M'),
        'is_mine':   m.sender_id == current_user.id,
    } for m in msgs])


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
