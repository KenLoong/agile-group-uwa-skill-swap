# Testing Guide

This document outlines how to execute tests and write new ones for the UWA Skill-Swap application. It covers both unit tests (testing backend logic) and end-to-end UI tests via Selenium.

## 1. Quick Start

If you have a clean repository and have installed the dependencies (via `requirements.txt` and `requirements-dev.txt`), you can run the entire test suite using the top-level `Makefile`:

```bash
make test
```

This command automatically discovers all tests in the `tests/` directory and executes them sequentially.

## 2. Unit Tests

All unit tests live in the `tests/` directory.

### Running Individual Tests

You can run individual test files natively without needing `PYTHONPATH` environment variable hacks. The `tests` package automatically configures the Python path.

```bash
# Run a specific test module
python -m unittest tests.test_post_set_status

# Run a specific test class inside a module
python -m unittest tests.test_post_set_status.TestPostSetStatusValidation

# Run an exact test method
python -m unittest tests.test_post_set_status.TestPostSetStatusValidation.test_not_json_400
```

### Writing New Tests

When creating a new backend test, inherit from the shared `BaseTestCase` located in `tests/helpers.py`.

The `BaseTestCase`:
- Creates a fresh instance of the Flask application (`testing=True`).
- Pushes the application context, meaning you can query `db.session` directly.
- Uses an isolated in-memory SQLite database (`sqlite:///:memory:`) so your tests will never interfere with your local development `instance/app.db`.

**Example:**
```python
import unittest
from tests.helpers import BaseTestCase, create_test_user, get_json

class TestMyFeature(BaseTestCase):
    def setUp(self) -> None:
        # super().setUp() handles the app, database, and client creation
        super().setUp()
        
    def test_example(self):
        # We provide helpers to seed entities safely!
        user = create_test_user(self.app_context, n=1)
        
        response = self.client.get("/api/dashboard/wanted")
        self.assertEqual(response.status_code, 401)
```

## 3. End-to-End Selenium Tests

Selenium tests verify the application exactly how a real user interacts with the browser. 

### Prerequisites

Selenium requires Google Chrome and the matching ChromeDriver executable. **You must set this up before Selenium tests will pass.**
Please follow the detailed setup instructions in [docs/SELENIUM_SETUP.md](SELENIUM_SETUP.md).

### Running Selenium Tests

By default, Selenium tests are executed when you run `make test`.
However, if you want to run *only* the Selenium tests to save time or to debug UI issues:

```bash
python -m unittest tests.test_selenium
```

Discover flows run against **`GET /discover`** (filter UI + `#post-grid` backed by `GET /api/filter`), not **`GET /`**, which renders featured homepage cards instead. Unless you set **`TEST_BASE_URL`** to drive an already-running Flask process, each Selenium session starts its own werkzeug listener on localhost with a seeded tempfile SQLite DB (see **`tests.selenium_support`**).

### Headless vs Headful Mode

By default, the UI tests will likely run in headless mode (no browser window appears). If you need to visually watch what the test is clicking, you can force the browser to appear by overriding the headless environment variable (if your local test configuration supports it):

```bash
SELENIUM_HEADLESS=false python -m unittest tests.test_selenium
```

*(See [docs/SELENIUM_SETUP.md](SELENIUM_SETUP.md) for more details on environment variables).*

## 4. Continuous Integration

Our automated pipelines will automatically run `make test` on every Pull Request.
Branches should not be merged if any unit or Selenium test fails. 

Please ensure you run `make test` locally before requesting a review.
