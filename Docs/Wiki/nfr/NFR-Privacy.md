# NFR-Privacy

| Field | Value |
|-------|-------|
| **Status** | Active |

---

## Overview

Privacy requirements ensure the EE-Lab application protects student educational data in compliance with FERPA regulations. This includes data access controls, PII protection in logs and operations, and audit trails for compliance verification.

## NFR-PRIV-01: FERPA-Compliant Data Access Controls

**Category:** Educational Data Protection

**Requirement:**
Student educational data must be protected with role-based access controls that comply with FERPA regulations. Teachers can only access data for students enrolled in their courses. Researchers can access aggregated data by default. Students can only access their own data. Expanded researcher access requires explicit sudo authorization and auditing.

**Acceptance Criteria:**
- [ ] Teachers cannot access student data for courses they do not teach
- [ ] Students cannot access other students' data
- [ ] Researchers view anonymized/aggregated data by default
- [ ] Researcher sudo permissions can grant expanded user-space access without granting admin-space control
- [ ] All researcher sudo-based expanded access is auditable with actor, scope, and outcome
- [ ] Direct student record access requires explicit authorization checks
- [ ] API endpoints enforce role-based data access filters at the database query level

**Verification Method:** Automated test - access control tests verify data isolation across roles and course boundaries

**Applicable FRs:** AUTH, CRS, SUB, VIZ, REG (REG-CN-10)

**Status:** Defined

## NFR-PRIV-02: PII Protection in Application Logs

**Category:** Data Protection

**Requirement:**
Application logs must protect personally identifiable information (PII) to prevent unauthorized access to sensitive student data. Email addresses must be redacted, student IDs must be hashed, and full names must not appear in plaintext logs.

**Acceptance Criteria:**
- [ ] Email addresses are redacted in logs (show domain only or hash completely)
- [ ] Student IDs are hashed before logging (consistent hash for correlation, not reversible)
- [ ] Full names do not appear in plaintext logs (use user IDs or hashed identifiers)
- [ ] OAuth tokens and session identifiers are never logged
- [ ] Database connection strings with credentials are never logged

**Verification Method:** Manual review - log analysis verifies PII redaction patterns are consistently applied

**Applicable FRs:** AUTH, REG, CRS, SUB

**Status:** Defined

## NFR-PRIV-03: Audit Trail for FERPA Data Access

**Category:** Compliance

**Requirement:**
Access to FERPA-protected student educational records must be logged to support compliance audits. Audit logs must record who accessed which student records, when, and for what purpose (the operation performed).

**Acceptance Criteria:**
- [ ] All student record queries log the requesting user, student ID (hashed), and operation type
- [ ] Audit log entries include timestamp, trace ID for correlation, and outcome (success/failure)
- [ ] Audit logs are write-only (no deletion, no modification after creation)
- [ ] Audit log access is restricted to authorized administrators and compliance reviewers
- [ ] Audit logs are retained for the duration required by FERPA regulations (3 years minimum)

**Verification Method:** Automated test - audit logging tests verify log entries are created for protected data access

**Applicable FRs:** AUTH, CRS, SUB, VIZ

**Status:** Defined
