// Playwright helper utilities.
export type EnvConfig = {
  baseURL: string;
  apiURL: string;
  adminUsername: string;
  adminPassword: string;
  adminName: string;
  defaultTeacherPassword: string;
  defaultStudentPassword: string;
};

const baseURL = process.env.E2E_BASE_URL || 'http://localhost:4200';
const apiURL = process.env.E2E_API_URL || 'http://localhost:8000/api/v1';

const adminUsername = process.env.E2E_ADMIN_USERNAME || 'admin@example.com';
const adminPassword = process.env.E2E_ADMIN_PASSWORD || 'change-me';
const adminName = process.env.E2E_ADMIN_NAME || 'Admin';

const defaultTeacherPassword = process.env.E2E_TEACHER_PASSWORD || 'teacherpass';
const defaultStudentPassword = process.env.E2E_STUDENT_PASSWORD || 'studentpass';

export const env: EnvConfig = {
  baseURL,
  apiURL,
  adminUsername,
  adminPassword,
  adminName,
  defaultTeacherPassword,
  defaultStudentPassword,
};

export function requireEnv(value: string, message: string): string {
  if (!value) {
    throw new Error(message);
  }
  return value;
}
