import { beforeEach, describe, expect, it, vi } from "vitest";

const mockApiPost = vi.fn();
const mockApiPatch = vi.fn();

function setupMocks() {
  vi.doMock("@/lib/api", () => ({
    default: { post: mockApiPost, patch: mockApiPatch, get: vi.fn() },
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

  describe("validateResetCode", () => {
    it("posts identifier and resetCode to /auth/reset-code-validations", async () => {
      mockApiPost.mockResolvedValueOnce({
        data: { valid: true, requestId: 42, expiresAt: "2026-03-01T00:00:00Z" },
      });

      const { validateResetCode } = await loadModule();
      const result = await validateResetCode("mblake", "RESET-ABC123");

      expect(mockApiPost).toHaveBeenCalledWith("/auth/reset-code-validations", {
        identifier: "mblake",
        resetCode: "RESET-ABC123",
      });
      expect(result).toEqual({ valid: true, requestId: 42, expiresAt: "2026-03-01T00:00:00Z" });
    });
  });

  describe("changePassword", () => {
    it("patches /auth/password with current and new password", async () => {
      mockApiPatch.mockResolvedValueOnce({
        data: { message: "Password changed." },
      });

      const { changePassword } = await loadModule();
      const result = await changePassword({
        currentPassword: "old-pass",
        newPassword: "new-pass-123!",
        confirmPassword: "new-pass-123!",
      });

      expect(mockApiPatch).toHaveBeenCalledWith("/auth/password", {
        currentPassword: "old-pass",
        newPassword: "new-pass-123!",
        confirmPassword: "new-pass-123!",
      });
      expect(result).toEqual({ message: "Password changed." });
    });
  });
});
