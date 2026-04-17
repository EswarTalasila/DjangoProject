import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockLogout = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/logout", () => ({
    logout: mockLogout,
  }));
}

async function loadUserAvatarMenu() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/layout/userAvatarMenu");
  return imported.UserAvatarMenu;
}

describe("UserAvatarMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders initials from name", async () => {
    const UserAvatarMenu = await loadUserAvatarMenu();
    render(<UserAvatarMenu name="Morgan Blake" username="mblake" role="TEACHER" />);

    expect(screen.getByText("M")).toBeInTheDocument();
  });

  it("falls back to username initial when name is empty", async () => {
    const UserAvatarMenu = await loadUserAvatarMenu();
    render(<UserAvatarMenu name="" username="mblake" role="TEACHER" />);

    expect(screen.getByText("M")).toBeInTheDocument();
  });

  it("falls back to U when both name and username are empty", async () => {
    const UserAvatarMenu = await loadUserAvatarMenu();
    render(<UserAvatarMenu name="" username="" role="TEACHER" />);

    expect(screen.getByText("U")).toBeInTheDocument();
  });

  it("shows dropdown with name, role, settings link, and logout on click", async () => {
    const UserAvatarMenu = await loadUserAvatarMenu();
    render(<UserAvatarMenu name="Morgan Blake" username="mblake" role="TEACHER" />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));

    expect(await screen.findByText("Morgan Blake")).toBeInTheDocument();
    expect(screen.getByText("TEACHER")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /settings/i })).toHaveAttribute("href", "/dashboard/settings");
  });

  it("calls logout when logout item is clicked", async () => {
    const UserAvatarMenu = await loadUserAvatarMenu();
    render(<UserAvatarMenu name="Morgan Blake" username="mblake" role="TEACHER" />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));
    await user.click(await screen.findByText("Log Out"));

    expect(mockLogout).toHaveBeenCalledOnce();
  });
});
