import unittest

from werkzeug.security import check_password_hash

from app import app, find_matches_for_user
from models import db, User, Interest, PostLike, Message, Tag, Notification, Comment, Post
from tests.test_helpers import (
    cleanup_test_artifacts,
    configure_app_for_tests,
    create_interest,
    create_post,
    create_user,
    get_category,
    login,
    reset_database,
)


class UnitRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_app_for_tests()

    @classmethod
    def tearDownClass(cls):
        cleanup_test_artifacts()

    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        reset_database()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_register_rejects_non_uwa_email(self):
        response = self.client.post(
            '/register',
            data={
                'username': 'invalidemailuser',
                'email': 'invalid@example.com',
                'password': 'password123',
                'confirm_password': 'password123',
                'submit': 'Sign Up',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please use your UWA student email.', response.data)
        self.assertEqual(User.query.count(), 0)

    def test_register_success_creates_user_with_hashed_password(self):
        response = self.client.post(
            '/register',
            data={
                'username': 'alice',
                'email': 'alice@student.uwa.edu.au',
                'password': 'password123',
                'confirm_password': 'password123',
                'submit': 'Sign Up',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Account created! You can now log in.', response.data)
        user = User.query.filter_by(email='alice@student.uwa.edu.au').first()
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, 'password123')
        self.assertTrue(check_password_hash(user.password_hash, 'password123'))

    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login?next=%2Fdashboard', response.headers['Location'])

    def test_cannot_interest_own_post(self):
        owner = create_user('owner')
        post = create_post(owner, title='Own skill')
        login(self.client, owner.email)

        response = self.client.post(f'/interest/{post.id}')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], 'You cannot request your own skill.')
        self.assertEqual(Interest.query.count(), 0)

    def test_duplicate_interest_is_blocked(self):
        owner = create_user('owner')
        sender = create_user('sender')
        post = create_post(owner, title='Guitar lesson')
        create_interest(sender, post)
        login(self.client, sender.email)

        response = self.client.post(f'/interest/{post.id}')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], 'Already sent a request.')
        self.assertEqual(Interest.query.count(), 1)

    def test_like_toggle_increments_and_decrements_count(self):
        owner = create_user('owner')
        liker = create_user('liker')
        post = create_post(owner, title='French conversation')
        login(self.client, liker.email)

        first = self.client.post(f'/post/{post.id}/like')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()['like_count'], 1)
        self.assertTrue(first.get_json()['liked'])
        self.assertEqual(PostLike.query.count(), 1)

        second = self.client.post(f'/post/{post.id}/like')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json()['like_count'], 0)
        self.assertFalse(second.get_json()['liked'])
        self.assertEqual(PostLike.query.count(), 0)

    def test_send_message_creates_private_message_for_recipient(self):
        sender = create_user('sender')
        recipient = create_user('recipient')
        login(self.client, sender.email)

        response = self.client.post(
            f'/api/messages/{recipient.username}',
            json={'content': 'Hi, are you still available for a skill swap?'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['content'], 'Hi, are you still available for a skill swap?')

        message = Message.query.one()
        self.assertEqual(message.sender_id, sender.id)
        self.assertEqual(message.recipient_id, recipient.id)
        self.assertFalse(message.read)

    def test_new_post_creates_tags_and_links_them_to_post(self):
        author = create_user('tagger')
        category = get_category('coding')
        login(self.client, author.email)

        response = self.client.post(
            '/post/new',
            data={
                'title': 'Python testing help',
                'description': 'I can help beginners write unit tests.',
                'category_id': category.id,
                'status': 'open',
                'tags': 'Python, unit testing, cits5505, Python',
                'submit': 'Post Skill',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        post = Post.query.filter_by(title='Python testing help').one()
        self.assertEqual({tag.slug for tag in post.tags}, {'python', 'unit-testing', 'cits5505'})
        self.assertEqual(Tag.query.count(), 3)

    def test_owner_can_update_post_status(self):
        owner = create_user('owner')
        post = create_post(owner, title='Open skill')
        login(self.client, owner.email)

        response = self.client.post(f'/post/{post.id}/set-status', json={'status': 'matched'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'ok': True, 'status': 'matched'})
        self.assertEqual(db.session.get(Post, post.id).status, 'matched')

    def test_comment_mention_creates_notification_for_mentioned_user(self):
        owner = create_user('owner')
        commenter = create_user('commenter')
        target = create_user('target')
        post = create_post(owner, title='Mentionable post')
        login(self.client, commenter.email)

        response = self.client.post(
            f'/post/{post.id}/comment',
            data={'content': 'This would help @target with the assignment.', 'submit': 'Post Comment'},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        comment = Comment.query.one()
        notification = Notification.query.one()
        self.assertEqual(notification.user_id, target.id)
        self.assertEqual(notification.actor_id, commenter.id)
        self.assertEqual(notification.post_id, post.id)
        self.assertEqual(notification.comment_id, comment.id)
        self.assertEqual(notification.notif_type, 'mention')
        self.assertFalse(notification.read)

    def test_bidirectional_matches_require_open_status_and_matching_wants(self):
        coding = get_category('coding')
        language = get_category('language')
        current = create_user('current')
        other = create_user('other')
        create_post(current, title='Coding help', category_slug='coding')
        create_post(other, title='Japanese help', category_slug='language')
        current.wanted_categories = [language]
        other.wanted_categories = [coding]
        db.session.commit()

        matches = find_matches_for_user(current)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['user'].username, 'other')
        self.assertEqual(matches[0]['their_posts'][0].title, 'Japanese help')

        matches[0]['their_posts'][0].status = 'closed'
        db.session.commit()
        self.assertEqual(find_matches_for_user(current), [])

    def test_stats_api_reports_feature_totals(self):
        author = create_user('statsuser')
        commenter = create_user('statscommenter')
        post = create_post(author, title='Stats post')
        tag = Tag(slug='analytics', label='analytics')
        post.tags.append(tag)
        comment = Comment(content='Useful post', user_id=commenter.id, post_id=post.id)
        db.session.add(comment)
        post.comment_count = 1
        db.session.commit()

        response = self.client.get('/api/stats')

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['totals']['posts'], 1)
        self.assertEqual(payload['totals']['users'], 2)
        self.assertEqual(payload['totals']['comments'], 1)
        self.assertEqual(payload['totals']['tags'], 1)
        self.assertEqual(len(payload['trend_30']), 30)
        self.assertTrue(any(row['label'] == 'Coding' for row in payload['category_counts']))


if __name__ == '__main__':
    unittest.main()
