# Selenium Setup Guide

This guide covers how to set up Selenium for end-to-end (E2E) UI testing on the **UWA Skill-Swap** application. It provides instructions for both macOS and Windows.

## 1. Prerequisites

Before setting up Selenium, ensure you have your Python virtual environment active and the required Python packages installed.

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate

# Install requirements (includes selenium)
pip install -r requirements.txt
```

## 2. Browser & Webdriver Setup

Selenium requires a browser and a corresponding webdriver to automate interactions. We will use **Google Chrome** and **ChromeDriver**.

### macOS Setup

1. **Install Google Chrome:** Ensure Google Chrome is installed on your Mac.
2. **Download ChromeDriver:**
   - Go to the [ChromeDriver Download Page](https://chromedriver.chromium.org/downloads) or the [Chrome for Testing dashboard](https://googlechromelabs.github.io/chrome-for-testing/).
   - Download the version that **matches** your installed Google Chrome version.
   - Unzip the file and note the path to the `chromedriver` executable.
3. **Set Environment Variable (Optional but recommended):**
   You can add the path to your `.bash_profile` or `.zshrc`:
   ```bash
   export CHROMEDRIVER_PATH="/path/to/your/chromedriver"
   ```

### Windows Setup

1. **Install Google Chrome:** Ensure Google Chrome is installed on your PC.
2. **Download ChromeDriver:**
   - Go to the [Chrome for Testing dashboard](https://googlechromelabs.github.io/chrome-for-testing/).
   - Download the Win32 or Win64 `chromedriver.exe` that **matches** your installed Chrome version.
   - Unzip the executable to a known directory (e.g., `C:\Program Files\WebDriver\bin\`).
3. **Set Environment Variable:**
   - Open Start Menu -> Search for "Environment Variables" -> "Edit the system environment variables".
   - Under "System variables", find `Path` and click "Edit".
   - Add the directory containing `chromedriver.exe` (e.g., `C:\Program Files\WebDriver\bin\`).
   - Alternatively, you can set `CHROMEDRIVER_PATH` in your `.env` file for the project.

## 3. Running Tests (Headless vs. Headful)

By default, the CI pipeline and most test scripts should run Selenium in **headless mode** (without opening a visible browser window) for speed and stability. 

However, when debugging failing UI tests locally, you may want to run in **headful mode** so you can see the browser interactions.

### Example Configuration in Python

When initializing your Selenium webdriver in your `unittest.TestCase` `setUp` method, you can configure headless mode as follows:

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os

class UITestCase(unittest.TestCase):
    def setUp(self):
        options = Options()
        
        # Toggle headless mode (set to False to see the browser)
        headless = os.environ.get('SELENIUM_HEADLESS', 'true').lower() == 'true'
        if headless:
            options.add_argument('--headless')
        
        # Optional: Set window size for consistent rendering
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        
        # Initialize the driver
        # It will automatically find chromedriver if it's in your PATH
        driver_path = os.environ.get('CHROMEDRIVER_PATH')
        if driver_path:
            service = Service(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            self.driver = webdriver.Chrome(options=options)
            
    def tearDown(self):
        self.driver.quit()
```

## 4. Environment Variables Reference

Ensure you define the following in your local `.env` file if you are not using default locations:

- `CHROMEDRIVER_PATH`: (Optional) Absolute path to your `chromedriver` executable if it's not in your system PATH.
- `SELENIUM_HEADLESS`: (Optional) Set to `false` to view the browser during tests. Defaults to `true` in CI.
