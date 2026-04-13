# NFR-Operations

| Field | Value |
|-------|-------|
| **Status** | Active |

---

## Overview

This document defines the operations policies that apply across the EE-Lab platform. Operations requirements ensure reliable deployment, configuration management, observability, and safe environment separation. All entries are cross-cutting policies that apply to multiple functional domains and support operational excellence.

---

## NFR-OPS-01: Environment Profile System

**Category:** Configuration Management

**Requirement:**
Application must support distinct environment configurations (development, testing, production) with a single authoritative signal that all components read to determine operational behavior.

**Acceptance Criteria:**
- [ ] ENVIRONMENT variable exists with exactly three valid values: development, testing, production
- [ ] All backend components read ENVIRONMENT from a single configuration source
- [ ] Environment-specific behaviors (debug tooling, API documentation exposure, credential validation) are keyed to ENVIRONMENT value
- [ ] Default environment is development for local development convenience
- [ ] Environment signal is explicitly set in production deployment templates

**Verification Method:** Automated test - environment configuration tests verify behavior changes per environment

**Applicable FRs:** AUTH, REG, CRS, SUB, VIZ, EXP, OBS (OBS-CN-04), ENV (ENV-CN-01, ENV-CN-12)

**Status:** Defined

---

## NFR-OPS-02: Startup Validation

**Category:** Configuration Management

**Requirement:**
Application must validate configuration at startup and fail fast with clear error messages when production configuration is insecure or incomplete.

**Acceptance Criteria:**
- [ ] Production environment startup validation rejects insecure DJANGO_SECRET_KEY values
- [ ] Production environment startup validation rejects DJANGO_DEBUG=true
- [ ] Production environment startup validation rejects development default DATABASE_URL
- [ ] Validation errors list all configuration violations in a single startup failure message
- [ ] Development and testing environments skip validation (allow convenient defaults)
- [ ] Application refuses to serve requests when production validation fails

**Verification Method:** Automated test - startup validation tests verify production guards and development bypass

**Applicable FRs:** All domains, OBS (OBS-CN-01), ENV (ENV-CN-02, ENV-CN-10)

**Status:** Defined

---

## NFR-OPS-03: Secret Management

**Category:** Security Operations

**Requirement:**
Production secrets must be encrypted at rest with separate decryption keys managed outside the codebase.

**Acceptance Criteria:**
- [ ] Production secrets stored in encrypted vault files (.env.vault)
- [ ] Decryption keys (.env.keys) never committed to version control
- [ ] Encryption tooling (dotenvx or equivalent) supports encrypted storage with plaintext-free deployment
- [ ] Secret rotation workflow supports re-encryption without service interruption
- [ ] Development environment continues using plaintext .env files for convenience

**Verification Method:** Policy - encryption tooling integrated, key distribution procedure documented

**Applicable FRs:** All domains, ENV (ENV-CN-06)

**Status:** Defined

---

## NFR-OPS-04: Deployment Guards

**Category:** Environment Safety

**Requirement:**
Dangerous operations (test data seeding, debug tooling) must be prevented in production environments.

**Acceptance Criteria:**
- [ ] Test data seeding commands refuse to execute when ENVIRONMENT=production
- [ ] API documentation endpoints (Swagger, ReDoc, schema) not registered in production URL patterns
- [ ] Debug toolbar and django_extensions not loaded in production INSTALLED_APPS
- [ ] Production guard violations result in clear error messages identifying the blocked operation
- [ ] Development and testing environments allow all debug tooling and seeding operations

**Verification Method:** Automated test - deployment guard tests verify production blocks and development/testing allow

**Applicable FRs:** All domains, ENV (ENV-CN-07)

**Status:** Defined

---

## NFR-OPS-05: Observability Instrumentation — DEFERRED

**Category:** Distributed Tracing

**Requirement:**
Application must have distributed tracing with W3C Trace Context propagation for end-to-end request correlation across services.

**Status:** Deferred. OpenTelemetry runtime code has been removed. If reintroduced later it will be rebuilt intentionally with a clean interface.

---

## NFR-OPS-06: Audit Logging

**Category:** Operational Logging

**Requirement:**
System must maintain structured logs with consistent format and trace correlation for operational debugging and incident investigation.

**Acceptance Criteria:**
- [ ] Backend logs use structured JSON format with consistent field names
- [ ] All log entries include timestamp, log level, logger name, and message
- [ ] HTTP request logs include method, path, status code, and response time
- [ ] Database query logs include statement type and execution time
- [ ] Log retention: 30 days for development, 90 days for production
- [ ] Logs aggregated to centralized collection in production

**Verification Method:** Manual review - log format inspection and aggregation pipeline verification

**Applicable FRs:** All domains (infrastructure requirement)

**Status:** Defined

---

## NFR-OPS-07: Runtime Observability

**Category:** Operations

**Requirement:**
Application logs and diagnostics must remain readable and actionable during local and server operation. Distributed tracing is currently deferred until it is rebuilt intentionally.

**Acceptance Criteria:**
- [ ] Backend logs remain structured and readable during startup, shutdown, and testing
- [ ] Task-driven diagnostics surface enough information to debug stack failures
- [ ] Observability additions are introduced only through an explicit future rebuild

**Verification Method:** Automated test + operator review

**Applicable FRs:** All domains (infrastructure requirement)

**Status:** Defined

---
