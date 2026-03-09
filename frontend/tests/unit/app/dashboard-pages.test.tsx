import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

/* ------------------------------------------------------------------ */
/*  Shared mock state                                                  */
/* ------------------------------------------------------------------ */

const mockRedirect = vi.fn();
const mockGetSessionProfile = vi.fn();
const mockGetSudoCapabilities = vi.fn();

/* ------------------------------------------------------------------ */
/*  Helpers for constructing profiles                                  */
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
  return { id: "1", name: "Admin A", username: "admin", email: "a@x.com", role: "RESEARCHER", isStaff: true };
}

/* ------------------------------------------------------------------ */
/*  Root page — app/page.tsx (redirect to /login)                      */
/* ------------------------------------------------------------------ */
describe("app/page.tsx — root page", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls redirect to /login", async () => {
    vi.resetModules();
    vi.doMock("next/navigation", () => ({
      redirect: mockRedirect,
    }));
    const mod = await import("@/app/page");
    mod.default();
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ------------------------------------------------------------------ */
/*  Auth layout — app/(auth)/layout.tsx                                */
/* ------------------------------------------------------------------ */
describe("app/(auth)/layout.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders children and branding", async () => {
    vi.resetModules();
    vi.doMock("lucide-react", () => ({
      MonitorSmartphone: (props: any) => <svg data-testid="monitor-icon" {...props} />,
    }));
    const mod = await import("@/app/(auth)/layout");
    const AuthLayout = mod.default;
    render(<AuthLayout><div>Login Form</div></AuthLayout>);
    expect(screen.getByText("Login Form")).toBeInTheDocument();
    expect(screen.getByText("EE Lab Dashboard")).toBeInTheDocument();
  });
});

/* ------------------------------------------------------------------ */
/*  Dashboard layout — app/(dashboard)/layout.tsx                      */
/* ------------------------------------------------------------------ */
describe("app/(dashboard)/layout.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupDashboardLayoutMocks() {
    vi.doMock("next/navigation", () => ({
      redirect: mockRedirect,
      useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
      usePathname: () => "/dashboard",
      useSearchParams: () => new URLSearchParams(),
    }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/layout/sidebarWrapper", () => ({
      SidebarWrapper: () => <nav data-testid="sidebar">Sidebar</nav>,
    }));
    vi.doMock("@/components/layout/userAvatarMenu", () => ({
      UserAvatarMenu: (props: any) => <div data-testid="avatar">{props.name}</div>,
    }));
  }

  it("renders children when profile exists", async () => {
    vi.resetModules();
    setupDashboardLayoutMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/layout");
    const Layout = mod.default;
    const el = await Layout({ children: <div>Dashboard Content</div> });
    render(el as any);
    expect(screen.getByText("Dashboard Content")).toBeInTheDocument();
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("avatar")).toBeInTheDocument();
    expect(screen.getByText("Ready, Set, Resilience")).toBeInTheDocument();
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setupDashboardLayoutMocks();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/layout");
    try {
      await mod.default({ children: <div>Test</div> });
    } catch {
      // redirect throws in test env
    }
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ------------------------------------------------------------------ */
/*  Dashboard page — app/(dashboard)/dashboard/page.tsx                */
/* ------------------------------------------------------------------ */
describe("app/(dashboard)/dashboard/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupDashboardPageMocks() {
    vi.doMock("next/navigation", () => ({
      redirect: mockRedirect,
      useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
      usePathname: () => "/dashboard",
      useSearchParams: () => new URLSearchParams(),
    }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/dashboard/views/TeacherView", () => ({
      default: () => <div>Teacher Dashboard</div>,
    }));
    vi.doMock("@/components/dashboard/views/ResearcherView", () => ({
      default: () => <div>Researcher Dashboard</div>,
    }));
    vi.doMock("@/components/dashboard/views/StudentView", () => ({
      default: () => <div>Student Dashboard</div>,
    }));
  }

  it("renders TeacherView for TEACHER", async () => {
    vi.resetModules();
    setupDashboardPageMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Teacher Dashboard")).toBeInTheDocument();
  });

  it("renders ResearcherView for RESEARCHER", async () => {
    vi.resetModules();
    setupDashboardPageMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Researcher Dashboard")).toBeInTheDocument();
  });

  it("renders StudentView for STUDENT", async () => {
    vi.resetModules();
    setupDashboardPageMocks();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Student Dashboard")).toBeInTheDocument();
  });

  it("redirects to /login when no profile", async () => {
    vi.resetModules();
    setupDashboardPageMocks();
    mockGetSessionProfile.mockResolvedValue(null);
    const mod = await import("@/app/(dashboard)/dashboard/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });
});

/* ------------------------------------------------------------------ */
/*  Archive manager — app/(dashboard)/dashboard/archive-manager/page   */
/* ------------------------------------------------------------------ */
describe("archive-manager/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupArchiveMocks() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
      getSudoCapabilities: mockGetSudoCapabilities,
    }));
    vi.doMock("@/components/archive/ArchiveManagerHub", () => ({
      default: (props: any) => <div>Archive Hub role={props.role} canExport={String(props.canExportIdentifiable)}</div>,
    }));
  }

  it("renders ArchiveManagerHub for TEACHER", async () => {
    vi.resetModules();
    setupArchiveMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/archive-manager/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/Archive Hub role=TEACHER canExport=true/)).toBeInTheDocument();
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setupArchiveMocks();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/archive-manager/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("checks EXPORT_IDENTIFIABLE permission for RESEARCHER", async () => {
    vi.resetModules();
    setupArchiveMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: false,
      permissions: ["EXPORT_IDENTIFIABLE"],
      isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/archive-manager/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/canExport=true/)).toBeInTheDocument();
  });

  it("researcher without EXPORT_IDENTIFIABLE gets canExport=false", async () => {
    vi.resetModules();
    setupArchiveMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: false,
      permissions: [],
      isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/archive-manager/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/canExport=false/)).toBeInTheDocument();
  });
});

/* ------------------------------------------------------------------ */
/*  Exports page — redirect to archive-manager                         */
/* ------------------------------------------------------------------ */
describe("exports/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  it("redirects to /dashboard/archive-manager", async () => {
    vi.resetModules();
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    const mod = await import("@/app/(dashboard)/dashboard/exports/page");
    mod.default();
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/archive-manager");
  });
});

/* ------------------------------------------------------------------ */
/*  Packages page — redirect to archive-manager                        */
/* ------------------------------------------------------------------ */
describe("packages/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  it("redirects to /dashboard/archive-manager", async () => {
    vi.resetModules();
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    const mod = await import("@/app/(dashboard)/dashboard/packages/page");
    mod.default();
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard/archive-manager");
  });
});

/* ------------------------------------------------------------------ */
/*  Codes page                                                         */
/* ------------------------------------------------------------------ */
describe("codes/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupCodesMocks() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
      getSudoCapabilities: mockGetSudoCapabilities,
    }));
    vi.doMock("@/components/codes/CodeManagementView", () => ({
      default: (props: any) => (
        <div>Codes role={props.userRole} perms={props.researcherPermissions.join(",") || "none"} staff={String(props.isStaff)}</div>
      ),
    }));
  }

  it("renders CodeManagementView for TEACHER", async () => {
    vi.resetModules();
    setupCodesMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/codes/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/Codes role=TEACHER/)).toBeInTheDocument();
  });

  it("renders CodeManagementView for RESEARCHER with sudo perms", async () => {
    vi.resetModules();
    setupCodesMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: false,
      permissions: ["ISSUE_STUDENT_REG_CODE"],
      isStaff: true,
    });
    const mod = await import("@/app/(dashboard)/dashboard/codes/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/role=RESEARCHER/)).toBeInTheDocument();
    expect(screen.getByText(/perms=ISSUE_STUDENT_REG_CODE/)).toBeInTheDocument();
    expect(screen.getByText(/staff=true/)).toBeInTheDocument();
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setupCodesMocks();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/codes/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });
});

/* ------------------------------------------------------------------ */
/*  Rubrics page                                                       */
/* ------------------------------------------------------------------ */
describe("rubrics/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupRubricsMocks() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/rubrics/RubricListView", () => ({
      default: (props: any) => <div>Rubrics canManage={String(props.canManage)}</div>,
    }));
  }

  it("renders RubricListView with canManage=true for RESEARCHER", async () => {
    vi.resetModules();
    setupRubricsMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Rubrics canManage=true")).toBeInTheDocument();
  });

  it("renders with canManage=false for TEACHER", async () => {
    vi.resetModules();
    setupRubricsMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Rubrics canManage=false")).toBeInTheDocument();
  });

  it("redirects STUDENT to /dashboard", async () => {
    vi.resetModules();
    setupRubricsMocks();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/rubrics/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });
});

/* ------------------------------------------------------------------ */
/*  Visualizations page                                                */
/* ------------------------------------------------------------------ */
describe("visualizations/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupVizMocks() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
    }));
    vi.doMock("@/components/visualizations/VizDashboardView", () => ({
      default: (props: any) => <div>Viz role={props.role}</div>,
    }));
  }

  it("renders VizDashboardView for TEACHER", async () => {
    vi.resetModules();
    setupVizMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Viz role=TEACHER")).toBeInTheDocument();
  });

  it("shows ADMIN role for staff researcher", async () => {
    vi.resetModules();
    setupVizMocks();
    mockGetSessionProfile.mockResolvedValue(adminProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Viz role=ADMIN")).toBeInTheDocument();
  });

  it("redirects STUDENT", async () => {
    vi.resetModules();
    setupVizMocks();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/visualizations/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });
});

/* ------------------------------------------------------------------ */
/*  Submissions page                                                   */
/* ------------------------------------------------------------------ */
describe("submissions/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupSubmissionsMocks() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
      getSudoCapabilities: mockGetSudoCapabilities,
    }));
    vi.doMock("@/components/submissions/SubmissionsHubView", () => ({
      default: (props: any) => <div>Submissions role={props.role} userId={props.userId}</div>,
    }));
  }

  it("renders for TEACHER", async () => {
    vi.resetModules();
    setupSubmissionsMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/submissions/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Submissions role=TEACHER userId=5")).toBeInTheDocument();
  });

  it("renders for STUDENT", async () => {
    vi.resetModules();
    setupSubmissionsMocks();
    mockGetSessionProfile.mockResolvedValue(studentProfile());
    const mod = await import("@/app/(dashboard)/dashboard/submissions/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Submissions role=STUDENT userId=42")).toBeInTheDocument();
  });

  it("redirects RESEARCHER without VIEW_SUBMISSIONS", async () => {
    vi.resetModules();
    setupSubmissionsMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: false,
      permissions: [],
      isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/submissions/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("renders for RESEARCHER with VIEW_SUBMISSIONS", async () => {
    vi.resetModules();
    setupSubmissionsMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: false,
      permissions: ["VIEW_SUBMISSIONS"],
      isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/submissions/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Submissions role=RESEARCHER userId=10")).toBeInTheDocument();
  });
});

/* ------------------------------------------------------------------ */
/*  Staff page                                                         */
/* ------------------------------------------------------------------ */
describe("staff/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupStaffMocks() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
      getSudoCapabilities: mockGetSudoCapabilities,
    }));
    vi.doMock("@/components/staff/StaffManagementView", () => ({
      default: (props: any) => (
        <div>
          Staff canResetStudents={String(props.canResetStudents)} canResetResearchers={String(props.canResetResearchers)}
        </div>
      ),
    }));
  }

  it("renders for RESEARCHER with staff permissions", async () => {
    vi.resetModules();
    setupStaffMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: false,
      permissions: ["ISSUE_STUDENT_RESET_CODE", "ISSUE_RESEARCHER_RESET_CODE"],
      isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/staff/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/canResetStudents=true/)).toBeInTheDocument();
    expect(screen.getByText(/canResetResearchers=true/)).toBeInTheDocument();
  });

  it("renders with limited permissions", async () => {
    vi.resetModules();
    setupStaffMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: false,
      permissions: [],
      isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/staff/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/canResetStudents=false/)).toBeInTheDocument();
    expect(screen.getByText(/canResetResearchers=false/)).toBeInTheDocument();
  });

  it("redirects TEACHER to /dashboard", async () => {
    vi.resetModules();
    setupStaffMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/staff/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("isStaff grants both reset capabilities", async () => {
    vi.resetModules();
    setupStaffMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: true,
      permissions: [],
      isStaff: true,
    });
    const mod = await import("@/app/(dashboard)/dashboard/staff/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText(/canResetStudents=true/)).toBeInTheDocument();
    expect(screen.getByText(/canResetResearchers=true/)).toBeInTheDocument();
  });
});

/* ------------------------------------------------------------------ */
/*  Sudo page                                                          */
/* ------------------------------------------------------------------ */
describe("sudo/page.tsx", () => {
  beforeEach(() => vi.clearAllMocks());

  function setupSudoMocks() {
    vi.doMock("next/navigation", () => ({ redirect: mockRedirect }));
    vi.doMock("@/lib/auth-session", () => ({
      getSessionProfile: mockGetSessionProfile,
      getSudoCapabilities: mockGetSudoCapabilities,
    }));
    vi.doMock("@/components/sudo/SudoDelegationView", () => ({
      default: (props: any) => <div>Sudo userId={props.currentUserId}</div>,
    }));
  }

  it("renders SudoDelegationView for RESEARCHER with canGrantSudo", async () => {
    vi.resetModules();
    setupSudoMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: true,
      permissions: [],
      isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/sudo/page");
    const el = await mod.default();
    render(el as any);
    expect(screen.getByText("Sudo userId=10")).toBeInTheDocument();
  });

  it("redirects non-RESEARCHER", async () => {
    vi.resetModules();
    setupSudoMocks();
    mockGetSessionProfile.mockResolvedValue(teacherProfile());
    const mod = await import("@/app/(dashboard)/dashboard/sudo/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects RESEARCHER without canGrantSudo", async () => {
    vi.resetModules();
    setupSudoMocks();
    mockGetSessionProfile.mockResolvedValue(researcherProfile());
    mockGetSudoCapabilities.mockResolvedValue({
      hasSudo: true,
      canGrantSudo: false,
      permissions: [],
      isStaff: false,
    });
    const mod = await import("@/app/(dashboard)/dashboard/sudo/page");
    try {
      await mod.default();
    } catch {}
    expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
  });
});
