import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListCourses = vi.fn();
const mockListAssignmentTemplates = vi.fn();
const mockListRubrics = vi.fn();
const mockOnAddItem = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("sonner", () => ({
    toast: { success: vi.fn(), error: mockToastError },
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/lib/assignment-template-api", () => ({
    listAssignmentTemplates: mockListAssignmentTemplates,
  }));
  vi.doMock("@/lib/rubric-api", () => ({
    listRubrics: mockListRubrics,
  }));
  vi.doMock("@/lib/package-api", () => ({}));
  vi.doMock("@/lib/utils", () => ({
    toErrorMessage: (e: unknown) =>
      e instanceof Error ? e.message : "Unknown error",
    cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/archive/DataCatalog");
  return imported.default;
}

const mockCourses = [
  {
    id: 1,
    name: "Intro to CS",
    studentCount: 30,
    assignmentIds: [],
    teacherId: 1,
    teacherName: "Prof Smith",
    createdAt: "2025-01-01",
    status: "ACTIVE",
  },
  {
    id: 2,
    name: "Advanced Math",
    studentCount: 20,
    assignmentIds: [],
    teacherId: 2,
    teacherName: "Prof Jones",
    createdAt: "2025-01-01",
    status: "ARCHIVED",
  },
];

const mockAssignmentTemplates = [
  {
    id: 1,
    title: "Midterm Exam",
    category: "EXAM",
    gradingMode: "MANUAL",
    scoringPolicy: "LATEST",
    questions: [],
    questionGroups: [],
    rubricId: null,
    rubricAssignmentTemplateIds: [],
    status: "ACTIVE",
  },
];

const mockRubricsList = [
  {
    id: 1,
    title: "Code Quality",
    description: "Rubric for code quality",
    status: "ACTIVE",
    createdBy: 1,
    createdAt: "2025-01-01",
    updatedAt: "2025-01-01",
    criteria: [],
  },
];

describe("DataCatalog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", async () => {
    mockListCourses.mockReturnValue(new Promise(() => {}));
    mockListAssignmentTemplates.mockReturnValue(new Promise(() => {}));
    mockListRubrics.mockReturnValue(new Promise(() => {}));
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    expect(screen.getByText("Loading catalog...")).toBeInTheDocument();
  });

  it("renders catalog sections after loading", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockListRubrics.mockResolvedValueOnce(mockRubricsList);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(screen.getByText("Courses")).toBeInTheDocument();
      expect(screen.getByText("Assignment Templates")).toBeInTheDocument();
      expect(screen.getByText("Rubrics")).toBeInTheDocument();
    });
  });

  it("shows course count in section header", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockListRubrics.mockResolvedValueOnce(mockRubricsList);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // 2 courses
    });
  });

  it("shows course names in the list", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockListRubrics.mockResolvedValueOnce(mockRubricsList);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(screen.getByText("Intro to CS")).toBeInTheDocument();
      expect(screen.getByText("Advanced Math")).toBeInTheDocument();
    });
  });

  it("shows assignment template titles", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockListRubrics.mockResolvedValueOnce(mockRubricsList);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(screen.getByText("Midterm Exam")).toBeInTheDocument();
    });
  });

  it("shows rubric titles", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockListRubrics.mockResolvedValueOnce(mockRubricsList);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(screen.getByText("Code Quality")).toBeInTheDocument();
    });
  });

  it("shows 'Template export coming soon' for assignment templates", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockListRubrics.mockResolvedValueOnce(mockRubricsList);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      const comingSoonTexts = screen.getAllByText("Template export coming soon");
      expect(comingSoonTexts.length).toBeGreaterThan(0);
    });
  });

  it("filters courses by name", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockListRubrics.mockResolvedValueOnce(mockRubricsList);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Intro to CS")).toBeInTheDocument();
    });
    const filterInput = screen.getByPlaceholderText("Filter by name...");
    await user.type(filterInput, "Advanced");
    expect(screen.queryByText("Intro to CS")).not.toBeInTheDocument();
    expect(screen.getByText("Advanced Math")).toBeInTheDocument();
  });

  it("shows 'No courses found.' when filter matches nothing", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    mockListRubrics.mockResolvedValueOnce([]);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Intro to CS")).toBeInTheDocument();
    });
    await user.type(
      screen.getByPlaceholderText("Filter by name..."),
      "zzzzzzz"
    );
    expect(screen.getByText("No courses found.")).toBeInTheDocument();
  });

  it("shows error toast on loading failure", async () => {
    mockListCourses.mockRejectedValueOnce(new Error("Failed"));
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    mockListRubrics.mockResolvedValueOnce([]);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Failed");
    });
  });

  it("expands course to show Roster and Submissions sub-items", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    mockListRubrics.mockResolvedValueOnce([]);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Intro to CS")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Intro to CS"));
    expect(screen.getByText("Roster")).toBeInTheDocument();
    expect(screen.getByText("Submissions")).toBeInTheDocument();
  });

  it("calls onAddItem with roster binding when Add Roster clicked", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    mockListRubrics.mockResolvedValueOnce([]);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Intro to CS")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Intro to CS"));
    const addRosterBtn = screen.getByTitle("Add Roster to package");
    await user.click(addRosterBtn);
    expect(mockOnAddItem).toHaveBeenCalledWith({
      label: "Intro to CS \u2014 Roster.csv",
      datasetBinding: "ROSTER",
      bindingCourseId: 1,
    });
  });

  it("calls onAddItem with submissions binding when Add Submissions clicked", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    mockListRubrics.mockResolvedValueOnce([]);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Intro to CS")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Intro to CS"));
    const addSubsBtn = screen.getByTitle("Add Submissions to package");
    await user.click(addSubsBtn);
    expect(mockOnAddItem).toHaveBeenCalledWith({
      label: "Intro to CS \u2014 Submissions.csv",
      datasetBinding: "COURSE_SUBMISSIONS",
      bindingCourseId: 1,
    });
  });

  it("shows descriptive text about data sources", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    mockListRubrics.mockResolvedValueOnce([]);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(
        screen.getByText(/Add data sources to the explorer/)
      ).toBeInTheDocument();
    });
  });

  it("shows 'Snapshot taken on build' for active courses", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    mockListRubrics.mockResolvedValueOnce([]);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(screen.getByText("Snapshot taken on build")).toBeInTheDocument();
    });
  });

  it("shows 'Static — export ready' for archived courses", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    mockListRubrics.mockResolvedValueOnce([]);
    const DataCatalog = await loadComponent();
    render(<DataCatalog onAddItem={mockOnAddItem} />);
    await waitFor(() => {
      expect(
        screen.getByText(/Static .* export ready/)
      ).toBeInTheDocument();
    });
  });
});
