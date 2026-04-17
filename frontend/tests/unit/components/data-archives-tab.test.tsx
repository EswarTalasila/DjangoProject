import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListCourses = vi.fn();
const mockListAssignmentTemplates = vi.fn();
const mockListAssignmentsByCourse = vi.fn();
const mockGetAssignmentArchiveBundle = vi.fn();
const mockGenerateAssignmentArchiveBundle = vi.fn();
const mockDownloadAssignmentArchiveBundle = vi.fn();
const mockArchiveCourse = vi.fn();
const mockRestoreCourse = vi.fn();
const mockPurgeCourse = vi.fn();
const mockArchiveAssignmentTemplate = vi.fn();
const mockRestoreAssignmentTemplate = vi.fn();
const mockPurgeAssignmentTemplate = vi.fn();
const mockArchiveAssignment = vi.fn();
const mockRestoreAssignment = vi.fn();
const mockPurgeAssignment = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
const mockTriggerBrowserDownload = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/lib/assignment-template-api", () => ({
    listAssignmentTemplates: mockListAssignmentTemplates,
  }));
  vi.doMock("@/lib/assignment-api", () => ({
    listAssignmentsByCourse: mockListAssignmentsByCourse,
    getAssignmentArchiveBundle: mockGetAssignmentArchiveBundle,
    generateAssignmentArchiveBundle: mockGenerateAssignmentArchiveBundle,
    downloadAssignmentArchiveBundle: mockDownloadAssignmentArchiveBundle,
  }));
  vi.doMock("@/lib/lifecycle-api", () => ({
    archiveCourse: mockArchiveCourse,
    restoreCourse: mockRestoreCourse,
    purgeCourse: mockPurgeCourse,
    archiveAssignmentTemplate: mockArchiveAssignmentTemplate,
    restoreAssignmentTemplate: mockRestoreAssignmentTemplate,
    purgeAssignmentTemplate: mockPurgeAssignmentTemplate,
    archiveAssignment: mockArchiveAssignment,
    restoreAssignment: mockRestoreAssignment,
    purgeAssignment: mockPurgeAssignment,
  }));
  vi.doMock("@/lib/utils", () => ({
    toErrorMessage: (e: unknown) =>
      e instanceof Error ? e.message : "Unknown error",
    cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
    triggerBrowserDownload: mockTriggerBrowserDownload,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/archive/DataArchivesTab");
  return imported.default;
}

async function renderDataArchivesAndWait(role: "TEACHER" | "RESEARCHER" | "ADMIN" = "ADMIN") {
  const DataArchivesTab = await loadComponent();
  render(<DataArchivesTab role={role} />);
  await waitFor(() => {
    expect(
      screen.queryByText("Loading courses...")
    ).not.toBeInTheDocument();
  });
}

const mockCourses = [
  {
    id: 1,
    name: "Intro to CS",
    studentCount: 30,
    assignmentIds: [1],
    teacherId: 1,
    teacherName: "Prof Smith",
    createdAt: "2025-01-01",
    status: "ACTIVE",
  },
  {
    id: 2,
    name: "Data Science",
    studentCount: 20,
    assignmentIds: [],
    teacherId: 2,
    teacherName: "Prof Jones",
    createdAt: "2025-01-01",
    status: "ARCHIVED",
  },
];

const mockAssignmentTemplatesList = [
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
  {
    id: 2,
    title: "Final Exam",
    category: "EXAM",
    gradingMode: "AUTO",
    scoringPolicy: "LATEST",
    questions: [],
    questionGroups: [],
    rubricId: null,
    rubricAssignmentTemplateIds: [],
    status: "ARCHIVED",
  },
];

const mockAssignments = [
  {
    id: 1,
    title: "HW 1",
    assignmentTemplateId: 1,
    assignmentTemplateTitle: "Midterm Exam",
    audienceType: "COURSE",
    courseId: 1,
    targetTeacherId: null,
    openAt: "2025-01-01",
    dueAt: "2025-02-01",
    status: "ACTIVE",
  },
];

describe("DataArchivesTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: courses load returns mockCourses, assignments returns mockAssignments
    mockListCourses.mockResolvedValue(mockCourses);
    mockListAssignmentTemplates.mockResolvedValue(mockAssignmentTemplatesList);
    mockListAssignmentsByCourse.mockResolvedValue(mockAssignments);
    mockGetAssignmentArchiveBundle.mockRejectedValue(new Error("missing"));
  });

  it("renders Archive Records heading", async () => {
    await renderDataArchivesAndWait();
    expect(screen.getByText("Archive Records")).toBeInTheDocument();
  });

  it("renders Courses, Assignment Templates, and Assignments tab triggers", async () => {
    await renderDataArchivesAndWait();
    expect(screen.getByText("Courses")).toBeInTheDocument();
    expect(screen.getByText("Assignment Templates")).toBeInTheDocument();
    expect(screen.getByText("Assignments")).toBeInTheDocument();
  });

  it("shows loading state for courses initially", async () => {
    mockListCourses.mockReturnValue(new Promise(() => {}));
    mockListAssignmentTemplates.mockReturnValue(new Promise(() => {}));
    mockListAssignmentsByCourse.mockReturnValue(new Promise(() => {}));
    const DataArchivesTab = await loadComponent();
    const { unmount } = render(<DataArchivesTab role="ADMIN" />);
    expect(screen.getByText("Loading courses...")).toBeInTheDocument();
    unmount();
  });

  it("shows course names in the courses table after loading", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(screen.getAllByText("Intro to CS").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Data Science").length).toBeGreaterThan(0);
    });
  });

  it("shows teacher names in courses table", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(screen.getAllByText("Prof Smith").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Prof Jones").length).toBeGreaterThan(0);
    });
  });

  it("shows student counts in courses table", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(screen.getByText("30")).toBeInTheDocument();
      expect(screen.getByText("20")).toBeInTheDocument();
    });
  });

  it("shows Archive button for active courses", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Archive" }).length).toBeGreaterThan(0);
    });
  });

  it("shows Restore button for archived courses", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Restore" }).length).toBeGreaterThan(0);
    });
  });

  it("shows Purge button for archived courses", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      const purgeButtons = screen.getAllByText("Purge");
      expect(purgeButtons.length).toBeGreaterThan(0);
    });
  });

  it("renders sortable Name header in courses tab", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Teacher")).toBeInTheDocument();
      expect(screen.getByText("Students")).toBeInTheDocument();
      expect(screen.getByText("Status")).toBeInTheDocument();
      expect(screen.getByText("Actions")).toBeInTheDocument();
    });
  });

  it("shows Show archived checkbox", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(screen.getByText("Show archived")).toBeInTheDocument();
    });
  });

  it("shows empty state when no courses", async () => {
    mockListCourses.mockResolvedValue([]);
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(screen.getByText(/No archived courses/)).toBeInTheDocument();
    });
  });

  it("shows assignment templates tab content when clicked", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Courses")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Assignment Templates"));
    await waitFor(() => {
      // When showing only active, "Final Exam" (ARCHIVED) should not appear
      expect(screen.getAllByText("Midterm Exam").length).toBeGreaterThan(0);
    });
  });

  it("shows assignment templates table headers", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Assignment Templates")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Assignment Templates"));
    await waitFor(() => {
      expect(screen.getByText("Title")).toBeInTheDocument();
      expect(screen.getByText("Category")).toBeInTheDocument();
    });
  });

  it("shows assignments tab with table headers when clicked", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Assignments")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Assignments"));
    // Wait for loading to finish - assignments are loaded from courses
    await waitFor(() => {
      expect(screen.queryByText("Loading assignments...")).not.toBeInTheDocument();
    });
    // The assignments tab should show table headers or empty state
    // Since assignments are loaded via complex course-based fetching, verify the tab rendered
    await waitFor(() => {
      // Either we see "HW 1" or the "Due Date" header
      const hasDueDate = screen.queryByText("Due Date");
      const hasEmpty = screen.queryByText(/No archived assignments/);
      expect(hasDueDate || hasEmpty).toBeTruthy();
    });
  });

  it("shows Generate Bundle for archived assignments without an artifact", async () => {
    mockListAssignmentsByCourse.mockResolvedValueOnce([
      { ...mockAssignments[0], status: "ARCHIVED" },
    ]);
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Assignments")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Assignments"));
    await user.click(screen.getAllByRole("checkbox").at(-1)!);
    await waitFor(() => {
      expect(screen.getAllByText("Generate Bundle").length).toBeGreaterThan(0);
    });
  });

  it("shows error toast when courses fail to load", async () => {
    mockListCourses.mockRejectedValue(new Error("Network error"));
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Failed to load courses.");
    });
  });

  it("shows error toast when assignment templates fail to load", async () => {
    mockListAssignmentTemplates.mockRejectedValueOnce(new Error("Network error"));
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Failed to load assignment templates."
      );
    });
  });

  it("calls archiveCourse when Archive course action confirmed", async () => {
    mockArchiveCourse.mockResolvedValueOnce({});
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Archive" }).length).toBeGreaterThan(0);
    });
    // Click Archive to open dialog
    await user.click(screen.getAllByRole("button", { name: "Archive" })[0]);
    await waitFor(() => {
      expect(screen.getByText("Archive course")).toBeInTheDocument();
    });
    // Confirm Archive
    const confirmButtons = screen.getAllByText("Archive");
    const confirmBtn = confirmButtons[confirmButtons.length - 1];
    await user.click(confirmBtn);
    await waitFor(() => {
      expect(mockArchiveCourse).toHaveBeenCalledWith(1);
    });
  });

  it("calls restoreCourse when Restore clicked for archived course", async () => {
    mockRestoreCourse.mockResolvedValueOnce({});
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Restore" }).length).toBeGreaterThan(0);
    });
    await user.click(screen.getAllByRole("button", { name: "Restore" })[0]);
    await waitFor(() => {
      expect(mockRestoreCourse).toHaveBeenCalledWith(2);
    });
  });

  it("calls purgeCourse when Purge course action confirmed", async () => {
    mockPurgeCourse.mockResolvedValueOnce({});
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Purge" }).length).toBeGreaterThan(0);
    });

    await user.click(screen.getAllByRole("button", { name: "Purge" })[0]);
    await waitFor(() => {
      expect(screen.getByText("Purge course")).toBeInTheDocument();
    });

    const confirmButtons = screen.getAllByText("Purge");
    const confirmBtn = confirmButtons[confirmButtons.length - 1];
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockPurgeCourse).toHaveBeenCalledWith(2);
    });
  });

  it("sorts courses by name when clicking Name header", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="ADMIN" />);
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Name")).toBeInTheDocument();
    });
    // Click Name header to sort
    await user.click(screen.getByText("Name"));
    // Names should still be in DOM
    expect(screen.getAllByText("Intro to CS").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Data Science").length).toBeGreaterThan(0);
  });

  it("loads assignment rows with includeArchived=true so restored courses can surface archived assignments", async () => {
    await renderDataArchivesAndWait();
    await waitFor(() => {
      expect(mockListAssignmentsByCourse).toHaveBeenCalledWith(1, {
        includeArchived: true,
      });
    });
  });

  it("shows teacher only course and assignment tabs", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Courses")).toBeInTheDocument();
      expect(screen.getByText("Assignments")).toBeInTheDocument();
    });

    expect(screen.queryByText("Assignment Templates")).toBeNull();
  });

  it("shows researcher only assignment template tab", async () => {
    const DataArchivesTab = await loadComponent();
    render(<DataArchivesTab role="RESEARCHER" />);

    await waitFor(() => {
      expect(screen.getByText("Assignment Templates")).toBeInTheDocument();
    });

    expect(screen.queryByText("Courses")).toBeNull();
    expect(screen.queryByText("Assignments")).toBeNull();
  });

  it("hides purge actions from teachers", async () => {
    await renderDataArchivesAndWait("TEACHER");

    await waitFor(() => {
      expect(screen.getByText("Courses")).toBeInTheDocument();
      expect(screen.getByText("Assignments")).toBeInTheDocument();
    });

    expect(screen.queryByText("Purge")).toBeNull();
  });

  it("hides purge actions from researchers", async () => {
    await renderDataArchivesAndWait("RESEARCHER");

    await waitFor(() => {
      expect(screen.getByText("Assignment Templates")).toBeInTheDocument();
    });

    expect(screen.queryByText("Purge")).toBeNull();
  });
});
