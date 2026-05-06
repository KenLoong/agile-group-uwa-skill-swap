"""
Selenium Discover + post-detail regression tests.

Unless ``TEST_BASE_URL`` is set, the suite spins an in-process werkzeug server
against a tempfile SQLite DB and seeds deterministic posts (shared helper in
``tests.selenium_support``). Homepage ``GET /`` stays featured-first; filtering
Assertions target ``GET /discover`` wired to ``GET /api/filter``.

When ``TEST_BASE_URL`` points at your own Flask instance you must replicate the
seed data manually (or ignore these tests).

Environment:

- ``SELENIUM_HEADLESS`` — ``true`` (default) or ``false`` for debugging.
- ``TEST_BASE_URL`` — optional explicit base URL; skips embedded server + seed.
- ``SELENIUM_TAGGED_POST_ID`` — resolved post id when using ``TEST_BASE_URL``.
"""
from __future__ import annotations

import os
import shutil
import unittest

from selenium import webdriver
from selenium.common.exceptions import NoSuchDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class SeleniumChromeTest(unittest.TestCase):
    """Starts Chrome/Chromium WebDriver."""

    driver: webdriver.Remote

    @classmethod
    def setUpClass(cls) -> None:
        options = Options()
        headless = os.environ.get("SELENIUM_HEADLESS", "true").lower() == "true"
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1440,1400")
        chrome_bin = os.environ.get("CHROME_BIN")
        if chrome_bin:
            options.binary_location = chrome_bin
        elif shutil.which("chromium"):
            b = shutil.which("chromium")
            if b:
                options.binary_location = b
        driver_path = os.environ.get("CHROMEDRIVER_PATH")
        try:
            if driver_path:
                cls.driver = webdriver.Chrome(service=Service(driver_path), options=options)
            else:
                cls.driver = webdriver.Chrome(options=options)
        except NoSuchDriverException as exc:
            raise unittest.SkipTest(
                "Chrome/Chromium WebDriver is not available."
            ) from exc
        except Exception as exc:  # noqa: BLE001 — surface driver bootstrap noise
            raise unittest.SkipTest(
                f"Could not start Chrome WebDriver: {exc}"
            ) from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "driver"):
            cls.driver.quit()


class SeleniumLiveHarness(SeleniumChromeTest):
    """Optional embedded Flask + seeded DB."""

    base_url: str = ""
    tagged_post_id: int = 0
    _live = None

    @classmethod
    def setUpClass(cls) -> None:
        explicit = os.environ.get("TEST_BASE_URL", "").strip()
        if explicit:
            cls.base_url = explicit.rstrip("/")
            cls.tagged_post_id = int(
                (os.environ.get("SELENIUM_TAGGED_POST_ID") or "1").strip()
            )
        else:
            from tests.selenium_support import start_live_discover_demo

            base_url, tagged_id, ctx = start_live_discover_demo()
            cls.base_url = base_url.rstrip("/")
            cls.tagged_post_id = tagged_id
            cls._live = ctx
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        if cls._live is not None:
            cls._live.shutdown()
            cls._live = None


class TestDiscoverPageFiltering(SeleniumLiveHarness):
    def setUp(self) -> None:
        self.driver.delete_all_cookies()

    def test_discover_page_category_filtering(self) -> None:
        self.driver.get(f"{self.base_url}/discover")
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "post-grid")))
        grid = self.driver.find_element(By.ID, "post-grid")
        wait.until(lambda d: "Language Post" in d.find_element(By.ID, "post-grid").text)
        grid_text_initial = grid.text
        self.assertIn("Language Post", grid_text_initial)
        self.assertIn("Coding Post", grid_text_initial)

        lang_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[data-category="languages"]')
        lang_btn.click()
        wait.until(
            lambda d: (
                "Language Post" in d.find_element(By.ID, "post-grid").text
                and "Coding Post" not in d.find_element(By.ID, "post-grid").text
            )
        )
        filtered = self.driver.find_element(By.ID, "post-grid").text
        self.assertIn("Language Post", filtered)
        self.assertNotIn("Coding Post", filtered)


class TestTaggedPostDetailRendering(SeleniumLiveHarness):
    def setUp(self) -> None:
        self.driver.delete_all_cookies()

    def test_tagged_post_detail_rendering(self) -> None:
        post_url = f"{self.base_url}/posts/{self.tagged_post_id}"
        self.driver.get(post_url)
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        page_src = self.driver.page_source.lower()
        self.assertIn("python", page_src)
        self.assertIn("selenium", page_src)
        pills = self.driver.find_elements(By.CSS_SELECTOR, ".tag-pill")
        visible_tags = [t.text.lower().strip("#") for t in pills]
        self.assertIn("python", visible_tags)
        self.assertIn("selenium", visible_tags)


if __name__ == "__main__":
    unittest.main()
