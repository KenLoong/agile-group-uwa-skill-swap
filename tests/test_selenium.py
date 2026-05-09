import os
import shutil
import unittest

from selenium import webdriver
from selenium.common.exceptions import NoSuchDriverException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from app import app
from models import Notification, User, db
from tests.test_helpers import (
    cleanup_test_artifacts,
    configure_app_for_tests,
    create_post,
    create_user,
    reset_database,
    LiveServerThread,
    wait_for_server,
)


class SeleniumFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_app_for_tests()
        cls.ctx = app.app_context()
        cls.ctx.push()
        reset_database()
        cls.server = LiveServerThread(app)
        cls.server.start()
        cls.base_url = f'http://127.0.0.1:{cls.server.port}'
        wait_for_server(cls.base_url)
        cls.driver = cls._build_driver()
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'driver'):
            cls.driver.quit()
        cls.server.shutdown()
        db.session.remove()
        cls.ctx.pop()
        cleanup_test_artifacts()

    @classmethod
    def _build_driver(cls):
        options = Options()
        chrome_bin = os.environ.get('CHROME_BIN')
        if chrome_bin:
            options.binary_location = chrome_bin
        elif shutil.which('chromium'):
            options.binary_location = shutil.which('chromium')

        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1440,1400')

        driver_path = os.environ.get('CHROMEDRIVER_PATH')
        try:
            if driver_path:
                return webdriver.Chrome(service=Service(driver_path), options=options)
            return webdriver.Chrome(options=options)
        except NoSuchDriverException as exc:
            raise unittest.SkipTest(
                'Chrome/Chromium WebDriver is not available. '
                'Install chromedriver or set CHROMEDRIVER_PATH before running selenium tests.'
            ) from exc
        except Exception as exc:
            raise unittest.SkipTest(
                f'Could not start Chrome WebDriver for selenium tests: {exc}'
            ) from exc

    def setUp(self):
        reset_database()
        self.driver.get(self.base_url)
        self.driver.delete_all_cookies()

    def open(self, path):
        self.driver.get(f'{self.base_url}{path}')

    def submit_form_by_id(self, form_id):
        """Submit a form without relying on viewport-dependent button clicks.

        Use the native HTMLFormElement.submit() method instead of clicking the
        visible submit button or requestSubmit(). In headless Chrome, click-based
        submits can be intercepted by layout, and requestSubmit() can be stopped
        by page-level JavaScript validation. Calling the native form submit keeps
        the Selenium tests focused on the Flask route behaviour.
        """
        form = self.wait.until(EC.presence_of_element_located((By.ID, form_id)))
        self.driver.execute_script(
            "HTMLFormElement.prototype.submit.call(arguments[0]);",
            form,
        )

    def login_via_ui(self, email, password='password123'):
        self.open('/login')
        self.wait.until(EC.presence_of_element_located((By.ID, 'login-email'))).send_keys(email)
        self.driver.find_element(By.ID, 'login-password').send_keys(password)
        self.submit_form_by_id('login-form')
        self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, 'Log out')))

    def login_with_session_cookie(self, email, password='password123'):
        """Attach a Flask-Login session cookie directly to the browser.

        This helper is used by Selenium tests that need an authenticated user
        but are not specifically testing the login form. It avoids depending on
        repeated UI login submissions, while still exercising the real browser
        routes after the session is installed.
        """
        user = User.query.filter_by(email=email).first()
        if user is None:
            self.fail(f'Cannot log in test browser: no user exists for {email}')

        serializer = app.session_interface.get_signing_serializer(app)
        if serializer is None:
            self.fail('Cannot create Flask session cookie: no signing serializer is available')

        cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
        cookie_value = serializer.dumps({
            '_user_id': str(user.id),
            '_fresh': True,
        })

        self.driver.get(self.base_url)
        self.driver.delete_all_cookies()
        self.driver.add_cookie({
            'name': cookie_name,
            'value': cookie_value,
            'path': '/',
        })
        self.driver.get(self.base_url)
        self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, 'Log out')))

    def test_register_flow_creates_account(self):
        self.open('/register')

        self.wait.until(
            EC.presence_of_element_located((By.ID, 'reg-username'))
        ).send_keys('newuser')
        self.driver.find_element(By.ID, 'reg-email').send_keys('newuser@student.uwa.edu.au')
        self.driver.find_element(By.ID, 'reg-password').send_keys('Password123!')
        self.driver.find_element(By.ID, 'reg-confirm').send_keys('Password123!')

        submit = self.driver.find_element(
            By.CSS_SELECTOR,
            '#register-form input[type="submit"], #register-form button[type="submit"]'
        )
        submit.click()

        self.wait.until(
            lambda d: 'Log in' in d.page_source or '/login' in d.current_url
        )
        self.assertTrue(
            'Log in' in self.driver.page_source or '/login' in self.driver.current_url
        )

    def test_login_and_logout_flow(self):
        create_user('alice')

        self.login_via_ui('alice@student.uwa.edu.au')
        self.assertIn('alice', self.driver.page_source)
        self.assertIn('Log out', self.driver.page_source)

        self.driver.find_element(By.LINK_TEXT, 'Log out').click()
        self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, 'Log in')))
        self.assertEqual(self.driver.current_url.rstrip('/'), self.base_url.rstrip('/'))

    def test_dashboard_requires_login_redirects_to_login(self):
        self.open('/dashboard')
        self.wait.until(EC.presence_of_element_located((By.ID, 'login-email')))
        self.assertIn('/login?next=%2Fdashboard', self.driver.current_url)

    def test_create_post_flow_shows_post_on_discovery_and_dashboard(self):
        create_user('poster')
        self.login_with_session_cookie('poster@student.uwa.edu.au')

        self.open('/post/new')
        self.wait.until(EC.presence_of_element_located((By.ID, 'post-title'))).send_keys('Selenium Guitar Lessons')
        Select(self.driver.find_element(By.ID, 'post-category')).select_by_visible_text('Music')
        self.driver.find_element(By.ID, 'post-description').send_keys('I can teach guitar chords and rhythm.')
        self.submit_form_by_id('post-form')

        self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, 'Selenium Guitar Lessons')))
        self.assertIn('Your skill has been posted!', self.driver.page_source)

        self.open('/dashboard')
        self.wait.until(EC.presence_of_element_located((By.ID, 'pane-posts')))
        self.assertIn('Selenium Guitar Lessons', self.driver.page_source)

    def test_search_returns_matching_post(self):
        user = create_user('searcher')
        create_post(user, title='Japanese conversation practice', category_slug='language')
        create_post(user, title='Beginner Python tutoring', category_slug='coding')

        self.open('/')
        search = self.wait.until(EC.presence_of_element_located((By.ID, 'search-input')))
        search.clear()
        search.send_keys('Japanese')
        self.driver.find_element(By.CSS_SELECTOR, '#search-form button[type="submit"]').click()

        self.wait.until(
            lambda d: 'Japanese conversation practice' in d.find_element(By.ID, 'post-grid').text
        )

        grid_text = self.driver.find_element(By.ID, 'post-grid').text
        self.assertIn('Japanese conversation practice', grid_text)

    def test_owner_cannot_interest_own_post(self):
        owner = create_user('owner')
        post = create_post(owner, title='My own skill listing')
        self.login_with_session_cookie(owner.email)

        self.open(f'/post/{post.id}')
        self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, 'Edit')))
        self.assertEqual(len(self.driver.find_elements(By.ID, 'interest-btn')), 0)
        self.assertIn('Delete', self.driver.page_source)

    def test_comment_with_mention_creates_visible_link_and_notification(self):
        owner = create_user('postowner')
        commenter = create_user('commenter')
        target = create_user('target')
        post = create_post(owner, title='Mention flow skill')
        self.login_with_session_cookie(commenter.email)

        self.open(f'/post/{post.id}')
        comment_box = self.wait.until(EC.presence_of_element_located((By.ID, 'comment-content')))
        comment_box.send_keys('This looks useful for @target')
        self.driver.find_element(By.ID, 'comment-submit').click()

        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.mention-link[href="/user/target"]')))
        self.assertIn('@target', self.driver.find_element(By.ID, 'comment-list').text)
        self.wait.until(lambda _driver: Notification.query.count() == 1)
        notification = Notification.query.one()
        self.assertEqual(notification.user_id, target.id)
        self.assertEqual(notification.actor_id, commenter.id)
        self.assertEqual(notification.post_id, post.id)

    def test_stats_page_renders_chart_canvases(self):
        user = create_user('statposter')
        create_post(user, title='Statistics test post', category_slug='coding')

        self.open('/stats')

        self.wait.until(EC.presence_of_element_located((By.ID, 'kpi-row')))
        self.assertIn('Platform Stats', self.driver.page_source)
        for canvas_id in ('chart-categories', 'chart-trend', 'chart-top-users'):
            chart = self.driver.find_element(By.ID, canvas_id)
            self.assertEqual(chart.tag_name.lower(), 'canvas')

    def test_profile_message_button_opens_conversation(self):
        viewer = create_user('viewer')
        recipient = create_user('recipient')
        self.login_with_session_cookie(viewer.email)

        self.open(f'/user/{recipient.username}')
        message_link = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'a[href="/messages/{recipient.username}"]'))
        )
        message_link.click()

        self.wait.until(EC.presence_of_element_located((By.ID, 'send-form')))
        self.assertIn(f'/messages/{recipient.username}', self.driver.current_url)
        self.assertIn(f'Chat with {recipient.username}', self.driver.page_source)


if __name__ == '__main__':
    unittest.main()
