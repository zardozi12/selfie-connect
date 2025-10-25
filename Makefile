# PhotoVault Makefile - One-command dev cycle
PY=python
UVICORN=uvicorn app.main:app --host 127.0.0.1 --port 8999 --reload

# Environment variables
export DATABASE_URL?=sqlite://./photovault.db
export JWT_SECRET?=dev-secret-please-change-in-production
export MASTER_KEY?=dev-master-please-change-in-production
export STORAGE_DIR?=./storage
export EMBEDDINGS_PROVIDER?=phash
export REDIS_URL?=redis://localhost:6379/0
export METRICS_ENABLED?=1

# Development
dev:
	@echo "🚀 Starting PhotoVault development server..."
	$(UVICORN)

dev-docker:
	@echo "🐳 Starting PhotoVault with Docker Compose..."
	docker compose up -d --build

worker:
	@echo "⚙️ Starting background worker..."
	rq worker -u $(REDIS_URL) photovault

# Testing
test:
	@echo "🧪 Running tests..."
	pytest -q

test-fast:
	@echo "⚡ Running fast tests (parallel)..."
	pytest -q -k "not slow" -n auto

test-coverage:
	@echo "📊 Running tests with coverage..."
	pytest --cov=app --cov-report=html

# Database
init-db:
	@echo "🗄️ Initializing database..."
	$(PY) init_db.py

seed-admin:
	@echo "👑 Setting up admin user..."
	$(PY) -c "import sqlite3; c=sqlite3.connect('photovault.db'); c.execute('update user set is_admin=1 where email=\"test@test.com\"'); c.commit(); c.close(); print('✅ Admin user set')"

# Code quality
fmt:
	@echo "🎨 Formatting code..."
	ruff check --fix . || true
	black .

lint:
	@echo "🔍 Linting code..."
	ruff check .
	black --check .

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	rm -rf .pytest_cache storage __pycache__ *.sqlite* .coverage htmlcov/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Production
prod:
	@echo "🚀 Starting production server..."
	gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --timeout 120 --bind 0.0.0.0:8999

# Help
help:
	@echo "PhotoVault Development Commands:"
	@echo "  make dev          - Start development server"
	@echo "  make dev-docker   - Start with Docker Compose"
	@echo "  make worker       - Start background worker"
	@echo "  make test         - Run tests"
	@echo "  make test-fast    - Run tests in parallel"
	@echo "  make init-db      - Initialize database"
	@echo "  make seed-admin   - Set up admin user"
	@echo "  make fmt          - Format code"
	@echo "  make lint         - Lint code"
	@echo "  make clean        - Clean up files"
	@echo "  make prod         - Start production server"
	@echo "  make help         - Show this help"

.PHONY: dev dev-docker worker test test-fast test-coverage init-db seed-admin fmt lint clean prod help

security:
	@echo "🛡️ Running security scans..."
	python -m pip install --quiet bandit semgrep || true
	bandit -r app -q || true
	semgrep --error --config=auto || true

docker:
	@echo "🐳 Building backend container..."
	docker build -f Dockerfile -t photovault-backend:latest .
