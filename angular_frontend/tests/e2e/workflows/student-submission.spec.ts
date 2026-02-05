// E2E test: student submission.
import { test, expect } from '@playwright/test';
import {
  apiCreateAssessment,
  apiCreateAssignment,
  apiCreateCourse,
  apiCreateStudent,
  apiCreateTeacher,
  uniqueEmail,
} from '../helpers/api';
import { env } from '../helpers/env';
import {
  acknowledgeDialog,
  confirmDialog,
  createAuthenticatedContext,
  loginViaApi,
} from '../helpers/ui';

// Test: student can save a draft and submit an assignment.
test('student can save a draft and submit an assignment', async ({ browser, request }) => {
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

  const assessmentTitle = `E2E Draft Flow ${Date.now()}`;
  const assessment = await apiCreateAssessment(
    request,
    adminSession.token,
    assessmentTitle
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

  const context = await createAuthenticatedContext(browser, studentSession);
  const page = await context.newPage();

  const assignmentsResponse = page.waitForResponse((response) => {
    return (
      response.url().includes(`/assignments/users/${studentSession.userId}`) &&
      response.status() === 200
    );
  });
  await page.goto(`/${studentSession.userId}/assignments`);
  await assignmentsResponse;
  await expect(page.getByRole('heading', { name: 'Assignments', level: 1 })).toBeVisible();

  const card = page.locator('.assessment-card');
  await expect(card).toHaveCount(1);
  await expect(card.getByRole('heading', { level: 3 })).toHaveText(assessmentTitle);
  await card.getByRole('button', { name: 'Start Assessment' }).click();

  await expect(page.getByRole('heading', { name: assessmentTitle })).toBeVisible();
  await page.locator('textarea.short-answer-input').fill('Draft answer');

  await page.getByRole('button', { name: 'Save Draft' }).click();
  await acknowledgeDialog(page, 'Success');

  await page.waitForURL(`**/${studentSession.userId}/assignments`);
  await page.waitForResponse((response) => {
    return response.url().includes(`/students/${studentSession.userId}/submissions`) &&
      response.status() === 200;
  });
  const draftCard = page.locator('.assessment-card', { hasText: assessmentTitle });
  await expect(draftCard.locator('.status-badge')).toHaveText('In Progress');
  await draftCard.getByRole('button', { name: 'Continue' }).click();

  await expect(page.getByRole('heading', { name: assessmentTitle })).toBeVisible();
  await page.getByRole('button', { name: 'Submit Assessment' }).click();
  await confirmDialog(page, 'Confirm Submission');
  await acknowledgeDialog(page, 'Success');

  await page.waitForURL(`**/${studentSession.userId}/assignments`);
  await page.waitForResponse((response) => {
    return response.url().includes(`/students/${studentSession.userId}/submissions`) &&
      response.status() === 200;
  });
  const submittedCard = page.locator('.assessment-card', { hasText: assessmentTitle });
  await expect(submittedCard.locator('.status-badge')).toHaveText(/Submitted|Graded/);
  await expect(
    submittedCard.getByRole('button', { name: 'View Submission' })
  ).toBeVisible();

  await context.close();
});
