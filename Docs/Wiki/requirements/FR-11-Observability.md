# FR-11 Observability (OBS) — Detailed Draft

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Date** | 2026-02-10 |
| **Domain** | OBS |
| **Applies To** | ALL (infrastructure-level) |
| **Related Issues** | #32 (OpenTelemetry instrumentation and collector infrastructure) |

---

## 1) Scope

### In Scope
- OpenTelemetry distributed tracing configuration (TracerProvider, Resource, processors)
- W3C Trace Context propagation (frontend to backend via traceparent headers)
- OTLP export to OpenTelemetry Collector
- Jaeger UI visualization
- Auto-instrumentation for Django HTTP requests and Psycopg database queries
- Log-trace correlation (trace ID injection into backend logs)
- File-based trace export for offline diagram generation (JSONL format)
- Environment-based tracing toggle (OTEL_ENABLED flag)
- Idempotent tracing configuration (safe to call configure_tracing() multiple times)
- Graceful degradation (application starts even if collector unreachable)

### Out of Scope
- Custom business logic spans (manual tracer.start_as_current_span() in views/services) - deferred
- Metrics collection (MeterProvider, counters, histograms) - not required for current goals
- Log aggregation infrastructure (centralized logging backend)
- Production-grade observability backend (Grafana Tempo, Honeycomb) - Jaeger sufficient for development
- Frontend OpenTelemetry SDK (frontend generates traceparent manually, not via @opentelemetry/web)
- Multi-service trace propagation beyond frontend-backend (no service mesh)
- Prometheus metrics export
- Alerting infrastructure

---

## 2) Actors

| Role | Type | Notes |
|------|------|-------|
| ALL | Infrastructure | Tracing is infrastructure-level; no role-specific behavior. Trace data viewing (Jaeger UI) is developer/admin activity, not end-user. |

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| OBS-US-01 | ALL | As an infrastructure engineer I can configure distributed tracing at application startup so that request and database activity is captured in traces. |
| OBS-US-02 | ALL | As a developer I can view distributed traces in Jaeger UI so that I can debug request flows and identify performance bottlenecks. |
| OBS-US-03 | ALL | As a developer I can correlate log entries with traces via trace IDs so that I can investigate errors with full context. |
| OBS-US-04 | ALL | As a developer I can export traces to file so that I can generate sequence diagrams from trace data. |

---

## 4) Use Cases

### OBS-UC-01 — Configure Distributed Tracing

**Roles:** ALL

**Preconditions:** Application startup sequence (WSGI/ASGI initialization).

**Trigger:** Backend starts; configure_tracing() called from wsgi.py or asgi.py before Django request handling begins.

**Main Flow:**
1. System checks OTEL_ENABLED environment variable (default: false).
2. If false, tracing configuration is skipped (noop).
3. If true:
   a. System checks _CONFIGURED guard; if already configured, skip (idempotent).
   b. System creates Resource with SERVICE_NAME attribute.
   c. System initializes TracerProvider with Resource.
   d. System sets global TracerProvider.
   e. System configures W3CTraceContextPropagator as global text map propagator.
   f. System adds OTLP exporter with BatchSpanProcessor (if OTLP endpoint configured).
   g. System adds file exporter with SimpleSpanProcessor (if trace file path configured).
   h. System activates DjangoInstrumentor for HTTP request spans.
   i. System activates PsycopgInstrumentor for database query spans.
   j. System marks tracing as configured (_CONFIGURED = True).
4. Application starts serving requests with tracing active.

**Postcondition:** TracerProvider configured; auto-instrumentation active; spans exported to collector and/or file.

**Role Coverage:**

> **OBS-UC-01-ALL**
> - Behavior: Infrastructure-level configuration; no role-specific logic
> - Entry: Application startup hook (wsgi.py, asgi.py)

**Errors:**

**OBS-UC-01-E1** — Collector unreachable at startup
- Trigger: OTEL_EXPORTER_OTLP_ENDPOINT configured but collector service not running
- Behavior: Warning logged; application starts successfully; file export continues if configured
- Constraint: OBS-CN-03 (graceful degradation)

**OBS-UC-01-E2** — Propagator not configured
- Trigger: W3CTraceContextPropagator not set; frontend traceparent headers ignored
- Behavior: Backend traces start as new root spans; no frontend-backend correlation
- Constraint: OBS-CN-02 (propagator required for W3C propagation)

**Tests:**

**Backend Unit:**
- test_OBS_UC_01 (aggregator - verifies tracing configuration with OTEL_ENABLED=true)
- test_OBS_UC_01_disabled (verifies noop when OTEL_ENABLED=false)
- test_OBS_UC_01_idempotent (verifies _CONFIGURED guard prevents double initialization)
- test_OBS_UC_01_E1 (verifies graceful degradation when collector unreachable)
- test_OBS_UC_01_E2 (verifies error when propagator missing)
- test_OBS_CN_01 (idempotent configuration)
- test_OBS_CN_02 (W3C propagator configured)
- test_OBS_CN_04 (environment toggle)

**Integration:**
- test_OBS_UC_01_startup_sequence (verifies configure_tracing() called before request handling)
- test_OBS_UC_01_auto_instrumentation (verifies Django and Psycopg spans captured)

---

### OBS-UC-02 — Export Traces to Collector

**Roles:** ALL

**Preconditions:** OBS-UC-01 complete; OTEL_EXPORTER_OTLP_ENDPOINT configured; OpenTelemetry Collector service running.

**Trigger:** Application generates span data (HTTP request, DB query).

**Main Flow:**
1. Auto-instrumentation captures span (HTTP request or DB query).
2. BatchSpanProcessor batches span data.
3. OTLPSpanExporter sends batched spans to collector via OTLP/HTTP.
4. Collector receives spans and forwards to Jaeger.
5. Traces visible in Jaeger UI at http://localhost:16686.

**Postcondition:** Trace data available in Jaeger for querying and visualization.

**Role Coverage:**

> **OBS-UC-02-ALL**
> - Behavior: Infrastructure-level export; no role-specific logic

**Errors:**

**OBS-UC-02-E1** — Collector service missing from Docker
- Trigger: OTLP endpoint configured but otel-collector service not defined in docker-compose.yml
- Behavior: OTLP export fails silently; spans buffered then dropped; file export continues
- Constraint: OBS-CN-03 (graceful degradation)

**Tests:**

**Backend Unit:**
- test_OBS_UC_02 (aggregator - verifies OTLP exporter configured)
- test_OBS_UC_02_E1 (verifies graceful handling when collector missing)
- test_OBS_CN_05 (dual export - both OTLP and file active)

**Integration:**
- test_OBS_UC_02_collector_export (verifies spans reach collector and Jaeger)
- test_OBS_UC_02_jaeger_query (verifies traces queryable in Jaeger API)

---

### OBS-UC-03 — Correlate Logs with Traces

**Roles:** ALL

**Preconditions:** OBS-UC-01 complete; LoggingInstrumentor configured.

**Trigger:** Backend code writes log entry during traced request.

**Main Flow:**
1. Application code calls logger.info() or logger.error().
2. LoggingInstrumentor injects otelTraceID and otelSpanID into log record.
3. Log entry written with trace context fields.
4. Developer searches logs by trace ID or searches traces by log timestamp to correlate.

**Postcondition:** Log entries include trace IDs; logs and traces correlated for debugging.

**Role Coverage:**

> **OBS-UC-03-ALL**
> - Behavior: Infrastructure-level log instrumentation; no role-specific logic

**Errors:**

**OBS-UC-03-E1** — Logging instrumentor not configured
- Trigger: LoggingInstrumentor().instrument() not called in configure_tracing()
- Behavior: Log entries lack otelTraceID and otelSpanID fields; correlation not possible

**Tests:**

**Backend Unit:**
- test_OBS_UC_03 (aggregator - verifies LoggingInstrumentor configured)
- test_OBS_UC_03_trace_id_injection (verifies otelTraceID in log records)
- test_OBS_UC_03_E1 (verifies error when instrumentor missing)

**Integration:**
- test_OBS_UC_03_log_trace_correlation (verifies trace ID in logs matches trace ID in exported spans)

---

### OBS-UC-04 — Export Traces to File

**Roles:** ALL

**Preconditions:** OBS-UC-01 complete; OTEL_TRACE_FILE configured; file path writable.

**Trigger:** Application generates span data.

**Main Flow:**
1. Auto-instrumentation captures span.
2. SimpleSpanProcessor sends span to FileSpanExporter.
3. FileSpanExporter serializes span to JSON (trace_id, span_id, parent_span_id, name, kind, timestamps, attributes, resource).
4. Span appended to JSONL file (one JSON object per line).
5. Developer runs trace_to_plantuml.py script to generate sequence diagrams from JSONL file.

**Postcondition:** Trace data written to Docs/diagrams/otel/trace.jsonl; available for offline diagram generation.

**Role Coverage:**

> **OBS-UC-04-ALL**
> - Behavior: Infrastructure-level file export; no role-specific logic

**Errors:** None defined (file write errors handled by exporter; graceful degradation).

**Tests:**

**Backend Unit:**
- test_OBS_UC_04 (aggregator - verifies FileSpanExporter configured)
- test_OBS_UC_04_jsonl_format (verifies span serialization format)
- test_OBS_UC_04_file_creation (verifies parent directories created if missing)
- test_OBS_CN_05 (dual export - both OTLP and file active)

**Integration:**
- test_OBS_UC_04_file_export (verifies spans written to file)
- test_OBS_UC_04_diagram_generation (verifies trace_to_plantuml.py can parse exported JSONL)

---

## 5) Constraints

### OBS-CN-01 — Idempotent Configuration

**Description:** The configure_tracing() function must be safely callable multiple times without causing errors or duplicate instrumentation. A global _CONFIGURED guard flag prevents re-initialization.

**Rationale:** Application startup hooks (WSGI/ASGI) may be called multiple times in testing or when reloading code. Double-instrumentation causes duplicate spans and memory leaks.

**Applies to:** OBS-UC-01

**Implements:** NFR-REL-02 (Idempotent Bootstrap Operations) - Ensures tracing configuration checks for existing state before initializing, matching the pattern of admin bootstrap and migration operations.

---

### OBS-CN-02 — W3C Trace Context Propagation

**Description:** Backend must configure W3CTraceContextPropagator via set_global_textmap() to extract traceparent headers from incoming requests. Without this, frontend-initiated traces cannot propagate to backend.

**Rationale:** Frontend generates W3C traceparent headers manually (auth.interceptor.ts). Backend auto-instrumentation (DjangoInstrumentor) requires a propagator to extract these headers and use them as parent context for backend spans.

**Applies to:** OBS-UC-01

**Implements:** NFR-OPS-05 (Observability Instrumentation) - Directly implements the "OpenTelemetry SDK configured with W3C Trace Context propagator" and "Backend extracts traceparent headers from incoming requests" acceptance criteria.

---

### OBS-CN-03 — Graceful Degradation

**Description:** Application must start successfully even if OpenTelemetry Collector is unreachable or tracing configuration encounters non-fatal errors. File export continues if configured; OTLP export failures are logged but do not block startup.

**Rationale:** Development workflows should not require collector infrastructure to be running. Tracing is an observability feature, not a critical dependency for application functionality.

**Applies to:** OBS-UC-01, OBS-UC-02

**Note:** Implements partial failure tolerance (collector unreachable, exporter errors). No exact NFR match exists for service degradation tolerance (NFR-REL-01 covers transaction atomicity, not service availability).

---

### OBS-CN-04 — Environment Toggle

**Description:** Tracing is controlled by OTEL_ENABLED environment variable (default: false). When false, configure_tracing() is a noop and no instrumentation is loaded. When true, full tracing pipeline activates.

**Rationale:** Test/CI environments should run with tracing off by default to avoid overhead. Development and diagram-generation workflows enable tracing explicitly.

**Applies to:** OBS-UC-01

**Implements:** NFR-OPS-01 (Environment Profile System) - (partial) Aligns with environment-keyed behavior toggling principle, though OTEL_ENABLED is a separate toggle rather than derived from ENVIRONMENT variable. Environment profile integration deferred to issue #30.

---

### OBS-CN-05 — Dual Export

**Description:** Both OTLP export (to collector) and file export (to JSONL) must be active simultaneously when both endpoints are configured. This supports live visualization (Jaeger) and offline diagram generation from the same trace data.

**Rationale:** Development workflow requires both real-time debugging (Jaeger UI) and persistent trace artifacts (JSONL files for PlantUML generation). Both exporters use separate span processors (Batch vs Simple) to avoid blocking.

**Applies to:** OBS-UC-01, OBS-UC-02, OBS-UC-04

---

## 6) Test Naming Convention

All test names follow the v5 convention:

**Use case tests:**
- test_OBS_UC_01
- test_OBS_UC_02
- test_OBS_UC_03
- test_OBS_UC_04

**Error tests:**
- test_OBS_UC_01_E1
- test_OBS_UC_01_E2
- test_OBS_UC_02_E1
- test_OBS_UC_03_E1

**Constraint tests:**
- test_OBS_CN_01
- test_OBS_CN_02
- test_OBS_CN_03
- test_OBS_CN_04
- test_OBS_CN_05

---

## 7) Package Dependencies

**Current versions (issue #32 states these are outdated):**
```
opentelemetry-api>=1.23,<2.0
opentelemetry-sdk>=1.23,<2.0
opentelemetry-exporter-otlp-proto-http>=1.23,<2.0
opentelemetry-instrumentation-django>=0.45b0,<1.0
opentelemetry-instrumentation-psycopg>=0.45b0,<1.0
```

**Proposed updates (per issue #32 Phase 1):**
```
opentelemetry-api==1.39.1
opentelemetry-sdk==1.39.1
opentelemetry-exporter-otlp-proto-http==1.39.1
opentelemetry-instrumentation-django==0.60b1
opentelemetry-instrumentation-psycopg==0.60b1
opentelemetry-instrumentation-logging==0.60b1
```

**Note:** Upgrading instrumentation from 0.45b0 to 0.60b1 changes semantic convention attributes (e.g., http.method becomes http.request.method). The trace_to_plantuml.py script must be updated to handle new attribute names.

---

## 8) Infrastructure Components

**Docker services (to be added per issue #32 Phase 2):**

**otel-collector:**
- Image: otel/opentelemetry-collector-contrib:latest
- Ports: 4317 (OTLP gRPC), 4318 (OTLP HTTP)
- Config: otel-collector-config.yaml (receivers, exporters, pipelines)

**jaeger:**
- Image: jaegertracing/all-in-one:latest
- Ports: 16686 (Jaeger UI)
- OTLP receiver enabled for collector integration

**Environment variables:**
- OTEL_ENABLED=true (default for development, false for CI/test)
- OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
- OTEL_TRACE_FILE=Docs/diagrams/otel/traces.jsonl
- OTEL_SERVICE_NAME=eel-backend

---

## 9) Related Issues

**Direct dependency:**
- #30 (Environment Profiles) — OBS environment variables (OTEL_ENABLED, endpoints, file paths) must be included in environment profiles. See issue #32 "Environment Profile Integration" section for per-environment configuration table.

**Soft dependency:**
- #31 (API Endpoint Audit) — Instrumented endpoint names in traces will reflect standardized API naming from #31 automatically once endpoints are renamed.

---

## 10) Implementation Notes

**Current state (per issue #32):**
- Backend OTel config exists (backend/src/config/otel.py) with TracerProvider, Resource, processors, auto-instrumentation
- File exporter works (backend/src/core/otel_exporter.py); 956 spans captured in Docs/diagrams/otel/trace.jsonl
- OTLP export configured but collector does not exist (broken path)
- W3C propagator NOT configured (frontend traceparent headers ignored)
- LoggingInstrumentor NOT configured (no log-trace correlation)
- Packages outdated (pinned to >=1.23, latest is 1.39.1)

**Fix plan (per issue #32):**
1. Phase 1: Update packages to 1.39.1 / 0.60b1
2. Phase 2: Add W3C propagator, add collector/Jaeger services, set default OTLP endpoint
3. Phase 3: Add LoggingInstrumentor, update .env.template defaults
4. Phase 4: Verify end-to-end (OTLP export to Jaeger, file export continues, W3C propagation works, log-trace correlation active)

---
