import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListCourses = vi.fn();
const mockJoinCourseByCode = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastInfo = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/lib/registration-code-api", () => ({
    joinCourseByCode: mockJoinCourseByCode,
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, info: mockToastInfo },
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

  it("renders join-course form and empty state when no courses", async () => {
    mockListCourses.mockResolvedValueOnce([]);

    const StudentView = await loadStudentView();
    render(<StudentView />);

    expect(screen.getByLabelText("Course Code")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Join" })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("No courses yet. Enter a course code above to get started.")).toBeInTheDocument();
    });
  });

  it("renders enrolled courses when they exist", async () => {
    mockListCourses.mockResolvedValueOnce([
      { id: 1, name: "Biology 101", studentCount: 20, assignmentIds: [] },
      { id: 2, name: "Chemistry 201", studentCount: 15, assignmentIds: [] },
    ]);

    const StudentView = await loadStudentView();
    render(<StudentView />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
      expect(screen.getByText("Chemistry 201")).toBeInTheDocument();
    });
  });

  it("submits code, shows success toast, and refreshes course list", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockJoinCourseByCode.mockResolvedValueOnce({
      message: "Invite redeemed",
      courseId: 5,
      alreadyEnrolled: false,
    });
    mockListCourses.mockResolvedValueOnce([
      { id: 5, name: "Physics 301", studentCount: 10, assignmentIds: [] },
    ]);

    const StudentView = await loadStudentView();
    render(<StudentView />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("No courses yet. Enter a course code above to get started.")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Course Code"), "VALID-CODE");
    await user.click(screen.getByRole("button", { name: "Join" }));

    await waitFor(() => {
      expect(mockJoinCourseByCode).toHaveBeenCalledWith("VALID-CODE");
      expect(mockToastSuccess).toHaveBeenCalledWith("Successfully joined the course!");
    });

    await waitFor(() => {
      expect(screen.getByText("Physics 301")).toBeInTheDocument();
    });
  });

  it("shows info toast for already-enrolled and refreshes course list", async () => {
    mockListCourses.mockResolvedValueOnce([
      { id: 5, name: "Physics 301", studentCount: 10, assignmentIds: [] },
    ]);
    mockJoinCourseByCode.mockResolvedValueOnce({
      message: "Already enrolled",
      courseId: 5,
      alreadyEnrolled: true,
    });
    mockListCourses.mockResolvedValueOnce([
      { id: 5, name: "Physics 301", studentCount: 10, assignmentIds: [] },
    ]);

    const StudentView = await loadStudentView();
    render(<StudentView />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Physics 301")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Course Code"), "DUPE-CODE");
    await user.click(screen.getByRole("button", { name: "Join" }));

    await waitFor(() => {
      expect(mockToastInfo).toHaveBeenCalledWith("You are already enrolled in this course.");
    });

    expect(mockListCourses).toHaveBeenCalledTimes(2);
  });

  it("shows inline error for invalid course code", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    mockJoinCourseByCode.mockRejectedValueOnce({
      response: { data: { detail: "Invalid or expired code." } },
    });

    const StudentView = await loadStudentView();
    render(<StudentView />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByLabelText("Course Code")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Course Code"), "BAD-CODE");
    await user.click(screen.getByRole("button", { name: "Join" }));

    await waitFor(() => {
      expect(screen.getByText("Invalid or expired code.")).toBeInTheDocument();
    });

    expect(mockToastSuccess).not.toHaveBeenCalled();
    expect(mockToastInfo).not.toHaveBeenCalled();
  });

  it("shows validation error when submitting empty code", async () => {
    mockListCourses.mockResolvedValueOnce([]);

    const StudentView = await loadStudentView();
    render(<StudentView />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByLabelText("Course Code")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Join" }));

    await waitFor(() => {
      expect(screen.getByText("Course code is required")).toBeInTheDocument();
    });

    expect(mockJoinCourseByCode).not.toHaveBeenCalled();
  });
});
