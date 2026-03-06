import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockFetchDashboard = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("next/link", () => ({
    default: ({ children, ...props }: any) => <a {...props}>{children}</a>,
  }));
  vi.doMock("@/lib/visualization-api", () => ({
    fetchDashboard: mockFetchDashboard,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/visualizations/VizDashboardView"
  );
  return imported.default;
}

async function renderVizDashboardAndWait(role: string) {
  const Component = await loadComponent();
  render(<Component role={role} />);
  await waitFor(() => {
    expect(mockFetchDashboard).toHaveBeenCalledTimes(1);
  });
  await waitFor(() => {
    expect(
      screen.queryByText("Loading dashboard...")
    ).not.toBeInTheDocument();
  });
}

const dashboardData = {
  generatedAt: "2026-03-01T12:00:00Z",
  courses: [
    {
      courseId: 1,
      courseName: "Biology 101",
      enrolledCount: 30,
      activeEnrollments: 28,
      assignmentCount: 5,
      avgCompletionRate: 0.85,
      avgScore: 78.3,
      pendingGrades: 3,
    },
    {
      courseId: 2,
      courseName: "Chemistry 201",
      enrolledCount: 20,
      activeEnrollments: 18,
      assignmentCount: 3,
      avgCompletionRate: null,
      avgScore: null,
      pendingGrades: 0,
    },
  ],
};

describe("VizDashboardView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading and teacher description", async () => {
    mockFetchDashboard.mockResolvedValueOnce({
      generatedAt: "2026-03-01T12:00:00Z",
      courses: [],
    });
    await renderVizDashboardAndWait("TEACHER");

    expect(screen.getByText("Analytics Dashboard")).toBeInTheDocument();
    expect(
      screen.getByText("Overview of your courses and student performance.")
    ).toBeInTheDocument();
  });

  it("renders researcher description for non-teacher role", async () => {
    mockFetchDashboard.mockResolvedValueOnce({
      generatedAt: "2026-03-01T12:00:00Z",
      courses: [],
    });
    await renderVizDashboardAndWait("RESEARCHER");

    expect(
      screen.getByText("System-wide course and performance overview.")
    ).toBeInTheDocument();
  });

  it("shows loading state", async () => {
    mockFetchDashboard.mockReturnValue(new Promise(() => {}));
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    expect(screen.getByText("Loading dashboard...")).toBeInTheDocument();
  });

  it("shows error when fetch fails", async () => {
    mockFetchDashboard.mockRejectedValueOnce(new Error("fail"));
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load dashboard data.")
      ).toBeInTheDocument();
    });
  });

  it("renders stat cards with correct totals", async () => {
    mockFetchDashboard.mockResolvedValueOnce(dashboardData);
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      // Total students: 30 + 20 = 50
      expect(screen.getByText("50")).toBeInTheDocument();
    });

    // Total assignments: 5 + 3 = 8
    expect(screen.getByText("8")).toBeInTheDocument();
    // Total pending: 3 + 0 = 3
    // Courses count: 2
    expect(screen.getByText("2")).toBeInTheDocument();

    // Labels
    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("Assignments")).toBeInTheDocument();
    expect(screen.getByText("Pending Grades")).toBeInTheDocument();
  });

  it("renders course rows", async () => {
    mockFetchDashboard.mockResolvedValueOnce(dashboardData);
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });
    expect(screen.getByText("Chemistry 201")).toBeInTheDocument();
  });

  it("shows completion and avg score for courses", async () => {
    mockFetchDashboard.mockResolvedValueOnce(dashboardData);
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      // Biology: 85% completion, 78.3 avg
      expect(screen.getByText("85%")).toBeInTheDocument();
      expect(screen.getByText("78.3")).toBeInTheDocument();
    });

    // Chemistry: N/A for both
    const naTexts = screen.getAllByText("N/A");
    expect(naTexts.length).toBeGreaterThanOrEqual(2);
  });

  it("shows pending badge when pendingGrades > 0", async () => {
    mockFetchDashboard.mockResolvedValueOnce(dashboardData);
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("3 pending")).toBeInTheDocument();
    });
  });

  it("shows student and assignment counts per course", async () => {
    mockFetchDashboard.mockResolvedValueOnce(dashboardData);
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText(/30 students.*5 assignments/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/20 students.*3 assignments/)
      ).toBeInTheDocument();
    });
  });

  it("renders 'No courses found' when courses array is empty", async () => {
    mockFetchDashboard.mockResolvedValueOnce({
      generatedAt: "2026-03-01T12:00:00Z",
      courses: [],
    });
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("No courses found.")).toBeInTheDocument();
    });
  });

  it("renders course link when courseId is set", async () => {
    mockFetchDashboard.mockResolvedValueOnce(dashboardData);
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    const link = screen.getByRole("link", {
      name: /Biology 101/,
    });
    expect(link).toHaveAttribute(
      "href",
      "/dashboard/visualizations/courses/1"
    );
  });

  it("renders generated timestamp", async () => {
    mockFetchDashboard.mockResolvedValueOnce(dashboardData);
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText(/Generated at/)).toBeInTheDocument();
    });
  });

  it("renders Courses section heading", async () => {
    mockFetchDashboard.mockResolvedValueOnce(dashboardData);
    const Component = await loadComponent();
    render(<Component role="TEACHER" />);

    await waitFor(() => {
      // "Courses" heading in the section, plus "Courses" stat card label
      const coursesTexts = screen.getAllByText("Courses");
      expect(coursesTexts.length).toBeGreaterThanOrEqual(2);
    });
  });
});
