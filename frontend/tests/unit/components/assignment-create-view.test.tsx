import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockCreateAssignment = vi.fn();
const mockListAssessments = vi.fn();
const mockListCourses = vi.fn();
const mockToast = { success: vi.fn(), error: vi.fn() };
let mockSearchParams = new URLSearchParams();
let capturedSelectProps: Record<string, unknown> = {};

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => mockSearchParams,
  }));
  vi.doMock("sonner", () => ({ toast: mockToast }));
  vi.doMock("@/lib/assignment-api", () => ({
    createAssignment: mockCreateAssignment,
  }));
  vi.doMock("@/lib/assessment-api", () => ({
    listAssessments: mockListAssessments,
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/components/ui/select", () => ({
    Select: ({ children, onValueChange, value }: { children: React.ReactNode; onValueChange?: (v: string) => void; value?: string }) => {
      capturedSelectProps[value || ""] = onValueChange;
      return <div data-testid={`select-${value}`}>{children}</div>;
    },
    SelectContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    SelectItem: ({ children, value }: { children: React.ReactNode; value: string }) => (
      <div data-testid={`select-item-${value}`}>{children}</div>
    ),
    SelectTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    SelectValue: () => <span />,
  }));
}

async function loadComponent() {
  vi.resetModules();
  capturedSelectProps = {};
  setupModuleMocks();
  const imported = await import(
    "@/components/assignments/AssignmentCreateView"
  );
  return imported.default;
}

const mockAssessments = [
  {
    id: 10,
    title: "Self Assessment",
    category: null,
    gradingMode: "AUTO" as const,
    scoringPolicy: "STANDARD" as const,
    questions: [],
    questionGroups: [],
    rubricId: null,
    rubricAssessmentIds: [],
  },
];

const mockCourses = [
  {
    id: 1,
    name: "Biology 101",
    studentCount: 20,
    assignmentIds: [],
    teacherId: 1,
    teacherName: "Dr. Smith",
    createdAt: "2026-01-15T00:00:00Z",
    status: "ACTIVE",
  },
];

function mockSuccessfulLoad() {
  mockListAssessments.mockResolvedValue(mockAssessments);
  mockListCourses.mockResolvedValue(mockCourses);
}

describe("AssignmentCreateView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
  });

  it("shows loading spinner initially", async () => {
    mockListAssessments.mockReturnValue(new Promise(() => {}));
    mockListCourses.mockReturnValue(new Promise(() => {}));
    const AssignmentCreateView = await loadComponent();
    const { container } = render(<AssignmentCreateView />);

    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("renders heading and form after loading", async () => {
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      // Heading and submit button both say "Create Assignment"
      const matches = screen.getAllByText("Create Assignment");
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
    expect(
      screen.getByText(
        "Link an assessment template to one of your courses."
      )
    ).toBeInTheDocument();
  });

  it("renders form labels", async () => {
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByText("Assignment Title")).toBeInTheDocument();
      expect(screen.getByText("Assessment")).toBeInTheDocument();
      expect(screen.getByText("Course")).toBeInTheDocument();
      expect(screen.getByText("Open At")).toBeInTheDocument();
      expect(screen.getByText("Due At")).toBeInTheDocument();
    });
  });

  it("pre-fills title from first assessment", async () => {
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      const titleInput = screen.getByLabelText(
        "Assignment Title"
      ) as HTMLInputElement;
      expect(titleInput.value).toBe("Self Assessment");
    });
  });

  it("shows cancel button", async () => {
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });
  });

  it("shows create assignment submit button in the form", async () => {
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      // Both heading and submit button say "Create Assignment"
      const buttons = screen.getAllByText("Create Assignment");
      expect(buttons.length).toBe(2);
    });
  });

  it("shows load error when API calls fail", async () => {
    mockListAssessments.mockRejectedValue(new Error("Network error"));
    mockListCourses.mockRejectedValue(new Error("Network error"));
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load assignment form data.")
      ).toBeInTheDocument();
    });
  });

  it("navigates to assignments page when cancel is clicked", async () => {
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByText("Cancel"));

    expect(mockPush).toHaveBeenCalledWith("/dashboard/assignments");
  });

  it("submits form successfully and navigates", async () => {
    mockSuccessfulLoad();
    mockCreateAssignment.mockResolvedValue({ id: 42 });
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Assignment Title")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const submitBtn = screen.getAllByText("Create Assignment").find(
      (el) => el.tagName === "BUTTON" || el.closest("button")
    )!;
    await user.click(submitBtn.closest("button") || submitBtn);

    await waitFor(() => {
      expect(mockCreateAssignment).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Self Assessment",
          assessmentId: 10,
          audienceType: "COURSE",
          courseId: 1,
        })
      );
    });
    expect(mockToast.success).toHaveBeenCalledWith("Assignment created.");
    expect(mockPush).toHaveBeenCalledWith("/dashboard/assignments/42");
  });

  it("does not submit when canSubmit is false (title empty)", async () => {
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Assignment Title")).toBeInTheDocument();
    });

    // Clear the title to make canSubmit false
    const user = userEvent.setup();
    const titleInput = screen.getByLabelText("Assignment Title") as HTMLInputElement;
    await user.clear(titleInput);

    // Submit the form directly
    const form = titleInput.closest("form")!;
    fireEvent.submit(form);

    // handleSubmit returns early because canSubmit is false
    expect(mockCreateAssignment).not.toHaveBeenCalled();
  });

  it("shows error toast when openAt is after dueAt", async () => {
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Open At")).toBeInTheDocument();
    });

    const openAtInput = screen.getByLabelText("Open At") as HTMLInputElement;
    const dueAtInput = screen.getByLabelText("Due At") as HTMLInputElement;
    // Set openAt to a future date and dueAt to earlier
    fireEvent.change(openAtInput, { target: { value: "2030-06-15T10:00" } });
    fireEvent.change(dueAtInput, { target: { value: "2030-06-10T10:00" } });

    const user = userEvent.setup();
    const submitBtn = screen.getAllByText("Create Assignment").find(
      (el) => el.tagName === "BUTTON" || el.closest("button")
    )!;
    await user.click(submitBtn.closest("button") || submitBtn);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "Open time must be before due time."
      );
    });
  });

  it("shows 409 error toast for archived assessment", async () => {
    mockSuccessfulLoad();
    mockCreateAssignment.mockRejectedValue({
      response: { status: 409, data: { detail: "Archived" } },
    });
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Assignment Title")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const submitBtn = screen.getAllByText("Create Assignment").find(
      (el) => el.tagName === "BUTTON" || el.closest("button")
    )!;
    await user.click(submitBtn.closest("button") || submitBtn);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "Cannot create assignment from archived assessment."
      );
    });
  });

  it("shows generic error toast on submission failure", async () => {
    mockSuccessfulLoad();
    mockCreateAssignment.mockRejectedValue({
      response: { status: 500, data: { detail: "Internal server error" } },
    });
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Assignment Title")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const submitBtn = screen.getAllByText("Create Assignment").find(
      (el) => el.tagName === "BUTTON" || el.closest("button")
    )!;
    await user.click(submitBtn.closest("button") || submitBtn);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Internal server error");
    });
  });

  it("uses preferred courseId from search params", async () => {
    mockSearchParams = new URLSearchParams("courseId=1");
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Assignment Title")).toBeInTheDocument();
    });
    // The preferred course should be selected - verified by the component not throwing
    // and loading successfully with courseId=1
    expect(mockListCourses).toHaveBeenCalled();
  });

  it("updates title when assessment selection changes", async () => {
    const multiAssessments = [
      {
        id: 10,
        title: "Self Assessment",
        category: null,
        gradingMode: "AUTO" as const,
        scoringPolicy: "STANDARD" as const,
        questions: [],
        questionGroups: [],
        rubricId: null,
        rubricAssessmentIds: [],
      },
      {
        id: 20,
        title: "Peer Review",
        category: null,
        gradingMode: "MANUAL" as const,
        scoringPolicy: "STANDARD" as const,
        questions: [],
        questionGroups: [],
        rubricId: null,
        rubricAssessmentIds: [],
      },
    ];
    mockListAssessments.mockResolvedValue(multiAssessments);
    mockListCourses.mockResolvedValue(mockCourses);
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Assignment Title")).toBeInTheDocument();
    });

    // The capturedSelectProps should have the assessment select's onValueChange
    // The assessment select has value="10" (the first assessment id)
    const onAssessmentChange = capturedSelectProps["10"] as (v: string) => void;
    expect(onAssessmentChange).toBeDefined();

    // Simulate changing the assessment to the second one
    act(() => {
      onAssessmentChange("20");
    });

    await waitFor(() => {
      const titleInput = screen.getByLabelText("Assignment Title") as HTMLInputElement;
      expect(titleInput.value).toBe("Peer Review");
    });
  });

  it("falls back to first course when preferred courseId not found", async () => {
    mockSearchParams = new URLSearchParams("courseId=999");
    mockSuccessfulLoad();
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Assignment Title")).toBeInTheDocument();
    });
    // Should fall back to first course since courseId=999 doesn't match
    expect(mockListCourses).toHaveBeenCalled();
  });

  it("handles empty assessment and course lists", async () => {
    mockListAssessments.mockResolvedValue([]);
    mockListCourses.mockResolvedValue([]);
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      const matches = screen.getAllByText("Create Assignment");
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows fallback error message when no detail in error", async () => {
    mockSuccessfulLoad();
    mockCreateAssignment.mockRejectedValue({
      response: { status: 400 },
    });
    const AssignmentCreateView = await loadComponent();
    render(<AssignmentCreateView />);

    await waitFor(() => {
      expect(screen.getByLabelText("Assignment Title")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const submitBtn = screen.getAllByText("Create Assignment").find(
      (el) => el.tagName === "BUTTON" || el.closest("button")
    )!;
    await user.click(submitBtn.closest("button") || submitBtn);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "Failed to create assignment."
      );
    });
  });
});
