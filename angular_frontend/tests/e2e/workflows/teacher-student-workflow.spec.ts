// E2E test: teacher student workflow.
import { test, expect } from '@playwright/test';
import {
  apiCreateAssessment,
  apiCreateAssignment,
  apiCreateCourse,
  apiCreateStudent,
  apiCreateTeacher,
  apiSubmitAssignment,
  uniqueEmail,
} from '../helpers/api';
import { env } from '../helpers/env';
import { createAuthenticatedContext, loginViaApi } from '../helpers/ui';

// Test: teacher and student can see assignment data concurrently.
test('teacher and student can see assignment data concurrently', async ({ browser, request }) => {
  test.setTimeout(120_000);

  const adminSession = await loginViaApi(
    request,
    env.adminUsername,
    env.adminPassword
  );

  const teacherEmail = uniqueEmail('teacher');
  await apiCreateTeacher(request, adminSession.token, teacherEmail, env.defaultTeacherPassword);
  const teacherSession = await loginViaApi(request, teacherEmail, env.defaultTeacherPassword);

  const course = await apiCreateCourse(request, teacherSession.token, `E2E Course ${Date.now()}`);

  const studentEmail = uniqueEmail('student');
  const studentName = `Student ${Date.now()}`;
  await apiCreateStudent(
    request,
    teacherSession.token,
    studentName,
    studentEmail,
    env.defaultStudentPassword,
    course.id
  );

  const assessmentTitle = `E2E Assignment ${Date.now()}`;
  const assessment = await apiCreateAssessment(request, adminSession.token, assessmentTitle);
  const assignment = await apiCreateAssignment(
    request,
    teacherSession.token,
    assessment.id,
    course.id
  );

  const studentSession = await loginViaApi(request, studentEmail, env.defaultStudentPassword);
  await apiSubmitAssignment(
    request,
    studentSession.token,
    assignment.id,
    studentSession.userId,
    assessment.questionId
  );

  const teacherContext = await createAuthenticatedContext(browser, teacherSession);
  const studentContext = await createAuthenticatedContext(browser, studentSession);

  const teacherPage = await teacherContext.newPage();
  const studentPage = await studentContext.newPage();

  await Promise.all([
    teacherPage.waitForResponse((response) => {
      return response.url().includes(`/assignments/${assignment.id}/submissions`) && response.status() === 200;
    }),
    teacherPage.goto(`/teacher/${teacherSession.userId}/${course.id}/${assignment.id}/gradelist`),
    studentPage.waitForResponse((response) => {
      return response.url().includes(`/assignments/users/${studentSession.userId}`) && response.status() === 200;
    }),
    studentPage.goto(`/${studentSession.userId}/assignments`),
  ]);

  await expect(teacherPage.getByRole('heading', { name: 'Submissions' })).toBeVisible();
  await expect(teacherPage.locator('tbody tr')).toHaveCount(1);
  await expect(teacherPage.getByText(studentName)).toBeVisible();

  await expect(studentPage.getByRole('heading', { name: 'Assignments' })).toBeVisible();
  const assignmentCards = studentPage.locator('.assessment-card');
  await expect(assignmentCards).toHaveCount(1);
  await expect(
    assignmentCards
      .first()
      .getByRole('button', { name: /Start Assessment|Continue|View Submission/ })
  ).toBeVisible();

  await teacherContext.close();
  await studentContext.close();
});
