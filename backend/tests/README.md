# Backend Tests

Pytest suite for the Django API.

## Structure
- `integration/`: API integration tests (requests against DRF views).
- `unit/`: Unit tests (placeholder).
- `security/`: Security-focused tests (placeholder).
- `fixtures/`: JSON fixtures for seeded users.
- `conftest.py`: Shared pytest fixtures.
- `factories.py`: Factory helpers for model setup.

## Run
```bash
# All tests
pytest

# Integration only
pytest tests/integration -v

# Workflow markers
pytest -m workflow -v
pytest -m workflow_teacher -v
pytest -m workflow_student -v

# Security marker
pytest -m security -v
```

## Markers
- `integration`: API-level tests.
- `security`: Security-focused authorization and abuse-path tests.
- `workflow`: End-to-end workflow suites.
- `workflow_admin`, `workflow_teacher`, `workflow_student`: Role-specific workflows.
- `workflow_error`: Error-path workflow coverage.

## Index
### Integration

- `integration/test_accounts_routes.py`
- `integration/test_assignment_templates_routes.py`
- `integration/test_assignments_errors.py`
- `integration/test_assignments_routes.py`
- `integration/test_auth_errors.py`
- `integration/test_courses_routes.py`
- `integration/test_submissions_errors.py`
- `integration/test_submissions_routes.py`
- `integration/test_visualizations_routes.py`
- `integration/test_workflows.py`
- `integration/test_workflows_extended.py`

### Unit

- `unit/__init__.py`

### Security

- `security/__init__.py`
- `security/test_authz_security.py`
