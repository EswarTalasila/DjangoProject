// E2E test: teacher grading.
import { test, expect } from '@playwright/test';
import {
  apiCreateAssignment,
  apiCreateCourse,
  apiCreateManualAssessmentWithRubric,
  apiCreateRubricAssessment,
  apiCreateStudent,
  apiCreateTeacher,
  apiSubmitAssignment,
  uniqueEmail,
} from '../helpers/api';
import { env } from '../helpers/env';
import { createAuthenticatedContext, loginViaApi } from '../helpers/ui';

// Test: teacher can grade a submission with a rubric.
test('teacher can grade a submission with a rubric', async ({ browser, request }) => {
  test.setTimeout(120_000);

  const adminSession = await loginViaApi(
    request,
    env.adminUsername,
    env.adminPassword
  );

  const teacherEmail = uniqueEmail('teacher');
  await apiCreateTeacher(
    request,
    adminSession.token,
    teacherEmail,
    env.defaultTeacherPassword
  );
  const teacherSession = await loginViaApi(
    request,
    teacherEmail,
    env.defaultTeacherPassword
  );

  const course = await apiCreateCourse(
    request,
    teacherSession.token,
    `E2E Course ${Date.now()}`
  );

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

  const rubric = await apiCreateRubricAssessment(
    request,
    adminSession.token,
    `E2E Rubric ${Date.now()}`
  );

  const assessmentTitle = `E2E Manual Assessment ${Date.now()}`;
  const assessment = await apiCreateManualAssessmentWithRubric(
    request,
    adminSession.token,
    assessmentTitle,
    rubric.id
  );

  const assignment = await apiCreateAssignment(
    request,
    teacherSession.token,
    assessment.id,
    course.id
  );

  const studentSession = await loginViaApi(
    request,
    studentEmail,
    env.defaultStudentPassword
  );

  await apiSubmitAssignment(
    request,
    studentSession.token,
    assignment.id,
    studentSession.userId,
    assessment.questionId
  );

  const context = await createAuthenticatedContext(browser, teacherSession);
  const page = await context.newPage();

  await page.goto(
    `/teacher/${teacherSession.userId}/${course.id}/${assignment.id}/gradelist`
  );
  await expect(page.getByRole('heading', { name: 'Submissions' })).toBeVisible();

  const submissionRow = page.locator('tbody tr', { hasText: studentName });
  await expect(submissionRow).toBeVisible();
  await submissionRow.getByRole('button', { name: 'Grade' }).click();

  await expect(page.getByRole('heading', { name: assessmentTitle })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Grading Rubric' })).toBeVisible();

  const rubricButton = page.getByRole('button', { name: /Rubric Item 1/i });
  await rubricButton.click();
  await page.locator('input.score-input').first().fill('4');

  await page.getByRole('button', { name: 'Submit Grading' }).click();
  await page.waitForURL('**/gradelist');

  const gradedRow = page.locator('tbody tr', { hasText: studentName });
  await expect(gradedRow.getByText('Graded')).toBeVisible();

  await context.close();
});
