# NFR-Reliability

| Field | Value |
|-------|-------|
| **Status** | Active |

---

## Overview

Reliability requirements ensure the EE-Lab application behaves consistently and predictably under normal and error conditions. This includes transaction atomicity for critical operations, idempotent system operations, REST-compliant API design, and consistent error handling across all endpoints.

## NFR-REL-01: Transaction Atomicity for Multi-Record Operations

**Category:** Data Integrity

**Requirement:**
Critical operations that modify multiple related database records must execute within a single database transaction to prevent partial state. If any step fails, all changes must be rolled back atomically.

**Acceptance Criteria:**
- [ ] Registration + code consumption executes in a single transaction (user creation, role assignment, profile creation, course enrollment, code usage increment)
- [ ] Network failure before transaction commit results in no database changes and no code consumption
- [ ] Network failure after transaction commit results in complete state with code consumed
- [ ] Transaction rollback on any step failure leaves no partial records (no orphaned users, no consumed codes without accounts)
- [ ] All multi-record operations identify which steps must be atomic and use database transaction boundaries

**Verification Method:** Automated test - integration tests verify transaction rollback on simulated failures and confirm all-or-nothing semantics

**Applicable FRs:** AUTH (AUTH-CN-08), REG (REG-CN-03)

**Status:** Defined

## NFR-REL-02: Idempotent Bootstrap Operations

**Category:** System Initialization

**Requirement:**
System bootstrap and setup operations must be safely re-runnable without creating duplicate records or corrupting existing state. Running the same bootstrap operation multiple times must produce the same final state as running it once.

**Acceptance Criteria:**
- [ ] Admin bootstrap command checks for existing admin before creating (skip if exists)
- [ ] Database migration operations are idempotent (Django's migration framework ensures this)
- [ ] Environment profile initialization can be re-run without errors
- [ ] Bootstrap operations log when they skip due to existing state (not silent)
- [ ] No bootstrap operation deletes and recreates existing records

**Verification Method:** Automated test - integration tests run bootstrap operations twice and verify state matches single-run state

**Applicable FRs:** AUTH, ENV (ENV-CN-05), OBS (OBS-CN-01)

**Status:** Defined

## NFR-REL-03: REST-Compliant API Design

**Category:** API Design

**Requirement:**
All API endpoints must follow REST conventions to ensure consistent, predictable behavior. This includes using resource nouns (not action verbs) in URL paths, correct HTTP methods for operations, and consistent pluralization of resource names.

**Acceptance Criteria:**
- [ ] All endpoint paths use resource nouns, not action verbs (e.g., `/users` not `/createuser`)
- [ ] POST creates new resources, PATCH updates existing resources (partial), PUT replaces entire resources, DELETE removes resources
- [ ] Resource IDs appear in URL paths for update/delete operations (e.g., `/users/<id>` not ID in request body)
- [ ] All resource names are consistently plural across modules (e.g., `/visualizations` not `/visualization`)
- [ ] Lifecycle state transitions on existing resources use PATCH on the resource endpoint (e.g., `/codes/{id}` with target state payload)
- [ ] Workflow state transitions on existing resources also use PATCH (e.g., `/reset-requests/{id}` with `status=APPROVED|DENIED`)
- [ ] HTTP method semantics match operation intent (creation uses POST, updates use PATCH/PUT)

**Verification Method:** Automated test - API contract tests verify endpoint paths and HTTP methods match REST conventions

**Applicable FRs:** AUTH, REG, CRS, SUB, VIZ, EXP

**Status:** Defined

## NFR-REL-04: Consistent API Error Format

**Category:** API Design

**Requirement:**
API error responses must follow a consistent structure across all endpoints to enable predictable error handling in client applications.

**Acceptance Criteria:**
- [ ] All API errors return a consistent JSON structure (error code, message, optional details)
- [ ] HTTP status codes correctly reflect error types (4xx for client errors, 5xx for server errors)
- [ ] Error messages do not expose internal system details (no stack traces, no database schema information)
- [ ] Validation errors include field-level detail (which field failed, why)
- [ ] Rate limit errors include retry-after information

**Verification Method:** Automated test - error handling tests verify response format consistency across all endpoints

**Applicable FRs:** AUTH, REG, CRS, SUB, VIZ, EXP

**Status:** Defined
