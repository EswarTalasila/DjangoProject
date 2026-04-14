import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockFetchAssignmentSummary = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("next/link", () => ({
    default: ({ children, ...props }: any) => <a {...props}>{children}</a>,
  }));
  // Mock recharts to avoid rendering issues in test env
  vi.doMock("recharts", () => ({
    BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
    Bar: ({ children }: any) => <div data-testid="bar">{children}</div>,
    XAxis: () => <div data-testid="x-axis" />,
    YAxis: () => <div data-testid="y-axis" />,
    CartesianGrid: () => <div data-testid="cartesian-grid" />,
    Tooltip: () => <div data-testid="tooltip" />,
    ResponsiveContainer: ({ children }: any) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    Cell: () => <div data-testid="cell" />,
  }));
  vi.doMock("@/lib/visualization-api", () => ({
    fetchAssignmentSummary: mockFetchAssignmentSummary,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/visualizations/VizAssignmentSummaryView"
  );
  return imported.default;
}

const summaryData = {
  generatedAt: "2026-03-01T10:00:00Z",
  filters: { startDate: null, endDate: null },
  assignmentId: 10,
  assignmentTemplateTitle: "Midterm Exam",
  assignmentTemplateCategory: "EXAM",
  totalStudents: 30,
  submittedCount: 25,
  gradedCount: 20,
  completionPct: 0.833,
  avgScore: 78.5,
  medianScore: 80.0,
  highScore: 98.0,
  lowScore: 45.0,
  distribution: [
    { range: "0-20", count: 1 },
    { range: "21-40", count: 2 },
    { range: "41-60", count: 4 },
    { range: "61-80", count: 8 },
    { range: "81-100", count: 5 },
  ],
};

describe("VizAssignmentSummaryView (assignment-summary-view)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders assignment_template title as heading", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce(summaryData);
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Midterm Exam")).toBeInTheDocument();
    });
  });

  it("renders category as subtitle", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce(summaryData);
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("EXAM")).toBeInTheDocument();
    });
  });

  it("shows loading state", async () => {
    mockFetchAssignmentSummary.mockReturnValue(new Promise(() => {}));
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    // "Loading..." appears in both the subtitle and the loading indicator
    const loadingTexts = screen.getAllByText("Loading...");
    expect(loadingTexts.length).toBeGreaterThanOrEqual(2);
  });

  it("shows error when fetch fails", async () => {
    mockFetchAssignmentSummary.mockRejectedValueOnce(new Error("fail"));
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load assignment summary.")
      ).toBeInTheDocument();
    });
  });

  it("shows fallback heading when assignmentTemplateTitle is missing", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce({
      ...summaryData,
      assignmentTemplateTitle: undefined,
    });
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Assignment 10")).toBeInTheDocument();
    });
  });

  it("shows 'Loading...' subtitle when data not yet loaded", async () => {
    mockFetchAssignmentSummary.mockReturnValue(new Promise(() => {}));
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    // "Loading..." appears in both the subtitle and the loading indicator
    const loadingTexts = screen.getAllByText("Loading...");
    expect(loadingTexts.length).toBeGreaterThanOrEqual(2);
  });

  it("renders stat items with correct values", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce(summaryData);
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("30")).toBeInTheDocument(); // totalStudents
    });
    expect(screen.getByText("25")).toBeInTheDocument(); // submittedCount
    expect(screen.getByText("20")).toBeInTheDocument(); // gradedCount
    expect(screen.getByText("83%")).toBeInTheDocument(); // completionPct

    // Labels
    expect(screen.getByText("Total Students")).toBeInTheDocument();
    expect(screen.getByText("Submitted")).toBeInTheDocument();
    expect(screen.getByText("Graded")).toBeInTheDocument();
    expect(screen.getByText("Completion")).toBeInTheDocument();
  });

  it("renders score summary cards", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce(summaryData);
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("78.5")).toBeInTheDocument(); // avg
    });
    expect(screen.getByText("80.0")).toBeInTheDocument(); // median
    expect(screen.getByText("98.0")).toBeInTheDocument(); // high
    expect(screen.getByText("45.0")).toBeInTheDocument(); // low

    // Labels
    expect(screen.getByText("Average")).toBeInTheDocument();
    expect(screen.getByText("Median")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Low")).toBeInTheDocument();
  });

  it("renders grade distribution chart", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce(summaryData);
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Grade Distribution")).toBeInTheDocument();
    });
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("shows 'No graded submissions' when gradedCount is 0", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce({
      ...summaryData,
      gradedCount: 0,
      distribution: [],
    });
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("No graded submissions yet.")
      ).toBeInTheDocument();
    });
  });

  it("renders back link to visualizations", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce(summaryData);
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      const link = screen.getByRole("link", { name: "" });
      expect(link).toHaveAttribute("href", "/dashboard/visualizations");
    });
  });

  it("renders generated timestamp", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce(summaryData);
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText(/Generated at/)).toBeInTheDocument();
    });
  });

  it("shows N/A for null scores", async () => {
    mockFetchAssignmentSummary.mockResolvedValueOnce({
      ...summaryData,
      avgScore: null,
      medianScore: null,
      highScore: null,
      lowScore: null,
      completionPct: null,
    });
    const Component = await loadComponent();
    render(<Component assignmentId={10} role="TEACHER" />);

    await waitFor(() => {
      const naTexts = screen.getAllByText("N/A");
      // 4 score cards + 1 completion = 5
      expect(naTexts.length).toBeGreaterThanOrEqual(5);
    });
  });
});
