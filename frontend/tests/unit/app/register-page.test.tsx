import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockApiPost = vi.fn();
const mockGoogleLoginTrigger = vi.fn();
const mockCookiesSet = vi.fn();
const mockToastSuccess = vi.fn();

// Captures the onSuccess callback from useGoogleLogin so tests can simulate Google auth
let capturedGoogleOnSuccess: ((resp: { access_token: string }) => void) | null = null;

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
  }));
  vi.doMock("@react-oauth/google", () => ({
    GoogleOAuthProvider: ({ children }: { children: ReactNode }) => children,
    useGoogleLogin: (opts: { onSuccess: (resp: { access_token: string }) => void }) => {
      capturedGoogleOnSuccess = opts.onSuccess;
      return mockGoogleLoginTrigger;
    },
  }));
  vi.doMock("js-cookie", () => ({
    default: { set: mockCookiesSet, remove: vi.fn(), get: vi.fn() },
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess },
  }));
  vi.doMock("@/lib/api", () => ({
    default: { post: mockApiPost },
  }));
}

async function loadRegisterPage() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/app/(auth)/register/page");
  return imported.default;
}

describe("Register page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-google-client";
  });

  it("submits student local registration using first/last name fields only", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { valid: true, code_type: "STUDENT", context: { course_name: "Biology" } },
    });
    mockApiPost.mockResolvedValueOnce({
      data: {
        message: "User registered",
        username: "atorres0",
        name: "Alex Torres",
        email: null,
        accessToken: "access-token",
        refreshToken: "refresh-token",
        tokenType: "Bearer",
        role: "STUDENT",
        id: "10",
        courseId: 5,
        createdNewUser: true,
        alreadyEnrolled: false,
      },
    });

    const RegisterPage = await loadRegisterPage();
    render(<RegisterPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Registration Code"), "STU-CODE");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByText("Student Registration");

    await user.type(screen.getByLabelText("First Name"), "Alex");
    await user.type(screen.getByLabelText("Last Name"), "Torres");
    await user.type(screen.getByLabelText("Password"), "change-me-123");
    await user.type(screen.getByLabelText("Confirm Password"), "change-me-123");
    await user.click(screen.getByRole("button", { name: "Complete Registration" }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenNthCalledWith(
        2,
        "/registration/accounts",
        expect.objectContaining({
          method: "LOCAL",
          code: "STU-CODE",
          firstName: "Alex",
          lastName: "Torres",
          password: "change-me-123",
          confirmPassword: "change-me-123",
        }),
      );
    });

    const secondPayload = mockApiPost.mock.calls[1][1];
    expect(secondPayload).not.toHaveProperty("name");
    expect(secondPayload).not.toHaveProperty("username");
    expect(screen.getByText("Your Username")).toBeInTheDocument();
    expect(screen.getByText("atorres0")).toBeInTheDocument();
  });

  it("submits teacher local registration and stores display-name cookie", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { valid: true, code_type: "TEACHER", context: {} },
    });
    mockApiPost.mockResolvedValueOnce({
      data: {
        message: "User registered",
        username: "mblake0",
        name: "Morgan Blake",
        email: "mblake@example.com",
        accessToken: "access-token",
        refreshToken: "refresh-token",
        tokenType: "Bearer",
        role: "TEACHER",
        id: "11",
        courseId: null,
        createdNewUser: true,
        alreadyEnrolled: false,
      },
    });

    const RegisterPage = await loadRegisterPage();
    render(<RegisterPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Registration Code"), "TEACH-CODE");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByText("Teacher Registration");

    await user.type(screen.getByLabelText("First Name"), "Morgan");
    await user.type(screen.getByLabelText("Last Name"), "Blake");
    await user.type(screen.getByLabelText("Email"), "mblake@example.com");
    await user.type(screen.getByLabelText("Password"), "change-me-123");
    await user.type(screen.getByLabelText("Confirm Password"), "change-me-123");
    await user.click(screen.getByRole("button", { name: "Complete Registration" }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenNthCalledWith(
        2,
        "/registration/accounts",
        expect.objectContaining({
          method: "LOCAL",
          code: "TEACH-CODE",
          firstName: "Morgan",
          lastName: "Blake",
          email: "mblake@example.com",
          password: "change-me-123",
          confirmPassword: "change-me-123",
        }),
      );
    });

    const secondPayload = mockApiPost.mock.calls[1][1];
    expect(secondPayload).not.toHaveProperty("name");
    expect(secondPayload).not.toHaveProperty("username");
    expect(mockCookiesSet).toHaveBeenCalledWith("user_name", "Morgan Blake", { expires: 1 });
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("requires oauth first/last name after google auth before completing registration", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { valid: true, code_type: "TEACHER", context: {} },
    });
    mockApiPost.mockResolvedValueOnce({
      data: {
        message: "User registered",
        username: "mblake0",
        name: "Morgan Blake",
        email: "mblake@gmail.com",
        accessToken: "access-token",
        refreshToken: "refresh-token",
        tokenType: "Bearer",
        role: "TEACHER",
        id: "11",
        courseId: null,
        createdNewUser: true,
        alreadyEnrolled: false,
      },
    });

    const RegisterPage = await loadRegisterPage();
    render(<RegisterPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Registration Code"), "TEACH-CODE");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await screen.findByText("Teacher Registration");

    // Switch to Google tab and click Continue with Google
    await user.click(screen.getByRole("button", { name: "Google" }));
    await user.click(screen.getByRole("button", { name: "Continue with Google" }));
    expect(mockGoogleLoginTrigger).toHaveBeenCalledTimes(1);

    // Simulate Google auth success — triggers the name form
    await waitFor(() => expect(capturedGoogleOnSuccess).not.toBeNull());
    capturedGoogleOnSuccess!({ access_token: "google-token-123" });

    // Name form should appear — submit empty to trigger validation
    const completeBtn = await screen.findByRole("button", { name: "Complete Registration" });
    await user.click(completeBtn);

    expect(await screen.findByText("First name is required")).toBeInTheDocument();
    expect(await screen.findByText("Last name is required")).toBeInTheDocument();
    expect(mockApiPost).toHaveBeenCalledTimes(1); // only code validation, no registration call

    // Fill names and submit
    await user.type(screen.getByLabelText("First Name"), "Morgan");
    await user.type(screen.getByLabelText("Last Name"), "Blake");
    await user.click(completeBtn);

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenNthCalledWith(
        2,
        "/registration/accounts",
        expect.objectContaining({
          method: "OAUTH",
          code: "TEACH-CODE",
          accessToken: "google-token-123",
          firstName: "Morgan",
          lastName: "Blake",
        }),
      );
    });
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("shows backend error when registration code validation fails", async () => {
    mockApiPost.mockRejectedValueOnce({
      response: { data: { detail: "Invalid registration code." } },
    });

    const RegisterPage = await loadRegisterPage();
    render(<RegisterPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Registration Code"), "BAD-CODE");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByText("Invalid registration code.")).toBeInTheDocument();
    expect(mockApiPost).toHaveBeenCalledTimes(1);
  });

  it("maps backend field errors for non-student local registration", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { valid: true, code_type: "TEACHER", context: {} },
    });
    mockApiPost.mockRejectedValueOnce({
      response: { data: { email: ["Email is already in use."] } },
    });

    const RegisterPage = await loadRegisterPage();
    render(<RegisterPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Registration Code"), "TEACH-CODE");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await screen.findByText("Teacher Registration");

    await user.type(screen.getByLabelText("First Name"), "Morgan");
    await user.type(screen.getByLabelText("Last Name"), "Blake");
    await user.type(screen.getByLabelText("Email"), "mblake@example.com");
    await user.type(screen.getByLabelText("Password"), "change-me-123");
    await user.type(screen.getByLabelText("Confirm Password"), "change-me-123");
    await user.click(screen.getByRole("button", { name: "Complete Registration" }));

    expect(await screen.findByText("Email is already in use.")).toBeInTheDocument();
  });

  it("prevents student submission when confirm password mismatches", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { valid: true, code_type: "STUDENT", context: { course_name: "Biology" } },
    });

    const RegisterPage = await loadRegisterPage();
    render(<RegisterPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Registration Code"), "STU-CODE");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await screen.findByText("Student Registration");

    await user.type(screen.getByLabelText("First Name"), "Alex");
    await user.type(screen.getByLabelText("Last Name"), "Torres");
    await user.type(screen.getByLabelText("Password"), "change-me-123");
    await user.type(screen.getByLabelText("Confirm Password"), "different-pass");
    await user.click(screen.getByRole("button", { name: "Complete Registration" }));

    expect(await screen.findByText("Passwords do not match")).toBeInTheDocument();
    expect(mockApiPost).toHaveBeenCalledTimes(1);
  });
});
