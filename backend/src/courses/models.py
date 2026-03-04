"""
Course and enrollment models for class management.

This module defines the models that represent courses (classes) and student
enrollments. Courses are created and owned by teachers, and students are
enrolled by teachers via roster import.

Course Workflow:
    1. Teacher creates a course (POST /api/v1/courses)
    2. Teacher imports students via CSV (POST /api/v1/students/import)
    3. Enrollments are automatically created linking students to the course
    4. Teacher creates assignments for the course
    5. Enrolled students can then view and submit assignments

Database Tables:
    courses     - Course records with name and teacher ownership
    enrollments - Many-to-many relationship between courses and students

Note:
    Deleting a course cascades to enrollments and related submissions.
    The teacher_profile uses PROTECT to prevent accidental data loss.
"""

from django.db import models

from accounts.models import StudentProfile, TeacherProfile, User


class CourseStatus(models.TextChoices):
    """
    Enumeration of course lifecycle states.

    Values:
        ACTIVE: Course is live and usable
        ARCHIVED: Course has been archived (soft-deleted)
    """

    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class EnrollmentStatus(models.TextChoices):
    """
    Enumeration of enrollment lifecycle states.

    Tracks whether a student is actively enrolled or has been dropped
    from a course. Dropped students retain historical submission data.

    Values:
        ACTIVE: Student is currently enrolled and can submit work
        DROPPED: Student was removed from course (historical data retained)
    """

    ACTIVE = "ACTIVE", "Active"
    DROPPED = "DROPPED", "Dropped"


class Course(models.Model):
    """
    A course (class) owned by a teacher.

    Courses are containers for assignments and student enrollments.
    Each course is owned by a single teacher who can manage students
    and create assignments.

    Attributes:
        name: Display name of the course (e.g., "Math 101 - Period 3")
        created_at: Timestamp when course was created
        teacher_profile: Foreign key to the owning TeacherProfile

    Related Models:
        enrollments: Enrollment instances for students in this course
        assignments: Assignment instances assigned to this course

    Note:
        Uses PROTECT on teacher_profile to prevent deleting a teacher
        who owns courses. Delete courses first, then the teacher.
    """

    # Course display name shown in UI
    name = models.CharField(max_length=255)

    # Timestamp for auditing when course was created
    created_at = models.DateTimeField(auto_now_add=True)

    # Teacher who owns and manages this course
    # PROTECT prevents orphaning courses if teacher is deleted
    teacher_profile = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        db_column="teacher_profile_id",
        related_name="courses",
    )

    # Lifecycle status for archival support
    status = models.CharField(
        max_length=16,
        choices=CourseStatus.choices,
        default=CourseStatus.ACTIVE,
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archived_courses",
    )
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restored_courses",
    )

    class Meta:
        """Database table configuration for Course."""

        db_table = "courses"
        indexes = [
            models.Index(fields=["name"], name="idx_course_name"),
            models.Index(fields=["teacher_profile"], name="idx_course_teacher"),
            models.Index(fields=["status"], name="idx_course_status"),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return self.name


class Enrollment(models.Model):
    """
    Links a student to a course they are enrolled in.

    Enrollments are created when teachers import students via CSV or
    manually add them to a course. The status field allows "soft delete"
    by marking students as DROPPED while retaining submission history.

    Attributes:
        course: Foreign key to the Course
        student_profile: Foreign key to the StudentProfile
        enrolled_at: Timestamp when enrollment was created
        status: Current enrollment state (ACTIVE or DROPPED)

    Related Models:
        submissions: Submission instances for this student in this course

    Unique Constraint:
        (course, student_profile) - prevents duplicate enrollments

    Note:
        Deleting a course cascades to delete all enrollments.
        Deleting a student profile cascades to delete enrollments.
    """

    # The course the student is enrolled in
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, db_column="course_id", related_name="enrollments"
    )

    # The student who is enrolled
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        db_column="student_profile_id",
        related_name="enrollments",
    )

    # When the enrollment was created
    enrolled_at = models.DateTimeField(auto_now_add=True)

    # Current status (ACTIVE or DROPPED for soft-delete)
    status = models.CharField(max_length=32, choices=EnrollmentStatus.choices)

    class Meta:
        """Database table configuration for Enrollment."""

        db_table = "enrollments"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student_profile"], name="uq_enrollment_course_student"
            ),
        ]
        indexes = [
            models.Index(fields=["course"], name="idx_enroll_course"),
            models.Index(fields=["student_profile"], name="idx_enroll_student"),
        ]

    def __str__(self):
        """Return a readable string representation."""
        return f"{self.course} -> {self.student_profile.user.username}"
