import unittest
import os
from io import BytesIO
from pathlib import Path

from app import app
from models import db, User
from tests.test_helpers import (
    cleanup_test_artifacts,
    configure_app_for_tests,
    create_user,
    login,
    reset_database,
)


class AvatarTests(unittest.TestCase):
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

    def test_register_with_avatar(self):
        """Test registering with an avatar file."""
        avatar_data = self._create_test_image()
        response = self.client.post(
            '/register',
            data={
                'username': 'alice_with_avatar',
                'email': 'alice_with_avatar@student.uwa.edu.au',
                'password': 'password123',
                'confirm_password': 'password123',
                'avatar': (avatar_data, 'avatar.png'),
                'submit': 'Sign Up',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Account created! You can now log in.', response.data)
        
        user = User.query.filter_by(email='alice_with_avatar@student.uwa.edu.au').first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.avatar_filename)
        
        # Verify avatar file exists
        avatar_path = os.path.join(app.config['AVATAR_UPLOAD_FOLDER'], user.avatar_filename)
        self.assertTrue(os.path.isfile(avatar_path))

    def test_update_avatar_on_account_page(self):
        """Test uploading avatar on account settings page."""
        user = create_user('avatar_updater')
        login(self.client, user.email)
        
        avatar_data = self._create_test_image()
        response = self.client.post(
            '/account',
            data={
                'avatar': (avatar_data, 'new_avatar.png'),
                'submit': 'Save profile',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Profile updated.', response.data)
        
        updated_user = db.session.get(User, user.id)
        self.assertIsNotNone(updated_user.avatar_filename)
        
        # Verify avatar file exists
        avatar_path = os.path.join(app.config['AVATAR_UPLOAD_FOLDER'], updated_user.avatar_filename)
        self.assertTrue(os.path.isfile(avatar_path))

    def test_remove_avatar(self):
        """Test removing an avatar."""
        user = create_user('avatar_remover')
        login(self.client, user.email)
        
        # First upload an avatar
        avatar_data = self._create_test_image()
        self.client.post(
            '/account',
            data={
                'avatar': (avatar_data, 'avatar_to_remove.png'),
                'submit': 'Save profile',
            },
            follow_redirects=True,
        )
        
        user = db.session.get(User, user.id)
        old_avatar_filename = user.avatar_filename
        self.assertIsNotNone(old_avatar_filename)
        
        # Now remove it
        response = self.client.post(
            '/account',
            data={
                'remove_avatar': True,
                'submit': 'Save profile',
            },
            follow_redirects=True,
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Profile updated.', response.data)
        
        user = db.session.get(User, user.id)
        self.assertIsNone(user.avatar_filename)
        
        # Old file should be deleted
        old_avatar_path = os.path.join(app.config['AVATAR_UPLOAD_FOLDER'], old_avatar_filename)
        self.assertFalse(os.path.isfile(old_avatar_path))

    def test_register_rejects_oversized_avatar(self):
        """Test that oversized avatar files are rejected."""
        large_avatar = BytesIO(b'x' * (3 * 1024 * 1024))  # 3 MB
        response = self.client.post(
            '/register',
            data={
                'username': 'too_large_avatar',
                'email': 'too_large_avatar@student.uwa.edu.au',
                'password': 'password123',
                'confirm_password': 'password123',
                'avatar': (large_avatar, 'large_avatar.png'),
                'submit': 'Sign Up',
            },
            follow_redirects=True,
        )

        # 413 Payload Too Large due to MAX_CONTENT_LENGTH
        self.assertEqual(response.status_code, 413)
        self.assertEqual(User.query.count(), 0)

    def _create_test_image(self):
        """Create a minimal PNG image for testing."""
        # Minimal 1x1 PNG image bytes
        png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
            b'\x00\x01\x01\x00\x05\x18\r\xc1\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return BytesIO(png_bytes)


if __name__ == '__main__':
    unittest.main()
