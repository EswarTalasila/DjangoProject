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

/* ================================================================== */
/*  courses/page.tsx — list page                                       */
/* ================================================================== */
describe("courses/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/courses/CoursesListView", () => ({
      default: (props: any) => <div>CoursesList role={props.userRole}</div>,
    }));
  }

  it("renders for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/courses/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("CoursesList role=TEACHER")).toBeInTheDocument();
  });

  it("renders for STUDENT", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/courses/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("CoursesList role=STUDENT")).toBeInTheDocument();
  });

  it("redirects RESEARCHER to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/courses/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/courses/page");
    try { await mod.default(); } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ================================================================== */
/*  courses/[id]/page.tsx — detail page                                */
/* ================================================================== */
describe("courses/[id]/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/courses/CourseDetailView", () => ({
      default: (props: any) => (
        <div>
          CourseDetail id={props.courseId} role={props.userRole} userId={props.userId}
        </div>
      ),
    }));
  }

  it("renders for TEACHER", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/courses/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "99" }) });
    render(el as any);
    expect(screen.getByText(/CourseDetail id=99/)).toBeInTheDocument();
    expect(screen.getByText(/role=TEACHER/)).toBeInTheDocument();
    expect(screen.getByText(/userId=5/)).toBeInTheDocument();
  });

  it("renders for STUDENT", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/courses/[id]/page");
    const el = await mod.default({ params: Promise.resolve({ id: "99" }) });
    render(el as any);
    expect(screen.getByText(/role=STUDENT/)).toBeInTheDocument();
    expect(screen.getByText(/userId=42/)).toBeInTheDocument();
  });

  it("redirects RESEARCHER to /dashboard", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/courses/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "99" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to /dashboard/courses when id is NaN", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/courses/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "abc" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/courses");
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setup();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/courses/[id]/page");
    try {
      await mod.default({ params: Promise.resolve({ id: "99" }) });
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});
