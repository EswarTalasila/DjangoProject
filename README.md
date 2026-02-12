# EE Lab Data Dashboard

A web application for managing educational assessments, student submissions, and data visualization. This is a Python/Django rewrite of the original Spring Boot application.

## Technology Stack

| Layer      | Technology                                       |
|------------|--------------------------------------------------|
| Frontend   | Next.js, TypeScript, Tailwind                     |
| Backend    | Django 5, Django REST Framework, Python 3.12     |
| Database   | PostgreSQL 17                                    |
| Auth       | JWT (SimpleJWT) + Google OAuth                   |
| Testing    | pytest (backend, 53 tests), Playwright (E2E)     |
| Containers | Docker, Docker Compose, Nginx (reverse proxy)    |

## Prerequisites

- Docker and Docker Compose (recommended)
- OR for local development:
  - Python 3.12+
  - Node.js 22 LTS (see `.nvmrc`)
  - PostgreSQL 17+

## User Guide

### Quick Start (Docker)

1. Clone the repository and navigate to the project root:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Copy the environment template and configure values:
```bash
cp .env.template .env
```

Edit `.env` and set at minimum:
```env
ENVIRONMENT=development
POSTGRES_PASSWORD=your-secure-password
DJANGO_SECRET_KEY=your-secure-random-string
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-oauth-client-id
```

3. Start all services:
```bash
task up:dev
```

4. Run database migrations:
```bash
docker compose exec backend python src/manage.py migrate
```

5. (Optional) Create an admin user:
```bash
docker compose exec backend python src/manage.py createsuperuser
```

6. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/v1/
- Django Admin: http://localhost:8000/admin/

### Docker Services

| Service        | Port | Description                                       |
|----------------|------|---------------------------------------------------|
| `frontend`     | 3000 | Nextjs dev server                                 |
| `backend`      | 8000 | Django REST API                                   |
| `database`     | 5432 | PostgreSQL 17                                     |
| `pgadmin`      | 5050 | Database management UI (auto-connects to database)|
| `nginx`        | 80   | Reverse proxy (production routing)                |
| `frontend-e2e` | -    | Playwright E2E test runner with headless Chromium |

### Roles and Workflows
- Admin: creates assessments and manages users.
- Researcher:
- Teacher: creates courses and assignments, reviews submissions.
- Student: completes assignments and submits answers.
- See `Docs/Specs/01-User-Stories.md` for detailed flows.

## Developer Guide

### Node Version Manager (nvm)
>[!TIP]
>This project uses [nvm](https://github.com/nvm-sh/nvm) to manage Node.js versions. The required version is specified in `.nvmrc`.

```bash
# Install nvm (macOS/Linux)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# Install the project's Node version
nvm install

# Use the project's Node version (run from project root)
nvm use
```

nvm reads the `.nvmrc` file automatically when you run `nvm use` or `nvm install` without a version argument.

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run code quality checks before each commit. Hooks are configured in `.pre-commit-config.yaml`.

```bash
# Install pre-commit (if not already installed)
pip install pre-commit
# or: brew install pre-commit

# Install the git hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

**How it works:**
1. You stage files with `git add`
2. You run `git commit`
3. Pre-commit runs ruff (linter + formatter) on staged files
4. If ruff makes changes, the commit is **aborted** and changes are left unstaged
5. You review the changes, verify they work, re-stage, and commit again

**Configured hooks:**
- **ruff (lint)** - Checks for errors, applies safe auto-fixes (formatting, import sorting)
- **ruff (format)** - Consistent code formatting
- **trailing-whitespace** - Removes trailing whitespace
- **end-of-file-fixer** - Ensures files end with newline
- **check-yaml/check-toml** - Validates config file syntax
- **no-commit-to-branch** - Prevents direct commits to main/master

Unsafe fixes (removing unused imports, code simplification) are reported as warnings for manual review but not auto-applied.

## Task Runner
>[!TIP]
>This project uses [Task](https://taskfile.dev/) for running common commands. Task is a modern alternative to Make with simpler syntax.

### Installing Task

```bash
# macOS
brew install go-task

# Linux (snap)
sudo snap install task --classic

# Linux (apt)
curl -1sLf 'https://dl.cloudsmith.io/public/task/task/setup.deb.sh' | sudo -E bash && sudo apt install task

# Linux (script)
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

# Windows (scoop)
scoop install task

# Windows (chocolatey)
choco install go-task
```

### Available Tasks

Run `task help` for a grouped command guide or `task list` for the raw list. Key tasks:

| Task                       | Description                                |
|----------------------------|--------------------------------------------|
| `task help`                | Show grouped command guide                 |
| `task list`                | Show raw task list (alphanumeric sort)     |
| `task list:json`           | Show task list in JSON                     |
| `task up`                  | Start all services                         |
| `task up:dev`              | Start services in development profile       |
| `task up:test`             | Start services in testing profile + auto-seed |
| `task up:prod`             | Start services in production profile + strict fail-fast |
| `task down`                | Stop all services                          |
| `task otel`                | Enable OpenTelemetry on running backend    |
| `task otel:off`            | Disable OpenTelemetry on running backend   |
| `task proxy`               | Start reverse proxy overlay                |
| `task proxy:off`           | Stop reverse proxy overlay                 |
| `task debug`               | Restart backend in foreground (current profile) |
| `task test`                | Run full test pipeline                     |
| `task test:all`            | Run all test layers                        |
| `task test:unit`           | Run unit tests across backend + frontend   |
| `task test:unit:backend`   | Run backend unit tests                     |
| `task test:unit:frontend`  | Run frontend unit tests (skip if not configured) |
| `task test:integration`    | Run integration tests (backend + frontend placeholder) |
| `task test:integration:backend` | Run backend integration tests         |
| `task test:integration:frontend` | Frontend integration placeholder      |
| `task test:integration:role` | Run role-filtered backend integration tests |
| `task test:security`       | Run security tests (skip if none)          |
| `task test:coverage`       | Run tests with coverage report             |
| `task lint`                | Run ruff linter                            |
| `task lint:fix`            | Run linter with safe auto-fixes            |
| `task format`              | Format code with ruff                      |
| `task typecheck`           | Run mypy type checker                      |
| `task check`               | Run all checks (lint + format + typecheck) |
| `task check:env`           | Run FR-12 env/runtime quality checks       |
| `task docker:rebuild`      | Full rebuild with volume reset             |
| `task docker:rebuild-clean`| Clean everything then rebuild from scratch |
| `task docker:volume-clean` | Remove project volumes (clear cached data) |
| `task docker:clean`        | Full cleanup (containers + volumes)        |
| `task docker:logs-backend` | Follow backend logs                        |
| `task docker:pgadmin`      | Open pgAdmin in browser                    |
| `task docker:db-shell`     | Open psql shell in database container      |
| `task migrate`             | Run Django migrations                      |
| `task hooks:install`       | Install pre-commit hooks                   |
| `task hooks:run`           | Run pre-commit on all files                |
| `task local:sync`          | Install deps locally for IDE support       |
| `task docs`                | Open API docs in browser (Swagger UI)      |
| `task django:shell-plus`   | Enhanced Django shell with auto-imports    |
| `task django:show-urls`    | Show all registered URL patterns           |
| `task diagrams:generate`   | Generate PlantUML from OTEL traces         |
| `task diagrams:index`      | Regenerate diagrams index                  |

### Task Groups

- `up`, `down`, `up:*` - Profile startup and teardown
- `otel`, `otel:off`, `proxy`, `proxy:off`, `debug` - Runtime overlays on a running stack
- `docker:*` - Container management (rebuild, logs, shell)
- `test:*` - Testing (unit, integration, role-filtered, security, e2e)
- `lint`, `format`, `typecheck`, `check` - Code quality
- `hooks:*` - Pre-commit hook management
- `django:*` - Django management commands and extensions
- `docs:*` - API documentation
- `diagrams:*` - PlantUML diagram generation from OTEL traces
- `local:*` - Local development (IDE support)

### Profile Diagnostics Output

Startup profile tasks (`task up:dev`, `task up:test`, `task up:prod`) run `scripts/runtime/profile_guard.py`, which calls backend diagnostics (`python src/manage.py env_report`) and prints concise `ENV-*` / `ENV-P*` messages with fix hints.

- Development/testing: warnings are non-blocking
- Production: strict errors fail startup

Backend-recreate overlays (`task otel`, `task otel:off`) preserve the current runtime profile from the running backend container and then run the same diagnostics guard.

## Common Commands

The following commands work without Task installed. For a streamlined experience, see the Task Runner section above.

### Starting and Stopping

```bash
# Start all services
docker compose up -d

# Start with build (after code changes to Dockerfile)
docker compose up -d --build

# Stop all services
docker compose down

# Stop and remove volumes (resets database)
docker compose down -v

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f backend
```

### Database

```bash
# Run migrations
docker compose exec backend python src/manage.py migrate

# Create new migration after model changes
docker compose exec backend python src/manage.py makemigrations

# Open Django shell
docker compose exec backend python src/manage.py shell

# Open database shell
docker compose exec database psql -U datadash -d datadash
```

#### pgAdmin (Database Management UI)

pgAdmin is available at http://localhost:5050 for visual database management.

- **Login:** `demo@example.com` / `secret`
- **Database:** Pre-configured to auto-connect (no password prompt)
- **Open in browser:** `task docker:pgadmin`

The database connection is automatically configured using credentials from your `.env` file. No manual server setup required.

### Testing

#### Backend Tests (pytest)
```bash
# Run all tests
docker compose exec backend pytest

# Run integration tests only
docker compose exec backend pytest tests/integration -v

# Run workflow tests
docker compose exec backend pytest -m workflow -v

# Run with coverage
docker compose exec backend pytest --cov=src --cov-report=term-missing
```
See `backend/tests/README.md` for test layout and markers.

#### Frontend Tests
```bash
# E2E tests (requires running services)
scripts/e2e/run_playwright.sh
```
Frontend unit/integration task commands are being standardized in the testing-task cleanup pass.

#### E2E Test Setup
```bash
# Seed test users
./scripts/e2e/seed_e2e.sh

# Run Playwright tests
E2E_BASE_URL=http://eel-frontend:3000 \
E2E_API_URL=http://eel-backend:8000/api/v1 \
scripts/e2e/run_playwright.sh
```

## Diagrams (PlantUML + OTEL)

Diagrams are generated in `Docs/diagrams/plantuml/` and indexed in
`Docs/diagrams/plantuml/Diagrams-Index.md`.

### Capture runtime sequences (OTEL)
```bash
# Enable OTEL file export for the backend container
OTEL_ENABLED=true OTEL_TRACE_FILE=/app/traces/trace.jsonl \
  docker compose up -d --force-recreate backend

# Clear old traces and exercise API flows
docker compose exec backend sh -c "echo -n '' > /app/traces/trace.jsonl"
docker compose exec backend sh -c \"E2E_ADMIN_USERNAME=admin@example.com E2E_ADMIN_PASSWORD=change-me OTEL_BASE_URL=http://localhost:8000/api/v1 python /app/scripts/diagrams/capture_otel_sequences.py\"
```

### Render diagrams (runs inside backend container)
```bash
scripts/diagrams/generate_all.sh --trace /app/Docs/diagrams/otel/trace.jsonl
```

>[!TIP]
>`scripts/diagrams/generate_all.sh` runs the generator and refreshes the index.

### Refresh the diagrams index
```bash
scripts/diagrams/index_diagrams.sh
```

### Viewing Diagrams in VSCode

Install the [PlantUML extension](https://marketplace.visualstudio.com/items?itemName=jebbs.plantuml) for VSCode to render `.puml` files directly in the editor:

1. Install the extension from the marketplace
2. Open any `.puml` file in `Docs/diagrams/plantuml/`
3. Use `Alt+D` (Windows/Linux) or `Option+D` (macOS) to preview the diagram
4. The extension supports live preview as you edit

### Future: GitHub Actions for Diagrams

A planned enhancement is to automatically generate and publish diagrams via GitHub Actions:
- Render PlantUML files on push to `main`
- Store generated PNGs/SVGs in GitHub releases or wiki
- Auto-update wiki pages with latest diagrams

This would eliminate the need for local PlantUML rendering and ensure diagrams stay in sync with code changes.

### Code Quality

```bash
# Backend lint + type + docstring checks (Docker)
scripts/lint/run_backend_checks.sh

# Backend docstring coverage only (Docker)
scripts/lint/run_docstring_check.sh

# Frontend linting (Docker)
docker compose run --rm frontend npm install
docker compose run --rm frontend npm run lint
```

## Local Development (Without Docker)

### Backend with uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that handles virtual environments and dependencies. It's 10-100x faster than pip.

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install uv (Windows)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Navigate to backend
cd backend

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Set environment variables (or use .env file)
export DATABASE_URL=postgres://user:pass@localhost:5432/datadash
export DJANGO_SECRET_KEY=local-dev-secret
export ENVIRONMENT=development

# Run migrations
python src/manage.py migrate

# Start development server
python src/manage.py runserver
```

**IDE Support:** If using Docker for development but want IDE autocompletion, run:
```bash
cd backend && uv venv && uv pip install -e ".[dev]"
```
This installs dependencies locally so your IDE can resolve imports without running the app locally.

### Backend with pip (Alternative)

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set environment variables (or use .env file)
export DATABASE_URL=postgres://user:pass@localhost:5432/datadash
export DJANGO_SECRET_KEY=local-dev-secret
export ENVIRONMENT=development

# Run migrations
python src/manage.py migrate

# Start development server
python src/manage.py runserver
```

### Frontend

```bash
cd frontend

# Use correct Node version
nvm use

# Install dependencies
npm install

# Start development server (with API proxy)
npm run dev
```

## Project Structure

```
<repository>/
├── backend/                 # Django REST API
│   ├── src/
│   │   ├── accounts/        # User auth and profiles
│   │   ├── assessments/     # Assessment templates and questions
│   │   ├── assignments/     # Assignment distribution
│   │   ├── courses/         # Course and enrollment management
│   │   ├── submissions/     # Student/teacher submissions
│   │   ├── visualizations/  # Data aggregation for dashboards
│   │   ├── exports/         # CSV/PDF export (stub)
│   │   ├── core/            # Shared utilities and permissions
│   │   └── config/          # Django settings and URLs
│   └── tests/               # pytest test suite
├── frontend/                # Next.js frontend
│   ├── app/                 # App Router pages and routes
│   ├── components/          # Shared UI components
│   ├── lib/                 # API client and frontend utilities
│   └── tests/e2e/           # Playwright E2E tests
├── Docs/
│   ├── Specs/               # Technical specifications
│   └── diagrams/            # PlantUML and OpenTelemetry diagrams
├── Deployment/templates/    # Docker and CI/CD templates
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Development container orchestration
└── .env.template            # Environment variable reference
```

## Environment Variables

See `.env.template` for the full list. Key variables:

| Variable                       | Description                                  | Required   |
|--------------------------------|----------------------------------------------|------------|
| `ENVIRONMENT`                  | Runtime profile (`development/testing/production`) | Yes |
| `POSTGRES_PASSWORD`            | Database password                            | Yes        |
| `DJANGO_SECRET_KEY`            | Django secret for sessions/CSRF              | Yes        |
| `DJANGO_ALLOWED_HOSTS`         | Comma-separated allowed hosts                | Yes (prod) |
| `DJANGO_CORS_ALLOWED_ORIGINS`  | Comma-separated CORS origins                 | Yes (prod) |
| `GOOGLE_CLIENT_ID`             | Backend Google OAuth client ID               | Yes (prod) |
| `GOOGLE_CLIENT_SECRET`         | Backend Google OAuth client secret           | Yes (prod) |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Frontend Google OAuth client ID              | Yes (prod) |
| `NEXT_PUBLIC_API_URL`          | Frontend API base URL                        | Yes        |
| `OTEL_TRACE_FILE`              | Local OTEL JSONL trace output (do not commit)| No         |

`DJANGO_DEBUG` is intentionally profile-derived from `ENVIRONMENT` in Docker workflows.

## API Endpoints

The API is versioned under `/api/v1/`. Key endpoint groups:

| Path                      | Description                             |
|---------------------------|-----------------------------------------|
| `/api/v1/auth/`           | Authentication (login, register, OAuth) |
| `/api/v1/assessments/`    | Assessment CRUD (admin only)            |
| `/api/v1/assignments/`    | Assignment distribution                 |
| `/api/v1/courses/`        | Course management                       |
| `/api/v1/students/`       | Student enrollment                      |
| `/api/v1/submissions/`    | Submission create/read/grade            |
| `/api/v1/visualizations/` | Dashboard data aggregation              |

### API Documentation (Interactive)

| Path           | Description                                      |
|----------------|--------------------------------------------------|
| `/api/docs/`   | Swagger UI - Interactive API documentation       |
| `/api/redoc/`  | ReDoc - Alternative API documentation viewer     |
| `/api/schema/` | OpenAPI 3.0 schema (YAML)                        |

See `Docs/Specs/12-API-Contract.md` for full API documentation.

## Authentication

This section covers setting up authentication for local development and API testing.

### Django Admin Setup

Create a superuser to access the Django admin panel:

```bash
# Using Task runner
task django:createsuperuser

# Or using docker compose directly
docker compose exec backend python src/manage.py createsuperuser
```

Follow the prompts to set email, name, and password. Access the admin panel at http://localhost:8000/admin/.

The admin panel allows:
- User management (create, edit, delete users)
- Role assignment (admin, teacher, student)
- Course and enrollment management
- Assessment and question management
- Submission review

### JWT Token Authentication

The API uses JWT (JSON Web Tokens) for authentication. Tokens are obtained via the login endpoint.

**Token lifetimes:**
- Access token: 1 hour
- Refresh token: 7 days

**Obtaining tokens:**

```bash
# Login to get tokens
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@example.com", "password": "your-password"}'

# Response:
# {
#   "accessToken": "eyJhbGciOiJIUzI1NiIs...",
#   "tokenType": "Bearer",
#   "role": "admin",
#   "id": "1"
# }
```

**Using tokens in requests:**

```bash
curl -X GET http://localhost:8000/api/v1/assessments/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### Swagger UI Authentication

The interactive API documentation at `/api/docs/` supports JWT authentication:

1. **Get a token** - Use the login endpoint above or via Swagger UI itself:
   - Expand `/api/v1/auth/login/`
   - Click "Try it out"
   - Enter credentials and execute
   - Copy the `accessToken` from the response

2. **Authorize Swagger UI**:
   - Click the "Authorize" button (lock icon) at the top right
   - Enter: `Bearer <your-access-token>` (include the word "Bearer")
   - Click "Authorize"

3. **Test authenticated endpoints** - All subsequent requests will include your token

**Note:** The `persistAuthorization: true` setting keeps your token between page refreshes.

### Troubleshooting Authentication

**Token expired:**
- Access tokens expire after 1 hour
- Re-authenticate via login endpoint to get new tokens

**"Authentication credentials were not provided":**
- Ensure the Authorization header is set
- Format must be: `Bearer <token>` (note the space)

**"Token is invalid or expired":**
- Token may have been revoked or expired
- Re-authenticate to get fresh tokens

**CORS errors in browser:**
- Check `DJANGO_CORS_ALLOWED_ORIGINS` includes your frontend URL
- Default: `http://localhost:3000`

## Django Patterns Reference

This section explains common Django and Django REST Framework patterns used throughout the backend. For newcomers to Django, this serves as a quick reference for understanding the codebase.

### Official Documentation

- [Django 5.2 Documentation](https://docs.djangoproject.com/en/5.2/) - Models, views, ORM, admin
- [Django REST Framework](https://www.django-rest-framework.org/) - Serializers, viewsets, permissions
- [Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/) - JWT authentication

### Models (`models.py`)

Models define database tables. Each class attribute becomes a column.

```python
class Course(models.Model):
    """A course taught by a teacher."""

    name = models.CharField(max_length=255)           # VARCHAR(255)
    teacher = models.ForeignKey(                       # Foreign key relationship
        User,
        on_delete=models.CASCADE,                      # Delete courses when teacher deleted
        related_name="courses_taught"                  # Access via user.courses_taught.all()
    )
    created_at = models.DateTimeField(auto_now_add=True)  # Set once on creation
```

**Key concepts:**
- `on_delete=CASCADE` - Delete related records when parent is deleted
- `on_delete=PROTECT` - Prevent deletion if related records exist
- `related_name` - Reverse accessor name on the related model

### Admin Registration (`admin.py`)

The `@admin.register()` decorator registers a model with Django's admin interface.

```python
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "teacher", "created_at")  # Columns in list view
    list_filter = ("teacher",)                         # Sidebar filters
    search_fields = ("name", "teacher__username")      # Searchable fields
    ordering = ("-created_at",)                        # Default sort order
```

### Serializers (`serializers.py`)

Serializers convert between Python objects and JSON. They handle validation and nested relationships.

```python
class CourseSerializer(serializers.ModelSerializer):
    """Converts Course model to/from JSON."""

    class Meta:
        model = Course
        fields = ["id", "name", "teacher", "created_at"]
        read_only_fields = ["id", "created_at"]
```

**Common serializer types:**
- `ModelSerializer` - Automatic field generation from model
- `Serializer` - Manual field definitions for custom input/output

### Views (`views.py`)

Views handle HTTP requests. We use function-based views with DRF decorators.

```python
@api_view(["GET", "POST"])           # Allowed HTTP methods
@permission_classes([IsTeacher])     # Who can access this endpoint
def course_list(request):
    if request.method == "GET":
        courses = Course.objects.filter(teacher=request.user)
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)
    # POST handling...
```

### Permission Classes (`core/permissions.py`)

Custom permission classes control endpoint access based on user roles.

```python
class IsTeacher(permissions.BasePermission):
    """Only allow teachers to access this view."""

    def has_permission(self, request, view):
        return has_role(request.user, Role.TEACHER)
```

**Usage:** `@permission_classes([IsTeacher])` or `@permission_classes([IsTeacherOrAdmin])`

### URL Routing (`urls.py`)

URLs map paths to view functions.

```python
urlpatterns = [
    path("courses/", views.course_list, name="course-list"),
    path("courses/<int:pk>/", views.course_detail, name="course-detail"),
]
```

### Common QuerySet Methods

```python
# Get all records
Course.objects.all()

# Filter records
Course.objects.filter(teacher=user)

# Get single record (raises DoesNotExist if not found)
Course.objects.get(pk=1)

# Get or None
Course.objects.filter(pk=1).first()

# Related object traversal
course.enrollments.all()           # Forward: course -> enrollments
enrollment.course                   # Backward: enrollment -> course
```

## Documentation

- `Docs/Specs/` - Technical specifications and architecture decisions
- `Docs/Specs/08-Migration-Plan.md` - Migration status and known issues
- `Docs/Specs/10-Development-Workflow.md` - Detailed development setup
- `Docs/Specs/11-Code-Style-and-Architecture.md` - Code conventions
- `Docs/diagrams/plantuml/` - PlantUML class/entity/sequence diagrams

## Known Issues

See `Docs/Specs/08-Migration-Plan.md` for tracked issues including:
- First-login password flow needs token-based security
- JWT stored in localStorage (XSS consideration)
- Export endpoints return 501 (not yet implemented)

## Contributing

1. Create a feature branch from `main`
2. Install pre-commit hooks: `pre-commit install`
3. Follow the code style in `Docs/Specs/11-Code-Style-and-Architecture.md`
4. Add tests for new functionality
5. Run `task check` before committing (or let pre-commit hooks run automatically)
6. Submit a pull request with a clear description
