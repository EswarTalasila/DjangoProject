# EE Lab Data Dashboard

A web application for managing educational assessments, student submissions, and data visualization. This is a Python/Django rewrite of the original Spring Boot application, maintaining full API compatibility with the existing Angular frontend.

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Angular 21, TypeScript, SCSS |
| Backend | Django 5, Django REST Framework, Python 3.12 |
| Database | PostgreSQL 16 |
| Auth | JWT (SimpleJWT) + Google OAuth |
| Testing | pytest (backend, 53 tests), Playwright (E2E) |
| Containers | Docker, Docker Compose, Traefik (reverse proxy) |

## Prerequisites

- Docker and Docker Compose (recommended)
- OR for local development:
  - Python 3.12+
  - Node.js 22 LTS (see `.nvmrc`)
  - PostgreSQL 16+

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
POSTGRES_PASSWORD=your-secure-password
DJANGO_SECRET_KEY=your-secure-random-string
JWT_SECRET_KEY=your-secure-random-string
```

3. Start all services:
```bash
docker compose up -d
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
- Frontend: http://localhost:4200
- Backend API: http://localhost:8000/api/v1/
- Django Admin: http://localhost:8000/admin/

### Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 4200 | Angular dev server with hot reload |
| `backend` | 8000 | Django REST API |
| `database` | 5432 | PostgreSQL 16 |
| `traefik` | 80 | Reverse proxy (production routing) |
| `frontend-e2e` | - | Playwright E2E test runner with headless Chromium |

### Roles and Workflows
- Admin: creates assessments and manages users.
- Teacher: creates courses and assignments, reviews submissions.
- Student: completes assignments and submits answers.
- See `Docs/Specs/01-User-Stories.md` for detailed flows.

## Developer Guide

### Node Version Manager (nvm)

This project uses [nvm](https://github.com/nvm-sh/nvm) to manage Node.js versions. The required version is specified in `.nvmrc`.

```bash
# Install nvm (macOS/Linux)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# Install the project's Node version
nvm install

# Use the project's Node version (run from project root)
nvm use
```

nvm reads the `.nvmrc` file automatically when you run `nvm use` or `nvm install` without a version argument.

## Common Commands

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
# Install frontend deps (Docker)
docker compose run --rm frontend npm install

# Unit tests
docker compose run --rm frontend npm test

# Unit tests (watch mode)
docker compose run --rm frontend npm run test:watch

# E2E tests (requires running services)
scripts/e2e/run_playwright.sh
```
See `frontend/tests/e2e/README.md` for E2E structure and specs.

#### E2E Test Setup
```bash
# Seed test users
./scripts/e2e/seed_e2e.sh

# Run Playwright tests
E2E_BASE_URL=http://eel-frontend:4200 \
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
Note: `scripts/diagrams/generate_all.sh` runs the generator and refreshes the index.

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

### Backend

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
export DJANGO_DEBUG=true

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
npm start
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
├── frontend/                # Angular SPA
│   ├── src/
│   │   ├── app/             # Components and routing
│   │   ├── services/        # API client services
│   │   └── models/          # TypeScript interfaces
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

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_PASSWORD` | Database password | Yes |
| `DJANGO_SECRET_KEY` | Django secret for sessions/CSRF | Yes |
| `JWT_SECRET_KEY` | JWT signing key | Yes |
| `DJANGO_DEBUG` | Enable debug mode (false in prod) | No |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | Yes (prod) |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins | Yes (prod) |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID | No |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth client secret | No |
| `OTEL_TRACE_FILE` | Local OTEL JSONL trace output (do not commit) | No |

## API Endpoints

The API is versioned under `/api/v1/`. Key endpoint groups:

| Path | Description |
|------|-------------|
| `/api/v1/auth/` | Authentication (login, register, OAuth) |
| `/api/v1/assessments/` | Assessment CRUD (admin only) |
| `/api/v1/assignments/` | Assignment distribution |
| `/api/v1/courses/` | Course management |
| `/api/v1/students/` | Student enrollment |
| `/api/v1/submissions/` | Submission create/read/grade |
| `/api/v1/visualizations/` | Dashboard data aggregation |

See `Docs/Specs/12-API-Contract.md` for full API documentation.

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
2. Follow the code style in `Docs/Specs/11-Code-Style-and-Architecture.md`
3. Add tests for new functionality
4. Run linting and tests before committing
5. Submit a pull request with a clear description
