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
/*  assignments/page.tsx — list page                                   */
/* ================================================================== */
describe("assignments/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assignments/AssignmentListView", () => ({
      default: (props: any) => (
        <div>
          AssignmentList role={props.role} userId={props.userId} canCreate={String(props.canCreate)}
        </div>
      ),
    }));
  }

  it("renders for TEACHER with canCreate=true", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/role=TEACHER/)).toBeInTheDocument();
    expect(screen.getByText(/canCreate=true/)).toBeInTheDocument();
  });

  it("renders for ADMIN (isStaff) with canCreate=false", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/role=ADMIN/)).toBeInTheDocument();
    expect(screen.getByText(/canCreate=false/)).toBeInTheDocument();
  });

  it("redirects RESEARCHER to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assignments/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  assignments/[id]/page.tsx — detail page                            */
/* ================================================================== */
describe("assignments/[id]/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assignments/AssignmentDetailView", () => ({
      default: (props: any) => (
        <div>
          AssignmentDetail id={props.assignmentId} canMutate={String(props.canMutate)} role={props.viewerRole} viewer={props.viewerId}
        </div>
      ),
    }));
  }

  it("renders for TEACHER with canMutate=true", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText(/id=7/)).toBeInTheDocument();
    expect(screen.getByText(/canMutate=true/)).toBeInTheDocument();
    expect(screen.getByText(/role=TEACHER/)).toBeInTheDocument();
  });

  it("renders for STUDENT with canMutate=false", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText(/canMutate=false/)).toBeInTheDocument();
    expect(screen.getByText(/role=STUDENT/)).toBeInTheDocument();
    expect(screen.getByText(/viewer=42/)).toBeInTheDocument();
  });

  it("renders for ADMIN with canMutate=false", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText(/role=ADMIN/)).toBeInTheDocument();
    expect(screen.getByText(/canMutate=false/)).toBeInTheDocument();
  });

  it("redirects RESEARCHER to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "7" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /dashboard/assignments when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "abc" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignments");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "7" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  assignments/[id]/edit/page.tsx — edit page                         */
/* ================================================================== */
describe("assignments/[id]/edit/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assignments/AssignmentDetailView", () => ({
      default: (props: any) => (
        <div>
          AssignmentEdit id={props.assignmentId} canMutate={String(props.canMutate)} role={props.viewerRole} mode={props.mode}
        </div>
      ),
    }));
  }

  it("renders the edit route for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/edit/page");
    const el = await mod.default({ params: Promise.resolve({ id: "7" }) });
    render(el as any);
    expect(screen.getByText(/id=7/)).toBeInTheDocument();
    expect(screen.getByText(/canMutate=true/)).toBeInTheDocument();
    expect(screen.getByText(/role=TEACHER/)).toBeInTheDocument();
    expect(screen.getByText(/mode=edit/)).toBeInTheDocument();
  });

  it("redirects ADMIN to /dashboard/assignments", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/edit/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "7" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignments");
  });

  it("redirects STUDENT to /dashboard/assignments", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/[id]/edit/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "7" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignments");
  });
});

/* ================================================================== */
/*  assignments/new/page.tsx — create page                             */
/* ================================================================== */
describe("assignments/new/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/assignments/AssignmentCreateView", () => ({
      default: () => <div>CreateView</div>,
    }));
  }

  it("renders AssignmentCreateView for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/new/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("CreateView")).toBeInTheDocument();
  });

  it("redirects ADMIN to /dashboard/assignments", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignments");
  });

  it("redirects STUDENT to /dashboard/assignments", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/assignments/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/assignments");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/assignments/new/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});
