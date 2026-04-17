import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListStudents = vi.fn();
const mockRemoveStudent = vi.fn();
const mockIssueReset = vi.fn();
const mockToastError = vi.fn();
const mockToastSuccess = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => "/dashboard/courses/1",
  }));
  vi.doMock("sonner", () => ({
    toast: {
      error: mockToastError,
      success: mockToastSuccess,
    },
  }));
  vi.doMock("@/lib/course-api", () => ({
    listStudentsInCourse: mockListStudents,
    removeStudentFromCourse: mockRemoveStudent,
  }));
  vi.doMock("@/lib/password-reset-api", () => ({
    issuePasswordResetCode: mockIssueReset,
  }));
  // Mock ResetCodeDialog
  vi.doMock("@/components/codes/ResetCodeDialog", () => ({
    ResetCodeDialog: ({
      open,
      code,
      targetName,
    }: {
      open: boolean;
      code: string | null;
      targetName: string | null;
    }) =>
      open ? (
        <div data-testid="reset-dialog">
          <span>{code}</span>
          <span>{targetName}</span>
        </div>
      ) : null,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/courses/CourseRosterTab");
  return imported.default;
}

const mockStudents = [
  {
    id: 10,
    name: "Alice Johnson",
    username: "alice.j",
    role: "STUDENT",
    consent: true,
    courseId: 1,
    enrolledAt: "2026-01-15T00:00:00Z",
  },
  {
    id: 11,
    name: "Bob Smith",
    username: "bob.s",
    role: "STUDENT",
    consent: false,
    courseId: 1,
    enrolledAt: null,
  },
];

describe("CourseRosterTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", async () => {
    mockListStudents.mockReturnValue(new Promise(() => {}));
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    expect(screen.getByText("Loading roster...")).toBeInTheDocument();
  });

  it("renders student table when students exist", async () => {
    mockListStudents.mockResolvedValue(mockStudents);
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    await waitFor(() => {
      expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    });
    expect(screen.getByText("alice.j")).toBeInTheDocument();
    expect(screen.getByText("Bob Smith")).toBeInTheDocument();
    expect(screen.getByText("bob.s")).toBeInTheDocument();
  });

  it("shows empty state when no students", async () => {
    mockListStudents.mockResolvedValue([]);
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    await waitFor(() => {
      expect(
        screen.getByText("No students enrolled in this course."),
      ).toBeInTheDocument();
    });
  });

  it("shows error state when API fails", async () => {
    mockListStudents.mockRejectedValue(new Error("fail"));
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    await waitFor(() => {
      expect(screen.getByText("Failed to load students.")).toBeInTheDocument();
    });
  });

  it("shows action buttons when canManage=true", async () => {
    mockListStudents.mockResolvedValue(mockStudents);
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    await waitFor(() => {
      expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Issue Reset")).toHaveLength(2);
    expect(screen.getAllByText("Remove")).toHaveLength(2);
  });

  it("hides action buttons when canManage=false", async () => {
    mockListStudents.mockResolvedValue(mockStudents);
    const Component = await loadComponent();
    render(<Component courseId={1} canManage={false} />);
    await waitFor(() => {
      expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    });
    expect(screen.queryByText("Issue Reset")).toBeNull();
    expect(screen.queryByText("Remove")).toBeNull();
  });

  it("shows - for null enrolledAt date", async () => {
    mockListStudents.mockResolvedValue(mockStudents);
    const Component = await loadComponent();
    render(<Component courseId={1} canManage={false} />);
    await waitFor(() => {
      expect(screen.getByText("Bob Smith")).toBeInTheDocument();
    });
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("handles remove student successfully", async () => {
    const user = userEvent.setup();
    mockListStudents.mockResolvedValue(mockStudents);
    mockRemoveStudent.mockResolvedValue(undefined);
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    await waitFor(() => {
      expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    });

    // Click the Remove button for Alice (first one)
    const removeButtons = screen.getAllByText("Remove");
    await user.click(removeButtons[0]);

    // AlertDialog should appear
    await waitFor(() => {
      expect(screen.getByText("Remove Student")).toBeInTheDocument();
    });

    // Click the confirm Remove button inside the dialog
    const confirmBtn = screen.getAllByText("Remove").find(
      (btn) =>
        btn.closest('[role="alertdialog"]') !== null,
    );
    expect(confirmBtn).toBeTruthy();
    await user.click(confirmBtn!);

    await waitFor(() => {
      expect(mockRemoveStudent).toHaveBeenCalledWith(1, 10);
    });
    expect(mockToastSuccess).toHaveBeenCalledWith(
      'Student "Alice Johnson" removed.',
    );
  });

  it("shows toast error when remove fails", async () => {
    const user = userEvent.setup();
    mockListStudents.mockResolvedValue(mockStudents);
    mockRemoveStudent.mockRejectedValue({
      response: { data: { detail: "Cannot remove" } },
    });
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    await waitFor(() => {
      expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    });

    const removeButtons = screen.getAllByText("Remove");
    await user.click(removeButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("Remove Student")).toBeInTheDocument();
    });

    const confirmBtn = screen.getAllByText("Remove").find(
      (btn) => btn.closest('[role="alertdialog"]') !== null,
    );
    await user.click(confirmBtn!);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Cannot remove");
    });
  });

  it("handles issue reset successfully", async () => {
    const user = userEvent.setup();
    mockListStudents.mockResolvedValue(mockStudents);
    mockIssueReset.mockResolvedValue({
      requestId: 1,
      targetUserId: 10,
      targetRole: "STUDENT",
      resetCode: "RESET-ABC",
      expiresAt: "2026-03-15T00:00:00Z",
    });
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    await waitFor(() => {
      expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    });

    const resetButtons = screen.getAllByText("Issue Reset");
    await user.click(resetButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId("reset-dialog")).toBeInTheDocument();
    });
    expect(screen.getByText("RESET-ABC")).toBeInTheDocument();
    // "Alice Johnson" appears in table + reset dialog, use getAllByText
    expect(screen.getAllByText("Alice Johnson").length).toBeGreaterThanOrEqual(2);
  });

  it("shows toast error when issue reset fails", async () => {
    const user = userEvent.setup();
    mockListStudents.mockResolvedValue(mockStudents);
    mockIssueReset.mockRejectedValue(new Error("fail"));
    const Component = await loadComponent();
    render(<Component courseId={1} canManage />);
    await waitFor(() => {
      expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    });

    const resetButtons = screen.getAllByText("Issue Reset");
    await user.click(resetButtons[0]);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Failed to issue reset code.",
      );
    });
  });
});
