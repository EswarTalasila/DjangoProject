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
/*  assessments/page.tsx — list page                                   */
/* ================================================================== */
describe("assessments/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assessments/AssessmentListView", () => ({
      default: (props: any) => <div>AssessmentList canManage={String(props.canManage)}</div>,
    }));
  }

  it("renders with canManage=true for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("AssessmentList canManage=true")).toBeInTheDocument();
  });

  it("renders with canManage=true for admin (isStaff)", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("AssessmentList canManage=true")).toBeInTheDocument();
  });

  it("renders with canManage=false for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("AssessmentList canManage=false")).toBeInTheDocument();
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assessments/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  assessments/[id]/page.tsx — detail page                            */
/* ================================================================== */
describe("assessments/[id]/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assessments/AssessmentDetailView", () => ({
      default: (props: any) => (
        <div>
          AssessmentDetail id={props.assessmentId} canManage={String(props.canManage)}
        </div>
      ),
    }));
  }

  it("renders for TEACHER with canManage=false", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("AssessmentDetail id=7 canManage=false")).toBeInTheDocument();
  });

  it("renders for RESEARCHER with canManage=true", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText("AssessmentDetail id=7 canManage=true")).toBeInTheDocument();
  });

  it("redirects to /dashboard/assessments when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "abc" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assessments");
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "7" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "7" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  assessments/[id]/edit/page.tsx — edit page                         */
/* ================================================================== */
describe("assessments/[id]/edit/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assessments/AssessmentBuilderForm", () => ({
      default: (props: any) => <div>Builder mode={props.mode} id={props.assessmentId}</div>,
    }));
  }

  it("renders edit form for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/edit/page");
    const el = await mod.default({ params: Promise.resolve({ id: "3" }) });
    render(el as any);
    expect(screen.getByText("Edit Assessment")).toBeInTheDocument();
    expect(screen.getByText("Builder mode=edit id=3")).toBeInTheDocument();
  });

  it("renders edit form for isStaff admin", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/edit/page");
    const el = await mod.default({ params: Promise.resolve({ id: "3" }) });
    render(el as any);
    expect(screen.getByText("Edit Assessment")).toBeInTheDocument();
  });

  it("redirects TEACHER to /dashboard/assessments", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/edit/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "3" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assessments");
  });

  it("redirects when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/edit/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "xyz" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assessments");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assessments/[id]/edit/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "3" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  assessments/new/page.tsx — create page                             */
/* ================================================================== */
describe("assessments/new/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assessments/AssessmentBuilderForm", () => ({
      default: (props: any) => <div>Builder mode={props.mode}</div>,
    }));
  }

  it("renders create form for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/new/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Create Assessment")).toBeInTheDocument();
    expect(screen.getByText("Builder mode=create")).toBeInTheDocument();
  });

  it("renders for isStaff admin", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/new/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Create Assessment")).toBeInTheDocument();
  });

  it("redirects TEACHER to /dashboard/assessments", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assessments/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assessments");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assessments/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});
