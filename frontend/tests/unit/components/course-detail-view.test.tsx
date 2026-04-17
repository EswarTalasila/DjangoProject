import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockReplace = vi.fn();
const mockGetCourse = vi.fn();
const mockUpdateCourse = vi.fn();
const mockToast = { success: vi.fn(), error: vi.fn() };

let mockSearchParams = new URLSearchParams();

function setupModuleMocks() {
  vi.doMock("sonner", () => ({ toast: mockToast }));
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush, replace: mockReplace }),
    useSearchParams: () => mockSearchParams,
    usePathname: () => "/dashboard/courses/1",
  }));
  vi.doMock("@/lib/course-api", () => ({
    getCourse: mockGetCourse,
    updateCourse: mockUpdateCourse,
  }));
  // Mock the sub-tab components to avoid their own API calls
  vi.doMock("@/components/courses/CourseRosterTab", () => ({
    default: () => <div data-testid="roster-tab">Roster Tab</div>,
  }));
  vi.doMock("@/components/courses/CourseRegistrationTab", () => ({
    default: () => <div data-testid="registration-tab">Registration Tab</div>,
  }));
  vi.doMock("@/components/courses/CourseAssignmentsTab", () => ({
    default: () => <div data-testid="assignments-tab">Assignments Tab</div>,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/courses/CourseDetailView");
  return imported.default;
}

const mockCourse = {
  id: 1,
  name: "Biology 101",
  studentCount: 25,
  assignmentIds: [1, 2],
  teacherId: 1,
  teacherName: "Dr. Smith",
  createdAt: "2026-01-15T00:00:00Z",
  status: "ACTIVE" as const,
};

describe("CourseDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
  });

  it("shows loading state initially", async () => {
    mockGetCourse.mockReturnValueOnce(new Promise(() => {})); // never resolves
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    expect(screen.getByText("Loading course...")).toBeInTheDocument();
  });

  it("renders course name after loading", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });
  });

  it("shows teacher info", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText(/Teacher: Dr. Smith/)).toBeInTheDocument();
    });
  });

  it("shows back to courses link", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Back to Courses")).toBeInTheDocument();
    });
  });

  it("shows all tabs for TEACHER", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Roster")).toBeInTheDocument();
      expect(screen.getByText("Registration")).toBeInTheDocument();
      expect(screen.getByText("Assignments")).toBeInTheDocument();
    });
  });

  it("shows only assignments tab for STUDENT", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="STUDENT" userId={2} />);

    await waitFor(() => {
      expect(screen.getByText("Assignments")).toBeInTheDocument();
    });
    expect(screen.queryByText("Roster")).not.toBeInTheDocument();
    expect(screen.queryByText("Registration")).not.toBeInTheDocument();
  });

  it("shows only roster tab for RESEARCHER", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="RESEARCHER" userId={3} />);

    await waitFor(() => {
      expect(screen.getByText("Roster")).toBeInTheDocument();
    });
    expect(screen.queryByText("Registration")).not.toBeInTheDocument();
    expect(screen.queryByText("Assignments")).not.toBeInTheDocument();
  });

  it("shows edit name button for TEACHER", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Edit course name")).toBeInTheDocument();
    });
  });

  it("does not show edit name button for STUDENT", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="STUDENT" userId={2} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });
    expect(screen.queryByLabelText("Edit course name")).not.toBeInTheDocument();
  });

  it("shows error state on load failure", async () => {
    mockGetCourse.mockRejectedValueOnce(new Error("Network error"));
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load course details.")
      ).toBeInTheDocument();
    });
  });

  it("renders default roster tab content for TEACHER", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId("roster-tab")).toBeInTheDocument();
    });
  });

  it("switches tabs when a tab button is clicked", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Assignments"));
    expect(mockReplace).toHaveBeenCalledWith(
      expect.stringContaining("tab=assignments")
    );
  });

  it("enters edit mode, types a new name, and saves successfully", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    mockUpdateCourse.mockResolvedValueOnce({
      ...mockCourse,
      name: "Biology 202",
    });
    const CourseDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    // Click the edit pencil
    await user.click(screen.getByLabelText("Edit course name"));

    // Input should appear with the current name
    const input = screen.getByDisplayValue("Biology 101");
    expect(input).toBeInTheDocument();

    // Clear and type a new name
    await user.clear(input);
    await user.type(input, "Biology 202");

    // Click save
    await user.click(screen.getByLabelText("Save name"));

    await waitFor(() => {
      expect(mockUpdateCourse).toHaveBeenCalledWith(1, "Biology 202");
    });
    expect(mockToast.success).toHaveBeenCalledWith("Course name updated.");
  });

  it("shows error toast when save name fails", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    mockUpdateCourse.mockRejectedValueOnce({
      response: { data: { detail: "Name too long" } },
    });
    const CourseDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Edit course name"));
    const input = screen.getByDisplayValue("Biology 101");
    await user.clear(input);
    await user.type(input, "New Name");
    await user.click(screen.getByLabelText("Save name"));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Name too long");
    });
  });

  it("cancels editing name when cancel button is clicked", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Edit course name"));
    expect(screen.getByDisplayValue("Biology 101")).toBeInTheDocument();

    await user.click(screen.getByLabelText("Cancel editing"));

    // Should be back to display mode
    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });
    expect(screen.queryByLabelText("Save name")).not.toBeInTheDocument();
  });

  it("saves name on Enter key press", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    mockUpdateCourse.mockResolvedValueOnce({
      ...mockCourse,
      name: "Physics 101",
    });
    const CourseDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Edit course name"));
    const input = screen.getByDisplayValue("Biology 101");
    await user.clear(input);
    await user.type(input, "Physics 101");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(mockUpdateCourse).toHaveBeenCalledWith(1, "Physics 101");
    });
  });

  it("cancels editing on Escape key press", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Edit course name"));
    expect(screen.getByDisplayValue("Biology 101")).toBeInTheDocument();

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(screen.queryByLabelText("Save name")).not.toBeInTheDocument();
    });
  });

  it("renders assignments tab for STUDENT by default", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="STUDENT" userId={2} />);

    await waitFor(() => {
      expect(screen.getByTestId("assignments-tab")).toBeInTheDocument();
    });
  });

  it("renders roster tab for RESEARCHER by default", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    const CourseDetailView = await loadComponent();
    render(<CourseDetailView courseId={1} userRole="RESEARCHER" userId={3} />);

    await waitFor(() => {
      expect(screen.getByTestId("roster-tab")).toBeInTheDocument();
    });
  });

  it("shows save error fallback when no detail in error response", async () => {
    mockGetCourse.mockResolvedValueOnce(mockCourse);
    mockUpdateCourse.mockRejectedValueOnce(new Error("generic"));
    const CourseDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<CourseDetailView courseId={1} userRole="TEACHER" userId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Edit course name"));
    const input = screen.getByDisplayValue("Biology 101");
    await user.clear(input);
    await user.type(input, "New");
    await user.click(screen.getByLabelText("Save name"));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "Failed to update course name."
      );
    });
  });
});
