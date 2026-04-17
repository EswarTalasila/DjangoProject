import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockRedirect = vi.fn();
const mockGetSessionProfile = vi.fn();

/* ------------------------------------------------------------------ */
/*  Profile helpers                                                    */
/* ------------------------------------------------------------------ */

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
/*  assignment-templates/page.tsx — list page                          */
/* ================================================================== */
describe("assignment-templates/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({
      redirect: mockRedirect,
      useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
      usePathname: () => "/dashboard/assignment-templates",
      useSearchParams: () => new URLSearchParams(),
    }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assignment-templates/AssignmentTemplateListView", () => ({
      default: (props: any) => <div>AssignmentTemplateList canManage={String(props.canManage)}</div>,
    }));
  }

  it("renders with canManage=true for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("AssignmentTemplateList canManage=true")).toBeInTheDocument();
  });

  it("renders with canManage=true for admin (isStaff)", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("AssignmentTemplateList canManage=true")).toBeInTheDocument();
  });

  it("renders with canManage=false for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("AssignmentTemplateList canManage=false")).toBeInTheDocument();
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  assignment-templates/[id]/page.tsx — detail page                   */
/* ================================================================== */
describe("assignment-templates/[id]/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({
      redirect: mockRedirect,
      useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
      usePathname: () => "/dashboard/assignment-templates/7",
      useSearchParams: () => new URLSearchParams(),
    }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assignment-templates/AssignmentTemplateDetailView", () => ({
      default: (props: any) => (
        <div>
          AssignmentTemplateDetail id={props.assignmentTemplateId} canManage={String(props.canManage)}
        </div>
      ),
    }));
  }

  it("renders for TEACHER with canManage=false", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("AssignmentTemplateDetail id=7 canManage=false")).toBeInTheDocument();
  });

  it("renders for RESEARCHER with canManage=true", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("AssignmentTemplateDetail id=7 canManage=true")).toBeInTheDocument();
  });

  it("redirects to /dashboard/assignment-templates when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "abc" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignment-templates");
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "7" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "7" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  assignment-templates/[id]/edit/page.tsx — edit page                */
/* ================================================================== */
describe("assignment-templates/[id]/edit/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({
      redirect: mockRedirect,
      useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
      usePathname: () => "/dashboard/assignment-templates/3/edit",
      useSearchParams: () => new URLSearchParams(),
    }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assignment-templates/studio/AssignmentTemplateStudioShell", () => ({
      default: (props: any) => (
        <div>
          Studio mode={props.mode} id={props.assignmentTemplateId ?? "none"}
        </div>
      ),
    }));
  }

  it("renders edit form for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/edit/page");
    const el = await mod.default({ params: Promise.resolve({ id: "3" }) });
    render(el as any);
    expect(screen.getByText("Studio mode=edit id=3")).toBeInTheDocument();
  });

  it("renders edit form for isStaff admin", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/edit/page");
    const el = await mod.default({ params: Promise.resolve({ id: "3" }) });
    render(el as any);
    expect(screen.getByText("Studio mode=edit id=3")).toBeInTheDocument();
  });

  it("redirects TEACHER to /dashboard/assignment-templates", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/edit/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "3" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignment-templates");
  });

  it("redirects when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/edit/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "xyz" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignment-templates");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/[id]/edit/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "3" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  assignment-templates/new/page.tsx — create page                    */
/* ================================================================== */
describe("assignment-templates/new/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({
      redirect: mockRedirect,
      useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
      usePathname: () => "/dashboard/assignment-templates/new",
      useSearchParams: () => new URLSearchParams(),
    }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assignment-templates/studio/AssignmentTemplateStudioShell", () => ({
      default: (props: any) => (
        <div>
          Studio mode={props.mode} id={props.assignmentTemplateId ?? "none"}
        </div>
      ),
    }));
  }

  it("renders create form for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/new/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Studio mode=create id=none")).toBeInTheDocument();
  });

  it("renders for isStaff admin", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/new/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Studio mode=create id=none")).toBeInTheDocument();
  });

  it("redirects TEACHER to /dashboard/assignment-templates", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignment-templates");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assignment-templates/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});
