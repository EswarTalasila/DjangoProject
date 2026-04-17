import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockListCourses = vi.fn();
const mockCreateCourse = vi.fn();
const mockJoinCourseByCode = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
const mockToastInfo = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
    createCourse: mockCreateCourse,
  }));
  vi.doMock("@/lib/registration-code-api", () => ({
    joinCourseByCode: mockJoinCourseByCode,
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError, info: mockToastInfo },
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/courses/CoursesListView");
  return imported.default;
}

async function renderCoursesListAndWait(userRole: "TEACHER" | "STUDENT" | "RESEARCHER") {
  const CoursesListView = await loadComponent();
  render(<CoursesListView userRole={userRole} />);
  await waitFor(() => {
    expect(mockListCourses).toHaveBeenCalledTimes(1);
  });
  await waitFor(() => {
    expect(
      screen.queryByText("Loading courses...")
    ).not.toBeInTheDocument();
  });
}

describe("CoursesListView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading and loading state", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    expect(screen.getByText("Courses")).toBeInTheDocument();
    expect(screen.getByText("Loading courses...")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.queryByText("Loading courses...")
      ).not.toBeInTheDocument();
    });
  });

  it("shows teacher description text", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderCoursesListAndWait("TEACHER");

    expect(
      screen.getByText("Manage your courses and enrolled students.")
    ).toBeInTheDocument();
  });

  it("shows student description text", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderCoursesListAndWait("STUDENT");

    expect(
      screen.getByText("View your enrolled courses or join a new one.")
    ).toBeInTheDocument();
  });

  it("shows researcher description text", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderCoursesListAndWait("RESEARCHER");

    expect(
      screen.getByText("View courses and enrolled students.")
    ).toBeInTheDocument();
  });

  it("shows Create Course button for TEACHER", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderCoursesListAndWait("TEACHER");

    expect(screen.getByText("Create Course")).toBeInTheDocument();
  });

  it("does not show Create Course button for STUDENT", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading courses...")).not.toBeInTheDocument();
    });
    expect(screen.queryByText("Create Course")).not.toBeInTheDocument();
  });

  it("shows empty state for teacher with no courses", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText(
          "No courses yet. Create your first course to get started."
        )
      ).toBeInTheDocument();
    });
  });

  it("shows empty state for student with no courses", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("No courses found.")).toBeInTheDocument();
    });
  });

  it("renders course table with data for teacher", async () => {
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [1, 2],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
      expect(screen.getByText("Dr. Smith")).toBeInTheDocument();
      expect(screen.getByText("25")).toBeInTheDocument();
    });
  });

  it("hides teacher and student count columns for STUDENT role", async () => {
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });
    // Teacher and Students columns should not appear for students
    expect(screen.queryByText("Dr. Smith")).not.toBeInTheDocument();
  });

  it("shows join course card for STUDENT role", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderCoursesListAndWait("STUDENT");

    expect(screen.getByText("Join a Course")).toBeInTheDocument();
    expect(screen.getByText("Join")).toBeInTheDocument();
  });

  it("does not show join course card for TEACHER role", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderCoursesListAndWait("TEACHER");

    expect(screen.queryByText("Join a Course")).not.toBeInTheDocument();
  });

  it("shows error state when loading fails", async () => {
    mockListCourses.mockRejectedValueOnce(new Error("Network error"));
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load courses.")
      ).toBeInTheDocument();
    });
  });

  it("shows search input", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    await renderCoursesListAndWait("TEACHER");

    expect(
      screen.getByPlaceholderText("Search courses...")
    ).toBeInTheDocument();
  });

  it("filters courses by search query", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
      {
        id: 2,
        name: "Chemistry 201",
        studentCount: 20,
        assignmentIds: [],
        teacherId: 2,
        teacherName: "Dr. Jones",
        createdAt: "2026-01-10T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search courses...");
    await user.type(searchInput, "Biology");

    expect(screen.getByText("Biology 101")).toBeInTheDocument();
    expect(screen.queryByText("Chemistry 201")).not.toBeInTheDocument();
  });

  it("filters courses by teacher name", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
      {
        id: 2,
        name: "Chemistry 201",
        studentCount: 20,
        assignmentIds: [],
        teacherId: 2,
        teacherName: "Dr. Jones",
        createdAt: "2026-01-10T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search courses...");
    await user.type(searchInput, "Jones");

    expect(screen.queryByText("Biology 101")).not.toBeInTheDocument();
    expect(screen.getByText("Chemistry 201")).toBeInTheDocument();
  });

  it("shows 'No courses match your search.' when filter has no results", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search courses...");
    await user.type(searchInput, "xyznotfound");

    expect(screen.getByText("No courses match your search.")).toBeInTheDocument();
  });

  it("navigates to course detail on row click", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Biology 101"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/courses/1");
  });

  it("opens create dialog when Create Course is clicked", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValueOnce([]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading courses...")).not.toBeInTheDocument();
    });

    const createButtons = screen.getAllByText("Create Course");
    await user.click(createButtons[0]);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("e.g. Physics 101")).toBeInTheDocument();
    });
  });

  it("creates course successfully", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValue([]);
    mockCreateCourse.mockResolvedValueOnce({ id: 1, name: "Physics 101" });
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading courses...")).not.toBeInTheDocument();
    });

    await user.click(screen.getByText("Create Course"));

    await waitFor(() => {
      expect(screen.getByPlaceholderText("e.g. Physics 101")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("e.g. Physics 101"), "Physics 101");
    // Click the Create button inside the dialog
    const createButtons = screen.getAllByText("Create");
    const dialogCreate = createButtons.find(
      (el) => el.closest("[role='dialog']")
    );
    if (dialogCreate) {
      await user.click(dialogCreate);
    }

    await waitFor(() => {
      expect(mockCreateCourse).toHaveBeenCalledWith("Physics 101");
      expect(mockToastSuccess).toHaveBeenCalledWith('Course "Physics 101" created.');
    });
  });

  it("shows error toast when create course fails", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValue([]);
    mockCreateCourse.mockRejectedValueOnce(new Error("fail"));
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading courses...")).not.toBeInTheDocument();
    });

    await user.click(screen.getByText("Create Course"));

    await waitFor(() => {
      expect(screen.getByPlaceholderText("e.g. Physics 101")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("e.g. Physics 101"), "Test");
    const createButtons = screen.getAllByText("Create");
    const dialogCreate = createButtons.find(
      (el) => el.closest("[role='dialog']")
    );
    if (dialogCreate) {
      await user.click(dialogCreate);
    }

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Failed to create course.");
    });
  });

  it("does not create course when name is empty", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValue([]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading courses...")).not.toBeInTheDocument();
    });

    await user.click(screen.getByText("Create Course"));

    await waitFor(() => {
      expect(screen.getByPlaceholderText("e.g. Physics 101")).toBeInTheDocument();
    });

    // Create button should be disabled when input is empty
    const createButtons = screen.getAllByText("Create");
    const dialogCreate = createButtons.find(
      (el) => el.closest("[role='dialog']")
    );
    if (dialogCreate) {
      expect(dialogCreate.closest("button")).toBeDisabled();
    }
  });

  it("shows date in formatted format", async () => {
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "Biology 101",
        studentCount: 25,
        assignmentIds: [],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("Biology 101")).toBeInTheDocument();
    });

    // Component uses en-US locale: "Jan 15, 2026"
    // In test environment TZ may shift the date, so match flexibly
    expect(screen.getByText(/Jan 1[45], 2026/)).toBeInTheDocument();
  });

  it("shows '-' when createdAt is null", async () => {
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "No Date Course",
        studentCount: 0,
        assignmentIds: [],
        teacherId: 1,
        teacherName: "Dr. Smith",
        createdAt: null,
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText("No Date Course")).toBeInTheDocument();
    });

    // The date column should show '-'
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("shows '-' when teacherName is null", async () => {
    mockListCourses.mockResolvedValueOnce([
      {
        id: 1,
        name: "No Teacher Course",
        studentCount: 0,
        assignmentIds: [],
        teacherId: null,
        teacherName: null,
        createdAt: "2026-01-15T00:00:00Z",
        status: "ACTIVE",
      },
    ]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="RESEARCHER" />);

    await waitFor(() => {
      expect(screen.getByText("No Teacher Course")).toBeInTheDocument();
    });

    // '-' should appear for teacher name
    const dashes = screen.getAllByText("-");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it("joins a course successfully as a student", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValue([]);
    mockJoinCourseByCode.mockResolvedValueOnce({ alreadyEnrolled: false });
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("Join a Course")).toBeInTheDocument();
    });

    const codeInput = screen.getByPlaceholderText("Enter your course code");
    await user.type(codeInput, "ABC123");
    await user.click(screen.getByText("Join"));

    await waitFor(() => {
      expect(mockJoinCourseByCode).toHaveBeenCalledWith("ABC123");
      expect(mockToastSuccess).toHaveBeenCalledWith("Successfully joined the course!");
    });
  });

  it("shows already enrolled info toast when joining existing course", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValue([]);
    mockJoinCourseByCode.mockResolvedValueOnce({ alreadyEnrolled: true });
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("Join a Course")).toBeInTheDocument();
    });

    const codeInput = screen.getByPlaceholderText("Enter your course code");
    await user.type(codeInput, "ABC123");
    await user.click(screen.getByText("Join"));

    await waitFor(() => {
      expect(mockToastInfo).toHaveBeenCalledWith("You are already enrolled in this course.");
    });
  });

  it("shows error when join fails", async () => {
    const user = userEvent.setup();
    mockListCourses.mockResolvedValue([]);
    mockJoinCourseByCode.mockRejectedValueOnce({
      response: { data: { detail: "Invalid code" } },
    });
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("Join a Course")).toBeInTheDocument();
    });

    const codeInput = screen.getByPlaceholderText("Enter your course code");
    await user.type(codeInput, "BADCODE");
    await user.click(screen.getByText("Join"));

    await waitFor(() => {
      expect(screen.getByText("Invalid code")).toBeInTheDocument();
    });
  });

  it("shows 'No courses found.' empty state for student", async () => {
    mockListCourses.mockResolvedValueOnce([]);
    const CoursesListView = await loadComponent();
    render(<CoursesListView userRole="STUDENT" />);

    await waitFor(() => {
      expect(screen.getByText("No courses found.")).toBeInTheDocument();
    });
  });
});
