# Non-Functional Requirements -- Index

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Scope** | Cross-cutting policies |

---

## Overview

This document serves as the central hub for all Non-Functional Requirements (NFR) in the EE-Lab platform. NFRs define cross-cutting policies that apply across multiple functional domains -- security measures, operational procedures, reliability guarantees, privacy protections, and performance targets. Unlike Functional Requirements (FRs) which describe what features the system provides, NFRs describe how the system behaves: response time thresholds, transaction consistency rules, credential management policies, audit logging standards, and FERPA compliance controls.

NFR entries are domain-level policies. They apply to entire functional areas (AUTH, REG, CRS) rather than individual use cases. Each entry includes measurable acceptance criteria with specific thresholds (rate limits, password lengths, response times) or clear verification procedures (code review checklists, security audits). The framework supports three status levels: Defined (requirement documented), Implemented (code exists), and Verified (tests confirm behavior).

This index provides navigation to all five NFR domain documents, documents the canonical entry template, maps NFR domains to FR domains, and defines verification methods used across all entries.

---

## ID Scheme

| Domain | Prefix | Example |
|--------|--------|---------|
| Security | NFR-SEC-## | NFR-SEC-01 |
| Operations | NFR-OPS-## | NFR-OPS-01 |
| Reliability | NFR-REL-## | NFR-REL-01 |
| Privacy | NFR-PRIV-## | NFR-PRIV-01 |
| Performance | NFR-PERF-## | NFR-PERF-01 |

**ID Pattern (Regex):**
```
NFR entry:    NFR-{DOMAIN}-{##}     e.g., NFR-SEC-01, NFR-OPS-03
Regex:        NFR-(SEC|OPS|REL|PRIV|PERF)-\d{2}
```

All NFR IDs use two-digit sequential numbering within each domain. IDs do not include role suffixes (no NFR-SEC-01-ADMIN) because NFRs are cross-cutting policies that apply to the system, not role-specific behaviors.

---

## Domain Summary

| Domain       | Document           | Entries | All Defined | All Implemented | All Verified |
|-------------|-------------------|---------|-------------|-----------------|--------------|
| Security    | NFR-Security.md    | 7       | 7           | 0               | 0            |
| Operations  | NFR-Operations.md  | 7       | 7           | 0               | 0            |
| Reliability | NFR-Reliability.md | 4       | 4           | 0               | 0            |
| Privacy     | NFR-Privacy.md     | 3       | 3           | 0               | 0            |
| Performance | NFR-Performance.md | 1       | 1           | 0               | 0            |
| **Total**   |                    | **22**  | **22**      | **0**           | **0**        |

All entries begin in "Defined" status when initially documented. Implementation tracking (transitioning entries to "Implemented" status) occurs during development phases. Verification tracking (transitioning entries to "Verified" status) occurs during testing phases. The status progression is one-way: Defined → Implemented → Verified.

---

## Canonical Entry Template

All NFR entries across all five domain documents use this standardized structure:

```markdown
## NFR-{DOMAIN}-{##}: {Title}

**Category:** {Subcategory within domain}

**Requirement:**
{1-3 sentence policy statement describing what must be true. Use "must" for mandatory requirements, "should" for recommendations. Frame as environment-consistent policies where the requirement applies uniformly but values may differ (e.g., password strength applies everywhere, minimum length varies by environment).}

**Acceptance Criteria:**
- [ ] {Specific, measurable criterion with exact numbers or clear verification steps}
- [ ] {Each checkbox is independently testable}
- [ ] {Use ranges for uncertain metrics, exact numbers for determined values}
- [ ] {Include all environments (dev/test/prod) if behavior differs}

**Verification Method:** {Method name - see Verification Methods section below}

**Applicable FRs:** {Domain names required: AUTH, REG, CRS, SUB, VIZ, EXP, OBS, ENV, INFRA; optional constraint qualifiers in parentheses}

**Status:** Defined | Implemented | Verified
```

**Field Notes:**

- **Category:** Subcategory within the NFR domain (e.g., Security domain has categories: API Security, Authentication Security, Credential Management, Session Management). Helps organize related entries within large domains.

- **Requirement:** Policy statement describing the cross-cutting concern. This is NOT a feature specification. Keep it domain-level (applies to AUTH, REG) rather than feature-specific (applies to login endpoint). Avoid implementation details (HTTP status codes, specific libraries, endpoint paths).

- **Acceptance Criteria:** Measurable checkboxes. Use exact numbers where determined (rate limit: 5 attempts per 15 minutes), ranges where uncertain (response time: 100-500ms), directional statements for qualitative requirements (must use cryptographically secure RNG). Each criterion should be independently verifiable.

- **Verification Method:** Select from the five standard methods documented below (Automated test, Manual review, Monitoring, Audit, Policy). This field is always present -- if truly untestable, explicitly note "No automated testing needed" with rationale.

- **Applicable FRs:** Always include domain-level references (AUTH, REG, CRS, SUB, VIZ, EXP, OBS, ENV, INFRA). Constraint-level qualifiers are optional and encouraged for traceability, e.g., `AUTH (AUTH-CN-03)`. Do NOT list individual use cases (AUTH-UC-01, REG-UC-03). This field shows which functional domains must consider this NFR during implementation.

- **Status:** Lifecycle tracker. Defined = requirement documented. Implemented = code exists that satisfies acceptance criteria. Verified = tests confirm behavior. One-way progression only.

---

## Cross-Reference Matrix

This matrix shows which NFR domains apply to which FR domains. An "X" indicates that at least one NFR entry in that domain lists the FR domain in its "Applicable FRs" field.

| FR Domain | Security | Operations | Reliability | Privacy | Performance |
|-----------|----------|------------|-------------|---------|-------------|
| AUTH      | X        | X          | X           | X       | X           |
| REG       | X        | X          | X           | X       |             |
| CRS       |          | X          | X           | X       |             |
| SUB       |          | X          | X           | X       | X           |
| VIZ       |          | X          | X           | X       | X           |
| EXP       |          | X          | X           |         | X           |
| OBS       |          | X          | X           |         |             |
| ENV       | X        | X          | X           |         |             |

**Cross-Reference Summary:**

**Phase 24 Complete:** Bidirectional cross-references have been established between FR constraints and NFR entries.

**Forward references (FR → NFR):** FR constraint sections include "Implements: NFR-XXX-##" annotations identifying which cross-cutting policy each constraint implements. Examples:
- AUTH-CN-03 implements NFR-SEC-01 (Rate Limiting Protection)
- REG-CN-03 implements NFR-REL-01 (Transaction Atomicity)
- REG-CN-22 implements NFR-SEC-07 (Registration Code Storage Hardening)
- ENV-CN-04 implements NFR-SEC-04 (Password Strength Policy)
- ENV-CN-10 implements NFR-OPS-02 (Startup Validation)
- ENV-CN-11 implements NFR-OPS-05 (Observability Instrumentation)

**Backward references (NFR → FR):** NFR entry "Applicable FRs" fields list implementing constraint IDs alongside domain names. Examples:
- NFR-SEC-01: AUTH (AUTH-CN-03), REG
- NFR-SEC-07: REG (REG-CN-08, REG-CN-22)
- NFR-REL-01: AUTH (AUTH-CN-08), REG (REG-CN-03)
- NFR-OPS-01: AUTH, REG, CRS, SUB, VIZ, EXP, OBS (OBS-CN-04), ENV (ENV-CN-01, ENV-CN-12)
- NFR-OPS-02: All domains, OBS (OBS-CN-01), ENV (ENV-CN-02, ENV-CN-10)
- NFR-OPS-05: All domains, OBS (OBS-CN-02), ENV (ENV-CN-11)

**Traceability:** Grep for any NFR-XXX-## in FR documents to find implementing constraints. Grep for any constraint ID in NFR documents to find backward references. No orphaned references exist in either direction.

---

## Verification Methods Overview

All NFR entries specify one of these five verification methods. Each method defines how acceptance criteria are confirmed to be satisfied.

### Automated Test

**Definition:** Verified by integration tests, unit tests, or performance tests that execute during CI/CD pipeline.

**When to use:** NFRs with programmatically verifiable behavior (rate limiting enforcement, transaction rollback, response time thresholds, cookie security flags).

**Examples:**
- **NFR-SEC-01 (Rate Limiting Protection):** Integration tests simulate >5 login attempts within 15 minutes and verify rate limit enforcement blocks additional attempts.
- **NFR-REL-01 (Transaction Atomicity):** Integration tests inject failure during multi-record registration operation and verify complete rollback (no orphaned user records, no consumed registration codes).
- **NFR-OPS-05 (Observability Instrumentation):** Integration tests verify trace context propagation from frontend request to backend spans with correct parent-child relationships.

### Manual Review

**Definition:** Verified by code review, configuration audit, or manual testing that requires human judgment.

**When to use:** NFRs with subjective criteria (error message quality, naming conventions, security posture assessment) or infrequent manual verification needs.

**Examples:**
- **NFR-SEC-03 (Enumeration Prevention):** Security audit verifies error messages do not reveal whether user accounts exist (identical messages for invalid username vs wrong password).
- **NFR-REL-03 (REST-Compliant API Design):** Code review verifies all endpoint paths use resource nouns (not action verbs), correct HTTP methods, and consistent pluralization.
- **NFR-OPS-06 (Audit Logging):** Log format inspection verifies structured JSON format, consistent field names, and retention policy configuration.

### Monitoring

**Definition:** Verified by runtime observability -- metrics dashboards, trace analysis, or log aggregation that confirm behavior in production.

**When to use:** NFRs that require production runtime verification (distributed tracing pipeline health, log aggregation success, performance under real load).

**Examples:**
- **NFR-OPS-05 (Observability Instrumentation):** Monitoring verifies trace data reaches OTLP collector and spans appear in Jaeger/Tempo with correct W3C Trace Context headers.
- **NFR-OPS-07 (Log-Trace Correlation):** Monitoring confirms log entries include otelTraceID and otelSpanID fields that match exported trace data.
- (Note: Performance thresholds (NFR-PERF-01) use "Automated test" during baseline establishment, but may use "Monitoring" for production SLA verification in future.)

### Audit

**Definition:** Verified by periodic compliance review -- regulatory audit, security assessment, or data governance check performed on a scheduled basis (quarterly, annually).

**When to use:** NFRs with compliance requirements (FERPA audit trails, PII protection verification, access control reviews).

**Examples:**
- **NFR-PRIV-02 (PII Protection in Application Logs):** Audit reviews log samples to verify email redaction, student ID hashing, and absence of full names in plaintext.
- **NFR-PRIV-03 (Audit Trail for FERPA Data Access):** Compliance audit verifies audit log completeness (all student record access logged), write-only enforcement, and retention period compliance (3 years minimum).

### Policy

**Definition:** Verified by deployment procedure, startup validation, or tool integration that enforces the policy automatically.

**When to use:** NFRs enforced by tooling or configuration rather than application behavior (secret encryption, startup guards, environment variable enforcement).

**Examples:**
- **NFR-OPS-02 (Startup Validation):** Production startup validation script rejects insecure configuration (DJANGO_DEBUG=true, weak SECRET_KEY) and refuses to start the application.
- **NFR-OPS-03 (Secret Management):** Encryption tooling (dotenvx) encrypts secrets at rest, deployment procedure documents key distribution process, and .env.keys files are excluded from version control.
- **NFR-SEC-06 (Credential Exposure Prevention):** Startup validation (same as NFR-OPS-02) enforces production credential security policies.

---

## Domain Documents

- [NFR-Security.md](NFR-Security.md) - Security policies (rate limiting, credential management, session security, enumeration prevention)
- [NFR-Operations.md](NFR-Operations.md) - Operations policies (environment profiles, startup validation, secret management, observability, audit logging)
- [NFR-Reliability.md](NFR-Reliability.md) - Reliability policies (transaction atomicity, idempotent operations, REST compliance, error consistency)
- [NFR-Privacy.md](NFR-Privacy.md) - Privacy policies (FERPA data access controls, PII protection, audit trails)
- [NFR-Performance.md](NFR-Performance.md) - Performance policies (API response time thresholds)

---

*Last updated: 2026-02-13*
*Status: Phase 24 complete (bidirectional cross-references established)*
