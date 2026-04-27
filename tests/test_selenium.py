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
        
        # Check if we should run headful for local debugging
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
                'Chrome/Chromium WebDriver is not available. '
                'Install chromedriver or set CHROMEDRIVER_PATH before running selenium tests.'
            ) from exc
        except Exception as exc:
            raise unittest.SkipTest(
                f'Could not start Chrome WebDriver for selenium tests: {exc}'
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

if __name__ == '__main__':
    unittest.main()
