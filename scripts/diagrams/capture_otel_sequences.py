#!/usr/bin/env python3
"""Exercise backend API routes to generate OTEL traces for sequence diagrams."""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any, Iterable, Tuple

BASE_URL = os.environ.get("OTEL_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")

ADMIN_EMAIL = os.environ.get("E2E_ADMIN_USERNAME", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "change-me")

DEFAULT_TEACHER_PASSWORD = os.environ.get("E2E_TEACHER_PASSWORD", "teacherpass")
DEFAULT_STUDENT_PASSWORD = os.environ.get("E2E_STUDENT_PASSWORD", "studentpass")


def _request_json(
    method: str,
    path: str,
    payload: dict | list | str | None = None,
    token: str | None = None,
) -> Tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        if isinstance(payload, str):
            headers["Content-Type"] = "text/plain"
            data = payload.encode("utf-8")
        else:
            data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        status = err.code
        body = err.read().decode("utf-8") if err.fp else ""
    except Exception as err:
        return 0, str(err)

    if not body:
        return status, None
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, body


def _expect(label: str, status: int, expected: Iterable[int]) -> None:
    ok = status in expected
    status_text = "ok" if ok else "unexpected"
    print(f"[{status_text}] {label}: {status}")


def _call(
    label: str,
    method: str,
    path: str,
    payload: dict | list | str | None = None,
    token: str | None = None,
    expected: Iterable[int] | None = None,
) -> Tuple[int, Any]:
    status, body = _request_json(method, path, payload, token)
    if expected is not None:
        _expect(label, status, expected)
    else:
        print(f"[info] {label}: {status}")
    return status, body


def _unique_email(prefix: str) -> str:
    stamp = int(time.time() * 1000)
    nonce = random.randint(1000, 9999)
    return f"{prefix}-{stamp}-{nonce}@example.com"


def main() -> None:
    print(f"Base URL: {BASE_URL}")

    _call(
        "auth.check-email existing",
        "POST",
        "/auth/check-email",
        {"email": ADMIN_EMAIL},
        expected={200, 404},
    )
    _call(
        "auth.check-email missing",
        "POST",
        "/auth/check-email",
        {"email": "missing@example.com"},
        expected={404},
    )

    status, body = _call(
        "auth.login",
        "POST",
        "/auth/login",
        {"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        expected={200},
    )
    admin_token = body.get("accessToken") if isinstance(body, dict) else None
    admin_id = body.get("id") if isinstance(body, dict) else None

    _call(
        "auth.login invalid",
        "POST",
        "/auth/login",
        {"username": ADMIN_EMAIL, "password": "wrong"},
        expected={401},
    )

    _call(
        "auth.google missing",
        "POST",
        "/auth/google",
        {},
        expected={400},
    )

    student_register_email = _unique_email("student")
    _call(
        "auth.register",
        "POST",
        "/auth/register",
        {
            "username": student_register_email,
            "password": DEFAULT_STUDENT_PASSWORD,
            "name": "Registered Student",
        },
        expected={200},
    )
    _call(
        "auth.register duplicate",
        "POST",
        "/auth/register",
        {
            "username": student_register_email,
            "password": DEFAULT_STUDENT_PASSWORD,
            "name": "Registered Student",
        },
        expected={400},
    )

    if not admin_token:
        print("No admin token available. Skipping admin/teacher-only flows.")
        return

    teacher_email = _unique_email("teacher")
    _call(
        "auth.createuser teacher",
        "POST",
        "/auth/createuser",
        {
            "username": teacher_email,
            "password": DEFAULT_TEACHER_PASSWORD,
            "name": "Teacher User",
            "role": "ROLE_TEACHER",
        },
        admin_token,
        expected={200},
    )

    reset_teacher_email = _unique_email("teacher")
    _call(
        "auth.createuser reset-teacher",
        "POST",
        "/auth/createuser",
        {
            "username": reset_teacher_email,
            "password": DEFAULT_TEACHER_PASSWORD,
            "name": "Reset Teacher",
            "role": "ROLE_TEACHER",
        },
        admin_token,
        expected={200},
    )

    _call(
        "auth.create.bulk invalid",
        "POST",
        "/auth/create/bulk",
        {"not": "a list"},
        admin_token,
        expected={400},
    )
    _call(
        "auth.create.bulk",
        "POST",
        "/auth/create/bulk",
        [
            {
                "username": _unique_email("teacher"),
                "password": DEFAULT_TEACHER_PASSWORD,
                "name": "Bulk Teacher",
                "role": "ROLE_TEACHER",
            }
        ],
        admin_token,
        expected={200},
    )
    _call(
        "auth.createuser unauthorized",
        "POST",
        "/auth/createuser",
        {
            "username": _unique_email("admin"),
            "password": "pass",
            "name": "Forbidden Admin",
            "role": "ROLE_ADMIN",
        },
        None,
        expected={401},
    )

    status, body = _call(
        "auth.login teacher",
        "POST",
        "/auth/login",
        {"username": teacher_email, "password": DEFAULT_TEACHER_PASSWORD},
        expected={200},
    )
    teacher_token = body.get("accessToken") if isinstance(body, dict) else None
    teacher_id = body.get("id") if isinstance(body, dict) else None

    _call("auth.teachers-admins", "GET", "/auth/teachers-admins", None, admin_token, {200})
    _call(
        "auth.teachers-admins unauthorized",
        "GET",
        "/auth/teachers-admins",
        None,
        None,
        {401},
    )

    reset_teacher_id = None
    status, body = _call(
        "auth.check-email reset-teacher",
        "POST",
        "/auth/check-email",
        {"email": reset_teacher_email},
        expected={200},
    )
    if isinstance(body, dict):
        reset_teacher_id = body.get("userId")

    if reset_teacher_id:
        _call(
            "auth.edituser",
            "POST",
            f"/auth/edituser/{reset_teacher_id}",
            {"name": "Reset Teacher Updated"},
            admin_token,
            expected={200},
        )
        _call(
            "auth.edituser missing",
            "POST",
            "/auth/edituser/999999",
            {"name": "Missing"},
            admin_token,
            expected={404},
        )
        _call(
            "auth.reset",
            "PUT",
            f"/auth/reset/{reset_teacher_id}",
            {},
            admin_token,
            expected={200},
        )
        _call(
            "auth.reset unauthorized",
            "PUT",
            f"/auth/reset/{reset_teacher_id}",
            {},
            None,
            expected={401},
        )
        _call(
            "auth.set-password",
            "POST",
            f"/auth/users/{reset_teacher_id}/set-password",
            "newpass",
            None,
            expected={200},
        )
        _call(
            "auth.set-password missing",
            "POST",
            f"/auth/users/{reset_teacher_id}/set-password",
            "",
            None,
            expected={400},
        )
        _call(
            "auth.set-password missing user",
            "POST",
            "/auth/users/999999/set-password",
            "pass",
            None,
            expected={404},
        )
        _call(
            "auth.delete-user",
            "DELETE",
            f"/auth/user/{reset_teacher_email}",
            None,
            admin_token,
            expected={200},
        )

    if not teacher_token:
        print("No teacher token available. Skipping teacher/student flows.")
        return

    assessment_payload = {
        "title": "OTEL Assessment",
        "gradingMode": "AUTO",
        "questions": [
            {
                "type": "SHORT_ANSWER",
                "prompt": "Describe your day",
                "maxPoints": 5,
                "data": {"trim": True, "caseSensitive": False},
            }
        ],
    }
    status, body = _call(
        "assessments.create",
        "POST",
        "/assessments/",
        assessment_payload,
        admin_token,
        expected={201},
    )
    assessment_id = body.get("id") if isinstance(body, dict) else None
    questions = body.get("questions") if isinstance(body, dict) else None
    question_id = questions[0]["id"] if isinstance(questions, list) and questions else None

    _call("assessments.list admin", "GET", "/assessments/", None, admin_token, {200})
    _call("assessments.list teacher", "GET", "/assessments/", None, teacher_token, {200})
    _call("assessments.list student forbidden", "GET", "/assessments/", None, None, {401})

    course_payload = {"name": "OTEL Course"}
    status, body = _call(
        "courses.create",
        "POST",
        "/courses/",
        course_payload,
        teacher_token,
        expected={200},
    )
    course_id = body.get("id") if isinstance(body, dict) else None

    _call("courses.list", "GET", "/courses/", None, teacher_token, {200})
    _call("courses.list unauthorized", "GET", "/courses/", None, None, {401})
    _call(
        "courses.create invalid",
        "POST",
        "/courses/",
        {},
        teacher_token,
        expected={400},
    )

    if course_id:
        _call(
            "courses.detail",
            "GET",
            f"/courses/{course_id}",
            None,
            teacher_token,
            expected={200},
        )
        _call(
            "courses.detail not-found",
            "GET",
            "/courses/999999",
            None,
            teacher_token,
            expected={404},
        )
        _call(
            "courses.update",
            "PUT",
            f"/courses/{course_id}",
            {"name": "OTEL Course Updated"},
            teacher_token,
            expected={200},
        )

    student_email = _unique_email("student")
    status, body = _call(
        "students.create",
        "POST",
        "/students/",
        {
            "name": "OTEL Student",
            "username": student_email,
            "courseId": course_id,
            "consent": True,
            "password": DEFAULT_STUDENT_PASSWORD,
        },
        teacher_token,
        expected={200},
    )
    student_id = body.get("id") if isinstance(body, dict) else None

    _call(
        "students.create forbidden",
        "POST",
        "/students/",
        {
            "name": "OTEL Student Forbidden",
            "username": _unique_email("student"),
            "courseId": course_id,
            "consent": True,
        },
        admin_token,
        expected={403},
    )
    _call(
        "students.create invalid",
        "POST",
        "/students/",
        {"name": "Missing Course", "username": _unique_email("student")},
        teacher_token,
        expected={400},
    )
    _call(
        "students.bulk invalid",
        "POST",
        "/students/bulk",
        {"not": "a list"},
        teacher_token,
        expected={400},
    )
    _call(
        "students.bulk",
        "POST",
        "/students/bulk",
        [
            {
                "name": "Bulk Student",
                "username": _unique_email("student"),
                "courseId": course_id,
                "password": DEFAULT_STUDENT_PASSWORD,
            }
        ],
        teacher_token,
        expected={200},
    )

    if student_id:
        _call(
            "auth.set-password student",
            "POST",
            f"/auth/users/{student_id}/set-password",
            DEFAULT_STUDENT_PASSWORD,
            None,
            expected={200},
        )

    status, body = _call(
        "auth.login student",
        "POST",
        "/auth/login",
        {"username": student_email, "password": DEFAULT_STUDENT_PASSWORD},
        expected={200},
    )
    student_token = body.get("accessToken") if isinstance(body, dict) else None

    open_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    assignment_payload = {
        "assessmentId": assessment_id,
        "audienceType": "COURSE",
        "courseId": course_id,
        "openAt": open_at,
    }
    status, body = _call(
        "assignments.create",
        "POST",
        "/assignments/",
        assignment_payload,
        teacher_token,
        expected={201},
    )
    assignment_id = body.get("id") if isinstance(body, dict) else None

    if assignment_id:
        _call(
            "assignments.detail",
            "GET",
            f"/assignments/{assignment_id}",
            None,
            teacher_token,
            expected={200},
        )
        _call(
            "assignments.detail not-found",
            "GET",
            "/assignments/999999",
            None,
            teacher_token,
            expected={404},
        )
        _call(
            "assignments.list course",
            "GET",
            f"/assignments/courses/{course_id}",
            None,
            teacher_token,
            expected={200},
        )
        if student_id:
            _call(
                "assignments.list user",
                "GET",
                f"/assignments/users/{student_id}",
                None,
                student_token,
                expected={200},
            )
            _call(
                "assignments.list user unauthorized",
                "GET",
                f"/assignments/users/{student_id}",
                None,
                None,
                expected={401},
            )

    if assessment_id:
        _call(
            "assessments.detail",
            "GET",
            f"/assessments/{assessment_id}",
            None,
            teacher_token,
            expected={200},
        )
        if student_token:
            _call(
                "assessments.detail student",
                "GET",
                f"/assessments/{assessment_id}",
                None,
                student_token,
                expected={200, 403},
            )
        _call(
            "assessments.detail missing",
            "GET",
            "/assessments/999999",
            None,
            admin_token,
            expected={404},
        )
        _call(
            "assessments.delete forbidden",
            "DELETE",
            f"/assessments/{assessment_id}",
            None,
            teacher_token,
            expected={403},
        )

    submission_id = None
    submission_assignment_id = None
    submission_student_id = None
    if assignment_id and student_id and student_token and question_id:
        _call(
            "students.draft",
            "PUT",
            f"/students/{student_id}/assignments/{assignment_id}/draft",
            {
                "answers": [
                    {
                        "questionId": question_id,
                        "type": "SHORT_ANSWER",
                        "data": {"text": "Draft"},
                    }
                ]
            },
            student_token,
            expected={200},
        )
        status, body = _call(
            "assignments.submit",
            "POST",
            f"/assignments/{assignment_id}/submissions",
            {
                "assignmentId": assignment_id,
                "studentId": student_id,
                "status": "SUBMITTED",
                "answers": [
                    {
                        "questionId": question_id,
                        "type": "SHORT_ANSWER",
                        "data": {"text": "Final"},
                    }
                ],
            },
            student_token,
            expected={201},
        )
        if isinstance(body, dict):
            submission_id = body.get("id")
            submission_assignment_id = body.get("assignmentId")
            submission_student_id = body.get("studentId")

        _call(
            "submissions.list by assignment",
            "GET",
            f"/assignments/{assignment_id}/submissions",
            None,
            teacher_token,
            expected={200},
        )
        _call(
            "submissions.list by student",
            "GET",
            f"/students/{student_id}/submissions",
            None,
            student_token,
            expected={200},
        )
        if teacher_id:
            _call(
                "submissions.list by teacher",
                "GET",
                f"/teachers/{teacher_id}/submissions",
                None,
                teacher_token,
                expected={200},
            )

        _call(
            "submissions.mine missing userId",
            "GET",
            "/submissions/mine",
            None,
            student_token,
            expected={400},
        )
        _call(
            "submissions.mine",
            "GET",
            f"/submissions/mine?userId={student_id}",
            None,
            student_token,
            expected={200},
        )

        _call(
            "submissions.student assignment",
            "GET",
            f"/students/{student_id}/assignments/{assignment_id}/submission",
            None,
            student_token,
            expected={200},
        )

    if assessment_id and question_id:
        self_assess_id = assessment_id
        self_question_id = question_id
        status, body = _call(
            "assessments.self-assess seed",
            "POST",
            "/assessments/",
            assessment_payload,
            admin_token,
            expected={201},
        )
        if isinstance(body, dict):
            self_assess_id = body.get("id") or self_assess_id
            questions = body.get("questions")
            if isinstance(questions, list) and questions:
                self_question_id = questions[0].get("id") or self_question_id
        _call(
            "assessments.teacher self assess",
            "POST",
            f"/assessments/{self_assess_id}/teacher-self-assess",
            [
                {
                    "questionId": self_question_id,
                    "type": "SHORT_ANSWER",
                    "data": {"text": "Teacher answer"},
                }
            ],
            teacher_token,
            expected={201},
        )
        _call(
            "assessments.teacher self assess invalid",
            "POST",
            f"/assessments/{assessment_id}/teacher-self-assess",
            {"not": "a list"},
            teacher_token,
            expected={400},
        )

    if submission_id:
        _call(
            "submissions.get",
            "GET",
            f"/submissions/{submission_id}",
            None,
            teacher_token,
            expected={200},
        )
        edit_assignment_id = submission_assignment_id or assignment_id
        edit_student_id = submission_student_id or student_id
        _call(
            "submissions.edit",
            "PUT",
            "/submissions/",
            {
                "id": submission_id,
                "assignmentId": edit_assignment_id,
                "studentId": edit_student_id,
                "status": "GRADED",
                "answers": [
                    {
                        "questionId": question_id,
                        "type": "SHORT_ANSWER",
                        "data": {"text": "Edited"},
                    }
                ],
            },
            admin_token,
            expected={200},
        )
        _call(
            "submissions.override",
            "PATCH",
            f"/submissions/{submission_id}/override-score",
            [5],
            teacher_token,
            expected={200},
        )
        _call(
            "submissions.override invalid",
            "PATCH",
            f"/submissions/{submission_id}/override-score",
            {"bad": "payload"},
            teacher_token,
            expected={400},
        )
        _call(
            "assessments.update",
            "PUT",
            f"/assessments/{assessment_id}",
            assessment_payload,
            admin_token,
            expected={200},
        )

    _call(
        "visualization.data",
        "POST",
        "/visualization/",
        {"courseId": course_id} if course_id else {},
        teacher_token,
        expected={200},
    )
    _call(
        "visualization.forbidden",
        "POST",
        "/visualization/",
        {},
        student_token,
        expected={403},
    )
    _call(
        "export.stub",
        "POST",
        "/export/",
        {},
        teacher_token,
        expected={501},
    )

    if course_id and student_id:
        _call(
            "courses.students",
            "GET",
            f"/courses/{course_id}/students",
            None,
            teacher_token,
            expected={200},
        )
        _call(
            "courses.remove student",
            "DELETE",
            f"/courses/{course_id}/students/{student_id}",
            None,
            teacher_token,
            expected={200},
        )

    if assignment_id:
        _call(
            "assignments.delete",
            "DELETE",
            f"/assignments/{assignment_id}",
            None,
            teacher_token,
            expected={200},
        )
    if assessment_id:
        _call(
            "assessments.delete",
            "DELETE",
            f"/assessments/{assessment_id}",
            None,
            admin_token,
            expected={200},
        )
    if course_id:
        _call(
            "courses.delete",
            "DELETE",
            f"/courses/{course_id}",
            None,
            teacher_token,
            expected={204},
        )


if __name__ == "__main__":
    main()
