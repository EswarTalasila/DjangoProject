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
/*  visualizations/courses/[courseId]/page.tsx                          */
/* ================================================================== */
describe("visualizations/courses/[courseId]/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/visualizations/VizCourseSummaryView", () => ({
      default: (props: any) => (
        <div>VizCourse courseId={props.courseId} role={props.role}</div>
      ),
    }));
  }

  it("renders for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/courses/[courseId]/page");
    const el = await mod.default({ params: Promise.resolve({ courseId: "5" }) });
    render(el as any);
    expect(screen.getByText("VizCourse courseId=5 role=TEACHER")).toBeInTheDocument();
  });

  it("renders for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/courses/[courseId]/page");
    const el = await mod.default({ params: Promise.resolve({ courseId: "5" }) });
    render(el as any);
    expect(screen.getByText("VizCourse courseId=5 role=RESEARCHER")).toBeInTheDocument();
  });

  it("renders for admin (isStaff) as ADMIN role", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/courses/[courseId]/page");
    const el = await mod.default({ params: Promise.resolve({ courseId: "5" }) });
    render(el as any);
    expect(screen.getByText("VizCourse courseId=5 role=ADMIN")).toBeInTheDocument();
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/courses/[courseId]/page");
    try { await mod.default({ params: Promise.resolve({ courseId: "5" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/courses/[courseId]/page");
    try { await mod.default({ params: Promise.resolve({ courseId: "5" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  visualizations/assignments/[assignmentId]/page.tsx                  */
/* ================================================================== */
describe("visualizations/assignments/[assignmentId]/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/visualizations/VizAssignmentSummaryView", () => ({
      default: (props: any) => (
        <div>VizAssignment assignmentId={props.assignmentId} role={props.role}</div>
      ),
    }));
  }

  it("renders for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/assignments/[assignmentId]/page");
    const el = await mod.default({ params: Promise.resolve({ assignmentId: "9" }) });
    render(el as any);
    expect(screen.getByText("VizAssignment assignmentId=9 role=TEACHER")).toBeInTheDocument();
  });

  it("renders for RESEARCHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/assignments/[assignmentId]/page");
    const el = await mod.default({ params: Promise.resolve({ assignmentId: "9" }) });
    render(el as any);
    expect(screen.getByText("VizAssignment assignmentId=9 role=RESEARCHER")).toBeInTheDocument();
  });

  it("renders for admin (isStaff) as ADMIN role", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/assignments/[assignmentId]/page");
    const el = await mod.default({ params: Promise.resolve({ assignmentId: "9" }) });
    render(el as any);
    expect(screen.getByText("VizAssignment assignmentId=9 role=ADMIN")).toBeInTheDocument();
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/assignments/[assignmentId]/page");
    try { await mod.default({ params: Promise.resolve({ assignmentId: "9" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/assignments/[assignmentId]/page");
    try { await mod.default({ params: Promise.resolve({ assignmentId: "9" }) }); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});
