import type { APIRequestContext } from "@playwright/test";
import { expect, test } from "@playwright/test";

const rawApiBaseUrl = process.env.E2E_API_URL || "http://backend:8000/api/v1";
const API_BASE_URL = rawApiBaseUrl
  .replace("localhost:8000", "backend:8000")
  .replace("127.0.0.1:8000", "backend:8000");
const teacherIdentifier = process.env.E2E_TEACHER_USERNAME || "e2e-teacher";
const teacherPassword = process.env.E2E_TEACHER_PASSWORD || "teacherpass";

async function waitForBackendReady(context: APIRequestContext) {
  let lastError: unknown;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      const response = await context.post(`${API_BASE_URL}/auth/sessions`, {
        data: {
          identifier: teacherIdentifier,
          password: teacherPassword,
        },
      });
      if (response.ok()) {
        return response;
      }
      lastError = new Error(`backend returned status ${response.status()}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw lastError;
}

async function createStudentRegistrationCode(context: APIRequestContext) {
  const login = await waitForBackendReady(context);
  expect(login.ok()).toBeTruthy();
  const loginBody = await login.json();
  const accessToken = loginBody.accessToken as string;
  expect(accessToken).toBeTruthy();

  const createCourse = await context.post(`${API_BASE_URL}/courses/`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      name: `E2E Course ${Date.now()}`,
    },
  });
  expect(createCourse.ok()).toBeTruthy();
  const courseBody = await createCourse.json();
  const courseId = courseBody?.id as number | undefined;
  expect(courseId).toBeTruthy();

  const expiresAt = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString();
  const createCode = await context.post(`${API_BASE_URL}/codes`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      codeType: "STUDENT",
      count: 1,
      usesPerCode: 1,
      expiresAt,
      courseId,
    },
  });
  expect(createCode.ok()).toBeTruthy();
  const codeBody = await createCode.json();
  const code = codeBody?.codes?.[0]?.code as string | undefined;
  expect(code).toBeTruthy();
  return code as string;
}

test.describe("Registration flow", () => {
  test("creates a new student account from a generated registration code", async ({ request }) => {
    const inviteCode = await createStudentRegistrationCode(request);
    const password = "Validpass1!";
    const suffix = Date.now().toString().slice(-5);

    const validate = await request.post(`${API_BASE_URL}/registration/code-validations`, {
      data: { code: inviteCode },
    });
    expect(validate.ok()).toBeTruthy();
    const validateBody = await validate.json();
    expect(validateBody.code_type).toBe("STUDENT");

    const register = await request.post(`${API_BASE_URL}/registration/accounts`, {
      data: {
        method: "LOCAL",
        code: inviteCode,
        firstName: "Alex",
        lastName: `Torres${suffix}`,
        password,
        confirmPassword: password,
      },
    });
    expect(register.status()).toBe(201);
    const registerBody = await register.json();
    expect(registerBody.username).toBeTruthy();
    expect(registerBody.role).toBe("STUDENT");

    const login = await request.post(`${API_BASE_URL}/auth/sessions`, {
      data: {
        identifier: registerBody.username,
        password,
      },
    });
    expect(login.ok()).toBeTruthy();
    const loginBody = await login.json();
    expect(loginBody.role).toBe("STUDENT");
    expect(loginBody.accessToken).toBeTruthy();
  });
});
