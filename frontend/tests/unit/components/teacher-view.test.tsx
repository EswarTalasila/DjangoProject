import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListCourses = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/dashboard/views/TeacherView"
  );
  return imported.default;
}

async function renderTeacherViewAndWait() {
  const TeacherView = await loadComponent();
  render(<TeacherView />);
  await waitFor(() => {
    expect(mockListCourses).toHaveBeenCalledTimes(1);
  });
  await waitFor(() => {
    expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
  });
}

describe("TeacherView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders dashboard heading", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderTeacherViewAndWait();

    expect(screen.getByText("Teacher Dashboard")).toBeInTheDocument();
    expect(
      screen.getByText("Overview of your courses and students.")
    ).toBeInTheDocument();
  });

  it("shows stats bar labels", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderTeacherViewAndWait();

    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("Active Courses")).toBeInTheDocument();
    // "Assignments" appears in stats bar AND feature card
    const assignmentMatches = screen.getAllByText("Assignments");
    expect(assignmentMatches.length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty state message when no courses", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderTeacherViewAndWait();

    expect(
      screen.getByText(
        "No courses yet. Create your first course to get started."
      )
    ).toBeInTheDocument();
  });

  it("shows correct stats when courses exist", async () => {
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [1, 2, 3],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
      {
        id: 2,
        name: "Chemistry 201",
        studentCount: 15,
        assignmentIds: [4],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-02-01T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    await renderTeacherViewAndWait();

    expect(screen.getByText("40")).toBeInTheDocument(); // 25 + 15 students
    expect(screen.getByText("4")).toBeInTheDocument(); // 3 + 1 assignments
  });

  it("shows course summary text when courses exist", async () => {
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [1],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    await renderTeacherViewAndWait();

    expect(
      screen.getByText("1 course with 25 total students.")
    ).toBeInTheDocument();
  });

  it("renders navigation links", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderTeacherViewAndWait();

    expect(screen.getByText("Manage Courses")).toBeInTheDocument();
    expect(screen.getByText("Open Assignments")).toBeInTheDocument();
    expect(screen.getByText("Open Submissions")).toBeInTheDocument();
    expect(screen.getByText("Open Analytics")).toBeInTheDocument();
  });

  it("shows card titles for feature sections", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderTeacherViewAndWait();

    // Section headings in the grid cards
    const headings = screen.getAllByText("Assignments");
    expect(headings.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Submissions")).toBeInTheDocument();
    expect(screen.getByText("Visualizations")).toBeInTheDocument();
  });
});
