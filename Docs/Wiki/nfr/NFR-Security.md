# NFR-Security

| Field | Value |
|-------|-------|
| **Status** | Active |

---

## Overview

This document defines the security policies that apply across the EE-Lab platform. Security requirements ensure protection against common attack vectors (brute-force, credential enumeration, session hijacking, credential exposure) while maintaining usability for teachers, students, and researchers. All entries are cross-cutting policies that apply to multiple functional domains.

---

## NFR-SEC-01: Rate Limiting Protection

**Category:** API Security

**Requirement:**
All authentication and registration endpoints must implement rate limiting to prevent brute-force attacks and credential enumeration.

**Acceptance Criteria:**
- [ ] Login endpoints limited to max 5 attempts per 15 minutes per subject identifier (e.g., email) with per-IP backstop limits
- [ ] Registration code validation endpoints limited to max 10 attempts per minute per code/subject identifier with per-IP backstop limits
- [ ] Account creation endpoints limited to max 3 attempts per hour per subject identifier with per-IP backstop limits
- [ ] Rate limiting applies to both AUTH and REG domains
- [ ] Rate limit enforcement verified via integration tests

**Verification Method:** Automated test - integration tests verify rate limit enforcement under load

**Applicable FRs:** AUTH (AUTH-CN-03), REG

**Status:** Defined

---

## NFR-SEC-02: Registration Code Entropy

**Category:** Authentication Security

**Requirement:**
Registration codes must have sufficient entropy to prevent brute-force guessing attacks within their validity window.

**Acceptance Criteria:**
- [ ] Student class codes use minimum 6 alphanumeric characters (36^6 combinations)
- [ ] Teacher registration codes use minimum 12 alphanumeric characters
- [ ] Researcher registration codes use minimum 12 alphanumeric characters
- [ ] Code generation uses cryptographically secure random number generator
- [ ] Combined with rate limiting and short expiration, brute-force attacks are impractical

**Verification Method:** Automated test - code generation tests verify length and character set requirements

**Applicable FRs:** REG (REG-CN-01)

**Status:** Defined

---

## NFR-SEC-03: Enumeration Prevention

**Category:** Authentication Security

**Requirement:**
System must not reveal whether specific user accounts exist through error messages, response timing, or status codes.

**Acceptance Criteria:**
- [ ] Login attempts return identical error messages for non-existent accounts and incorrect passwords
- [ ] Registration code validation does not reveal whether a code exists
- [ ] Password reset flows do not confirm whether an email address is registered
- [ ] Response timing for valid vs invalid credentials is consistent (no timing-based enumeration)

**Verification Method:** Manual review - security audit verifies error messages and response patterns

**Applicable FRs:** AUTH (AUTH-CN-04), REG

**Status:** Defined

---

## NFR-SEC-04: Password Strength Policy

**Category:** Credential Management

**Requirement:**
User passwords must meet minimum strength requirements to prevent compromise through dictionary attacks or common credential lists.

**Acceptance Criteria:**
- [ ] Production environment: minimum 12 characters for bootstrap admin accounts
- [ ] Production environment: passwords rejected if matching denylist (change-me, password, admin, secret)
- [ ] Development/testing environments may use explicit default values for local convenience
- [ ] Production environment must reject template placeholders and insecure default credentials at startup
- [ ] All environments: password strength validation uses industry-standard guidelines (NIST SP 800-63B)

**Verification Method:** Automated test - startup validation tests verify password strength enforcement per environment

**Applicable FRs:** AUTH (AUTH-CN-01), ENV (ENV-CN-04)

**Status:** Defined

---

## NFR-SEC-05: Session Security

**Category:** Session Management

**Requirement:**
Authentication tokens must use secure storage mechanisms and short-lived access tokens to minimize exposure risk.

**Acceptance Criteria:**
- [ ] Access tokens stored in HTTP-only cookies (prevents XSS access)
- [ ] Cookies use Secure flag in non-development environments
- [ ] Cookies use SameSite flag for CSRF protection
- [ ] Access tokens are short-lived and bounded by a domain constraint policy (AUTH-CN-02)
- [ ] A dedicated refresh-token mechanism exists with bounded lifetime and replay mitigation

**Verification Method:** Automated test - integration tests verify cookie security flags and token lifetime enforcement

**Applicable FRs:** AUTH (AUTH-CN-02, AUTH-CN-11), ENV (ENV-CN-08)

**Status:** Defined

---

## NFR-SEC-06: Credential Exposure Prevention

**Category:** Credential Management

**Requirement:**
System must refuse to start in production with known-insecure default credentials or configuration values.

**Acceptance Criteria:**
- [ ] Production startup validation rejects DJANGO_SECRET_KEY containing "insecure" or matching template defaults
- [ ] Production startup validation rejects ADMIN_PASSWORD matching .env.template placeholder values
- [ ] Production startup validation rejects DATABASE_URL matching development default connection strings
- [ ] Application fails fast on startup with clear error messages listing all configuration violations
- [ ] Development and testing environments allow convenient defaults (validation skipped)

**Verification Method:** Automated test - startup validation tests verify production credential enforcement

**Applicable FRs:** AUTH, ENV (ENV-CN-09)

**Status:** Defined

---
