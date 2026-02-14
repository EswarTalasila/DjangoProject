# Security Test Patterns

| Property | Value |
|----------|-------|
| Status | FINAL |
| Scope | Security abuse case test patterns |
| Applies To | backend/tests/security/ |
| Last Updated | 2026-02-10 |
| OWASP Reference | WSTG v4.2 |

## 1. Purpose

This document provides reusable pytest patterns for security abuse cases following the OWASP Web Security Testing Guide (WSTG) methodology.

Each pattern serves as a template that developers use when implementing test stubs in `backend/tests/security/`. The patterns use the project's actual fixtures (`api_client` and `authenticated_client` from `conftest.py`) to ensure consistency and compatibility with the existing test infrastructure.

These patterns bridge the gap between test stub declarations and production implementations, providing executable code templates with clear threat models, mitigation strategies, and OWASP traceability.

## 2. Pattern Structure

Each security test pattern includes the following components:

- **Threat**: What the attacker attempts to exploit
- **Mitigation**: How the system prevents the attack
- **Template**: Executable pytest code showing test implementation
- **OWASP Reference**: WSTG test ID for audit traceability
- **Implementation Notes**: Project-specific guidance and prerequisites

## 3. Authentication Abuse Patterns

Maps to: `test_auth_abuse.py`

### 3.1 Brute Force Protection (WSTG-ATHN-03)

**Threat**: Automated password guessing attacks attempting to discover valid credentials through repeated login attempts.

**Mitigation**: Rate limiting on authentication endpoints that throttles or blocks requests after N failed attempts.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_brute_force_login_rate_limiting(api_client):
    """Verify account lockout or rate limiting after N failed login attempts."""
    # Perform 10 failed login attempts
    for i in range(10):
        response = api_client.post(
            '/api/v1/auth/sessions',
            {'email': 'test@example.com', 'password': 'WrongPassword123!'},
            format='json'
        )
        assert response.status_code == 401

    # 11th attempt should be rate limited
    response = api_client.post(
        '/api/v1/auth/sessions',
        {'email': 'test@example.com', 'password': 'WrongPassword123!'},
        format='json'
    )
    assert response.status_code == 429  # Too Many Requests
    assert 'rate limit' in str(response.data).lower()
```

**OWASP Reference**: [WSTG-ATHN-03](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/04-Authentication_Testing/03-Testing_for_Weak_Lock_Out_Mechanism)

**Implementation Notes**: Depends on rate limiting middleware being in place. Test stub skip reason specifies this prerequisite. Consider testing both per-account and per-IP rate limits.

### 3.2 JWT Token Manipulation (WSTG-SESS-06)

**Threat**: Attacker modifies JWT payload (e.g., changing role claim from 'student' to 'admin') to escalate privileges.

**Mitigation**: Signature validation and claim verification reject tokens with invalid signatures or unexpected claims.

**Template**:

```python
import jwt
from datetime import datetime, timedelta

@pytest.mark.security
@pytest.mark.django_db
def test_jwt_token_manipulation(api_client, django_user_model):
    """Verify tampered JWT tokens are rejected."""
    # Create user and get valid token
    user = django_user_model.objects.create_user(
        email='student@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='Student'
    )

    # Get valid token via login
    response = api_client.post(
        '/api/v1/auth/sessions',
        {'email': 'student@example.com', 'password': 'SecurePass123!'},
        format='json'
    )
    valid_token = response.data['access_token']

    # Decode without verification to manipulate payload
    decoded = jwt.decode(valid_token, options={"verify_signature": False})
    decoded['role'] = 'admin'  # Attempt privilege escalation

    # Re-encode with wrong key
    tampered_token = jwt.encode(decoded, 'wrong-secret-key', algorithm='HS256')

    # Attempt to access admin endpoint with tampered token
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tampered_token}')
    response = api_client.get('/api/admin/users/')

    assert response.status_code == 401  # Unauthorized
```

**OWASP Reference**: [WSTG-SESS-06](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/06-Session_Management_Testing/06-Testing_for_JSON_Web_Tokens)

**Implementation Notes**: Uses PyJWT library for decode/encode operations. Import with `import jwt`. Test verifies signature validation is working correctly.

### 3.3 Expired Token Rejection (WSTG-SESS-07)

**Threat**: Replay attack using expired authentication tokens to gain unauthorized access after session should have ended.

**Mitigation**: Token expiration validation rejects tokens past their expiration time.

**Template**:

```python
import jwt
from datetime import datetime, timedelta
from django.conf import settings

@pytest.mark.security
@pytest.mark.django_db
def test_expired_token_rejection(api_client, django_user_model):
    """Verify expired tokens return 401."""
    user = django_user_model.objects.create_user(
        email='test@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='User'
    )

    # Create token with past expiration
    payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        'iat': datetime.utcnow() - timedelta(hours=2)
    }

    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    # Attempt API call with expired token
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {expired_token}')
    response = api_client.get('/api/courses/')

    assert response.status_code == 401
    assert 'expired' in str(response.data).lower()
```

**OWASP Reference**: [WSTG-SESS-07](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/06-Session_Management_Testing/07-Testing_Session_Timeout)

**Implementation Notes**: Can use `timedelta` to create expired tokens or mock time. Ensure JWT expiration validation is enabled in authentication middleware.

### 3.4 Session Fixation Prevention (WSTG-SESS-03)

**Threat**: Attacker sets session ID before authentication, then hijacks session after victim logs in with that fixed session ID.

**Mitigation**: Session regeneration on authentication creates new session ID after successful login.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_session_fixation_prevention(api_client, django_user_model):
    """Verify session ID changes after authentication."""
    user = django_user_model.objects.create_user(
        email='test@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='User'
    )

    # Get initial session ID (before login)
    response = api_client.get('/api/auth/status/')
    initial_session_id = api_client.cookies.get('sessionid')

    # Authenticate
    response = api_client.post(
        '/api/v1/auth/sessions',
        {'email': 'test@example.com', 'password': 'SecurePass123!'},
        format='json'
    )
    assert response.status_code == 200

    # Get session ID after login
    post_auth_session_id = api_client.cookies.get('sessionid')

    # Session ID should have changed
    assert initial_session_id != post_auth_session_id
    assert post_auth_session_id is not None
```

**OWASP Reference**: [WSTG-SESS-03](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/06-Session_Management_Testing/03-Testing_for_Session_Fixation)

**Implementation Notes**: Django sessions auto-regenerate by default via `update_session_auth_hash()`. Test verifies this behavior is not disabled. May need to adjust for JWT-only authentication systems.

## 4. Authorization Bypass Patterns

Maps to: `test_authorization_bypass.py`

### 4.1 Student-to-Admin Role Escalation (WSTG-ATHZ-02)

**Threat**: Lower-privileged user (student) attempts to access higher-privileged endpoints (admin-only) to perform unauthorized actions.

**Mitigation**: Role-based access control (RBAC) enforces permission checks on protected endpoints.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_student_cannot_access_admin_endpoints(api_client, django_user_model):
    """Verify student role cannot reach admin-only endpoints."""
    # Create student user
    student = django_user_model.objects.create_user(
        email='student@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='Student',
        role='STUDENT'
    )

    # Authenticate as student
    api_client.force_authenticate(user=student)

    # Attempt to access admin endpoints
    admin_endpoints = [
        ('/api/admin/users/', 'get'),
        ('/api/admin/courses/', 'post'),
        ('/api/admin/system/config/', 'get'),
    ]

    for endpoint, method in admin_endpoints:
        response = getattr(api_client, method)(endpoint)
        assert response.status_code == 403, f"Student accessed {endpoint}"
```

**OWASP Reference**: [WSTG-ATHZ-02](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/05-Authorization_Testing/02-Testing_for_Bypassing_Authorization_Schema)

**Implementation Notes**: Test all admin-only endpoints. Use `authenticated_client` fixture with student role override. Consider parameterized test with `pytest.mark.parametrize` for endpoint coverage.

### 4.2 Teacher-to-Admin Escalation (WSTG-ATHZ-02)

**Threat**: Teacher role performs admin actions like user management or system configuration that should be restricted to administrators only.

**Mitigation**: RBAC with admin-only restrictions prevents teachers from accessing administrative functions.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_teacher_cannot_escalate_to_admin(api_client, django_user_model):
    """Verify teacher role cannot perform admin actions."""
    # Create teacher user
    teacher = django_user_model.objects.create_user(
        email='teacher@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='Teacher',
        role='TEACHER'
    )

    # Authenticate as teacher
    api_client.force_authenticate(user=teacher)

    # Attempt admin actions
    response = api_client.get('/api/admin/users/')
    assert response.status_code == 403

    response = api_client.post(
        '/api/admin/users/',
        {'email': 'newuser@example.com', 'role': 'ADMIN'},
        format='json'
    )
    assert response.status_code == 403

    response = api_client.delete('/api/admin/users/1/')
    assert response.status_code == 403
```

**OWASP Reference**: [WSTG-ATHZ-02](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/05-Authorization_Testing/02-Testing_for_Bypassing_Authorization_Schema)

**Implementation Notes**: Separate from student test because teacher has more permissions (can create courses, manage own students) but still not admin. Verify each HTTP method (GET, POST, PUT, DELETE) is protected.

### 4.3 IDOR - Accessing Other Users' Data (WSTG-ATHZ-04)

**Threat**: User manipulates resource IDs in API requests to access or modify resources belonging to other users (Insecure Direct Object Reference).

**Mitigation**: Object-level permission checks verify ownership or access rights before returning data.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_idor_user_cannot_access_other_user_data(api_client, django_user_model):
    """Verify users cannot access resources belonging to other users by manipulating IDs."""
    # Create two users
    user1 = django_user_model.objects.create_user(
        email='user1@example.com',
        password='SecurePass123!',
        first_name='User',
        last_name='One',
        role='TEACHER'
    )
    user2 = django_user_model.objects.create_user(
        email='user2@example.com',
        password='SecurePass123!',
        first_name='User',
        last_name='Two',
        role='TEACHER'
    )

    # User1 creates a course
    api_client.force_authenticate(user=user1)
    response = api_client.post(
        '/api/courses/',
        {'name': 'User1 Course', 'description': 'Private'},
        format='json'
    )
    course_id = response.data['id']

    # User2 attempts to access User1's course
    api_client.force_authenticate(user=user2)
    response = api_client.get(f'/api/courses/{course_id}/')
    assert response.status_code == 403

    # User2 attempts to modify User1's course
    response = api_client.put(
        f'/api/courses/{course_id}/',
        {'name': 'Hijacked Course'},
        format='json'
    )
    assert response.status_code == 403
```

**OWASP Reference**: [WSTG-ATHZ-04](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References)

**Implementation Notes**: Test with courses, assessments, and submissions endpoints. Each resource type needs its own IDOR test. Verify both read and write operations are protected.

### 4.4 Unauthenticated Access Rejection (WSTG-ATHZ-01)

**Threat**: Bypassing authentication entirely by accessing protected endpoints without providing credentials.

**Mitigation**: Authentication middleware on all protected endpoints rejects unauthenticated requests.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_unauthenticated_access_rejected(api_client):
    """Verify protected endpoints return 401 without auth."""
    # Do NOT authenticate - use raw api_client

    protected_endpoints = [
        ('/api/courses/', 'get'),
        ('/api/courses/', 'post'),
        ('/api/assessments/', 'get'),
        ('/api/submissions/', 'post'),
        ('/api/admin/users/', 'get'),
    ]

    for endpoint, method in protected_endpoints:
        response = getattr(api_client, method)(endpoint)
        assert response.status_code == 401, f"Unauthenticated access allowed to {endpoint}"
```

**OWASP Reference**: [WSTG-ATHZ-01](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/05-Authorization_Testing/01-Testing_Directory_Traversal_File_Include)

**Implementation Notes**: Enumerate all protected endpoints. Consider parameterized test with `pytest.mark.parametrize` for comprehensive coverage. Verify both API and admin endpoints require authentication.

## 5. Input Validation Patterns

Maps to: `test_input_validation.py`

### 5.1 SQL Injection in Query Parameters (WSTG-INPV-05)

**Threat**: SQL code injection via input fields that could allow database manipulation or data exfiltration.

**Mitigation**: Parameterized queries (Django ORM automatically handles this) prevent SQL injection by treating user input as data, not executable code.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_sql_injection_in_query_params(api_client, authenticated_client, django_user_model):
    """Verify SQL injection attempts in query parameters are sanitized."""
    # Create test course data
    user = django_user_model.objects.create_user(
        email='teacher@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='Teacher',
        role='TEACHER'
    )
    authenticated_client.force_authenticate(user=user)

    # Create test course
    authenticated_client.post(
        '/api/courses/',
        {'name': 'Test Course', 'description': 'Test'},
        format='json'
    )

    # Attempt SQL injection via search parameter
    sql_payload = "'; DROP TABLE courses; --"
    response = authenticated_client.get(
        f'/api/courses/?search={sql_payload}'
    )

    # Should return 200 (not 500) and not execute SQL
    assert response.status_code == 200

    # Verify data still exists (table not dropped)
    response = authenticated_client.get('/api/courses/')
    assert response.status_code == 200
    assert len(response.data) > 0
```

**OWASP Reference**: [WSTG-INPV-05](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection)

**Implementation Notes**: Django ORM parameterizes queries by default. Test verifies no raw SQL is used that could bypass parameterization. Test various injection vectors (query params, form fields, JSON bodies).

### 5.2 XSS in Text Fields (WSTG-INPV-01)

**Threat**: JavaScript injection via text inputs that executes in other users' browsers when viewing the content.

**Mitigation**: Output escaping and Content Security Policy (CSP) prevent execution of injected scripts.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_xss_in_text_fields(api_client, authenticated_client, django_user_model):
    """Verify XSS payloads in text inputs are escaped or rejected."""
    user = django_user_model.objects.create_user(
        email='teacher@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='Teacher',
        role='TEACHER'
    )
    authenticated_client.force_authenticate(user=user)

    # XSS payload
    xss_payload = '<script>alert("XSS")</script>'

    # POST to create resource with XSS in title
    response = authenticated_client.post(
        '/api/courses/',
        {'name': xss_payload, 'description': 'Test'},
        format='json'
    )

    # Either rejected (400) or stored safely
    if response.status_code == 400:
        assert 'invalid' in str(response.data).lower()
    else:
        assert response.status_code == 201
        course_id = response.data['id']

        # Retrieve and verify escaping
        response = authenticated_client.get(f'/api/courses/{course_id}/')
        assert response.status_code == 200
        # Raw <script> tag should not appear in response
        assert '<script>' not in response.data['name']
```

**OWASP Reference**: [WSTG-INPV-01](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/07-Input_Validation_Testing/01-Testing_for_Reflected_Cross_Site_Scripting)

**Implementation Notes**: Django auto-escapes template output. Test verifies API responses also escape or reject XSS payloads. Test both reflected XSS (immediate response) and stored XSS (retrieved later).

### 5.3 Oversized Payload Rejection (WSTG-INPV-17)

**Threat**: Denial of service via extremely large request bodies that exhaust server memory or processing resources.

**Mitigation**: Request size limits reject payloads exceeding configured thresholds.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_oversized_payload_rejected(api_client, authenticated_client, django_user_model):
    """Verify extremely large request bodies are rejected."""
    user = django_user_model.objects.create_user(
        email='teacher@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='Teacher',
        role='TEACHER'
    )
    authenticated_client.force_authenticate(user=user)

    # Create 10MB payload (exceeds Django default of 2.5MB)
    oversized_description = 'A' * (10 * 1024 * 1024)  # 10MB

    response = authenticated_client.post(
        '/api/courses/',
        {'name': 'Test', 'description': oversized_description},
        format='json'
    )

    # Should be rejected with 413 or 400
    assert response.status_code in [413, 400]
```

**OWASP Reference**: [WSTG-INPV-17](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/07-Input_Validation_Testing/17-Testing_for_HTTP_Incoming_Requests)

**Implementation Notes**: Django default `DATA_UPLOAD_MAX_MEMORY_SIZE` is 2.5MB. Test should exceed this threshold. May also test file upload size limits separately.

### 5.4 Malformed JSON Handling (WSTG-INPV-01)

**Threat**: Application crash from invalid input format, potentially exposing stack traces or causing downtime.

**Mitigation**: Input validation and error handling return user-friendly errors without crashing.

**Template**:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_malformed_json_handling(api_client, authenticated_client, django_user_model):
    """Verify malformed JSON in request body returns 400, not 500."""
    user = django_user_model.objects.create_user(
        email='teacher@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='Teacher',
        role='TEACHER'
    )
    authenticated_client.force_authenticate(user=user)

    # Send invalid JSON
    response = authenticated_client.post(
        '/api/courses/',
        data='{"name": "Test", invalid json here}',
        content_type='application/json'
    )

    # Should return 400 (client error), not 500 (server error)
    assert response.status_code == 400
    assert 'json' in str(response.data).lower() or 'parse' in str(response.data).lower()
```

**OWASP Reference**: [WSTG-INPV-01](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/07-Input_Validation_Testing/01-Testing_for_Reflected_Cross_Site_Scripting)

**Implementation Notes**: Django REST Framework handles JSON parsing errors by default. Test verifies graceful degradation with 400 not 500. Ensure error messages don't leak sensitive information.

## 6. Running Security Tests

Execute security tests using pytest markers:

```bash
# Run all security tests
pytest -m security

# Run specific test category
pytest backend/tests/security/test_auth_abuse.py -m security

# Run with verbose output
pytest -m security -v

# Run security tests that don't require database
pytest -m "security and not django_db"

# Run with coverage
pytest -m security --cov=backend/src --cov-report=term-missing
```

## 7. OWASP WSTG Mapping Table

This table maps each test stub to its corresponding OWASP WSTG test ID for audit traceability:

| Test File | Test Function | OWASP WSTG ID | WSTG Category Name |
|-----------|---------------|---------------|-------------------|
| test_auth_abuse.py | test_brute_force_login_rate_limiting | WSTG-ATHN-03 | Testing for Weak Lock Out Mechanism |
| test_auth_abuse.py | test_jwt_token_manipulation | WSTG-SESS-06 | Testing JSON Web Tokens |
| test_auth_abuse.py | test_expired_token_rejection | WSTG-SESS-07 | Testing Session Timeout |
| test_auth_abuse.py | test_session_fixation_prevention | WSTG-SESS-03 | Testing for Session Fixation |
| test_authorization_bypass.py | test_student_cannot_access_admin_endpoints | WSTG-ATHZ-02 | Testing for Bypassing Authorization Schema |
| test_authorization_bypass.py | test_teacher_cannot_escalate_to_admin | WSTG-ATHZ-02 | Testing for Bypassing Authorization Schema |
| test_authorization_bypass.py | test_idor_user_cannot_access_other_user_data | WSTG-ATHZ-04 | Testing for Insecure Direct Object References |
| test_authorization_bypass.py | test_unauthenticated_access_rejected | WSTG-ATHZ-01 | Testing Directory Traversal File Include |
| test_input_validation.py | test_sql_injection_in_query_params | WSTG-INPV-05 | Testing for SQL Injection |
| test_input_validation.py | test_xss_in_text_fields | WSTG-INPV-01 | Testing for Reflected Cross Site Scripting |
| test_input_validation.py | test_oversized_payload_rejected | WSTG-INPV-17 | Testing for HTTP Incoming Requests |
| test_input_validation.py | test_malformed_json_handling | WSTG-INPV-01 | Testing for Reflected Cross Site Scripting |

## 8. Shared Fixtures Reference

The patterns use fixtures defined in `backend/tests/security/conftest.py`:

### api_client

```python
@pytest.fixture
def api_client():
    """Return a Django REST Framework APIClient instance."""
    return APIClient()
```

**Usage**: Unauthenticated API client for testing endpoints that should reject unauthenticated requests.

### authenticated_client

```python
@pytest.fixture
def authenticated_client(api_client):
    """Return an authenticated APIClient with a test user."""
    User = get_user_model()
    user = User.objects.create_user(
        email="test@example.com",
        password="SecurePassword123!",
        first_name="Test",
        last_name="User"
    )
    api_client.force_authenticate(user=user)
    return api_client
```

**Usage**: Pre-authenticated API client for testing authorized operations.

### Role-Specific Authentication

For tests requiring specific roles (student, teacher, admin), create user with specific role and authenticate:

```python
@pytest.mark.security
@pytest.mark.django_db
def test_role_specific(api_client, django_user_model):
    student = django_user_model.objects.create_user(
        email='student@example.com',
        password='SecurePass123!',
        first_name='Test',
        last_name='Student',
        role='STUDENT'
    )
    api_client.force_authenticate(user=student)
    # Test with student role...
```

**Note**: Use `api_client` fixture (not `django.test.Client`) to ensure compatibility with Django REST Framework views and serializers.
