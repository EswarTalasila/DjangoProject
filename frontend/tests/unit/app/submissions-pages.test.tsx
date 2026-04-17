import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockRedirect = vi.fn();
const mockGetSessionProfile = vi.fn();
const mockGetSudoCapabilities = vi.fn();

function teacherProfile() {
  return { id: "5", name: "Prof X", username: "profx", email: "p@x.com", role: "TEACHER", isStaff: false };
}
function researcherProfile() {
  return { id: "10", name: "Dr R", username: "drr", email: "r@x.com", role: "RESEARCHER", isStaff: false };
}
function studentProfile() {
  return { id: "42", name: "Stu D", username: "stud", email: "s@x.com", role: "STUDENT", isStaff: false };
}
function adminProfile() {
  return { id: "1", name: "Admin", username: "admin", email: "a@x.com", role: "TEACHER", isStaff: true };
}

/* ================================================================== */
/*  submissions/[id]/page.tsx — detail page                            */
/* ================================================================== */
describe("submissions/[id]/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
      getSudoCapabilities: mockGetSudoCapabilities,
    }));
    vi.doMock("@/components/submissions/SubmissionDetailView", () => ({
      default: (props: any) => (
        <div>SubmissionDetail id={props.submissionId} role={props.viewerRole}</div>
      ),
    }));
  }

  it("renders for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/submissions/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("SubmissionDetail id=7 role=TEACHER")).toBeInTheDocument();
  });

  it("renders for STUDENT", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/submissions/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("SubmissionDetail id=7 role=STUDENT")).toBeInTheDocument();
  });

  it("renders for admin (isStaff) as ADMIN role", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/submissions/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("SubmissionDetail id=7 role=ADMIN")).toBeInTheDocument();
  });

  it("renders for RESEARCHER with VIEW_SUBMISSIONS permission", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({ permissions: ["VIEW_SUBMISSIONS"] });
    const mod = await import("@/app/(dashboard)/dashboard/submissions/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("SubmissionDetail id=7 role=RESEARCHER")).toBeInTheDocument();
  });

  it("redirects RESEARCHER without VIEW_SUBMISSIONS to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({ permissions: [] });
    const mod = await import("@/app/(dashboard)/dashboard/submissions/[id]/page");
    try { await mod.default({ params: Promise.resolve({ id: "7" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /dashboard/submissions when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/submissions/[id]/page");
    try { await mod.default({ params: Promise.resolve({ id: "abc" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/submissions");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/submissions/[id]/page");
    try { await mod.default({ params: Promise.resolve({ id: "7" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });

  it("redirects unknown role to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue({
      id: "99", name: "X", username: "x", email: "x@x.com", role: "UNKNOWN", isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/submissions/[id]/page");
    try { await mod.default({ params: Promise.resolve({ id: "7" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });
});
