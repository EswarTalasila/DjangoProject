import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockListByCourse = vi.fn();
const mockListForUser = vi.fn();
const mockArchiveAssignment = vi.fn();
const mockRestoreAssignment = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => "/dashboard/courses/1",
  }));
  vi.doMock("@/lib/assignment-api", () => ({
    listAssignmentsByCourse: mockListByCourse,
    listAssignmentsForUser: mockListForUser,
    archiveAssignment: mockArchiveAssignment,
    restoreAssignment: mockRestoreAssignment,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/courses/CourseAssignmentsTab"
  );
  return imported.default;
}

const mockAssignments = [
  {
    id: 1,
    title: "Homework 1",
    assignmentTemplateId: 10,
    assignmentTemplateTitle: "SEL Check-in",
    audienceType: "COURSE" as const,
    courseId: 1,
    targetTeacherId: null,
    openAt: "2026-02-01T00:00:00Z",
    dueAt: "2026-02-15T00:00:00Z",
    status: "ACTIVE" as const,
  },
  {
    id: 2,
    title: "Homework 2",
    assignmentTemplateId: 11,
    assignmentTemplateTitle: null,
    audienceType: "COURSE" as const,
    courseId: 1,
    targetTeacherId: null,
    openAt: null,
    dueAt: null,
    status: "ARCHIVED" as const,
  },
];

describe("CourseAssignmentsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", async () => {
    mockListByCourse.mockReturnValue(new Promise(() => {})); // never resolves
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    expect(screen.getByText("Loading assignments...")).toBeInTheDocument();
  });

  it("renders assignment table for TEACHER", async () => {
    mockListByCourse.mockResolvedValue([mockAssignments[0]]);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Homework 1")).toBeInTheDocument();
    });
    expect(screen.queryByText("Homework 2")).toBeNull();
    expect(screen.getByText("SEL Check-in")).toBeInTheDocument();
  });

  it("shows Create Assignment button for TEACHER", async () => {
    mockListByCourse.mockResolvedValue([]);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Create Assignment")).toBeInTheDocument();
    });
  });

  it("hides Create Assignment button for STUDENT", async () => {
    mockListForUser.mockResolvedValue([]);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="STUDENT" userId={5} />);
    await waitFor(() => {
      expect(screen.queryByText("Create Assignment")).toBeNull();
    });
  });

  it("hides Create Assignment button for RESEARCHER", async () => {
    mockListByCourse.mockResolvedValue([]);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="RESEARCHER" userId={5} />);
    await waitFor(() => {
      expect(screen.queryByText("Create Assignment")).toBeNull();
    });
  });

  it("shows empty state when no assignments", async () => {
    mockListByCourse.mockResolvedValue([]);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    await waitFor(() => {
      expect(
        screen.getByText(
          "No active assignments for this course. Turn on Show archived to review archived assignments or restore them after a course restore.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("shows archived restore guidance for teachers while archived rows are hidden", async () => {
    mockListByCourse.mockResolvedValue([mockAssignments[0]]);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(
        screen.getByText(
          "Restored courses keep previously archived assignments archived. Turn on Show archived to review and restore those assignments when needed.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("shows error state when API fails", async () => {
    mockListByCourse.mockRejectedValue(new Error("Network error"));
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    await waitFor(() => {
      expect(
        screen.getByText("Failed to load assignments for this course."),
      ).toBeInTheDocument();
    });
  });

  it("shows API error detail when available", async () => {
    mockListByCourse.mockRejectedValue({
      response: { data: { detail: "Custom API error" } },
    });
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Custom API error")).toBeInTheDocument();
    });
  });

  it("navigates to assignment detail on row click", async () => {
    const user = userEvent.setup();
    mockListByCourse.mockResolvedValue([mockAssignments[0]]);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Homework 1")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Homework 1"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/assignments/1");
  });

  it("navigates to create assignment page on button click", async () => {
    const user = userEvent.setup();
    mockListByCourse.mockResolvedValue([]);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Create Assignment")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Create Assignment"));
    expect(mockPush).toHaveBeenCalledWith(
      "/dashboard/assignments/new?courseId=1",
    );
  });

  it("uses listAssignmentsForUser for STUDENT and filters by courseId", async () => {
    const allAssignments = [
      ...mockAssignments,
      {
        id: 3,
        title: "Other course HW",
        assignmentTemplateId: 12,
        assignmentTemplateTitle: "Other",
        audienceType: "COURSE" as const,
        courseId: 99,
        targetTeacherId: null,
        openAt: null,
        dueAt: null,
        status: "ACTIVE" as const,
      },
    ];
    mockListForUser.mockResolvedValue(allAssignments);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="STUDENT" userId={5} />);
    await waitFor(() => {
      expect(screen.getByText("Homework 1")).toBeInTheDocument();
    });
    expect(screen.queryByText("Other course HW")).toBeNull();
  });

  it("formats dates correctly, showing - for null dates", async () => {
    mockListByCourse.mockResolvedValue(mockAssignments);
    const Component = await loadComponent();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);
    await waitFor(() => {
      expect(mockListByCourse).toHaveBeenCalledWith(1, undefined);
    });
  });

  it("requests archived assignments when show archived is enabled", async () => {
    mockListByCourse
      .mockResolvedValueOnce([mockAssignments[0]])
      .mockResolvedValueOnce(mockAssignments);
    const Component = await loadComponent();
    const user = userEvent.setup();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Homework 1")).toBeInTheDocument();
    });
    expect(screen.queryByText("Homework 2")).toBeNull();

    await user.click(screen.getByText("Show archived"));

    await waitFor(() => {
      expect(mockListByCourse).toHaveBeenLastCalledWith(1, { includeArchived: true });
    });
    expect(screen.getByText("Homework 2")).toBeInTheDocument();
    expect(screen.getByText("Assignment template unavailable")).toBeInTheDocument();
  });

  it("archives an active assignment from the table", async () => {
    mockListByCourse
      .mockResolvedValueOnce([mockAssignments[0]])
      .mockResolvedValueOnce([mockAssignments[0]]);
    mockArchiveAssignment.mockResolvedValue(undefined);
    const Component = await loadComponent();
    const user = userEvent.setup();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Archive" })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Archive" }));

    await waitFor(() => {
      expect(mockArchiveAssignment).toHaveBeenCalledWith(1);
    });
  });

  it("restores an archived assignment when visible", async () => {
    mockListByCourse
      .mockResolvedValueOnce(mockAssignments)
      .mockResolvedValueOnce(mockAssignments);
    mockRestoreAssignment.mockResolvedValue(undefined);
    const Component = await loadComponent();
    const user = userEvent.setup();
    render(<Component courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Show archived")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Show archived"));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Restore" })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Restore" }));

    await waitFor(() => {
      expect(mockRestoreAssignment).toHaveBeenCalledWith(2);
    });
  });
});
