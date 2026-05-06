# Marker Runbook

This guide is designed for markers, graders, and contributors who need to reliably set up, reset, and test the **UWA Skill-Swap** application from a fresh state. 

We have provided a `Makefile` to simplify common commands.

## 1. Initial Setup & Virtual Environment

Before running any commands, ensure your virtual environment is activated and dependencies are installed.

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Resetting the Database & Applying Migrations

If you need to start from a completely clean state (e.g. to wipe existing user data), follow these steps to reset the database and apply the latest schema:

```bash
# 1. Remove the existing local SQLite database
rm -rf instance/

# 2. Apply all migrations to build a fresh schema
make migrate
```
*(Under the hood, `make migrate` runs `flask db upgrade`)*

## 3. Seeding Test Data

To populate the application with reliable test data (e.g., test users, sample posts, tags, and categories) for manual UI testing:

```bash
export SECRET_KEY="dev-local-secret-for-checkpoint"
make seed
```
*(Under the hood, `make seed` runs `python seed.py`)*

**Demo Accounts:** You can log in using `alice@student.uwa.edu.au`, `bob@student.uwa.edu.au`, or `carol@student.uwa.edu.au` (Password: `demo12345`).

## 4. Running the Application

Once the database is migrated and seeded, you can start the local development server using the production factory:

```bash
export SECRET_KEY="dev-local-secret-for-checkpoint"
make run
```
The app will be available at `http://127.0.0.1:5000`.

## 5. Running the Test Suite

We use `unittest` for both our unit and integration/Selenium tests. To run the full test suite in one go:

```bash
make test
```
*(Under the hood, `make test` runs `python -m unittest discover tests`)*

If you want to clean up Python cache files and test coverage artifacts after running tests, use:
```bash
make clean
```
