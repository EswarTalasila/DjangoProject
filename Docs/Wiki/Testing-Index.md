# Testing — Index

| Field | Value |
|-------|-------|
| **Status** | FINAL |
| **Scope** | Cross-domain testing policy |
| **Applies To** | All FR domains |
| **Last Updated** | 2026-02-10 |

---

## 1) Test Layers (per domain)

Each domain (FR) should include the following testing layers within its detail doc:

- **Backend Unit** — service logic, validators, constraints, policy rules
- **Frontend Unit** — component rendering, form validation, client-side state
- **Backend Integration** — API flows with database
- **Frontend Integration** — UI flows + mocked backend responses
- **Security** — auth, role guards, abuse cases, rate limits
- **E2E (Playwright)** — browser-based multi-role flows
- **System Tests (Black Box)** — scripted walkthroughs tied to UC + error paths

> Each FR doc should list all relevant tests under the UC it validates.

---

## 2) Naming Conventions

### Unit / Integration / E2E / Security

```
# Backend unit
 test_{DOMAIN}_UC_##_{ROLE}
 test_{DOMAIN}_UC_##_E#
 test_{DOMAIN}_CN_##

# Frontend unit
 test_{DOMAIN}_UC_##_form_validation
 test_{DOMAIN}_UC_##_error_display

# Backend integration
 test_{DOMAIN}_UC_##_flow

# Frontend integration
 test_{DOMAIN}_UC_##_ui_flow

# Security
 test_{DOMAIN}_UC_##_security

# E2E
 test_{DOMAIN}_UC_##_e2e_flow
```

### System Tests (Black Box)

```
ST-{DOMAIN}-UC-##
ST-{DOMAIN}-UC-##-E#
```

System tests should trace to:
- UC or UC error
- Wireframe screen ID(s)
- Relevant constraints

---

## 3) System Test Template

```
ST-REG-UC-01: Invalid Access Code Rejection

Precondition:
- No account exists for tester
- No valid access code is held

Steps:
1. Navigate to landing page
2. Click "Register with Access Code"
3. Enter code ZZZZ-0000-XXXX and click "Verify Code"

Expected:
- Error message: "Invalid access code"
- No account created

Traces to:
- REG-UC-01-E1
- Wireframe C1b
- REG-CN-01, REG-CN-02, REG-CN-05
```

---

## 4) Tooling

| Layer | Tooling | Version | Notes |
|-------|---------|---------|-------|
| Backend Unit | pytest + pytest-django | 8.0+ | Service + validator logic |
| Frontend Unit | Vitest + React Testing Library | 3.x / 16.x | Next.js + React + Tailwind |
| Backend Integration | pytest + DRF APIClient | 8.0+ | Django REST API flows |
| Frontend Integration | React Testing Library + MSW | 16.x / 2.x | Mocked APIs (Client Components only; async Server Components use E2E) |
| Security | pytest + @security marker | 8.0+ | Role guards, rate limits, abuse cases |
| E2E | Playwright | 1.x | Browser workflows |
| System Tests | Manual scripts | N/A | Human-run walkthroughs |
| SAST | Bandit (Python) + ESLint security (JS/TS) | 1.9.x / latest | Pre-commit + CI enforcement |
| DAST | OWASP ZAP baseline scan | stable (Docker) | CI on PR/merge to development/master (report-only mode) |

---

## 5) Coverage Rules

- Every UC must have:
  - At least **1 Backend Unit** test
  - At least **1 Integration** test
  - At least **1 E2E** or **System Test**
- Every UC error path must have:
  - At least **1 Backend Unit** test
  - At least **1 System Test**

See Section 8 for threshold enforcement policy and CI integration.

---

## 6) Notes

- Use role-split tests even when UC is "ALL" (no ALL in test names).
- System tests are black-box and should not rely on code knowledge.
- Security tests should be domain-specific (e.g., AUTH rate limiting).
- E2E seeding uses deterministic defaults by default; `.env.template` should not require E2E identity variables.
- E2E identity env vars are override-only for targeted scenarios or CI specialization.
- Runtime diagnostics code assertions (`ENV-*`, `ENV-P*`) are defined in `Diagnostics-Index.md` and should be used for startup/profile guard validation tests.

---

## 7) Server Component Testing Strategy

### MSW Limitation with Next.js Async Server Components

MSW (Mock Service Worker) **cannot intercept fetch calls in Next.js async Server Components** because:

1. **Server Components run in server rendering context** — They execute on the server during page generation, not in the browser where MSW's Service Worker exists.
2. **MSW Node setupServer initializes too late** — By the time MSW's Node.js server starts in test setup, Next.js has already called fetch during component rendering.

This limitation affects any async Server Component that fetches data directly:

```tsx
// ❌ MSW cannot intercept this fetch
export default async function CoursesPage() {
  const response = await fetch('http://localhost:8000/api/courses/');
  const courses = await response.json();

  return <CourseList courses={courses} />;
}
```

### Two Testing Approaches

#### Option 1 (Default): E2E Tests Only

Test async Server Components via Playwright E2E tests that exercise the full rendering pipeline:

```typescript
// tests/e2e/courses.spec.ts
test('displays courses list for authenticated teacher', async ({ page }) => {
  // Playwright intercepts happen at network layer
  await page.route('**/api/courses/', route => {
    route.fulfill({
      status: 200,
      body: JSON.stringify([
        { id: 1, name: 'Math 101', teacher: 'Smith' },
        { id: 2, name: 'English 202', teacher: 'Jones' }
      ])
    });
  });

  await page.goto('/courses');

  await expect(page.locator('text=Math 101')).toBeVisible();
  await expect(page.locator('text=English 202')).toBeVisible();
});
```

**Advantages:**
- Tests full rendering pipeline (Server Component + Client Component integration)
- No refactoring required
- Catches routing, authentication, and layout issues

**Disadvantages:**
- Slower than unit tests (browser startup overhead)
- Harder to test edge cases (must configure via Playwright route mocks)
- Less granular failure messages

#### Option 2 (When Needed): Extract Data-Fetching to Testable Functions

For complex flows with multiple API calls, conditional logic, or error handling, extract data-fetching to `lib/api/*` functions:

```typescript
// lib/api/courses.ts
export async function fetchCourses(): Promise<Course[]> {
  const response = await fetch('http://localhost:8000/api/courses/');
  if (!response.ok) throw new Error('Failed to fetch courses');
  return response.json();
}

// Unit test with MSW
import { fetchCourses } from '@/lib/api/courses';
import { server } from '@/mocks/server';
import { http, HttpResponse } from 'msw';

test('fetchCourses returns courses on success', async () => {
  server.use(
    http.get('http://localhost:8000/api/courses/', () => {
      return HttpResponse.json([
        { id: 1, name: 'Math 101', teacher: 'Smith' }
      ]);
    })
  );

  const courses = await fetchCourses();
  expect(courses).toHaveLength(1);
  expect(courses[0].name).toBe('Math 101');
});

// Thin Server Component calls testable function
export default async function CoursesPage() {
  const courses = await fetchCourses();
  return <CourseList courses={courses} />;
}
```

**Advantages:**
- Data-fetching logic unit testable with MSW
- Faster feedback loop for API integration testing
- Easier to test error conditions and edge cases

**Disadvantages:**
- Requires refactoring Server Components
- Extra abstraction layer
- Still need E2E tests for rendering integration

### Project Decision

**Phase 23-24 Default Approach:**
- **E2E-only for async Server Components** — Accept Playwright tests as the primary testing method for Server Components that fetch data.
- **Extract data-fetching only when necessary** — For complex flows with multiple API calls, conditional branching, or critical error handling, refactor to `lib/api/*` for unit testability.
- **Client Components continue with Vitest + MSW** — The MSW limitation does not affect Client Components, which continue to use Vitest unit tests with MSW mocks.

**Rationale:**
- Most Server Components are thin wrappers around single API calls — E2E tests provide sufficient coverage without refactoring overhead.
- Extracting data-fetching for all Server Components is premature abstraction — apply when complexity justifies it.
- Unified testing strategy reduces cognitive load — team doesn't need to decide "unit vs E2E" for every component.

---

## 8) Coverage Enforcement Policy

### Thresholds

| Metric | Backend | Frontend | Rationale |
|--------|---------|----------|-----------|
| Lines | 80% | 80% | Unified target across stack |
| Branches | 80% | 80% | Conditional logic coverage |
| Functions | 80% | 80% | Entry point coverage |
| Statements | 80% | 80% | Execution path coverage |

### Backend Enforcement

Configured in `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
  "--cov=src",
  "--cov-report=term",
  "--cov-report=lcov",
  "--cov-fail-under=80"
]
```

Run via: `pytest --cov=src --cov-report=term --cov-report=lcov --cov-fail-under=80`

### Frontend Enforcement

Configured in `frontend/vitest.config.ts`:

```typescript
coverage: {
  provider: 'v8',
  reporter: ['text', 'lcov', 'html'],
  thresholds: {
    lines: 80,
    functions: 80,
    branches: 80,
    statements: 80
  }
}
```

Run via: `npm run test:coverage`

### CI Behavior

- **Coverage runs on every PR and push to development/master**
- **CI job fails if any threshold not met** — Blocks PR merge until coverage restored
- **Coverage reports uploaded as LCOV artifacts** — Available for 30 days in GitHub Actions artifacts
- **Both backend and frontend coverage gates must pass** — Separate CI jobs for backend and frontend

### Exclusions (with justification)

| File Pattern | Rationale |
|--------------|-----------|
| `*.test.*`, `*.spec.*`, `__tests__/**` | Test code has no runtime logic to cover |
| `backend/*/migrations/**` | Auto-generated Django migrations |
| `frontend/**/*.d.ts` | TypeScript type definitions |
| `frontend/app/**/layout.tsx` | Next.js framework boilerplate |
| `frontend/app/**/loading.tsx` | Next.js framework boilerplate |
| `frontend/app/**/error.tsx` | Next.js framework boilerplate |
| `frontend/mocks/**` | Test infrastructure, not production code |

### Threshold Evolution

| Phase | Frontend Target | Backend Target | Notes |
|-------|----------------|----------------|-------|
| 22 (Bootstrap) | 70% | 80% | Initial frontend tooling setup |
| 23-24 (Implementation) | 75% | 80% | Incremental ratcheting |
| 25+ (Maintenance) | 80% | 80% | Unified threshold |

**Rationale for 80% threshold:**

80% balances risk reduction with diminishing returns. Coverage above 80% often targets trivial code paths (getters, setters, error formatting) that provide minimal risk reduction. Coverage below 80% leaves significant business logic untested.

**Industry benchmarks:**
- Google: 60% minimum (large codebase, strong code review culture)
- Meta: 80% (medium-to-high coverage with fast CI)
- Typical startups: 70% (balances speed and quality)

**Unified threshold rationale:**
- Prevents "split enforcement" where one stack gets more attention than the other
- Simplifies communication ("80% across the board")
- Reflects equal importance of frontend and backend quality

---

## 9) CI Integration Plan

### Workflow Files

- **Backend Tests + Coverage:** `.github/workflows/test-backend.yml` (to be created in Phase 23)
- **Frontend Tests + Coverage:** `.github/workflows/test-frontend.yml` (to be created in Phase 23)
- **Security Scanning:** `.github/workflows/security-scan.yml` (existing from Phase 22)

### Backend CI

**On every PR and push to development/master:**

1. **pytest with coverage** — Runs all backend tests with coverage threshold enforcement
2. **Bandit SAST scan** — Static analysis for OWASP Top 10 Python vulnerabilities
3. **Security test marker execution** — Runs `pytest -m security` for security-specific tests

**Commands:**
```bash
pytest --cov=src --cov-report=term --cov-report=lcov --cov-fail-under=80
bandit -r src/ -c pyproject.toml
pytest -m security
```

### Frontend CI

**On every PR and push to development/master:**

1. **Vitest with coverage** — Runs all frontend unit tests with coverage threshold enforcement
2. **ESLint security plugin check** — Lints TypeScript/JavaScript for security issues (eval, secrets, injection)

**Commands:**
```bash
npm run test:coverage  # Vitest with 80% threshold enforcement
npx eslint --max-warnings 0  # ESLint with security plugins
```

### Security CI

**On every PR and push to development/master:**

1. **OWASP ZAP baseline scan** — Passive DAST scan of backend API (http://localhost:8000) and frontend (http://localhost:3000)
2. **Report-only mode** — `continue-on-error: true` and `-I` flag to establish baseline without breaking CI
3. **Artifact upload** — Reports uploaded as HTML, JSON, and Markdown for manual triage

**Scan targets:**
- Backend: `http://localhost:8000` (Django REST API)
- Frontend: `http://localhost:3000` (Next.js application)

**Report retention:** 30 days

### Pre-Commit Enforcement

**Configured in `.pre-commit-config.yaml`:**

1. **Bandit (Python)** — Scans staged Python files for security issues before commit
2. **ESLint security (JS/TS)** — Scans staged frontend files for security issues before commit

**Trigger:** Runs automatically on `git commit` for staged files only

**Behavior:** Blocks commit if security violations detected (errors, not warnings)

### PR Merge Protection

**GitHub branch protection rules (to be configured):**

- **Required status checks:**
  - `test-backend` — Backend tests + coverage must pass
  - `test-frontend` — Frontend tests + coverage must pass
  - `security-scan` — ZAP scan must complete (informational only, does not block)

- **Cannot bypass:** Administrators and maintainers must pass status checks

**Rationale:**
- Coverage thresholds enforced at CI level prevent coverage regressions from merging
- Pre-commit hooks catch issues early (shift-left)
- ZAP scan provides security visibility without blocking on false positives (Phase 23 will triage and enforce critical findings)
