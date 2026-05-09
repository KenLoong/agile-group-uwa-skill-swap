.PHONY: help run test migrate seed clean

# Default target when just running 'make'
help:
	@echo "UWA Skill-Swap Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make run      - Start the Flask application locally for development"
	@echo "  make test     - Run the full project test suite via unittest"
	@echo "  make migrate  - Apply database migrations using Flask-Migrate"
	@echo "  make seed     - Prepare demo or test data for local testing"
	@echo "  make clean    - Remove common temporary and generated cache files safely"

run:
	@echo "Starting Flask development server..."
	flask --app "app:create_production_app" run --debug

test:
	@echo "Running tests..."
	python -m unittest discover tests

migrate:
	@echo "Applying database migrations..."
	flask --app "app:create_production_app" db upgrade

seed:
	@echo "Seeding test/demo data..."
	python seed.py

clean:
	@echo "Removing temporary files and Python cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .coverage htmlcov
	@echo "Cleanup complete."
