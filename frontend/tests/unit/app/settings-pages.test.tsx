import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockRedirect = vi.fn();
const mockGetSessionProfile = vi.fn();

function teacherProfile() {
  return { id: "5", name: "Prof X", username: "profx", email: "p@x.com", role: "TEACHER", isStaff: false };
}

/* ================================================================== */
/*  settings/page.tsx — page-level auth gating                         */
/* ================================================================== */
describe("settings/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/settings/changePasswordForm", () => ({
      ChangePasswordForm: (props: any) => (
        <div>ChangePasswordForm name={props.profile.name}</div>
      ),
    }));
  }

  it("renders ChangePasswordForm when profile exists", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/settings/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("ChangePasswordForm name=Prof X")).toBeInTheDocument();
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/settings/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});
