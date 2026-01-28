# EEL Data Dashboard - Frontend

Angular SPA frontend for the EE Lab Data Dashboard.

## Stack

- Angular 18
- TypeScript
- SCSS
- Playwright (E2E testing)
- ECharts (visualizations)

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── features/              # Feature modules
│   │   │   ├── account/           # Account management
│   │   │   ├── assessments/       # Assessment views and templates
│   │   │   ├── assignments/       # Assignment creation
│   │   │   ├── course/            # Course management
│   │   │   ├── dashboard/         # Data visualization
│   │   │   ├── login/             # Authentication
│   │   │   └── ...
│   │   ├── guards/                # Route guards (role-based)
│   │   ├── app.routes.ts          # Route definitions
│   │   ├── app.config.ts          # App configuration
│   │   └── auth.interceptor.ts    # JWT interceptor
│   ├── services/                  # API client services
│   ├── models/                    # TypeScript interfaces
│   └── styles.scss                # Global styles
├── tests/
│   └── e2e/                       # Playwright E2E tests
│       ├── api/                   # API-level tests
│       ├── crud/                  # CRUD operation tests
│       ├── smoke/                 # Smoke tests
│       ├── workflows/             # Full workflow tests
│       ├── fixtures/              # Test data
│       ├── helpers/               # Test utilities
│       └── global-setup.ts        # Test setup
├── playwright.config.ts           # Playwright configuration
├── proxy.conf.js                  # Dev server proxy config
├── angular.json                   # Angular CLI configuration
└── package.json
```

## Prerequisites

- Node.js 20+ (see `.nvmrc` for exact version)
- npm 10+

```bash
# If using nvm
nvm install
nvm use
```

## Local Development

### With Docker (recommended)

From the project root:
```bash
docker compose up -d frontend
```

The frontend will be available at http://localhost:4200 with hot reload.

### Without Docker

```bash
# Install dependencies
npm install

# Start development server with API proxy
npm start
```

The dev server proxies `/api/*` requests to `http://localhost:8000` by default. Configure via `proxy.conf.js` or environment variables.

## Building

```bash
# Development build
npm run build

# Production build
npm run build -- --configuration=production

# Build output is in dist/frontend/
```

## Testing

### Unit Tests

```bash
# Run unit tests
npm test

# Run tests with coverage
npm test -- --code-coverage

# Run tests in watch mode
npm test -- --watch
```

### E2E Tests (Playwright)

#### Prerequisites

1. Backend and frontend must be running
2. E2E test users must be seeded

```bash
# Seed test users (from project root)
./scripts/e2e/seed_e2e.sh
```

#### Running E2E Tests

```bash
# Run all E2E tests
npm run e2e

# Run with headed browser (visible)
npm run e2e -- --headed

# Run specific test file
npm run e2e -- tests/e2e/workflows/teacher-grading.spec.ts

# Run tests matching pattern
npm run e2e -- --grep "login"
```

#### E2E Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `E2E_BASE_URL` | Frontend URL | `http://localhost:4200` |
| `E2E_API_URL` | Backend API URL | `http://localhost:8000/api/v1` |
| `E2E_START_SERVER` | Auto-start frontend | `false` |
| `E2E_ADMIN_USERNAME` | Test admin email | From fixture |
| `E2E_ADMIN_PASSWORD` | Test admin password | From fixture |

#### Test Categories

| Directory | Description |
|-----------|-------------|
| `tests/e2e/smoke/` | Basic login and navigation |
| `tests/e2e/api/` | API-level tests |
| `tests/e2e/crud/` | Create, update, delete operations |
| `tests/e2e/workflows/` | Full user workflows |

## Code Quality

```bash
# Install dependencies (Docker)
docker compose run --rm frontend npm install

# Linting (Docker)
docker compose run --rm frontend npm run lint

# Fix linting issues (Docker)
docker compose run --rm frontend npm run lint -- --fix
```

## Common Commands

```bash
# Start dev server
npm start

# Start with custom host (for Docker)
npm start -- --host 0.0.0.0

# Build production
npm run build -- --configuration=production

# Run unit tests (headless)
docker compose run --rm frontend npm install
docker compose run --rm frontend npm test

# Run unit tests with watch mode
docker compose run --rm frontend npm run test:watch

# Run E2E tests
scripts/e2e/run_playwright.sh

# Generate component
ng generate component features/my-component

# Generate service
ng generate service services/my-service
```

## API Proxy Configuration

The development server proxies API requests to the backend. Configuration is in `proxy.conf.js`:

```javascript
module.exports = {
  '/api': {
    target: process.env.PROXY_TARGET || 'http://localhost:8000',
    secure: false,
    changeOrigin: true,
  },
};
```

Set `PROXY_TARGET` environment variable to change the backend URL.

## Key Components

| Component | Path | Description |
|-----------|------|-------------|
| Login | `features/login/` | User authentication |
| Dashboard | `features/dashboard/` | Data visualizations |
| Assessment List | `features/assessments/admin-assessment-list/` | Admin assessment management |
| Assessment Template | `features/assessments/assessment-template/` | Question type components |
| Course View | `features/course/view/` | Course details and students |
| Gradebook | `features/assessments/teacher-assessment/gradebook/` | Teacher grading interface |

## Services

| Service | Description |
|---------|-------------|
| `user.service.ts` | Authentication and user management |
| `course.service.ts` | Course CRUD operations |
| `assessment-service.ts` | Assessment management |
| `assignment.service.ts` | Assignment distribution |
| `student.service.ts` | Student enrollment |
| `visualization.service.ts` | Dashboard data fetching |

## Authentication

- JWT tokens are stored in `localStorage`
- `auth.interceptor.ts` attaches tokens to API requests
- `role.guard.ts` protects routes based on user roles

## Notes

- The frontend maintains API compatibility with the original Spring Boot backend
- All API calls use `/api/v1/` prefix
- Role-based routing: ADMIN, TEACHER, STUDENT
