import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListStaffUsers = vi.fn();
const mockListStudents = vi.fn();
const mockListCourses = vi.fn();
const mockIssuePasswordResetCode = vi.fn();
const mockToast = { success: vi.fn(), error: vi.fn() };

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("sonner", () => ({ toast: mockToast }));
  vi.doMock("@/lib/password-reset-api", () => ({
    listStaffUsers: mockListStaffUsers,
    listStudents: mockListStudents,
    issuePasswordResetCode: mockIssuePasswordResetCode,
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/components/codes/ResetCodeDialog", () => ({
    ResetCodeDialog: ({ open, code, targetName }: { open: boolean; code: string | null; targetName: string | null }) =>
      open ? <div data-testid="reset-dialog">Reset for {targetName}: {code}</div> : null,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/staff/StaffManagementView"
  );
  return imported.default;
}

async function renderStaffAndWait(props: {
  canResetStudents: boolean;
  canResetResearchers: boolean;
}) {
  const StaffManagementView = await loadComponent();
  render(<StaffManagementView {...props} />);
  await waitFor(() => {
    expect(
      screen.queryByText("Loading...")
    ).not.toBeInTheDocument();
  });
}

const mockStaff = [
  {
    id: 1,
    name: "Alice Teacher",
    username: "alice",
    email: "alice@school.edu",
    role: "TEACHER" as const,
  },
  {
    id: 2,
    name: "Bob Researcher",
    username: "bob",
    email: "bob@school.edu",
    role: "RESEARCHER" as const,
  },
];

const mockStudentsList = [
  {
    id: 3,
    name: "Charlie Student",
    username: "charlie",
    courses: [{ id: 1, name: "Biology 101" }],
  },
];

const mockCoursesList = [
  {
    id: 1,
    name: "Biology 101",
    studentCount: 20,
    assignmentIds: [],
    teacherId: 1,
    teacherName: "Alice Teacher",
    createdAt: "2026-01-15T00:00:00Z",
    status: "ACTIVE",
  },
];

describe("StaffManagementView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValueOnce(mockStudentsList);
    await renderStaffAndWait({
      canResetStudents: true,
      canResetResearchers: true,
    });

    expect(screen.getByText("User Management")).toBeInTheDocument();
    expect(
      screen.getByText("Manage accounts and issue password reset codes.")
    ).toBeInTheDocument();
  });

  it("shows loading state", async () => {
    mockListStaffUsers.mockReturnValueOnce(new Promise(() => {}));
    mockListCourses.mockReturnValueOnce(new Promise(() => {}));
    const StaffManagementView = await loadComponent();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows Teachers tab by default with teacher data", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const StaffManagementView = await loadComponent();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
      expect(screen.getByText("alice@school.edu")).toBeInTheDocument();
      expect(screen.getByText("@alice")).toBeInTheDocument();
    });
  });

  it("shows tabs including Students when canResetStudents", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValueOnce(mockStudentsList);
    await renderStaffAndWait({
      canResetStudents: true,
      canResetResearchers: false,
    });

    expect(screen.getByText("Teachers")).toBeInTheDocument();
    expect(screen.getByText("Students")).toBeInTheDocument();
  });

  it("shows tabs including Researchers when canResetResearchers", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    await renderStaffAndWait({
      canResetStudents: false,
      canResetResearchers: true,
    });

    expect(screen.getByText("Teachers")).toBeInTheDocument();
    expect(screen.getByText("Researchers")).toBeInTheDocument();
  });

  it("does not show Students tab when canResetStudents is false", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    await renderStaffAndWait({
      canResetStudents: false,
      canResetResearchers: false,
    });

    expect(screen.queryByText("Students")).not.toBeInTheDocument();
    expect(screen.queryByText("Researchers")).not.toBeInTheDocument();
  });

  it("shows Issue Reset buttons for teachers", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const StaffManagementView = await loadComponent();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Issue Reset")).toBeInTheDocument();
    });
  });

  it("shows error state on load failure", async () => {
    mockListStaffUsers.mockRejectedValueOnce(new Error("Network error"));
    mockListCourses.mockRejectedValueOnce(new Error("Network error"));
    const StaffManagementView = await loadComponent();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load staff data.")
      ).toBeInTheDocument();
    });
  });

  it("shows search input", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    await renderStaffAndWait({
      canResetStudents: false,
      canResetResearchers: false,
    });

    expect(
      screen.getByPlaceholderText("Search teachers...")
    ).toBeInTheDocument();
  });

  it("shows no teachers message when empty", async () => {
    mockListStaffUsers.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce([]);
    const StaffManagementView = await loadComponent();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("No teachers found.")).toBeInTheDocument();
    });
  });

  it("switches to Students tab and shows student data", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue(mockStudentsList);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("Charlie Student")).toBeInTheDocument();
      expect(screen.getByText("@charlie")).toBeInTheDocument();
      // Biology 101 appears in both course filter dropdown and student row
      expect(screen.getAllByText("Biology 101").length).toBeGreaterThanOrEqual(2);
    });
  });

  it("switches to Researchers tab and shows researcher data", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Researchers"));

    await waitFor(() => {
      expect(screen.getByText("Bob Researcher")).toBeInTheDocument();
      expect(screen.getByText("bob@school.edu")).toBeInTheDocument();
      expect(screen.getByText("@bob")).toBeInTheDocument();
    });
  });

  it("shows no researchers message when empty", async () => {
    mockListStaffUsers.mockResolvedValueOnce([
      { id: 1, name: "Alice Teacher", username: "alice", email: "alice@school.edu", role: "TEACHER" },
    ]);
    mockListCourses.mockResolvedValueOnce([]);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Researchers"));

    await waitFor(() => {
      expect(screen.getByText("No researchers found.")).toBeInTheDocument();
    });
  });

  it("shows no students message when empty", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue([]);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("No students found.")).toBeInTheDocument();
    });
  });

  it("filters teachers by search", async () => {
    const staffWithTwo = [
      { id: 1, name: "Alice Teacher", username: "alice", email: "alice@school.edu", role: "TEACHER" as const },
      { id: 10, name: "Zara Instructor", username: "zara", email: "zara@school.edu", role: "TEACHER" as const },
    ];
    mockListStaffUsers.mockResolvedValueOnce(staffWithTwo);
    mockListCourses.mockResolvedValueOnce([]);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
      expect(screen.getByText("Zara Instructor")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("Search teachers..."), "zara");

    await waitFor(() => {
      expect(screen.getByText("Zara Instructor")).toBeInTheDocument();
      expect(screen.queryByText("Alice Teacher")).not.toBeInTheDocument();
    });
  });

  it("filters researchers by search", async () => {
    const staffData = [
      { id: 1, name: "Alice Teacher", username: "alice", email: "alice@school.edu", role: "TEACHER" as const },
      { id: 2, name: "Bob Researcher", username: "bob", email: "bob@school.edu", role: "RESEARCHER" as const },
      { id: 5, name: "Eve Scientist", username: "eve", email: "eve@school.edu", role: "RESEARCHER" as const },
    ];
    mockListStaffUsers.mockResolvedValueOnce(staffData);
    mockListCourses.mockResolvedValueOnce([]);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Researchers"));

    await waitFor(() => {
      expect(screen.getByText("Bob Researcher")).toBeInTheDocument();
      expect(screen.getByText("Eve Scientist")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("Search researchers..."), "eve");

    await waitFor(() => {
      expect(screen.getByText("Eve Scientist")).toBeInTheDocument();
      expect(screen.queryByText("Bob Researcher")).not.toBeInTheDocument();
    });
  });

  it("filters students by search", async () => {
    const studentData = [
      { id: 3, name: "Charlie Student", username: "charlie", courses: [] },
      { id: 4, name: "Diana Learner", username: "diana", courses: [] },
    ];
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue(studentData);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("Charlie Student")).toBeInTheDocument();
      expect(screen.getByText("Diana Learner")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("Search students..."), "diana");

    await waitFor(() => {
      expect(screen.getByText("Diana Learner")).toBeInTheDocument();
      expect(screen.queryByText("Charlie Student")).not.toBeInTheDocument();
    });
  });

  it("shows course filter dropdown on students tab", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue(mockStudentsList);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    // Course filter should not be visible on teachers tab
    expect(screen.queryByText("All Courses")).not.toBeInTheDocument();

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("All Courses")).toBeInTheDocument();
    });
  });

  it("reloads students when course filter changes", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue(mockStudentsList);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("Charlie Student")).toBeInTheDocument();
    });

    // Select a course filter
    const select = screen.getByDisplayValue("All Courses") as HTMLSelectElement;
    await user.selectOptions(select, "1");

    await waitFor(() => {
      // listStudents should be called with courseId filter
      expect(mockListStudents).toHaveBeenCalledWith({ courseId: 1 });
    });
  });

  it("clears course filter back to null", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue(mockStudentsList);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("Charlie Student")).toBeInTheDocument();
    });

    const select = screen.getByDisplayValue("All Courses") as HTMLSelectElement;
    await user.selectOptions(select, "1");

    await waitFor(() => {
      expect(mockListStudents).toHaveBeenCalledWith({ courseId: 1 });
    });

    // Clear filter back to "All Courses"
    await user.selectOptions(select, "");

    await waitFor(() => {
      expect(mockListStudents).toHaveBeenCalledWith(undefined);
    });
  });

  it("handles Issue Reset success for teacher", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockIssuePasswordResetCode.mockResolvedValueOnce({
      resetCode: "ABC123",
      expiresAt: "2026-03-06T00:00:00Z",
    });
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Issue Reset"));

    await waitFor(() => {
      expect(mockIssuePasswordResetCode).toHaveBeenCalledWith(1);
      expect(screen.getByTestId("reset-dialog")).toBeInTheDocument();
      expect(screen.getByText(/Reset for Alice Teacher: ABC123/)).toBeInTheDocument();
    });
  });

  it("handles Issue Reset error with detail from API", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockIssuePasswordResetCode.mockRejectedValueOnce({
      response: { data: { detail: "User is locked" } },
    });
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Issue Reset"));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("User is locked");
    });
  });

  it("handles Issue Reset error with fallback message", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockIssuePasswordResetCode.mockRejectedValueOnce(new Error("network"));
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Issue Reset"));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Failed to issue reset code.");
    });
  });

  it("handles Issue Reset for researcher", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockIssuePasswordResetCode.mockResolvedValueOnce({
      resetCode: "XYZ789",
      expiresAt: "2026-03-06T00:00:00Z",
    });
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Researchers"));

    await waitFor(() => {
      expect(screen.getByText("Bob Researcher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Issue Reset"));

    await waitFor(() => {
      expect(mockIssuePasswordResetCode).toHaveBeenCalledWith(2);
    });
  });

  it("handles Issue Reset for student", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue(mockStudentsList);
    mockIssuePasswordResetCode.mockResolvedValueOnce({
      resetCode: "STU456",
      expiresAt: "2026-03-06T00:00:00Z",
    });
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("Charlie Student")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Issue Reset"));

    await waitFor(() => {
      expect(mockIssuePasswordResetCode).toHaveBeenCalledWith(3);
    });
  });

  it("shows dash for teacher with no email", async () => {
    mockListStaffUsers.mockResolvedValueOnce([
      { id: 1, name: "No Email Teacher", username: "noemail", email: null, role: "TEACHER" },
    ]);
    mockListCourses.mockResolvedValueOnce([]);
    const StaffManagementView = await loadComponent();
    render(
      <StaffManagementView
        canResetStudents={false}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("No Email Teacher")).toBeInTheDocument();
      expect(screen.getByText("-")).toBeInTheDocument();
    });
  });

  it("shows 'No courses' for student with no courses", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce([]);
    mockListStudents.mockResolvedValue([
      { id: 3, name: "Lonely Student", username: "lonely", courses: [] },
    ]);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("No courses")).toBeInTheDocument();
    });
  });

  it("clears search when switching tabs", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue(mockStudentsList);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    // Type search on teachers tab
    await user.type(screen.getByPlaceholderText("Search teachers..."), "xyz");

    // Switch to students tab - search should clear
    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      const input = screen.getByPlaceholderText("Search students...") as HTMLInputElement;
      expect(input.value).toBe("");
    });
  });

  it("shows error when student reload fails", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    // Initial load succeeds
    mockListStudents.mockResolvedValueOnce(mockStudentsList);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Alice Teacher")).toBeInTheDocument();
    });

    // Now make reload fail
    mockListStudents.mockRejectedValueOnce(new Error("Network error"));

    await user.click(screen.getByText("Students"));

    await waitFor(() => {
      expect(screen.getByText("Failed to load students.")).toBeInTheDocument();
    });
  });

  it("updates search placeholder based on active tab", async () => {
    mockListStaffUsers.mockResolvedValueOnce(mockStaff);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockListStudents.mockResolvedValue(mockStudentsList);
    const StaffManagementView = await loadComponent();
    const user = userEvent.setup();
    render(
      <StaffManagementView
        canResetStudents={true}
        canResetResearchers={true}
      />
    );

    expect(screen.getByPlaceholderText("Search teachers...")).toBeInTheDocument();

    await user.click(screen.getByText("Students"));
    expect(screen.getByPlaceholderText("Search students...")).toBeInTheDocument();

    await user.click(screen.getByText("Researchers"));
    expect(screen.getByPlaceholderText("Search researchers...")).toBeInTheDocument();
  });
});
