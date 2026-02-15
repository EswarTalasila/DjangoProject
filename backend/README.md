# EEL Data Dashboard - Backend

Django REST Framework API backend for the EE Lab Data Dashboard.

## Stack

- Python 3.12
- Django 5.0
- Django REST Framework
- PostgreSQL 16
- JWT Authentication (SimpleJWT)
- OpenTelemetry instrumentation

## Project Structure

```
backend/
├── src/
│   ├── accounts/          # User models, auth views, profile services
│   ├── assessments/       # Assessment templates, questions, grading modes
│   ├── assignments/       # Assignment creation and distribution
│   ├── courses/           # Course CRUD, enrollment, student management
│   ├── submissions/       # Submission lifecycle, grading, score override
│   ├── visualizations/    # Dashboard data aggregation
│   ├── exports/           # CSV/PDF export (stub)
│   ├── core/              # Shared permissions, error handlers, otel
│   ├── config/            # Django settings, URL routing, WSGI/ASGI
│   └── manage.py
├── tests/
│   ├── integration/       # API integration tests
│   ├── unit/              # Unit tests (TODO)
│   ├── security/          # Security tests (TODO)
│   ├── conftest.py        # pytest fixtures
│   └── factories.py       # factory_boy model factories
├── pyproject.toml         # Dependencies and tool config
└── Dockerfile
```

## Local Development

### With Docker (recommended)

From the project root:
```bash
docker compose up -d
docker compose exec backend python src/manage.py migrate
docker compose exec backend python src/manage.py runserver 0.0.0.0:8000
```

### Without Docker

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Set required environment variables
export DATABASE_URL=postgres://datadash:password@localhost:5432/datadash
export DJANGO_SECRET_KEY=local-dev-secret-key
export ENVIRONMENT=development
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Run migrations
python src/manage.py migrate

# Start development server
python src/manage.py runserver
```

## Testing

```bash
# Run all tests
pytest

# Run integration tests with verbose output
pytest tests/integration -v

# Run specific workflow tests
pytest -m workflow -v
pytest -m workflow_teacher -v
pytest -m workflow_student -v

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run with coverage HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `unit` | Unit tests |
| `integration` | Integration tests |
| `security` | Security tests |
| `workflow` | Full workflow tests |
| `workflow_admin` | Admin-specific workflows |
| `workflow_teacher` | Teacher-specific workflows |
| `workflow_student` | Student-specific workflows |
| `workflow_error` | Error path workflows |
| `slow` | Long-running tests |

## Code Quality (Docker)

```bash
# Lint + type + docstring checks
scripts/lint/run_backend_checks.sh

# Docstring-only coverage check
scripts/lint/run_docstring_check.sh
```

## Management Commands

```bash
# Ensure bootstrap admin exists (idempotent; strict validation in production)
python src/manage.py ensure_admin

# Create superuser
python src/manage.py createsuperuser

# Seed E2E test data
python src/manage.py seed_e2e

# Environment diagnostics report (profile-aware)
python src/manage.py env_report --profile development
python src/manage.py env_report --profile testing
python src/manage.py env_report --profile production --strict

# Open Django shell
python src/manage.py shell

# Generate migrations
python src/manage.py makemigrations

# Apply migrations
python src/manage.py migrate

# Show migration status
python src/manage.py showmigrations
```

## API Overview

Base URL: `/api/v1/`

For canonical endpoint definitions, use:
- `/Users/znboston/Learning/csc492/2026Spring-Team26-EE-Lab/Docs/Wiki/API-Reference.md`

Quick auth/registration snapshot:

| Endpoint | Methods | Auth | Description |
|----------|---------|------|-------------|
| `/auth/sessions` | POST | Public | User login via identifier/password |
| `/auth/sessions/oauth` | POST | Public | Google OAuth login |
| `/auth/token-exchanges` | POST | Public | Exchange refresh token for access token |
| `/auth/session-revocations` | POST | Access token | Revoke refresh token / logout |
| `/auth/password` | PATCH | Access token | Change password |
| `/registration/code-validations` | POST | Public | Validate registration code |
| `/registration/accounts` | POST | Public | Register account (`method: LOCAL|OAUTH`) |
| `/enrollments` | POST | Student | Join course with student code |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime profile (`development/testing/production`) | `development` |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `DJANGO_SECRET_KEY` | Django secret key | Required |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `localhost` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Required in production |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Required in production |
| `OTEL_ENABLED` | Enable OpenTelemetry | Profile-driven default |
| `OTEL_SERVICE_NAME` | Service name for traces | `eel-backend` |
| `OTEL_TRACE_FILE` | Path for trace output | `traces.jsonl` |

## Architecture Notes

- Services layer handles business logic (see `*/services.py`)
- Views are thin wrappers calling services
- Serializers handle validation and DTO transformation
- Permissions are in `core/permissions.py`
- Models use explicit `db_table` and `db_column` for schema compatibility
