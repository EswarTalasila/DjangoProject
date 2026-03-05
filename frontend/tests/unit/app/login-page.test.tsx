import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockApiPost = vi.fn();
const mockCookiesSet = vi.fn();
const mockGoogleLoginTrigger = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
  }));
  vi.doMock("js-cookie", () => ({
    default: { set: mockCookiesSet, remove: vi.fn(), get: vi.fn() },
  }));
  vi.doMock("@react-oauth/google", () => ({
    GoogleOAuthProvider: ({ children }: { children: ReactNode }) => children,
    useGoogleLogin: () => mockGoogleLoginTrigger,
  }));
  vi.doMock("@/lib/api", () => ({
    default: { post: mockApiPost },
  }));
}

async function loadLoginPage() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/app/(auth)/login/page");
  return imported.default;
}

describe("Login page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000/api/v1";
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
});
