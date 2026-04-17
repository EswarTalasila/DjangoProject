# Code Style and Architecture Principles

## Official Documentation

Before diving into our conventions, familiarize yourself with the frameworks:

- [Django 5.2 Documentation](https://docs.djangoproject.com/en/5.2/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Python Style Guide (PEP 8)](https://peps.python.org/pep-0008/)

## Guiding philosophy
- Prefer clarity, local reasoning, and low coupling over clever abstraction.
- Keep functions small and single-purpose; avoid multi-responsibility functions.
- Use composition and small modules; avoid deep inheritance trees.

## Ownership-like discipline (Rust-inspired)
Python does not enforce ownership, but we can emulate the benefits:
- Treat data as immutable by default (dataclasses with `frozen=True` where possible).
- Pass data explicitly; avoid hidden mutation across module boundaries.
- Keep write operations within well-defined service functions (single writers).
- Use context managers for explicit resource lifetimes (DB transactions, file handles).
- Avoid shared mutable globals; prefer local state and return values.

## Function design
- One function does one thing; if it grows, split it.
- Pure functions for validation, scoring, and mapping are preferred.
- Side effects (DB writes, IO) are isolated to thin orchestration functions.

## Abstraction policy
- Do not generalize prematurely.
- Share code only when duplication causes real maintenance cost.
- If shared, keep the abstraction small and domain-aligned.

## Cohesion over coupling
- Domain modules own their logic and data transformations.
- Cross-domain calls go through clear service boundaries.
- Avoid circular imports by placing shared utilities in `core/`.

## OOP usage (minimal and purposeful)
- Django models stay lean (fields + minimal helpers).
- Service classes only if stateful behavior is unavoidable.
- Use strategy functions or mappings for grading modes rather than inheritance.

## Declarative patterns
- Use mapping tables and configuration dictionaries for behavior selection.
- Prefer data-driven configuration over class hierarchies.

---

## Detailed Examples

### Models: Do's and Don'ts

**DO: Keep models focused on data definition**
```python
class Course(models.Model):
    """
    A course taught by a teacher.

    Enrollments link students to courses. Assignments distribute
    assignment templates to course students.
    """

    name = models.CharField(max_length=255)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="courses_taught",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
```

**DON'T: Put business logic in models**
```python
# BAD - Model doing too much
class Course(models.Model):
    name = models.CharField(max_length=255)

    def enroll_student(self, student, created_by):
        # Business logic belongs in services.py, not here
        profile = StudentProfile.objects.get_or_create(user=student)
        enrollment = Enrollment.objects.create(
            course=self,
            student_profile=profile,
        )
        # Creating submissions here couples Course to Submission
        for assignment in self.assignments.all():
            Submission.objects.create(enrollment=enrollment, assignment=assignment)
        return enrollment
```

**DO: Use services.py for business logic**
```python
# courses/services.py
def enroll_student_in_course(course, student, created_by):
    """
    Enroll a student in a course and create empty submissions.

    Args:
        course: Course to enroll in
        student: User with STUDENT role
        created_by: User performing the enrollment (teacher)

    Returns:
        Enrollment instance

    Raises:
        ValueError: If student is already enrolled
    """
    if Enrollment.objects.filter(course=course, student_profile__user=student).exists():
        raise ValueError("Student already enrolled in this course")

    profile, _ = StudentProfile.objects.get_or_create(
        user=student,
        defaults={"created_by": created_by}
    )

    enrollment = Enrollment.objects.create(
        course=course,
        student_profile=profile,
    )

    # Create empty submissions for existing assignments
    _create_submissions_for_enrollment(enrollment)

    return enrollment
```

### Serializers: Do's and Don'ts

**DO: Use ModelSerializer for standard CRUD**
```python
class CourseSerializer(serializers.ModelSerializer):
    """
    Serializer for Course model.

    Used for course list/detail endpoints. Teacher field is read-only
    and set automatically from the request user.
    """

    class Meta:
        model = Course
        fields = ["id", "name", "teacher", "created_at"]
        read_only_fields = ["id", "teacher", "created_at"]
```

**DO: Use plain Serializer for custom input validation**
```python
class StudentInputSerializer(serializers.Serializer):
    """
    Input validation for adding a student to a course.

    This is not a ModelSerializer because it creates multiple
    objects (User, StudentProfile, Enrollment) from a single input.
    """

    name = serializers.CharField(max_length=255)
    username = serializers.EmailField()  # Email used as username
    courseId = serializers.IntegerField()
    consent = serializers.BooleanField(default=False)
    password = serializers.CharField(required=False, allow_blank=True)
```

**DON'T: Put business logic in serializers**
```python
# BAD - Serializer doing too much
class StudentInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    username = serializers.EmailField()
    courseId = serializers.IntegerField()

    def create(self, validated_data):
        # This belongs in services.py
        user = User.objects.create(
            username=validated_data["username"],
            name=validated_data["name"],
        )
        # ... more creation logic
```

### Views: Do's and Don'ts

**DO: Keep views thin - validate, delegate, respond**
```python
@api_view(["POST"])
@permission_classes([IsTeacher])
def add_student(request):
    """
    Add a single student to a course.

    POST /api/v1/students
    """
    # 1. Validate input
    serializer = StudentInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # 2. Delegate to service
    try:
        enrollment = create_student_in_course(request.user, serializer.validated_data)
    except ValueError as exc:
        return error_response(exc)

    # 3. Format and return response
    return Response(enrollment_to_payload(enrollment), status=status.HTTP_200_OK)
```

**DON'T: Put database queries directly in views**
```python
# BAD - View doing too much
@api_view(["POST"])
@permission_classes([IsTeacher])
def add_student(request):
    course = Course.objects.get(pk=request.data["courseId"])
    if course.teacher != request.user:
        return Response("Not your course", status=403)

    user = User.objects.create(
        username=request.data["username"],
        name=request.data["name"],
    )
    UserRole.objects.create(user=user, role=Role.STUDENT)
    # ... more inline logic
```

### Permission Classes: Do's and Don'ts

**DO: Create reusable permission classes**
```python
# core/permissions.py
class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Allow access to teachers or admins.

    Use this for management endpoints where both roles
    should have access (e.g., viewing submissions).
    """

    def has_permission(self, request, view):
        return has_any_role(request.user, (Role.ADMIN, Role.TEACHER))
```

**DO: Use permission classes on every endpoint**
```python
@api_view(["GET"])
@permission_classes([IsTeacherOrAdmin])  # Always specify permissions
def get_course_submissions(request, course_id):
    ...
```

**DON'T: Check roles inline in views**
```python
# BAD - Inline role checking
@api_view(["GET"])
def get_course_submissions(request, course_id):
    if request.user.roles.filter(role="TEACHER").exists():
        # ... handle teacher
    elif request.user.roles.filter(role="ADMIN").exists():
        # ... handle admin
    else:
        return Response("Forbidden", status=403)
```

### Error Handling: Do's and Don'ts

**DO: Use the shared error helpers**
```python
from core.errors import error_response, server_error_response

@api_view(["GET"])
def get_course(request, pk):
    try:
        course = Course.objects.get(pk=pk)
    except Course.DoesNotExist:
        return error_response("Course not found")  # Auto-detects 404

    return Response(CourseSerializer(course).data)
```

**DON'T: Create ad-hoc error responses**
```python
# BAD - Inconsistent error format
@api_view(["GET"])
def get_course(request, pk):
    try:
        course = Course.objects.get(pk=pk)
    except Course.DoesNotExist:
        return Response({"error": "Not found"}, status=404)  # Different format
```

### Docstrings: Do's and Don'ts

**DO: Document the "why" and public interface**
```python
def create_student_in_course(teacher, data):
    """
    Create a student account and enroll them in a course.

    This is the primary entry point for adding students. It handles:
    - Creating the User account with STUDENT role
    - Creating or retrieving the StudentProfile
    - Creating the Enrollment
    - Creating empty Submissions for existing assignments

    Args:
        teacher: The teacher adding the student (must own the course)
        data: Validated dict with name, username, courseId, consent, password

    Returns:
        Enrollment instance for the new student

    Raises:
        ValueError: If course not found or teacher doesn't own it
        ValueError: If student already enrolled
    """
```

**DON'T: Document obvious code**
```python
# BAD - Stating the obvious
def get_course(pk):
    """Get a course by primary key."""  # The function name already says this
    return Course.objects.get(pk=pk)
```

**DO: Keep docstrings minimal for simple functions**
```python
def enrollment_to_payload(enrollment):
    """Convert an Enrollment to the student API response format."""
    # No need to document every field - the code is clear
    return {
        "id": enrollment.student_profile.user.id,
        "name": enrollment.student_profile.user.name,
        ...
    }
```

---

## Project Structure Conventions

```
backend/src/
├── accounts/          # User authentication and profiles
│   ├── models.py      # User, UserRole, StudentProfile, TeacherProfile
│   ├── serializers.py # Input/output validation
│   ├── views.py       # Auth endpoints (login, register, etc.)
│   ├── services.py    # Business logic (user creation, etc.)
│   └── admin.py       # Django admin configuration
├── courses/
│   ├── models.py      # Course, Enrollment
│   ├── services.py    # Enrollment logic, student creation
│   └── views.py       # Course CRUD endpoints
├── core/              # Shared utilities (no models)
│   ├── permissions.py # Role-based permission classes
│   └── errors.py      # Error response helpers
└── config/            # Django settings and root URL config
```

**Convention:** Each domain module follows the same structure:
- `models.py` - Data definitions only
- `serializers.py` - Input validation and output formatting
- `views.py` - Thin HTTP handlers
- `services.py` - Business logic and orchestration
- `admin.py` - Django admin configuration

---

## Tooling and enforcement
- Linting: ruff for style and complexity thresholds.
- Formatting: black.
- Type hints: mypy (gradual adoption; tighten to strict on core modules over time).
- Tests required for any shared abstraction.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
