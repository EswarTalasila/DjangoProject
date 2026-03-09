import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockLogout = vi.fn();
const mockChangePassword = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/logout", () => ({ logout: mockLogout }));
  vi.doMock("@/lib/password-reset-api", () => ({
    changePassword: mockChangePassword,
  }));
}

async function loadChangePasswordForm() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/settings/changePasswordForm");
  return imported.ChangePasswordForm;
}

describe("Settings page — ChangePasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders account info from props", async () => {
    const ChangePasswordForm = await loadChangePasswordForm();
    render(
      <ChangePasswordForm
        profile={{ id: "1", name: "Morgan Blake", username: "mblake", email: "m@example.com", role: "TEACHER", isStaff: false }}
      />
    );

    expect(screen.getByText("Morgan Blake")).toBeInTheDocument();
    expect(screen.getByText("mblake")).toBeInTheDocument();
    expect(screen.getByText("m@example.com")).toBeInTheDocument();
    expect(screen.getByText("TEACHER")).toBeInTheDocument();
  });

  it("shows 'Not set' when email is null", async () => {
    const ChangePasswordForm = await loadChangePasswordForm();
    render(
      <ChangePasswordForm
        profile={{ id: "1", name: "Morgan Blake", username: "mblake", email: null, role: "STUDENT", isStaff: false }}
      />
    );

    expect(screen.getByText("Not set")).toBeInTheDocument();
  });

  it("submits change password and calls logout on success", async () => {
    mockChangePassword.mockResolvedValueOnce({ message: "Password changed." });

    const ChangePasswordForm = await loadChangePasswordForm();
    render(
      <ChangePasswordForm
        profile={{ id: "1", name: "Morgan Blake", username: "mblake", email: null, role: "TEACHER", isStaff: false }}
      />
    );

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Current password"), "old-pass");
    await user.type(screen.getByLabelText("New password"), "NewPass123!");
    await user.type(screen.getByLabelText("Confirm new password"), "NewPass123!");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    await waitFor(() => {
      expect(mockChangePassword).toHaveBeenCalledWith({
        currentPassword: "old-pass",
        newPassword: "NewPass123!",
        confirmPassword: "NewPass123!",
      });
    });

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledOnce();
    });
  });

  it("shows API error detail on failure", async () => {
    mockChangePassword.mockRejectedValueOnce({
      response: { data: { detail: "Current password is incorrect." } },
    });

    const ChangePasswordForm = await loadChangePasswordForm();
    render(
      <ChangePasswordForm
        profile={{ id: "1", name: "Morgan Blake", username: "mblake", email: null, role: "TEACHER", isStaff: false }}
      />
    );

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Current password"), "wrong");
    await user.type(screen.getByLabelText("New password"), "NewPass123!");
    await user.type(screen.getByLabelText("Confirm new password"), "NewPass123!");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByText("Current password is incorrect.")).toBeInTheDocument();
    expect(mockLogout).not.toHaveBeenCalled();
  });

  it("validates passwords match client-side", async () => {
    const ChangePasswordForm = await loadChangePasswordForm();
    render(
      <ChangePasswordForm
        profile={{ id: "1", name: "Morgan Blake", username: "mblake", email: null, role: "TEACHER", isStaff: false }}
      />
    );

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Current password"), "old-pass");
    await user.type(screen.getByLabelText("New password"), "NewPass123!");
    await user.type(screen.getByLabelText("Confirm new password"), "DifferentPass!");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByText("Passwords do not match")).toBeInTheDocument();
    expect(mockChangePassword).not.toHaveBeenCalled();
  });
});
