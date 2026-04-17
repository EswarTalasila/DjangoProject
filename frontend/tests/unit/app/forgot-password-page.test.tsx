import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockValidateResetCode = vi.fn();
const mockCompletePasswordReset = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/password-reset-api", () => ({
    validateResetCode: mockValidateResetCode,
    completePasswordReset: mockCompletePasswordReset,
  }));
}

async function loadForgotPasswordPage() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/app/(auth)/forgot-password/page");
  return imported.default;
}

describe("Forgot password page — two-step flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders step 1 with identifier and reset code fields only", async () => {
    const ForgotPasswordPage = await loadForgotPasswordPage();
    render(<ForgotPasswordPage />);

    expect(screen.getByLabelText("Identifier")).toBeInTheDocument();
    expect(screen.getByLabelText("Reset code")).toBeInTheDocument();
    expect(screen.queryByLabelText("New password")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Confirm password")).not.toBeInTheDocument();
  });

  it("validates reset code in step 1 and transitions to step 2", async () => {
    mockValidateResetCode.mockResolvedValueOnce({
      valid: true,
      requestId: 42,
      expiresAt: "2026-03-01T00:00:00Z",
    });

    const ForgotPasswordPage = await loadForgotPasswordPage();
    render(<ForgotPasswordPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "mblake");
    await user.type(screen.getByLabelText("Reset code"), "RESET-ABC123");
    await user.click(screen.getByRole("button", { name: "Verify code" }));

    await waitFor(() => {
      expect(mockValidateResetCode).toHaveBeenCalledWith("mblake", "RESET-ABC123");
    });

    // Step 2 should now show password fields
    expect(await screen.findByLabelText("New password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm password")).toBeInTheDocument();
  });

  it("shows error when reset code is invalid", async () => {
    mockValidateResetCode.mockRejectedValueOnce({
      response: { data: { detail: "Invalid or expired reset code." } },
    });

    const ForgotPasswordPage = await loadForgotPasswordPage();
    render(<ForgotPasswordPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "mblake");
    await user.type(screen.getByLabelText("Reset code"), "BAD-CODE");
    await user.click(screen.getByRole("button", { name: "Verify code" }));

    expect(await screen.findByText("Invalid or expired reset code.")).toBeInTheDocument();
    // Should stay on step 1
    expect(screen.queryByLabelText("New password")).not.toBeInTheDocument();
  });

  it("completes password reset in step 2", async () => {
    mockValidateResetCode.mockResolvedValueOnce({
      valid: true,
      requestId: 42,
      expiresAt: "2026-03-01T00:00:00Z",
    });
    mockCompletePasswordReset.mockResolvedValueOnce({
      message: "Password reset.",
    });

    const ForgotPasswordPage = await loadForgotPasswordPage();
    render(<ForgotPasswordPage />);

    const user = userEvent.setup();

    // Step 1
    await user.type(screen.getByLabelText("Identifier"), "mblake");
    await user.type(screen.getByLabelText("Reset code"), "RESET-ABC123");
    await user.click(screen.getByRole("button", { name: "Verify code" }));

    // Step 2
    await user.type(await screen.findByLabelText("New password"), "NewPass123!");
    await user.type(screen.getByLabelText("Confirm password"), "NewPass123!");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(mockCompletePasswordReset).toHaveBeenCalledWith({
        identifier: "mblake",
        resetCode: "RESET-ABC123",
        newPassword: "NewPass123!",
        confirmPassword: "NewPass123!",
      });
    });

    // Success state
    expect(await screen.findByText("Password updated")).toBeInTheDocument();
  });
});
