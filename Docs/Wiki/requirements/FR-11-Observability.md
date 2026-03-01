# FR-11 Observability (OBS) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | OBS |
| **Applies To** | ALL (infrastructure-level), ADMIN (audit log querying) |
| **Related Issues** | #32 (OpenTelemetry instrumentation and collector infrastructure) |
| **Dependencies** | FR-12 ENV (profile-driven tracing defaults via `effective_otel_enabled`), FR-13 INFRA (Docker Compose hosts collector and Jaeger services) |

---

## 1) Scope

### In Scope
- OpenTelemetry distributed tracing: `TracerProvider`, `Resource`, span processors, auto-instrumentation for Django HTTP requests and Psycopg database queries.
- W3C Trace Context propagation: `W3CTraceContextTextMapPropagator` configured as global text map propagator so frontend `traceparent` headers propagate to backend spans.
- OTLP export to OpenTelemetry Collector via `OTLPSpanExporter` with `BatchSpanProcessor`.
- Jaeger UI visualization: collector forwards traces to Jaeger for developer querying at `http://localhost:16686`.
- File-based trace export: custom `FileSpanExporter` writes JSONL to disk for offline PlantUML sequence diagram generation via `SimpleSpanProcessor`.
- Log-trace correlation: `LoggingInstrumentor` injects `otelTraceID` and `otelSpanID` into Python `logging` records.
- Profile-driven tracing toggle: `effective_otel_enabled` property in `env.py` determines defaults per environment profile (FR-12 ENV).
- Idempotent tracing configuration: `_CONFIGURED` guard prevents duplicate initialization.
- Graceful degradation: application starts and serves requests even if collector is unreachable.
- Audit logging for sensitive actions: `AuditLog` model records actor, target, action type, old/new values, and outcome for compliance-critical operations.

### Out of Scope
- Custom business logic spans (manual `tracer.start_as_current_span()` in views/services) — deferred.
- Metrics collection (`MeterProvider`, counters, histograms).
- Log aggregation infrastructure (centralized logging backend, ELK, Grafana Loki).
- Production-grade observability backend (Grafana Tempo, Honeycomb) — Jaeger sufficient for development.
- Frontend OpenTelemetry SDK (`@opentelemetry/web`) — frontend generates `traceparent` manually in `auth.interceptor.ts`.
- Multi-service trace propagation beyond frontend-backend.
- Prometheus metrics export.
- Alerting infrastructure.
- Export-specific audit logging (`ExportAuditLog` — FR-10 EXP domain owns its own audit model).
- Structured JSON log formatter (deferred; console handler sufficient for current goals).
- Admin-facing REST endpoint for audit log querying (v1 uses Django admin panel only).
- Wireframes and Playwright E2E scripts (tracked separately).

### Removals
- None. Existing OTel code (`config/otel.py`, `core/otel_exporter.py`) is retained and extended.

---

## 2) Actors

| Role | Type | OBS domain notes |
|------|------|-----------------|
| ALL | Infrastructure | Tracing is infrastructure-level; spans are generated automatically for all requests regardless of caller role. No role-specific tracing behavior. |
| ADMIN | System role (`is_staff=True`) | Audit log entries queryable via Django admin panel. Admin actions (sudo grants, user deletion, password resets) generate audit entries. |

**Actor ordering:** Not applicable (infrastructure-level).

> **Note:** OBS has no user-facing REST endpoints. Tracing and audit logging are automatic infrastructure behavior. Jaeger UI and Django admin panel are developer/admin tools, not end-user interfaces.

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| OBS-US-01 | ALL | As a developer I can configure distributed tracing at application startup so that HTTP requests and database queries are captured as spans. |
| OBS-US-02 | ALL | As a developer I can view distributed traces in Jaeger UI so that I can debug request flows and identify performance bottlenecks. |
| OBS-US-03 | ALL | As a developer I can correlate log entries with traces via trace IDs so that I can investigate errors with full request context. |
| OBS-US-04 | ALL | As a developer I can export traces to a JSONL file so that I can generate PlantUML sequence diagrams from trace data. |
| OBS-US-05 | ADMIN | As an admin I can review audit log entries for sensitive operations so that I can verify who performed what action and when for compliance monitoring. |

---

## 4) Use Cases

### OBS-UC-01 — Configure Distributed Tracing

**Roles:** ALL
**Trigger:** Backend starts; `configure_tracing()` called from `wsgi.py` or `asgi.py` before Django request handling begins.

**Preconditions:**
- Backend service starting.
- Environment variables loaded (`OTEL_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_TRACE_FILE`, `OTEL_SERVICE_NAME`).

**Main Flow:**
1. System checks `effective_otel_enabled` (profile-driven defaults per OBS-CN-04).
2. If disabled, tracing configuration is skipped entirely (noop).
3. If enabled:
   a. System checks `_CONFIGURED` guard; if already configured, skip (OBS-CN-01).
   b. System creates `Resource` with `SERVICE_NAME` attribute (default: `eel-backend`).
   c. System initializes `TracerProvider` with `Resource`.
   d. System sets global `TracerProvider` via `trace.set_tracer_provider()`.
   e. System configures `W3CTraceContextTextMapPropagator` as global text map propagator (OBS-CN-02).
   f. If `OTEL_EXPORTER_OTLP_ENDPOINT` is set, system adds `OTLPSpanExporter` with `BatchSpanProcessor`.
   g. If `OTEL_TRACE_FILE` is set AND environment is not production (OBS-CN-06), system adds `FileSpanExporter` with `SimpleSpanProcessor`.
   h. System activates `DjangoInstrumentor` for HTTP request spans.
   i. System activates `PsycopgInstrumentor` for database query spans.
   j. System activates `LoggingInstrumentor` for trace ID injection into log records (OBS-CN-07).
   k. System sets `_CONFIGURED = True`.
4. Application starts serving requests with tracing active.

**Postconditions:**
- TracerProvider configured; auto-instrumentation active.
- Spans exported to collector and/or file depending on configuration.
- Log records include `otelTraceID` and `otelSpanID` when written within a traced request.

**Errors:**
- `OBS-UC-01-E1`: Collector unreachable at startup — warning logged; application starts successfully; file export continues if configured (OBS-CN-03).
- `OBS-UC-01-E2`: Invalid `OTEL_EXPORTER_OTLP_HEADERS` format — malformed entries silently skipped by header parser; no crash.

**Tests (representative):**
- `test_OBS_UC_01` (tracing configured with OTEL_ENABLED=true)
- `test_OBS_UC_01_disabled` (noop when OTEL_ENABLED=false)
- `test_OBS_UC_01_idempotent` (_CONFIGURED guard prevents double initialization)
- `test_OBS_UC_01_E1` (graceful degradation when collector unreachable)
- `test_OBS_CN_01` (idempotent configuration)
- `test_OBS_CN_02` (W3C propagator registered)
- `test_OBS_CN_04` (environment toggle respects profile defaults)

---

### OBS-UC-02 — Export Traces to Collector

**Roles:** ALL
**Trigger:** Application generates span data (HTTP request processed, database query executed).

**Preconditions:**
- OBS-UC-01 complete (tracing configured).
- `OTEL_EXPORTER_OTLP_ENDPOINT` configured.
- OpenTelemetry Collector service running.

**Main Flow:**
1. Auto-instrumentation captures span (HTTP request or database query).
2. `BatchSpanProcessor` batches span data.
3. `OTLPSpanExporter` sends batched spans to collector via OTLP/HTTP.
4. Collector receives spans and forwards to Jaeger.
5. Traces visible in Jaeger UI at `http://localhost:16686`.

**Postconditions:**
- Trace data available in Jaeger for querying and visualization.
- No application data modified.

**Errors:**
- `OBS-UC-02-E1`: Collector service not running — OTLP export fails silently; spans buffered then dropped by `BatchSpanProcessor`; file export continues if configured (OBS-CN-03).

**Tests (representative):**
- `test_OBS_UC_02` (OTLP exporter added when endpoint configured)
- `test_OBS_UC_02_E1` (graceful handling when collector missing)
- `test_OBS_CN_05` (dual export: both OTLP and file active simultaneously)

---

### OBS-UC-03 — Correlate Logs with Traces

**Roles:** ALL
**Trigger:** Backend code writes a log entry during a traced request.

**Preconditions:**
- OBS-UC-01 complete (tracing configured).
- `LoggingInstrumentor` activated.

**Main Flow:**
1. Application code calls `logger.info()`, `logger.warning()`, or `logger.error()`.
2. `LoggingInstrumentor` injects `otelTraceID` and `otelSpanID` into the Python `LogRecord`.
3. Log entry written with trace context fields included.
4. Developer can search logs by trace ID and correlate with spans in Jaeger.

**Postconditions:**
- Log entries include `otelTraceID` and `otelSpanID` when written within a traced request.
- Logs written outside a trace context have empty trace ID fields.

**Errors:**
- `OBS-UC-03-E1`: `LoggingInstrumentor` not configured — log entries lack `otelTraceID` and `otelSpanID`; log-trace correlation not possible; no crash.

**Tests (representative):**
- `test_OBS_UC_03` (LoggingInstrumentor configured)
- `test_OBS_UC_03_trace_id_injection` (`otelTraceID` present in log records during traced requests)
- `test_OBS_UC_03_no_trace_context` (empty trace IDs outside trace context)
- `test_OBS_UC_03_E1` (log entries lack trace IDs when instrumentor missing)

---

### OBS-UC-04 — Export Traces to File

**Roles:** ALL
**Trigger:** Application generates span data.

**Preconditions:**
- OBS-UC-01 complete (tracing configured).
- `OTEL_TRACE_FILE` configured.
- Environment is not production (OBS-CN-06).
- File path is writable.

**Main Flow:**
1. Auto-instrumentation captures span.
2. `SimpleSpanProcessor` sends span synchronously to `FileSpanExporter`.
3. `FileSpanExporter` serializes span to JSON dict with fields: `trace_id`, `span_id`, `parent_span_id`, `name`, `kind`, `start_time_unix_nano`, `end_time_unix_nano`, `start_time_iso`, `end_time_iso`, `attributes`, `resource`.
4. JSON object appended as one line to JSONL file (newline-delimited).
5. Developer runs `task diagrams:generate` to produce PlantUML sequence diagrams from the JSONL file.

**Postconditions:**
- Trace data written to `OTEL_TRACE_FILE` (default: `Docs/diagrams/otel/traces.jsonl`).
- File available for offline diagram generation.

**Errors:**
- File write failures caught by `FileSpanExporter.export()`; logged but do not crash the request.

**Tests (representative):**
- `test_OBS_UC_04` (FileSpanExporter configured when trace file set)
- `test_OBS_UC_04_jsonl_format` (span serialization matches expected schema)
- `test_OBS_UC_04_file_creation` (parent directories created if missing)
- `test_OBS_CN_06` (file export disabled in production)

---

### OBS-UC-05 — Record Audit Trail for Sensitive Actions

**Roles:** ADMIN, RESEARCHER (with sudo), TEACHER
**Trigger:** A sensitive action is performed by an authenticated user.

**Preconditions:**
- User is authenticated.
- Action is classified as sensitive (OBS-CN-08).

**Main Flow:**
1. User performs a sensitive action via an API endpoint (e.g., sudo grant, role change, user deletion).
2. The service layer creates an `AuditLog` entry with `outcome=PENDING` BEFORE executing the action (captures intent; ensures denied and failed attempts are recorded even if the action never completes).
3. The action executes.
4. Service layer updates the audit entry's `outcome` to `SUCCESS`, `FAILURE`, or `DENIED` based on the result.
5. If the outcome update fails (e.g., DB error after action committed), the entry remains with `outcome=PENDING` — a stale `PENDING` entry signals an incomplete audit cycle and is safer than a missing entry.
6. Admin can query audit log entries via Django admin panel.

**Sensitive Actions (OBS-CN-08):**

| Action Enum | Trigger | Actor | Target |
|-------------|---------|-------|--------|
| `SUDO_GRANT` | Admin grants sudo permission to researcher | ADMIN | Researcher user |
| `SUDO_REVOKE` | Admin revokes sudo permission from researcher | ADMIN | Researcher user |
| `ROLE_CHANGE` | Admin or researcher-with-sudo changes a user's role | ADMIN, RESEARCHER | Affected user |
| `USER_DELETE` | Admin deletes a user account | ADMIN | Deleted user |
| `PASSWORD_RESET` | Admin resets a user's password | ADMIN | Affected user |
| `SCORE_OVERRIDE` | Teacher manually overrides a submission score | TEACHER | Student (via submission) |

**Postconditions:**
- `AuditLog` entry stored in `audit_logs` database table with final `outcome` (`SUCCESS`, `FAILURE`, or `DENIED`).
- If the outcome update fails, the entry remains with `outcome=PENDING`.

**Errors:**
- Initial audit log write failure (step 2) must not block the underlying action. If the intent write fails, the failure is logged via Python `logging` and the action proceeds without an audit entry.
- Outcome update failure (step 4) must not block. The `PENDING` entry persists as a sentinel for incomplete audit cycles.
- Audit logging is observe-only; it must not introduce transactional coupling with the business action.

**Tests (representative):**
- `test_OBS_UC_05_ADMIN_sudo_grant`
- `test_OBS_UC_05_ADMIN_sudo_revoke`
- `test_OBS_UC_05_ADMIN_user_delete`
- `test_OBS_UC_05_ADMIN_password_reset`
- `test_OBS_UC_05_ADMIN_role_change`
- `test_OBS_UC_05_TEACHER_score_override`
- `test_OBS_UC_05_audit_persists_on_action_failure`
- `test_OBS_CN_08_all_sensitive_actions_covered`

---

## 5) Constraints

### OBS-CN-01 — Idempotent Configuration

- `configure_tracing()` must be safely callable multiple times without duplicate instrumentation or memory leaks.
- Global `_CONFIGURED` flag prevents re-initialization.
- Rationale: WSGI/ASGI startup hooks may be called multiple times in testing or code reload scenarios. Double-instrumentation causes duplicate spans and memory leaks.
- Applies to: OBS-UC-01.

### OBS-CN-02 — W3C Trace Context Propagation

- Backend must configure `W3CTraceContextTextMapPropagator` via `set_global_textmap()` to extract `traceparent` headers from incoming requests.
- Without this propagator, frontend-initiated traces cannot propagate to backend — backend starts new root spans instead of continuing the frontend trace.
- Frontend generates `traceparent` headers in `auth.interceptor.ts`; backend must extract and honor them.
- Applies to: OBS-UC-01.

### OBS-CN-03 — Graceful Degradation

- Application must start successfully even if OpenTelemetry Collector is unreachable.
- File export continues if configured; OTLP export failures are logged but do not block startup or crash requests.
- `BatchSpanProcessor` handles collector unavailability with internal retry and drop semantics.
- Tracing is an observability feature, not a functional dependency for application behavior.
- Applies to: OBS-UC-01, OBS-UC-02.

### OBS-CN-04 — Profile-Driven Tracing Defaults

- Tracing behavior is governed by `effective_otel_enabled` in `env.py`, which derives defaults from the active environment profile (FR-12 ENV):
  - `development`: enabled by default; overridable via `OTEL_ENABLED`.
  - `testing`: enabled by default; overridable via `OTEL_ENABLED`.
  - `production`: disabled by default; opt-in via `OTEL_ENABLED=true`.
- When production enables tracing, `OTEL_EXPORTER_OTLP_ENDPOINT` is required and `OTEL_TRACE_FILE` is prohibited (OBS-CN-06). Enforced by `_validate_otel_export_policy` in `env.py`.
- Applies to: OBS-UC-01.

### OBS-CN-05 — Dual Export (OTLP + File)

- Both OTLP export (to collector) and file export (to JSONL) are active simultaneously when both are configured in non-production environments.
- OTLP uses `BatchSpanProcessor` (asynchronous, non-blocking).
- File uses `SimpleSpanProcessor` (synchronous, ensures every span is written before request completes).
- Supports both real-time debugging (Jaeger UI) and offline artifact generation (JSONL for PlantUML).
- Applies to: OBS-UC-01, OBS-UC-02, OBS-UC-04.

### OBS-CN-06 — File Export Non-Production Guard

- `FileSpanExporter` is NOT activated when `env.is_production` is `True`.
- Production validation (`_validate_otel_export_policy`) rejects startup if `OTEL_TRACE_FILE` is set in production.
- Production validation also rejects startup if `OTEL_ENABLED=true` but `OTEL_EXPORTER_OTLP_ENDPOINT` is empty.
- Rationale: file export writes trace data (including SQL queries, HTTP headers) to disk. Production must route traces exclusively through the OTLP collector pipeline.
- Applies to: OBS-UC-04.

### OBS-CN-07 — Log-Trace Correlation Fields

- `LoggingInstrumentor` injects `otelTraceID` and `otelSpanID` into Python `LogRecord` objects.
- Log entries written during a traced request context include these fields automatically.
- Log entries written outside a trace context have empty or absent trace ID fields.
- No Django logging configuration changes required for injection; `LoggingInstrumentor` patches `LogRecord` at the Python `logging` module level.
- Applies to: OBS-UC-03.

### OBS-CN-08 — Audit Trail for Sensitive Actions

- The following actions MUST generate an `AuditLog` entry:
  - `SUDO_GRANT`: admin grants sudo permission to researcher (FR-03).
  - `SUDO_REVOKE`: admin revokes sudo permission from researcher (FR-03).
  - `ROLE_CHANGE`: admin or researcher-with-sudo changes a user's role (FR-04 USER).
  - `USER_DELETE`: admin deletes a user account (FR-04 USER).
  - `PASSWORD_RESET`: admin resets a user's password (FR-01 AUTH).
  - `SCORE_OVERRIDE`: teacher manually overrides a submission score (FR-08 SUB).
- Audit entry schema:
  - `actor` (FK to User): user performing the action.
  - `action` (CharField, choices from `AuditAction` enum): action type.
  - `target_user` (FK to User, nullable): affected user (if action targets a user).
  - `target_resource_type` (CharField, nullable): model name of affected resource (e.g., `Submission`).
  - `target_resource_id` (IntegerField, nullable): PK of affected resource.
  - `old_value` (JSONField, nullable): previous state (e.g., `{"role": "STUDENT"}`).
  - `new_value` (JSONField, nullable): new state (e.g., `{"role": "TEACHER"}`).
  - `outcome` (CharField, choices: `PENDING`, `SUCCESS`, `FAILURE`, `DENIED`): result of the action. Written as `PENDING` on initial insert, updated to final value after action completes.
  - `ip_address` (GenericIPAddressField, nullable): request IP address.
  - `created_at` (DateTimeField, auto_now_add): timestamp.
- **Two-phase audit protocol:** (1) insert entry with `outcome=PENDING` before action executes; (2) update `outcome` to `SUCCESS`, `FAILURE`, or `DENIED` after action completes. A stale `PENDING` entry signals an incomplete audit cycle.
- Initial write failure must not block the underlying action (logged via Python `logging`; action proceeds without audit entry). Outcome update failure must not block either (entry remains `PENDING`).
- `old_value`/`new_value` must NOT store raw passwords; password changes record `{"password": "changed"}` only.
- Audit entries queryable via Django admin panel. No dedicated REST endpoint in v1.
- Database table: `audit_logs`.
- Applies to: OBS-UC-05.

### OBS-CN-09 — Package Version Requirements

- OpenTelemetry packages must be updated to latest stable releases:
  ```
  opentelemetry-api==1.39.1
  opentelemetry-sdk==1.39.1
  opentelemetry-exporter-otlp-proto-http==1.39.1
  opentelemetry-instrumentation-django==0.60b1
  opentelemetry-instrumentation-psycopg==0.60b1
  opentelemetry-instrumentation-logging==0.60b1  (new dependency)
  ```
- Instrumentation upgrade from `0.45b0` to `0.60b1` changes semantic convention attribute names (e.g., `http.method` becomes `http.request.method`). The `capture_otel_sequences.py` and diagram generation scripts must handle both old and new attribute names during the transition.
- Applies to: OBS-UC-01 through OBS-UC-04.

---

## 6) Infrastructure Contract

OBS has no user-facing REST API endpoints. All tracing and logging behavior is infrastructure-level and automatic.

### Docker Services (to be added to `docker-compose.yml`)

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.120.0` | `4317` (gRPC), `4318` (HTTP) | Receives OTLP spans from backend, forwards to Jaeger |
| `jaeger` | `jaegertracing/all-in-one:1.65` | `16686` (UI) | Trace visualization and querying |

### Collector Configuration (`otel-collector-config.yaml`)

- Receiver: OTLP (gRPC on 4317, HTTP on 4318).
- Exporter: OTLP to Jaeger.
- Pipeline: `traces` receiver (OTLP) to exporter (Jaeger OTLP).

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | (empty; profile-driven) | Runtime tracing toggle. See OBS-CN-04 for per-profile defaults. |
| `OTEL_SERVICE_NAME` | `eel-backend` | Service name in trace resource attributes. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | (empty) | Collector OTLP HTTP endpoint (e.g., `http://otel-collector:4318/v1/traces`). |
| `OTEL_EXPORTER_OTLP_HEADERS` | (empty) | Comma-separated `key=value` headers for OTLP exporter. |
| `OTEL_TRACE_FILE` | `Docs/diagrams/otel/traces.jsonl` | Local JSONL trace file path. Non-production only (OBS-CN-06). |

### AuditLog Model Schema

| Field | Type | Description |
|-------|------|-------------|
| `actor` | FK to User | User performing the action |
| `action` | CharField (choices) | `AuditAction` enum value |
| `target_user` | FK to User, nullable | Affected user (if applicable) |
| `target_resource_type` | CharField, nullable | Model name of affected resource |
| `target_resource_id` | IntegerField, nullable | PK of affected resource |
| `old_value` | JSONField, nullable | Previous state |
| `new_value` | JSONField, nullable | New state |
| `outcome` | CharField (choices) | `PENDING`, `SUCCESS`, `FAILURE`, `DENIED` |
| `ip_address` | GenericIPAddressField, nullable | Request IP address |
| `created_at` | DateTimeField, auto_now_add | Timestamp |

Database table: `audit_logs`. Registered in Django admin for querying.

### AuditAction Enum

```
SUDO_GRANT
SUDO_REVOKE
ROLE_CHANGE
USER_DELETE
PASSWORD_RESET
SCORE_OVERRIDE
```

---

## 7) Error Model

OBS errors are infrastructure-level. They manifest as startup failures or logged warnings, not HTTP error responses to end users.

| Scenario | Behavior | Constraint |
|----------|----------|------------|
| Tracing disabled by profile | `configure_tracing()` is noop; no error | OBS-CN-04 |
| Collector unreachable | Warning logged; app starts; OTLP export fails silently | OBS-CN-03 |
| File path not writable | `FileSpanExporter.export()` logs error; request completes | OBS-CN-03 |
| Production + `OTEL_TRACE_FILE` set | Startup rejected by `_validate_otel_export_policy` | OBS-CN-06 |
| Production + `OTEL_ENABLED=true` + no OTLP endpoint | Startup rejected by `_validate_otel_export_policy` | OBS-CN-06 |
| `LoggingInstrumentor` missing | Log entries lack trace IDs; no crash | OBS-UC-03-E1 |
| Audit intent write failure (phase 1) | Action proceeds without audit entry; failure logged via `logging` | OBS-CN-08 |
| Audit outcome update failure (phase 2) | Entry remains `PENDING`; action result unaffected | OBS-CN-08 |
| Invalid OTLP headers format | Malformed entries skipped; valid entries used | OBS-UC-01-E2 |

---

## 8) Test Strategy by Layer

### Backend Unit
- Tracing configuration: `configure_tracing()` creates TracerProvider, sets propagator, adds processors, activates instrumentors.
- Idempotent guard: double-call to `configure_tracing()` does not duplicate instrumentation.
- Environment toggle: noop when `effective_otel_enabled` is false.
- W3C propagator: `W3CTraceContextTextMapPropagator` registered as global text map.
- Dual export: both OTLP and file exporters active when both endpoints configured.
- File export guard: `FileSpanExporter` not added when `env.is_production`.
- LoggingInstrumentor: `otelTraceID` and `otelSpanID` present in log records during traced requests.
- FileSpanExporter JSONL format: span dict matches expected schema (trace_id, span_id, parent_span_id, name, kind, timestamps, attributes, resource).
- AuditLog model: CRUD operations, field validation, `AuditAction` enum choices.
- Audit logging: each sensitive action type generates correct audit entry with expected actor, target, old/new values, outcome.
- Audit password safety: `old_value`/`new_value` never contain raw passwords.

### Backend Integration
- Startup sequence: `configure_tracing()` called before request handling in WSGI/ASGI.
- Auto-instrumentation: Django HTTP and Psycopg DB spans captured for real requests.
- W3C propagation: backend span has parent context from frontend `traceparent` header.
- Log-trace correlation: trace ID in log records matches trace ID in exported spans.
- File export: spans written to JSONL file during traced requests; file parseable by diagram scripts.
- Audit log integration: sensitive API actions (sudo grant, user delete, role change, score override) produce `AuditLog` entries with correct actor, target, old/new values.
- Audit log resilience: action completes even when audit write is mocked to fail.

### System Tests (Black Box)
- `ST-OBS-UC-01` (tracing configured at startup)
- `ST-OBS-UC-02` (spans visible in Jaeger after API requests)
- `ST-OBS-UC-03` (log entries contain trace IDs)
- `ST-OBS-UC-04` (JSONL file populated after API requests)
- `ST-OBS-UC-05` (audit log entries created for sensitive actions)
- `ST-OBS-CN-01` (idempotent configuration)
- `ST-OBS-CN-02` (W3C traceparent propagation from frontend headers)
- `ST-OBS-CN-03` (app starts without collector running)
- `ST-OBS-CN-06` (file export rejected in production)
- `ST-OBS-CN-08` (all 6 sensitive action types produce audit entries)

---

## 9) NFR Cross-References

- **NFR-Security**
  - Audit trail for sensitive actions (OBS-CN-08) enables FERPA compliance monitoring and security investigation.
  - Audit entries record actor, target, action, old/new values, and outcome for accountability.
  - File export prohibited in production (OBS-CN-06) prevents sensitive trace data (SQL queries, HTTP headers) from being written to disk.
  - Audit log `old_value`/`new_value` must never store raw passwords.
- **NFR-Privacy**
  - Trace data may include HTTP headers and query parameters. Production traces are routed exclusively through the collector pipeline (OBS-CN-06), not written to local files.
  - Audit entries record state changes (e.g., old/new role) but not raw credentials.
- **NFR-Reliability**
  - Graceful degradation (OBS-CN-03): tracing failures do not crash requests or block startup.
  - Idempotent configuration (OBS-CN-01): safe for multi-call startup scenarios.
  - Audit log write failures do not block the underlying action (fire-and-forget with error logging).
- **NFR-Performance**
  - `BatchSpanProcessor` for OTLP export minimizes per-request overhead via asynchronous batching.
  - `SimpleSpanProcessor` for file export ensures synchronous writes for diagram generation accuracy.
  - Auto-instrumentation adds minimal overhead (OTel SDK design).
  - Audit log writes are single INSERT operations per sensitive action; negligible performance impact.
- **NFR-Maintainability**
  - OTel configuration centralized in `config/otel.py`.
  - Custom file exporter isolated in `core/otel_exporter.py`.
  - Audit logging uses a single model with enum-based action types, extensible for future sensitive action categories.

---

## 10) Cross-Domain References

| FR | Reference | Notes |
|----|-----------|-------|
| FR-01 AUTH | `PASSWORD_RESET` audit action | Admin-initiated password resets generate audit entries with actor and target user. |
| FR-03 SUDO | `SUDO_GRANT`, `SUDO_REVOKE` audit actions | Sudo permission changes are audit-logged with actor, target researcher, and permission name in `old_value`/`new_value`. |
| FR-04 USER | `ROLE_CHANGE`, `USER_DELETE` audit actions | Role changes record old/new role in `old_value`/`new_value`. User deletions record the deleted user's identity. |
| FR-08 SUB | `SCORE_OVERRIDE` audit action | Teacher score overrides record old/new score in `old_value`/`new_value` with `target_resource_type=Submission` and `target_resource_id`. |
| FR-10 EXP | `ExportAuditLog` (separate model) | Export audit logging is domain-specific (EXP-CN-06) and uses its own model in the exports app. FR-11 `AuditLog` covers non-export sensitive actions. No overlap. |
| FR-12 ENV | `effective_otel_enabled`, profile-driven defaults | FR-12 defines the environment profile system; FR-11 consumes `effective_otel_enabled` to determine tracing behavior. Production OTel validation (`_validate_otel_export_policy`) enforces OBS-CN-06 constraints. |
| FR-13 INFRA | Docker Compose services | FR-13 owns `docker-compose.yml`; FR-11 defines the `otel-collector` and `jaeger` service specs that must be added. |

---

## 11) Current Implementation Alignment Notes

This spec defines the target FR-11 contract. Current code has partial OTel implementation that must be extended:

1. **Add W3C propagator.** Current: no propagator configured in `config/otel.py`; frontend `traceparent` headers are ignored. Target: call `set_global_textmap(W3CTraceContextTextMapPropagator())` in `configure_tracing()` before instrumentors are activated.
2. **Add LoggingInstrumentor.** Current: not configured; log entries lack trace IDs. Target: add `LoggingInstrumentor().instrument()` in `configure_tracing()`. Requires new dependency: `opentelemetry-instrumentation-logging`.
3. **Add OTel Collector and Jaeger Docker services.** Current: `OTEL_EXPORTER_OTLP_ENDPOINT` accepted in env but no collector service in `docker-compose.yml`. Target: add `otel-collector` and `jaeger` services with `otel-collector-config.yaml`. Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces` as default in backend service environment.
4. **Update OTel packages.** Current: `>=1.23,<2.0` / `>=0.45b0,<1.0`. Target: pin to `1.39.1` / `0.60b1`. Update `capture_otel_sequences.py` and diagram generation scripts to handle new semantic convention attribute names (e.g., `http.method` to `http.request.method`).
5. **Add `AuditLog` model and `AuditAction` enum.** New model with 6 action types. Register in Django admin for querying. Requires database migration.
6. **Wire audit logging into existing service layers.** Add audit log writes to: sudo grant/revoke services (`accounts`), role change and user deletion services (`accounts`/`users`), password reset (`accounts`), score override (`submissions`). Each call site creates an `AuditLog` entry with actor from `request.user`, target, old/new values, and outcome.
7. **Add tests.** Unit tests for OTel configuration (propagator, instrumentors, exporters, idempotency, profile toggle). Integration tests for auto-instrumentation, log-trace correlation, and W3C propagation. Unit and integration tests for audit logging of all 6 sensitive action types.
8. **Retain existing code.** `config/otel.py` and `core/otel_exporter.py` are extended in place, not rewritten. `FileSpanExporter` JSONL format is unchanged. Profile-driven `effective_otel_enabled` and `_validate_otel_export_policy` in `env.py` are already implemented and correct.
