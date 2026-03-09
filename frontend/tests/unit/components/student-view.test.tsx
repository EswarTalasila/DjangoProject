import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListCourses = vi.fn();
const mockListMySubmissions = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/lib/submission-api", () => ({
    listMySubmissions: mockListMySubmissions,
  }));
}

async function loadStudentView() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/dashboard/views/StudentView");
  return imported.default;
}

describe("StudentView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders dashboard heading and stats bar", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockListMySubmissions.mockResolvedValueOnce({ results: [] });

    const StudentView = await loadStudentView();
    render(<StudentView />);

    expect(screen.getByText("Student Dashboard")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("In Progress")).toBeInTheDocument();
      expect(screen.getByText("Submitted")).toBeInTheDocument();
      expect(screen.getByText("Graded")).toBeInTheDocument();
    });
  });

  it("shows empty state when no courses enrolled", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockListMySubmissions.mockResolvedValueOnce({ results: [] });

    const StudentView = await loadStudentView();
    render(<StudentView />);

    await waitFor(() => {
      expect(
        screen.getByText("You are not enrolled in any courses yet.")
      ).toBeInTheDocument();
    });
  });

  it("shows course count when enrolled", async () => {
    mockListCourses.mockResolvedValueOnce([
      { id: 1, name: "Biology 101", studentCount: 20, assignmentIds: [] },
      { id: 2, name: "Physics 301", studentCount: 15, assignmentIds: [] },
    ]);
    mockListMySubmissions.mockResolvedValueOnce({ results: [] });

    const StudentView = await loadStudentView();
    render(<StudentView />);

    await waitFor(() => {
      expect(
        screen.getByText("You are enrolled in 2 courses.")
      ).toBeInTheDocument();
    });
  });

  it("shows submission stats breakdown", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockListMySubmissions.mockResolvedValueOnce({
      results: [
        { id: 1, assignmentId: 1, submittedAt: null, score: null, status: "IN_PROGRESS" },
        { id: 2, assignmentId: 2, submittedAt: "2026-03-01", score: null, status: "SUBMITTED" },
        { id: 3, assignmentId: 3, submittedAt: "2026-03-01", score: 85, status: "GRADED" },
        { id: 4, assignmentId: 4, submittedAt: null, score: null, status: "NOT_STARTED" },
      ],
    });

    const StudentView = await loadStudentView();
    render(<StudentView />);

    await waitFor(() => {
      expect(
        screen.getByText("2 in progress, 1 submitted, 1 graded.")
      ).toBeInTheDocument();
    });
  });

  it("shows empty submission state", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockListMySubmissions.mockResolvedValueOnce({ results: [] });

    const StudentView = await loadStudentView();
    render(<StudentView />);

    await waitFor(() => {
      expect(
        screen.getByText("No submissions yet. Start an assignment from your course page.")
      ).toBeInTheDocument();
    });
  });

  it("renders navigation links to courses and submissions", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockListMySubmissions.mockResolvedValueOnce({ results: [] });

    const StudentView = await loadStudentView();
    render(<StudentView />);

    await waitFor(() => {
      expect(screen.getByText("Open My Courses")).toBeInTheDocument();
      expect(screen.getByText("Open My Submissions")).toBeInTheDocument();
    });
  });

  it("handles array response from listMySubmissions", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockListMySubmissions.mockResolvedValueOnce([
      { id: 1, assignmentId: 1, submittedAt: null, score: null, status: "IN_PROGRESS" },
    ]);

    const StudentView = await loadStudentView();
    render(<StudentView />);

    await waitFor(() => {
      expect(
        screen.getByText("1 in progress, 0 submitted, 0 graded.")
      ).toBeInTheDocument();
    });
  });
});
