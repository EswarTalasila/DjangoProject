import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockApiPost = vi.fn();
const mockCookiesSet = vi.fn();
const mockCookiesRemove = vi.fn();
const mockGoogleLoginTrigger = vi.fn();
let capturedGoogleLoginConfig: {
  onSuccess?: (tokenResponse: { access_token: string }) => void;
  onError?: () => void;
} = {};

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
  }));
  vi.doMock("js-cookie", () => ({
    default: { set: mockCookiesSet, remove: mockCookiesRemove, get: vi.fn() },
  }));
  vi.doMock("@react-oauth/google", () => ({
    GoogleOAuthProvider: ({ children }: { children: ReactNode }) => children,
    useGoogleLogin: (config: typeof capturedGoogleLoginConfig) => {
      capturedGoogleLoginConfig = config;
      return mockGoogleLoginTrigger;
    },
  }));
  vi.doMock("@/lib/api", () => ({
    default: { post: mockApiPost },
  }));
}

async function loadLoginPage() {
  vi.resetModules();
  capturedGoogleLoginConfig = {};
  setupModuleMocks();
  const imported = await import("@/app/(auth)/login/page");
  return imported.default;
}

describe("Login page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.NEXT_PUBLIC_API_URL = "/api/v1";
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-google-client.apps.googleusercontent.com";
    window.history.replaceState({}, "", "/login");
  });

  it("shows the updated identifier guidance text", async () => {
    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    expect(
      screen.getByText(
        "Students use username. Teachers and researchers can use username or email.",
      ),
    ).toBeInTheDocument();
  });

  it("renders admin console link to Django admin", async () => {
    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const link = screen.getByRole("link", { name: "Admin? Open Django Admin" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/admin/");
  });

  it("submits local login and stores display-name cookie", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { accessToken: "access-token", role: "TEACHER", name: "Morgan Blake" },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "mblake");
    await user.type(screen.getByLabelText("Password"), "change-me");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith("/auth/sessions", {
        identifier: "mblake",
        password: "change-me",
      });
    });
    expect(mockCookiesSet).toHaveBeenCalledWith("user_name", "Morgan Blake", { expires: 1 });
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("blocks admin login and shows admin-console guidance", async () => {
    mockApiPost.mockRejectedValueOnce({
      response: { data: { detail: "Admin accounts must use Django admin." } },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "admin@example.com");
    await user.type(screen.getByLabelText("Password"), "change-me");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith("/auth/sessions", {
        identifier: "admin@example.com",
        password: "change-me",
      });
    });
    expect(mockPush).not.toHaveBeenCalled();
    expect(mockCookiesSet).not.toHaveBeenCalled();
    expect(await screen.findByText("Admin accounts must use Django admin.")).toBeInTheDocument();
    expect(await screen.findByText("Use Django Admin")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Django Admin" })).toHaveAttribute(
      "href",
      "/admin/",
    );
  });

  it("maps field-level backend validation errors", async () => {
    mockApiPost.mockRejectedValueOnce({
      response: { data: { identifier: ["Invalid identifier"] } },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "bad-id");
    await user.type(screen.getByLabelText("Password"), "wrong-pass");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByText("Invalid identifier")).toBeInTheDocument();
  });

  it("shows backend detail for generic auth failures", async () => {
    mockApiPost.mockRejectedValueOnce({
      response: { data: { detail: "Invalid identifier or password." } },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "mblake");
    await user.type(screen.getByLabelText("Password"), "wrong-pass");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByText("Invalid identifier or password.")).toBeInTheDocument();
  });

  it("blocks ADMIN role login, removes cookie and shows admin guidance", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { role: "ADMIN", name: "Super Admin" },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "admin");
    await user.type(screen.getByLabelText("Password"), "admin-pass");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockCookiesRemove).toHaveBeenCalledWith("user_name");
    });
    expect(mockPush).not.toHaveBeenCalled();
    expect(mockCookiesSet).not.toHaveBeenCalled();
    expect(await screen.findByText("Use Django Admin")).toBeInTheDocument();
  });

  it("handles successful Google OAuth login", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { role: "TEACHER", name: "Google Teacher" },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    // Trigger the captured onSuccess callback (simulating Google OAuth flow)
    expect(capturedGoogleLoginConfig.onSuccess).toBeDefined();
    await act(async () => {
      await capturedGoogleLoginConfig.onSuccess!({
        access_token: "google-token-123",
      });
    });

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith("/auth/sessions/oauth", {
        accessToken: "google-token-123",
      });
    });
    expect(mockCookiesSet).toHaveBeenCalledWith("user_name", "Google Teacher", { expires: 1 });
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("shows error when Google OAuth login fails on API call", async () => {
    mockApiPost.mockRejectedValueOnce({
      response: { data: { detail: "Unregistered Google account." } },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    expect(capturedGoogleLoginConfig.onSuccess).toBeDefined();
    await act(async () => {
      await capturedGoogleLoginConfig.onSuccess!({ access_token: "bad-token" });
    });

    expect(await screen.findByText("Unregistered Google account.")).toBeInTheDocument();
  });

  it("shows fallback error when Google OAuth API error has no detail", async () => {
    mockApiPost.mockRejectedValueOnce({
      response: { data: {} },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    expect(capturedGoogleLoginConfig.onSuccess).toBeDefined();
    await act(async () => {
      await capturedGoogleLoginConfig.onSuccess!({ access_token: "bad-token" });
    });

    expect(await screen.findByText("Google login failed.")).toBeInTheDocument();
  });

  it("shows error when Google OAuth fails to initialize", async () => {
    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    expect(capturedGoogleLoginConfig.onError).toBeDefined();
    act(() => {
      capturedGoogleLoginConfig.onError!();
    });

    expect(await screen.findByText("Google login failed to initialize.")).toBeInTheDocument();
  });

  it("calls Google login trigger when Continue with Google is clicked", async () => {
    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Continue with Google/i }));

    expect(mockGoogleLoginTrigger).toHaveBeenCalled();
  });

  it("does not mount Google OAuth when no client id is configured", async () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "";
    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const button = screen.getByRole("button", { name: /Continue with Google/i });
    expect(button).toBeDisabled();
    expect(
      screen.getByText("Google sign-in is unavailable in this environment."),
    ).toBeInTheDocument();
  });

  it("uses default name Instructor when login response has no name", async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { role: "TEACHER" },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "teacher1");
    await user.type(screen.getByLabelText("Password"), "pass123");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockCookiesSet).toHaveBeenCalledWith("user_name", "Instructor", { expires: 1 });
    });
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("shows default fallback for error with string data", async () => {
    mockApiPost.mockRejectedValueOnce({
      response: { data: "Something went wrong" },
    });

    const LoginPage = await loadLoginPage();
    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Identifier"), "user1");
    await user.type(screen.getByLabelText("Password"), "pass");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByText("Something went wrong")).toBeInTheDocument();
  });
});
