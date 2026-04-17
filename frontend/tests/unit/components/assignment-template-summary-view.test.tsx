import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockFetchCourseSummary = vi.fn();

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
    fetchCourseSummary: mockFetchCourseSummary,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/visualizations/VizCourseSummaryView"
  );
  return imported.default;
}

const courseSummaryData = {
  generatedAt: "2026-03-01T10:00:00Z",
  filters: {
    startDate: null,
    endDate: null,
    category: null,
    assignmentTemplateId: null,
  },
  courseId: 1,
  courseName: "Biology 101",
  enrolledCount: 30,
  assignments: [
    {
      assignmentId: 10,
      assignmentTitle: "Biology Midterm",
      assignmentTemplateTitle: "Midterm Exam",
      assignmentTemplateCategory: "EXAM",
      submittedCount: 25,
      totalStudents: 30,
      completionPct: 0.833,
      gradedCount: 20,
      avgScore: 85.5,
      pendingGrades: 5,
    },
    {
      assignmentId: 11,
      assignmentTitle: "Lab Report Week 3",
      assignmentTemplateTitle: "Lab Report 1",
      assignmentTemplateCategory: "LAB",
      submittedCount: 28,
      totalStudents: 30,
      completionPct: 0.933,
      gradedCount: 28,
      avgScore: 92.1,
      pendingGrades: 0,
    },
  ],
};

describe("VizCourseSummaryView (assignment-template-summary-view)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders course name as heading", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });
  });

  it("shows enrolled student count", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("30 enrolled students")
      ).toBeInTheDocument();
    });
  });

  it("shows loading state", async () => {
    mockFetchCourseSummary.mockReturnValue(new Promise(() => {}));
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    // "Loading..." appears in both the subtitle and the loading indicator
    const loadingTexts = screen.getAllByText("Loading...");
    expect(loadingTexts.length).toBeGreaterThanOrEqual(2);
  });

  it("shows error when fetch fails", async () => {
    mockFetchCourseSummary.mockRejectedValueOnce(new Error("fail"));
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load course summary.")
      ).toBeInTheDocument();
    });
  });

  it("shows fallback heading when courseName is missing", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce({
      ...courseSummaryData,
      courseName: undefined,
    });
    const Component = await loadComponent();
    render(<Component courseId={5} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Course 5")).toBeInTheDocument();
    });
  });

  it("renders assignment table rows", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology Midterm")).toBeInTheDocument();
    });
    expect(screen.getByText("Lab Report Week 3")).toBeInTheDocument();
  });

  it("renders assignment_template categories", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("EXAM")).toBeInTheDocument();
    });
    expect(screen.getByText("LAB")).toBeInTheDocument();
  });

  it("renders submitted counts", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("25/30")).toBeInTheDocument();
    });
    expect(screen.getByText("28/30")).toBeInTheDocument();
  });

  it("renders completion percentages", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("83%")).toBeInTheDocument();
      expect(screen.getByText("93%")).toBeInTheDocument();
    });
  });

  it("renders avg scores", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("85.5")).toBeInTheDocument();
      expect(screen.getByText("92.1")).toBeInTheDocument();
    });
  });

  it("renders pending badge when > 0", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("5")).toBeInTheDocument();
    });
  });

  it("renders '0' for pending when 0", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      // Lab Report 1 has 0 pending, rendered as "0" text
      const zeros = screen.getAllByText("0");
      expect(zeros.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows empty state when no assignments", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce({
      ...courseSummaryData,
      assignments: [],
    });
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("No assignments found.")
      ).toBeInTheDocument();
    });
  });

  it("renders back link to dashboard", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      const link = screen.getByRole("link", { name: "" });
      expect(link).toHaveAttribute("href", "/dashboard/visualizations");
    });
  });

  it("renders generated timestamp", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText(/Generated at/)).toBeInTheDocument();
    });
  });

  it("shows '-' for null assignmentTemplateCategory", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce({
      ...courseSummaryData,
      assignments: [
        {
          ...courseSummaryData.assignments[0],
          assignmentTemplateCategory: null,
        },
      ],
    });
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("-")).toBeInTheDocument();
    });
  });

  it("shows N/A for null completion and avg score", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce({
      ...courseSummaryData,
      assignments: [
        {
          ...courseSummaryData.assignments[0],
          completionPct: null,
          avgScore: null,
        },
      ],
    });
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      const naTexts = screen.getAllByText("N/A");
      expect(naTexts.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("renders Assignments card title", async () => {
    mockFetchCourseSummary.mockResolvedValueOnce(courseSummaryData);
    const Component = await loadComponent();
    render(<Component courseId={1} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Assignments")).toBeInTheDocument();
    });
  });
});
