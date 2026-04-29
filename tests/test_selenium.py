import os
import shutil
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchDriverException

class BaseSeleniumTest(unittest.TestCase):
    """
    Base class for Selenium UI tests. 
    Handles setup of ChromeDriver in headless or headful mode.
    """
    
    @classmethod
    def setUpClass(cls):
        options = Options()
        
        headless = os.environ.get('SELENIUM_HEADLESS', 'true').lower() == 'true'
        if headless:
            options.add_argument('--headless=new')
            
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1440,1400')
        
        chrome_bin = os.environ.get('CHROME_BIN')
        if chrome_bin:
            options.binary_location = chrome_bin
        elif shutil.which('chromium'):
            options.binary_location = shutil.which('chromium')

        driver_path = os.environ.get('CHROMEDRIVER_PATH')
        
        try:
            if driver_path:
                cls.driver = webdriver.Chrome(service=Service(driver_path), options=options)
            else:
                cls.driver = webdriver.Chrome(options=options)
        except NoSuchDriverException as exc:
            raise unittest.SkipTest(
                'Chrome/Chromium WebDriver is not available.'
            ) from exc
        except Exception as exc:
            raise unittest.SkipTest(
                f'Could not start Chrome WebDriver: {exc}'
            ) from exc

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'driver'):
            cls.driver.quit()


class TestDiscoverPageFiltering(BaseSeleniumTest):
    """
    Selenium end-to-end tests for the discover page filtering flow.
    
    Setup Assumptions:
    - The Flask application is running at a defined `self.base_url` (defaults to http://127.0.0.1:5000).
    - The database is seeded with predictable data:
        * At least one post in the 'Language' category containing 'Language Post' in its text.
        * At least one post in the 'Coding' category containing 'Coding Post' in its text.
    - The discover page (index `/`) contains a category pill with `data-category="language"`.
    """
    
    def setUp(self):
        self.base_url = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:5000')
        self.driver.get(self.base_url)
        self.driver.delete_all_cookies()

    def test_discover_page_category_filtering(self):
        # Navigate to discover page
        self.driver.get(f'{self.base_url}/')
        
        wait = WebDriverWait(self.driver, 10)
        
        # Ensure the grid loads and displays posts from multiple categories initially
        wait.until(EC.presence_of_element_located((By.ID, 'post-grid')))
        grid_text_initial = self.driver.find_element(By.ID, 'post-grid').text
        self.assertIn('Language Post', grid_text_initial, "Setup Assumption Failed: 'Language Post' missing")
        self.assertIn('Coding Post', grid_text_initial, "Setup Assumption Failed: 'Coding Post' missing")
        
        # Click Language category
        lang_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[data-category="language"]')
        lang_btn.click()
        
        # Wait for grid to update and assert visible card set matches expectations
        wait.until(
            lambda d: 'Language Post' in d.find_element(By.ID, 'post-grid').text and 'Coding Post' not in d.find_element(By.ID, 'post-grid').text
        )
        
        grid_text_filtered = self.driver.find_element(By.ID, 'post-grid').text
        self.assertIn('Language Post', grid_text_filtered)
        self.assertNotIn('Coding Post', grid_text_filtered)

class TestTaggedPostDetailRendering(BaseSeleniumTest):
    """
    Selenium end-to-end tests for verifying tag visibility on the post detail page.
    
    Setup Assumptions:
    - The Flask application is running at `self.base_url` (defaults to http://127.0.0.1:5000).
    - The database is seeded with a post at `/post/1` that contains the tags 'python' and 'selenium'.
    - Tag elements on the detail page have the class `tag-pill` or are visibly rendered in the page text.
    """
    
    def setUp(self):
        self.base_url = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:5000')
        self.driver.get(self.base_url)
        self.driver.delete_all_cookies()

    def test_tagged_post_detail_rendering(self):
        # Navigate to the seeded post detail page
        post_url = f'{self.base_url}/post/1'
        self.driver.get(post_url)
        
        wait = WebDriverWait(self.driver, 10)
        
        # Wait for the post title to ensure the page has loaded
        wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h1')))
        
        # Verify that expected tags are visible on the post detail page
        page_text = self.driver.page_source.lower()
        self.assertIn('python', page_text, "Expected tag 'python' not found in page source.")
        self.assertIn('selenium', page_text, "Expected tag 'selenium' not found in page source.")
        
        # Verify that tag labels appear in the intended user-facing location (tag pills)
        tag_elements = self.driver.find_elements(By.CSS_SELECTOR, '.tag-pill')
        visible_tags = [tag.text.lower().strip('#') for tag in tag_elements]
        
        self.assertIn('python', visible_tags, "Tag 'python' is not rendered in a .tag-pill element.")
        self.assertIn('selenium', visible_tags, "Tag 'selenium' is not rendered in a .tag-pill element.")

if __name__ == '__main__':
    unittest.main()
