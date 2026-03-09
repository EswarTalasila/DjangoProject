import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();

function setupMocks() {
  vi.doMock("@/lib/api", () => ({
    default: { get: mockGet, post: mockPost, patch: mockPatch },
  }));
}

async function loadModule() {
  vi.resetModules();
  setupMocks();
  return await import("@/lib/password-reset-api");
}

describe("password-reset-api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("issuePasswordResetCode", () => {
    it("posts targetUserId to /auth/password-reset-codes", async () => {
      const resp = { requestId: 1, targetUserId: 42, targetRole: "STUDENT", resetCode: "RESET-XYZ", expiresAt: "2026-04-01T00:00:00Z" };
      mockPost.mockResolvedValueOnce({ data: resp });
      const { issuePasswordResetCode } = await loadModule();
      const result = await issuePasswordResetCode(42);
      expect(mockPost).toHaveBeenCalledWith("/auth/password-reset-codes", { targetUserId: 42 });
      expect(result).toEqual(resp);
    });
  });

  describe("completePasswordReset", () => {
    it("posts reset payload to /auth/password-resets", async () => {
      mockPost.mockResolvedValueOnce({ data: { message: "Password reset complete." } });
      const { completePasswordReset } = await loadModule();
      const payload = {
        identifier: "jdoe",
        resetCode: "RESET-ABC",
        newPassword: "new-pass-1!",
        confirmPassword: "new-pass-1!",
      };
      const result = await completePasswordReset(payload);
      expect(mockPost).toHaveBeenCalledWith("/auth/password-resets", payload);
      expect(result).toEqual({ message: "Password reset complete." });
    });
  });

  describe("listStaffUsers", () => {
    it("returns results from paginated response", async () => {
      mockGet.mockResolvedValueOnce({
        data: { count: 1, next: null, previous: null, results: [{ id: 1, name: "Admin", username: "admin", email: null, role: "RESEARCHER" }] },
      });
      const { listStaffUsers } = await loadModule();
      const result = await listStaffUsers();
      expect(mockGet).toHaveBeenCalledWith("/users/staff");
      expect(result).toHaveLength(1);
      expect(result[0].role).toBe("RESEARCHER");
    });

    it("returns raw array response", async () => {
      mockGet.mockResolvedValueOnce({
        data: [{ id: 2, name: "Teacher1", username: "t1", email: null, role: "TEACHER" }],
      });
      const { listStaffUsers } = await loadModule();
      const result = await listStaffUsers();
      expect(result).toEqual([{ id: 2, name: "Teacher1", username: "t1", email: null, role: "TEACHER" }]);
    });
  });

  describe("listStudents", () => {
    it("returns students without query params", async () => {
      mockGet.mockResolvedValueOnce({
        data: [{ id: 10, name: "Student A", username: "sa", courses: [] }],
      });
      const { listStudents } = await loadModule();
      const result = await listStudents();
      expect(mockGet).toHaveBeenCalledWith("/users/students");
      expect(result).toHaveLength(1);
    });

    it("adds q and courseId query params", async () => {
      mockGet.mockResolvedValueOnce({
        data: { count: 1, results: [{ id: 11, name: "Student B", username: "sb", courses: [{ id: 5, name: "Math" }] }] },
      });
      const { listStudents } = await loadModule();
      const result = await listStudents({ q: "student", courseId: 5 });
      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining("/users/students?"));
      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining("q=student"));
      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining("courseId=5"));
      expect(result).toHaveLength(1);
    });

    it("handles paginated response for students", async () => {
      mockGet.mockResolvedValueOnce({
        data: { count: 0, results: [] },
      });
      const { listStudents } = await loadModule();
      const result = await listStudents({ q: "none" });
      expect(result).toEqual([]);
    });
  });

  describe("getMySudoGrant", () => {
    it("fetches sudo grant status from /sudo-grants/me", async () => {
      const resp = { hasSudo: true, canGrantSudo: false, permissions: ["RESET_PASSWORDS"], isStaff: true };
      mockGet.mockResolvedValueOnce({ data: resp });
      const { getMySudoGrant } = await loadModule();
      const result = await getMySudoGrant();
      expect(mockGet).toHaveBeenCalledWith("/sudo-grants/me");
      expect(result).toEqual(resp);
    });
  });

  describe("validateResetCode", () => {
    it("posts identifier and resetCode to /auth/reset-code-validations", async () => {
      mockPost.mockResolvedValueOnce({
        data: { valid: true, requestId: 42, expiresAt: "2026-03-01T00:00:00Z" },
      });
      const { validateResetCode } = await loadModule();
      const result = await validateResetCode("mblake", "RESET-ABC123");
      expect(mockPost).toHaveBeenCalledWith("/auth/reset-code-validations", {
        identifier: "mblake",
        resetCode: "RESET-ABC123",
      });
      expect(result).toEqual({ valid: true, requestId: 42, expiresAt: "2026-03-01T00:00:00Z" });
    });
  });

  describe("changePassword", () => {
    it("patches /auth/password with current and new password", async () => {
      mockPatch.mockResolvedValueOnce({
        data: { message: "Password changed." },
      });
      const { changePassword } = await loadModule();
      const result = await changePassword({
        currentPassword: "old-pass",
        newPassword: "new-pass-123!",
        confirmPassword: "new-pass-123!",
      });
      expect(mockPatch).toHaveBeenCalledWith("/auth/password", {
        currentPassword: "old-pass",
        newPassword: "new-pass-123!",
        confirmPassword: "new-pass-123!",
      });
      expect(result).toEqual({ message: "Password changed." });
    });
  });
});
