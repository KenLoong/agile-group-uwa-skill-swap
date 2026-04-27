import os
import shutil
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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

if __name__ == '__main__':
    unittest.main()
