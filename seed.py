"""
seed.py – Populate the database with rich sample data for manual testing.

Covers:
  - 5 categories, 8 users, 20+ posts (all categories, all statuses)
  - Tags on posts (10+ unique tags, many posts share tags)
  - Wanted skills per user (enables bidirectional matching)
  - Comments, likes, bookmarks, interests spread across many combinations
  - Data spread over the last 30 days so trend charts look interesting
  - Random avatars assigned to users
"""

from datetime import datetime, timedelta
import random
import os
import shutil
import uuid

from app import app, db
from models import (
    User, Post, Comment, Interest, Category, Bookmark, PostLike, Tag,
    post_tags, user_wanted_categories,
)
from werkzeug.security import generate_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def days_ago(n, jitter_hours=0):
    """Return a UTC datetime n days ago with optional random jitter."""
    base = datetime.utcnow() - timedelta(days=n)
    if jitter_hours:
        base += timedelta(hours=random.randint(0, jitter_hours))
    return base


def upsert_tag(session, slug, label):
    t = Tag.query.filter_by(slug=slug).first()
    if not t:
        t = Tag(slug=slug, label=label)
        session.add(t)
        session.flush()
    return t


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def seed_data():
    with app.app_context():
        random.seed(42)

        # ── Wipe existing data in dependency order ───────────────────────
        db.session.execute(post_tags.delete())
        db.session.execute(user_wanted_categories.delete())
        Comment.query.delete()
        PostLike.query.delete()
        Bookmark.query.delete()
        Interest.query.delete()
        Post.query.delete()
        Tag.query.delete()
        User.query.delete()
        Category.query.delete()
        db.session.commit()

        # ── Categories ───────────────────────────────────────────────────
        cats_raw = [
            ('coding',      'Coding & IT',              10),
            ('academic',    'Academic / Tutoring',       15),
            ('language',    'Languages',                 20),
            ('business',    'Business & Finance',        25),
            ('engineering', 'Engineering & Science',     30),
            ('music',       'Music & Arts',              35),
            ('design',      'Design & Creative',         40),
            ('sports',      'Sports & Fitness',          45),
            ('health',      'Health & Wellness',         50),
            ('cooking',     'Cooking & Food',            55),
            ('career',      'Career & Professional',     60),
            ('gaming',      'Gaming',                    65),
            ('other',       'Other',                     99),
        ]
        for slug, label, order in cats_raw:
            db.session.add(Category(slug=slug, label=label, sort_order=order))
        db.session.commit()

        coding   = Category.query.filter_by(slug='coding').first()
        language = Category.query.filter_by(slug='language').first()
        music    = Category.query.filter_by(slug='music').first()
        sports   = Category.query.filter_by(slug='sports').first()
        other    = Category.query.filter_by(slug='other').first()

        # ── Tags ─────────────────────────────────────────────────────────
        tag_defs = [
            ('python',     'Python'),
            ('cits1401',   'CITS1401'),
            ('cits2200',   'CITS2200'),
            ('javascript', 'JavaScript'),
            ('web-dev',    'Web Dev'),
            ('beginner',   'Beginner'),
            ('advanced',   'Advanced'),
            ('mandarin',   'Mandarin'),
            ('french',     'French'),
            ('guitar',     'Guitar'),
            ('piano',      'Piano'),
            ('swimming',   'Swimming'),
            ('yoga',       'Yoga'),
            ('uwa',        'UWA'),
            ('online',     'Online'),
        ]
        tags = {slug: upsert_tag(db.session, slug, label) for slug, label in tag_defs}
        db.session.commit()

        # ── Users ─────────────────────────────────────────────────────────
        pw = generate_password_hash('password123')

        users_raw = [
            ('alice',   'alice@student.uwa.edu.au'),
            ('bob',     'bob@student.uwa.edu.au'),
            ('carol',   'carol@student.uwa.edu.au'),
            ('dave',    'dave@student.uwa.edu.au'),
            ('emma',    'emma@student.uwa.edu.au'),
            ('frank',   'frank@student.uwa.edu.au'),
            ('grace',   'grace@student.uwa.edu.au'),
            ('henry',   'henry@student.uwa.edu.au'),
        ]

        # Source avatar files placed in static/uploads/avatars/ by hand.
        # Each user gets their own COPY so that one user's avatar change
        # never deletes a file that another user's record still points to.
        # Detect available seed files dynamically (h*.jpeg) to survive
        # partial deletions caused by previous runs.
        avatar_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'static', 'uploads', 'avatars',
        )
        avatar_src_files = sorted(
            f for f in os.listdir(avatar_dir)
            if f.startswith('h') and f.endswith('.jpeg')
        )
        if not avatar_src_files:
            raise RuntimeError(
                'No seed avatar files (h*.jpeg) found in '
                + avatar_dir + '. Please restore them before running seed.py.'
            )

        def copy_avatar(src_name):
            """Copy a seed avatar to a unique filename; return the new name."""
            ext = os.path.splitext(src_name)[1]
            dest_name = uuid.uuid4().hex + ext
            shutil.copy2(
                os.path.join(avatar_dir, src_name),
                os.path.join(avatar_dir, dest_name),
            )
            return dest_name

        users = {}
        for username, email in users_raw:
            avatar_filename = copy_avatar(random.choice(avatar_src_files))
            u = User(username=username, email=email, password_hash=pw,
                     avatar_filename=avatar_filename)
            db.session.add(u)
            users[username] = u
        db.session.commit()

        alice = users['alice']
        bob   = users['bob']
        carol = users['carol']
        dave  = users['dave']
        emma  = users['emma']
        frank = users['frank']
        grace = users['grace']
        henry = users['henry']

        # ── Wanted skills (enables bidirectional matching) ────────────────
        # alice offers coding, wants language + music
        alice.wanted_categories = [language, music]
        # bob offers language, wants coding → alice ↔ bob MATCH
        bob.wanted_categories   = [coding]
        # carol offers music, wants coding → alice ↔ carol MATCH
        carol.wanted_categories = [coding, language]
        # dave offers sports, wants music + language
        dave.wanted_categories  = [music, language]
        # emma offers language, wants sports → dave ↔ emma MATCH
        emma.wanted_categories  = [sports]
        # frank offers coding + music, wants language
        frank.wanted_categories = [language]
        # grace offers other, wants coding
        grace.wanted_categories = [coding]
        # henry wants sports + music
        henry.wanted_categories = [sports, music]
        db.session.commit()

        # ── Posts ─────────────────────────────────────────────────────────
        # (title, description, user, category, status, tags_list, days_back)
        posts_raw = [
            # --- Coding ---
            (
                'Python Tutoring (CITS1401)',
                'Can help with **CITS1401** logic, lists, dicts and file I/O.\n\n'
                '- Sessions via Zoom or UWA library\n'
                '- Bring your assignment questions!\n\n'
                'In return I\'d love help with Mandarin or piano.',
                alice, coding, 'open',
                [tags['python'], tags['cits1401'], tags['beginner'], tags['uwa']],
                28,
            ),
            (
                'Data Structures Help (CITS2200)',
                'Comfortable with **trees, graphs and sorting** algorithms.\n\n'
                'Can run through past exam questions and explain the intuition.\n\n'
                "> My pace is slow and patient — don't worry if you're struggling.",
                alice, coding, 'open',
                [tags['cits2200'], tags['advanced'], tags['uwa']],
                20,
            ),
            (
                'JavaScript & React Basics',
                'I build hobby projects with **React + Vite**.\n\n'
                'Happy to pair-program or do code reviews.\n\n'
                '**Topics:** hooks, state management, fetch API.',
                frank, coding, 'matched',
                [tags['javascript'], tags['web-dev'], tags['beginner']],
                15,
            ),
            (
                'Web Dev Fundamentals (HTML/CSS/JS)',
                'Covering the whole front-end stack from scratch.\n\n'
                '```html\n<div class="hello">Hello, UWA!</div>\n```\n\n'
                'Good for complete beginners.',
                frank, coding, 'open',
                [tags['web-dev'], tags['javascript'], tags['beginner'], tags['online']],
                8,
            ),
            (
                'Linux & Bash Scripting',
                'Know your way around the terminal? I can teach:\n\n'
                '- File permissions\n- Shell scripting\n- SSH & Git basics\n\n'
                'Useful for any CITS unit that uses the lab machines.',
                henry, coding, 'open',
                [tags['advanced'], tags['uwa']],
                3,
            ),

            # --- Language ---
            (
                'Mandarin for Beginners',
                'Native speaker offering **conversational Mandarin** lessons.\n\n'
                'Great for travelling or connecting with Chinese-speaking classmates.\n\n'
                'Lesson format: 1 hr chat + optional character writing.',
                bob, language, 'open',
                [tags['mandarin'], tags['beginner'], tags['online']],
                25,
            ),
            (
                'French Conversation Practice',
                'DELF B1 certified. Can help with:\n\n'
                '- Pronunciation\n- Grammar basics\n- Listening exercises\n\n'
                'Looking to swap for coding or guitar lessons.',
                carol, language, 'open',
                [tags['french'], tags['beginner']],
                18,
            ),
            (
                'Advanced Mandarin – HSK 4/5',
                'Can read and write **Traditional & Simplified** Chinese.\n\n'
                'Great for students preparing for HSK or work in Asia.',
                emma, language, 'matched',
                [tags['mandarin'], tags['advanced'], tags['online']],
                12,
            ),
            (
                'English Academic Writing',
                'Happy to proofread **essays, reports and emails** for non-native speakers.\n\n'
                'I was a writing tutor at the UWA Guild.',
                grace, language, 'open',
                [tags['uwa'], tags['beginner']],
                5,
            ),

            # --- Music / Arts ---
            (
                'Guitar Lessons – Acoustic Beginner',
                'Teaching **open chords, strumming patterns** and simple songs.\n\n'
                '> Bring your own guitar if you have one.\n\n'
                'First lesson free to make sure we click!',
                carol, music, 'open',
                [tags['guitar'], tags['beginner']],
                26,
            ),
            (
                'Classical Piano – Grade 1–4',
                'AMEB Grade 6 pianist. Can teach:\n\n'
                '- Scales and sight-reading\n- Beginner pieces (Bach, Mozart)\n- Theory basics\n\n'
                'Sessions at my place (Crawley) or via Zoom.',
                dave, music, 'open',
                [tags['piano'], tags['beginner'], tags['online']],
                17,
            ),
            (
                'Electric Guitar – Intermediate Techniques',
                'Covers bending, legato, alternate picking.\n\n'
                'Tabs provided for each lesson. Favourite genres: rock, blues, jazz.',
                henry, music, 'closed',
                [tags['guitar'], tags['advanced']],
                10,
            ),
            (
                'Music Theory & Ear Training',
                'Learn to **read sheet music**, identify intervals and chord progressions.\n\n'
                'Useful for any instrument. Based on the ABRSM theory syllabus.',
                grace, music, 'open',
                [tags['beginner'], tags['online']],
                2,
            ),

            # --- Sports / Fitness ---
            (
                'Swimming – Freestyle Technique',
                'Competitive swimmer (UWA Club) offering stroke correction sessions.\n\n'
                '- Breathing technique\n- Flip turns\n- Training plans\n\n'
                'Pool: UWA Aquatic Centre (bring your own pass).',
                emma, sports, 'open',
                [tags['swimming'], tags['uwa'], tags['advanced']],
                22,
            ),
            (
                'Yoga for Beginners',
                '200-hr certified yoga instructor.\n\n'
                '**Styles I teach:** Hatha, Yin, Vinyasa flow.\n\n'
                'Great for stress relief during exam periods!',
                bob, sports, 'open',
                [tags['yoga'], tags['beginner'], tags['online']],
                14,
            ),
            (
                'Running Coaching – 5K to 10K',
                'Sub-40 min 10K runner. I can build you a **personalised training plan**.\n\n'
                'Weekly check-ins via WhatsApp or in person on the UWA track.',
                dave, sports, 'matched',
                [tags['uwa'], tags['beginner']],
                7,
            ),
            (
                'Rock Climbing Basics',
                'Indoor bouldering at Claremont Climbing is my hobby.\n\n'
                'Can teach footwork, body positioning and reading routes.\n\n'
                'Day pass costs ~$20 but I\'ll cover your first session.',
                alice, sports, 'open',
                [tags['beginner']],
                1,
            ),

            # --- Other ---
            (
                'Photography – Portrait & Street',
                'Sony A7 shooter. Happy to share:\n\n'
                '- Exposure triangle\n- Lightroom editing workflow\n- Composition tips\n\n'
                'Swap for any language or coding lessons.',
                frank, other, 'open',
                [tags['beginner'], tags['online']],
                19,
            ),
            (
                'Academic Referencing & Endnote',
                'Research librarian background. I can show you how to use **Endnote** and avoid '
                'common APA / Harvard referencing mistakes.\n\n'
                'Particularly helpful before major essay deadlines.',
                grace, other, 'open',
                [tags['uwa'], tags['beginner']],
                11,
            ),
            (
                'Cooking – Asian Home Cuisine',
                'I\'ll teach you 5 easy weeknight recipes:\n\n'
                '1. Egg fried rice\n2. Mapo tofu\n3. Dumplings\n4. Stir-fry noodles\n5. Miso soup\n\n'
                'Great for students tired of instant ramen 😄',
                henry, other, 'open',
                [tags['beginner']],
                4,
            ),
        ]

        posts = []
        for title, desc, user, cat, status, post_tag_list, days_back in posts_raw:
            p = Post(
                title=title,
                description=desc,
                user_id=user.id,
                category_id=cat.id,
                status=status,
                timestamp=days_ago(days_back, jitter_hours=18),
                like_count=0,
                comment_count=0,
            )
            p.tags = post_tag_list
            db.session.add(p)
            posts.append(p)
        db.session.commit()

        # Name-to-post lookup for readable interest/like/comment setup below
        def find_post(title_fragment):
            return next(p for p in posts if title_fragment in p.title)

        p_python   = find_post('Python Tutoring')
        p_ds       = find_post('Data Structures')
        p_react    = find_post('JavaScript & React')
        p_webfund  = find_post('Web Dev Fundamentals')
        p_linux    = find_post('Linux')
        p_mandarin = find_post('Mandarin for Beginners')
        p_french   = find_post('French')
        p_adv_mand = find_post('Advanced Mandarin')
        p_eng_writ = find_post('English Academic')
        p_guitar   = find_post('Guitar Lessons')
        p_piano    = find_post('Classical Piano')
        p_elec_git = find_post('Electric Guitar')
        p_music_th = find_post('Music Theory')
        p_swim     = find_post('Swimming')
        p_yoga     = find_post('Yoga')
        p_running  = find_post('Running')
        p_climb    = find_post('Rock Climbing')
        p_photo    = find_post('Photography')
        p_ref      = find_post('Academic Referencing')
        p_cook     = find_post('Cooking')

        # ── Interests ─────────────────────────────────────────────────────
        interests_raw = [
            # (sender, post, days_back)
            (bob,   p_python,   25),
            (carol, p_python,   24),
            (dave,  p_python,   22),
            (emma,  p_ds,       18),
            (grace, p_webfund,  7),
            (henry, p_react,    14),
            (alice, p_mandarin, 23),
            (dave,  p_mandarin, 20),
            (grace, p_mandarin, 17),
            (alice, p_guitar,   25),
            (bob,   p_piano,    15),
            (emma,  p_guitar,   12),
            (frank, p_piano,    10),
            (henry, p_music_th, 2),
            (alice, p_swim,     20),
            (bob,   p_yoga,     13),
            (carol, p_running,  6),
            (grace, p_yoga,     5),
            (alice, p_photo,    18),
            (bob,   p_ref,      9),
            (carol, p_cook,     3),
            (dave,  p_linux,    1),
        ]
        for sender, post, days_back in interests_raw:
            if sender.id != post.user_id:
                db.session.add(Interest(
                    sender_id=sender.id,
                    post_id=post.id,
                    timestamp=days_ago(days_back, jitter_hours=12),
                ))
        db.session.commit()

        # ── Likes ─────────────────────────────────────────────────────────
        likes_raw = [
            (bob,   p_python,   27),
            (carol, p_python,   26),
            (dave,  p_python,   24),
            (emma,  p_python,   23),
            (frank, p_python,   21),
            (grace, p_ds,       19),
            (henry, p_ds,       18),
            (alice, p_mandarin, 24),
            (carol, p_mandarin, 22),
            (emma,  p_mandarin, 20),
            (frank, p_mandarin, 18),
            (alice, p_guitar,   25),
            (bob,   p_guitar,   24),
            (dave,  p_guitar,   23),
            (henry, p_guitar,   22),
            (alice, p_piano,    16),
            (carol, p_piano,    15),
            (emma,  p_piano,    14),
            (grace, p_swim,     21),
            (henry, p_swim,     20),
            (alice, p_yoga,     13),
            (carol, p_yoga,     12),
            (frank, p_yoga,     11),
            (bob,   p_react,    14),
            (alice, p_photo,    17),
            (carol, p_photo,    16),
            (dave,  p_cook,     4),
            (emma,  p_cook,     3),
            (frank, p_cook,     2),
        ]
        like_set = set()
        for liker, post, days_back in likes_raw:
            key = (liker.id, post.id)
            if liker.id != post.user_id and key not in like_set:
                like_set.add(key)
                db.session.add(PostLike(
                    user_id=liker.id,
                    post_id=post.id,
                    timestamp=days_ago(days_back, jitter_hours=10),
                ))
                post.like_count += 1
        db.session.commit()

        # ── Comments ──────────────────────────────────────────────────────
        comments_raw = [
            (bob,   p_python,   'Really helpful, thanks Alice! The CITS1401 content is spot on.', 26),
            (carol, p_python,   'Can we cover recursion too? I always get confused.', 25),
            (dave,  p_python,   'Booked a session for next Thursday, see you then!', 23),
            (alice, p_mandarin, 'Bob this sounds amazing, I\'ve always wanted to learn Mandarin!', 22),
            (emma,  p_mandarin, 'Is online okay? I\'m not on campus much.', 21),
            (grace, p_mandarin, 'Do you also teach reading characters or just speaking?', 19),
            (alice, p_guitar,   'Just expressed interest — so keen to learn!', 24),
            (bob,   p_guitar,   'Will you cover fingerpicking? That\'s my goal.', 23),
            (dave,  p_guitar,   'Love this, looking forward to it.', 21),
            (emma,  p_guitar,   'Do I need to buy a guitar first?', 20),
            (alice, p_piano,    'Grade 4 here I come! Loved the first session.', 15),
            (grace, p_swim,     'Any advice for beginners who are scared of deep water?', 20),
            (henry, p_swim,     'What times are the UWA Aquatic Centre sessions? I\'ll come along.', 19),
            (bob,   p_yoga,     'Perfect timing, exam stress is real. Signed up!', 12),
            (carol, p_yoga,     'Yin yoga sounds great for flexibility.', 11),
            (alice, p_photo,    'Your Instagram is stunning, Frank. Would love to learn your editing style.', 17),
            (carol, p_photo,    'Do you use any presets in Lightroom?', 16),
            (bob,   p_ref,      'Endnote has been the bane of my life — this is exactly what I need.', 8),
            (carol, p_cook,     'The dumpling recipe alone makes this worth it!', 3),
            (dave,  p_cook,     'Can we do mapo tofu first? It\'s my favourite.', 2),
            (frank, p_react,    'Do you have a GitHub I can look at before we start?', 13),
            (alice, p_webfund,  'Great intro post. I\'m a complete newbie so this is perfect.', 7),
            (grace, p_linux,    'Bash scripting would save me so much time in my research job.', 2),
        ]
        for author, post, content, days_back in comments_raw:
            db.session.add(Comment(
                content=content,
                user_id=author.id,
                post_id=post.id,
                timestamp=days_ago(days_back, jitter_hours=8),
            ))
            post.comment_count += 1
        db.session.commit()

        # ── Bookmarks ─────────────────────────────────────────────────────
        bookmarks_raw = [
            (alice, p_mandarin, 23),
            (alice, p_yoga,     13),
            (bob,   p_python,   25),
            (bob,   p_piano,    15),
            (carol, p_swim,     21),
            (dave,  p_french,   17),
            (emma,  p_react,    13),
            (frank, p_mandarin, 17),
            (grace, p_python,   22),
            (henry, p_guitar,   22),
        ]
        bm_set = set()
        for saver, post, days_back in bookmarks_raw:
            key = (saver.id, post.id)
            if saver.id != post.user_id and key not in bm_set:
                bm_set.add(key)
                db.session.add(Bookmark(
                    user_id=saver.id,
                    post_id=post.id,
                    timestamp=days_ago(days_back, jitter_hours=6),
                ))
        db.session.commit()

        # ── Summary ───────────────────────────────────────────────────────
        print('\n✅  Seed complete!')
        print(f'   Users:      {User.query.count()}')
        print(f'   Posts:      {Post.query.count()}')
        print(f'   Tags:       {Tag.query.count()}')
        print(f'   Interests:  {Interest.query.count()}')
        print(f'   Likes:      {PostLike.query.count()}')
        print(f'   Comments:   {Comment.query.count()}')
        print(f'   Bookmarks:  {Bookmark.query.count()}')
        print()
        print('Login with any of these accounts (password: password123):')
        print('  alice@student.uwa.edu.au  → offers Coding, wants Language + Music')
        print('  bob@student.uwa.edu.au    → offers Language/Yoga, wants Coding  [MATCH with alice]')
        print('  carol@student.uwa.edu.au  → offers Music/Language, wants Coding [MATCH with alice]')
        print('  dave@student.uwa.edu.au   → offers Music/Sports, wants Music+Language')
        print('  emma@student.uwa.edu.au   → offers Language/Sports, wants Sports [MATCH with dave]')
        print('  frank@student.uwa.edu.au  → offers Coding/Other, wants Language')
        print('  grace@student.uwa.edu.au  → offers Language/Other, wants Coding')
        print('  henry@student.uwa.edu.au  → offers Coding/Music/Other, wants Sports+Music')


if __name__ == '__main__':
    seed_data()
