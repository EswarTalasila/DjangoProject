import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockRedirect = vi.fn();
const mockGetSessionProfile = vi.fn();

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
/*  rubrics/[id]/page.tsx — detail page                                */
/* ================================================================== */
describe("rubrics/[id]/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/rubrics/RubricDetailView", () => ({
      default: (props: any) => (
        <div>RubricDetail id={props.rubricId} canManage={String(props.canManage)}</div>
      ),
    }));
  }

  it("renders for TEACHER with canManage=false", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("RubricDetail id=7 canManage=false")).toBeInTheDocument();
  });

  it("renders for RESEARCHER with canManage=true", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("RubricDetail id=7 canManage=true")).toBeInTheDocument();
  });

  it("renders for admin (isStaff) with canManage=true", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("RubricDetail id=7 canManage=true")).toBeInTheDocument();
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/page");
    try { await mod.default({ params: Promise.resolve({ id: "7" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /dashboard/rubrics when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/page");
    try { await mod.default({ params: Promise.resolve({ id: "abc" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/rubrics");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/page");
    try { await mod.default({ params: Promise.resolve({ id: "7" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  rubrics/[id]/edit/page.tsx — edit page                             */
/* ================================================================== */
describe("rubrics/[id]/edit/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/rubrics/RubricBuilderForm", () => ({
      default: (props: any) => <div>RubricBuilder mode={props.mode} id={props.rubricId}</div>,
    }));
  }

  it("renders edit form for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/edit/page");
    const el = await mod.default({ params: Promise.resolve({ id: "3" }) });
    render(el as any);
    expect(screen.getByText("Edit Rubric")).toBeInTheDocument();
    expect(screen.getByText("RubricBuilder mode=edit id=3")).toBeInTheDocument();
  });

  it("renders edit form for admin (isStaff)", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/edit/page");
    const el = await mod.default({ params: Promise.resolve({ id: "3" }) });
    render(el as any);
    expect(screen.getByText("Edit Rubric")).toBeInTheDocument();
  });

  it("redirects TEACHER to /dashboard/rubrics", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/edit/page");
    try { await mod.default({ params: Promise.resolve({ id: "3" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/rubrics");
  });

  it("redirects when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/edit/page");
    try { await mod.default({ params: Promise.resolve({ id: "xyz" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/rubrics");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/[id]/edit/page");
    try { await mod.default({ params: Promise.resolve({ id: "3" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  rubrics/new/page.tsx — create page                                 */
/* ================================================================== */
describe("rubrics/new/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/rubrics/RubricBuilderForm", () => ({
      default: (props: any) => <div>RubricBuilder mode={props.mode}</div>,
    }));
  }

  it("renders create form for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/new/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Create Rubric")).toBeInTheDocument();
    expect(screen.getByText("RubricBuilder mode=create")).toBeInTheDocument();
  });

  it("renders create form for admin (isStaff)", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/new/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Create Rubric")).toBeInTheDocument();
  });

  it("redirects TEACHER to /dashboard/rubrics", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/rubrics");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});
