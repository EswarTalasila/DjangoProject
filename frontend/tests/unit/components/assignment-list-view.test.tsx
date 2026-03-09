import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockListCourses = vi.fn();
const mockListAssignmentsByCourse = vi.fn();
const mockListAssignmentsForUser = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/lib/assignment-api", () => ({
    listAssignmentsByCourse: mockListAssignmentsByCourse,
    listAssignmentsForUser: mockListAssignmentsForUser,
  }));
  vi.doMock("@/components/ui/select", () => ({
    Select: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    SelectContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    SelectItem: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    SelectTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    SelectValue: () => <span />,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assignments/AssignmentListView"
  );
  return imported.default;
}

async function renderAssignmentListAndWait(props: {
  role: "TEACHER" | "RESEARCHER" | "ADMIN";
  userId: string;
  canCreate: boolean;
}) {
  const AssignmentListView = await loadComponent();
  render(<AssignmentListView {...props} />);
  await waitFor(() => {
    expect(mockListCourses).toHaveBeenCalled();
  });
  await waitFor(() => {
    expect(
      screen.queryByText("Loading assignments...")
    ).not.toBeInTheDocument();
  });
}

const mockCourses = [
  {
    id: 1,
    name: "Biology 101",
    studentCount: 20,
    assignmentIds: [1],
    teacherId: 1,
    teacherName: "Dr. Smith",
    createdAt: "2026-01-15T00:00:00Z",
    status: "ACTIVE",
  },
];

const mockAssignments = [
  {
    id: 1,
    title: "Week 1 Check-In",
    assessmentId: 10,
    assessmentTitle: "Self Assessment",
    audienceType: "COURSE" as const,
    courseId: 1,
    targetTeacherId: null,
    openAt: "2026-02-01T08:00:00Z",
    dueAt: "2026-02-08T23:59:00Z",
    status: "ACTIVE" as const,
  },
];

describe("AssignmentListView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading and teacher description", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentsForUser.mockResolvedValueOnce(mockAssignments);
    await renderAssignmentListAndWait({
      role: "TEACHER",
      userId: "1",
      canCreate: true,
    });

    expect(screen.getByText("Assignments")).toBeInTheDocument();
    expect(
      screen.getByText("Manage assignments you created.")
    ).toBeInTheDocument();
  });

  it("shows non-teacher description for RESEARCHER", async () => {
    mockListCourses.mockResolvedValue(mockCourses);
    mockListAssignmentsByCourse.mockResolvedValue(mockAssignments);
    await renderAssignmentListAndWait({
      role: "RESEARCHER",
      userId: "2",
      canCreate: false,
    });

    expect(
      screen.getByText("Browse assignments by course.")
    ).toBeInTheDocument();
  });

  it("shows Create Assignment button when canCreate is true", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentsForUser.mockResolvedValueOnce([]);
    await renderAssignmentListAndWait({
      role: "TEACHER",
      userId: "1",
      canCreate: true,
    });

    expect(screen.getByText("Create Assignment")).toBeInTheDocument();
  });

  it("does not show Create Assignment button when canCreate is false", async () => {
    mockListCourses.mockResolvedValue(mockCourses);
    mockListAssignmentsByCourse.mockResolvedValue([]);
    await renderAssignmentListAndWait({
      role: "RESEARCHER",
      userId: "2",
      canCreate: false,
    });

    expect(screen.queryByText("Create Assignment")).not.toBeInTheDocument();
  });

  it("shows loading state", async () => {
    mockListCourses.mockReturnValueOnce(new Promise(() => {}));
    const AssignmentListView = await loadComponent();
    render(
      <AssignmentListView role="TEACHER" userId="1" canCreate={true} />
    );

    expect(
      screen.getByText("Loading assignments...")
    ).toBeInTheDocument();
  });

  it("shows empty state when no assignments", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentsForUser.mockResolvedValueOnce([]);
    await renderAssignmentListAndWait({
      role: "TEACHER",
      userId: "1",
      canCreate: true,
    });

    expect(screen.getByText("No assignments found.")).toBeInTheDocument();
  });

  it("renders assignment table with data", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentsForUser.mockResolvedValueOnce(mockAssignments);
    await renderAssignmentListAndWait({
      role: "TEACHER",
      userId: "1",
      canCreate: true,
    });

    expect(screen.getByText("Week 1 Check-In")).toBeInTheDocument();
    expect(screen.getByText("Self Assessment")).toBeInTheDocument();
    expect(screen.getByText("Biology 101")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });

  it("shows error state on failure", async () => {
    mockListCourses.mockRejectedValueOnce(new Error("Network error"));
    await renderAssignmentListAndWait({
      role: "TEACHER",
      userId: "1",
      canCreate: true,
    });
    expect(screen.getByText("Failed to load assignments.")).toBeInTheDocument();
  });

  it("shows search input", async () => {
    mockListCourses.mockResolvedValueOnce(mockCourses);
    mockListAssignmentsForUser.mockResolvedValueOnce([]);
    await renderAssignmentListAndWait({
      role: "TEACHER",
      userId: "1",
      canCreate: true,
    });

    expect(
      screen.getByPlaceholderText("Search assignments...")
    ).toBeInTheDocument();
  });
});
