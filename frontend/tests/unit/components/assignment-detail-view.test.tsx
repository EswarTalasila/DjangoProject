import { render, screen, waitFor, within, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

/* ------------------------------------------------------------------ */
/*  Shared mock functions                                              */
/* ------------------------------------------------------------------ */
const mockPush = vi.fn();
const mockBack = vi.fn();
const mockGetAssignment = vi.fn();
const mockGetAssignmentTemplate = vi.fn();
const mockUpdateAssignment = vi.fn();
const mockArchiveAssignment = vi.fn();
const mockDeleteAssignment = vi.fn();
const mockListCourses = vi.fn();
const mockGetStudentSubmission = vi.fn();
const mockSaveDraft = vi.fn();
const mockSubmitFinal = vi.fn();
const mockToast = { success: vi.fn(), error: vi.fn() };

/* ------------------------------------------------------------------ */
/*  Fixtures                                                           */
/* ------------------------------------------------------------------ */

function makeAssignment(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    title: "Unit Test Assignment",
    assessmentId: 10,
    assessmentTitle: "Assessment Alpha",
    audienceType: "COURSE",
    courseId: 100,
    targetTeacherId: null,
    openAt: "2024-01-01T00:00:00.000Z",
    dueAt: "2025-12-31T23:59:59.000Z",
    status: "ACTIVE",
    ...overrides,
  };
}

function makeTemplate(overrides: Record<string, unknown> = {}) {
  return {
    id: 10,
    title: "Assessment Alpha",
    category: null,
    gradingMode: "AUTO",
    scoringPolicy: "STANDARD",
    rubricId: null,
    rubricAssessmentIds: [],
    questionGroups: [{ id: 1, name: "Group A", rubricId: null, orderIndex: 0 }],
    questions: [
      {
        questionId: 101,
        id: 101,
        type: "MULTIPLE_CHOICE",
        prompt: "Pick the correct answer",
        maxPoints: 5,
        autoGradable: true,
        graded: false,
        data: {
          choices: [
            { prompt: "Option A", score: 5 },
            { prompt: "Option B", score: 0 },
          ],
          selectAll: false,
        },
        selectAll: false,
        min: null,
        max: null,
        groupId: 1,
        rubricId: null,
        gradingStrategy: "AUTO",
      },
      {
        questionId: 102,
        id: 102,
        type: "SHORT_ANSWER",
        prompt: "Explain your reasoning",
        maxPoints: 10,
        autoGradable: false,
        graded: false,
        data: { trim: true, caseSensitive: false },
        selectAll: null,
        min: null,
        max: null,
        groupId: 1,
        rubricId: null,
        gradingStrategy: "MANUAL",
      },
      {
        questionId: 103,
        id: 103,
        type: "NUMBER_SCALE",
        prompt: "Rate 1-10",
        maxPoints: 3,
        autoGradable: true,
        graded: false,
        data: { min: 1, max: 10, target: 7 },
        selectAll: null,
        min: 1,
        max: 10,
        groupId: null,
        rubricId: null,
        gradingStrategy: "AUTO",
      },
    ],
    ...overrides,
  };
}

function makeCourses() {
  return [
    { id: 100, name: "Science 101", studentCount: 30, assignmentIds: [1], teacherId: 5, teacherName: "Prof X", createdAt: null, status: "ACTIVE" },
  ];
}

function makeSubmission(overrides: Record<string, unknown> = {}) {
  return {
    id: 500,
    assignmentId: 1,
    studentId: 42,
    teacherId: null,
    submittedAt: null,
    score: null,
    status: "IN_PROGRESS",
    answers: [
      { questionId: 101, type: "MULTIPLE_CHOICE", data: { selected: [0] } },
      { questionId: 102, type: "SHORT_ANSWER", data: { text: "draft text" } },
      { questionId: 103, type: "NUMBER_SCALE", data: { val: 5 } },
    ],
    ...overrides,
  };
}

/* ------------------------------------------------------------------ */
/*  Module mocking setup                                               */
/* ------------------------------------------------------------------ */

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush, back: mockBack }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({ id: "1" }),
  }));

  vi.doMock("next/link", () => ({
    default: ({ children, ...props }: any) => <a {...props}>{children}</a>,
  }));

  vi.doMock("sonner", () => ({ toast: mockToast }));

  vi.doMock("@/lib/assignment-api", () => ({
    getAssignment: mockGetAssignment,
    getAssignmentTemplate: mockGetAssignmentTemplate,
    updateAssignment: mockUpdateAssignment,
    archiveAssignment: mockArchiveAssignment,
    deleteAssignment: mockDeleteAssignment,
  }));

  vi.doMock("@/lib/assessment-api", () => ({}));

  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));

  vi.doMock("@/lib/submission-api", () => ({
    getStudentSubmission: mockGetStudentSubmission,
    saveDraft: mockSaveDraft,
    submitFinal: mockSubmitFinal,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assignments/AssignmentDetailView"
  );
  return imported.default;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function setupTeacherDefaults() {
  mockGetAssignment.mockResolvedValue(makeAssignment());
  mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
  mockListCourses.mockResolvedValue(makeCourses());
}

function setupStudentDefaults(submissionOverrides: Record<string, unknown> = {}) {
  mockGetAssignment.mockResolvedValue(makeAssignment());
  mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
  mockListCourses.mockResolvedValue(makeCourses());
  mockGetStudentSubmission.mockResolvedValue(makeSubmission(submissionOverrides));
}

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("AssignmentDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /* ---- Loading state ---- */
  describe("loading state", () => {
    it("shows a spinner while data is being fetched", async () => {
      // Never resolve so we stay in loading state
      mockGetAssignment.mockReturnValue(new Promise(() => {}));
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      // The Loader2 element is rendered inside a div with animate-spin
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  /* ---- Error state ---- */
  describe("error state", () => {
    it("shows error message when loading fails", async () => {
      mockGetAssignment.mockRejectedValue({
        response: { data: { detail: "Not found" }, status: 404 },
      });
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      expect(await screen.findByText("Not found")).toBeInTheDocument();
      expect(screen.getByText("Back to Assignments")).toBeInTheDocument();
    });

    it("shows fallback error message when no detail", async () => {
      mockGetAssignment.mockRejectedValue(new Error("boom"));
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      expect(
        await screen.findByText("Failed to load assignment.")
      ).toBeInTheDocument();
    });
  });

  /* ---- Teacher view: assignment data display ---- */
  describe("teacher view — data display", () => {
    it("renders assignment title, template, and course name", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      expect(await screen.findByText("Unit Test Assignment")).toBeInTheDocument();
      expect(screen.getAllByText(/Assessment Alpha/).length).toBeGreaterThan(0);
      expect(screen.getByText("Science 101")).toBeInTheDocument();
    });

    it("displays question count and total points", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("3")).toBeInTheDocument(); // 3 questions
      expect(screen.getByText("18")).toBeInTheDocument(); // 5+10+3 = 18 total points
    });

    it("shows assignment status badge", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    });

    it("falls back to Course # when course is not found", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment({ courseId: 999 }));
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue([]);
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      expect(await screen.findByText("Course #999")).toBeInTheDocument();
    });

    it("falls back to dash when no courseId", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment({ courseId: null }));
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue([]);
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      // '-' appears in Course row
      const courseSection = screen.getAllByText("-");
      expect(courseSection.length).toBeGreaterThan(0);
    });
  });

  /* ---- Teacher view: teacher template questions ---- */
  describe("teacher view — template questions (teacher mode)", () => {
    it("renders grouped questions with details", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      // Teacher template view label
      expect(screen.getByText("Teacher template view")).toBeInTheDocument();
      // Question prompts
      expect(screen.getByText(/Pick the correct answer/)).toBeInTheDocument();
      expect(screen.getByText(/Explain your reasoning/)).toBeInTheDocument();
      expect(screen.getByText(/Rate 1-10/)).toBeInTheDocument();
    });

    it("shows MC choice details", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("Option A")).toBeInTheDocument();
      expect(screen.getByText("Option B")).toBeInTheDocument();
      expect(screen.getByText("Single correct option")).toBeInTheDocument();
    });

    it("shows SHORT_ANSWER details (trim/caseSensitive)", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText(/Trim whitespace: On/)).toBeInTheDocument();
      expect(screen.getByText(/Case sensitive: Off/)).toBeInTheDocument();
    });

    it("shows NUMBER_SCALE range details", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText(/Range: 1 to 10/)).toBeInTheDocument();
    });

    it("shows group title and question count", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("Group A")).toBeInTheDocument();
      expect(screen.getByText("2 question(s)")).toBeInTheDocument();
    });

    it("shows ungrouped bucket for questions without groupId", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("Ungrouped")).toBeInTheDocument();
      expect(screen.getByText("1 question(s)")).toBeInTheDocument();
    });
  });

  /* ---- Teacher: manage panel ---- */
  describe("teacher view — manage panel", () => {
    it("renders manage panel when canMutate=true", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("Manage Assignment")).toBeInTheDocument();
      expect(screen.getByText("Save Changes")).toBeInTheDocument();
      expect(screen.getByText("Archive")).toBeInTheDocument();
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });

    it("does NOT render manage panel when canMutate=false", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="ADMIN" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.queryByText("Manage Assignment")).not.toBeInTheDocument();
    });

    it("has preview mode toggle buttons", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("Teacher View")).toBeInTheDocument();
      expect(screen.getByText("Student View")).toBeInTheDocument();
    });
  });

  /* ---- Teacher: update assignment ---- */
  describe("teacher — update assignment", () => {
    it("calls updateAssignment on save and toasts success", async () => {
      vi.useRealTimers();
      setupTeacherDefaults();
      mockUpdateAssignment.mockResolvedValue(
        makeAssignment({ title: "Updated Title" })
      );
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");

      await user.click(screen.getByText("Save Changes"));

      await waitFor(() => {
        expect(mockUpdateAssignment).toHaveBeenCalledOnce();
      });
      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalledWith("Assignment updated.");
      });
    });

    it("toasts error when title is empty", async () => {
      vi.useRealTimers();
      setupTeacherDefaults();
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      // Clear the title input
      const titleInput = screen.getByLabelText("Assignment Title");
      await user.clear(titleInput);
      await user.click(screen.getByText("Save Changes"));

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith(
          "Assignment title cannot be empty."
        );
      });
      expect(mockUpdateAssignment).not.toHaveBeenCalled();
    });

    it("toasts error on API failure during update", async () => {
      vi.useRealTimers();
      setupTeacherDefaults();
      mockUpdateAssignment.mockRejectedValue({
        response: { data: { detail: "Server error" } },
      });
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      await user.click(screen.getByText("Save Changes"));

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith("Server error");
      });
    });
  });

  /* ---- Teacher: archive ---- */
  describe("teacher — archive", () => {
    it("archive button is disabled when already archived", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment({ status: "ARCHIVED" }));
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      const archiveBtn = screen.getByRole("button", { name: "Archive" });
      expect(archiveBtn).toBeDisabled();
    });
  });

  /* ---- Teacher: delete ---- */
  describe("teacher — delete", () => {
    it("calls deleteAssignment and navigates on success", async () => {
      vi.useRealTimers();
      setupTeacherDefaults();
      mockDeleteAssignment.mockResolvedValue(undefined);
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");

      // Click the Delete button to open the dialog
      await user.click(screen.getByRole("button", { name: "Delete" }));
      // Click the confirm button in dialog
      const confirmBtn = await screen.findByRole("button", { name: "Confirm Delete" });
      await user.click(confirmBtn);

      await waitFor(() => {
        expect(mockDeleteAssignment).toHaveBeenCalledWith(1);
      });
      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalledWith("Assignment deleted.");
      });
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard/assignments");
      });
    });
  });

  /* ---- Teacher: preview mode switch to student ---- */
  describe("teacher — preview mode switch", () => {
    it("switches to student preview mode and shows question wizard", async () => {
      vi.useRealTimers();
      setupTeacherDefaults();
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      // Default: teacher view
      expect(screen.getByText("Teacher template view")).toBeInTheDocument();

      await user.click(screen.getByText("Student View"));
      expect(screen.getByText("Student preview")).toBeInTheDocument();
      // Student wizard shows question 1
      expect(screen.getByText("Question 1 of 3")).toBeInTheDocument();
    });

    it("teacher student preview has Submit (Preview) button", async () => {
      vi.useRealTimers();
      setupTeacherDefaults();
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      await user.click(screen.getByText("Student View"));
      expect(screen.getByText("Submit (Preview)")).toBeInTheDocument();
    });
  });

  /* ---- Student view: basic rendering ---- */
  describe("student view — basic rendering", () => {
    it("auto-selects student preview mode for STUDENT role", async () => {
      setupStudentDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("Student preview")).toBeInTheDocument();
    });

    it("shows status badge IN_PROGRESS for existing draft", async () => {
      setupStudentDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("In Progress")).toBeInTheDocument();
    });

    it("shows NOT_STARTED when no submission exists (404)", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockRejectedValue({
        response: { data: { detail: "No submission found" }, status: 404 },
      });
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("Not Started")).toBeInTheDocument();
    });

    it("hydrates answers from existing submission", async () => {
      vi.useRealTimers();
      setupStudentDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Unit Test Assignment");
      // First question is MC — the first choice should be checked
      const radio = screen.getByRole("radio", { name: "Option A" }) as HTMLInputElement;
      expect(radio.checked).toBe(true);
    });
  });

  /* ---- Student view: question navigation ---- */
  describe("student view — question navigation", () => {
    it("navigates forward and backward through questions", async () => {
      vi.useRealTimers();
      setupStudentDefaults();
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Unit Test Assignment");
      // Q1
      expect(screen.getByText("Question 1 of 3")).toBeInTheDocument();
      expect(screen.getByText(/Pick the correct answer/)).toBeInTheDocument();

      // Navigate next
      await user.click(screen.getByText("Next"));
      expect(screen.getByText("Question 2 of 3")).toBeInTheDocument();
      expect(screen.getByText(/Explain your reasoning/)).toBeInTheDocument();

      // Navigate next again
      await user.click(screen.getByText("Next"));
      expect(screen.getByText("Question 3 of 3")).toBeInTheDocument();
      expect(screen.getByText(/Rate 1-10/)).toBeInTheDocument();

      // Navigate back
      await user.click(screen.getByText("Previous"));
      expect(screen.getByText("Question 2 of 3")).toBeInTheDocument();
    });

    it("Previous is disabled on first question", async () => {
      setupStudentDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Question 1 of 3");
      expect(screen.getByText("Previous").closest("button")).toBeDisabled();
    });

    it("Next is disabled on last question", async () => {
      vi.useRealTimers();
      setupStudentDefaults();
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Question 1 of 3");
      await user.click(screen.getByText("Next"));
      await user.click(screen.getByText("Next"));
      expect(screen.getByText("Question 3 of 3")).toBeInTheDocument();
      expect(screen.getByText("Next").closest("button")).toBeDisabled();
    });
  });

  /* ---- Student view: answer interactions ---- */
  describe("student view — answer interactions", () => {
    it("selects a multiple choice option (radio)", async () => {
      vi.useRealTimers();
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockRejectedValue({
        response: { data: { detail: "No submission" }, status: 404 },
      });
      // Prevent draft save from firing
      mockSaveDraft.mockResolvedValue(makeSubmission());
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Question 1 of 3");
      const optionB = screen.getByRole("radio", { name: "Option B" });
      await user.click(optionB);
      expect((optionB as HTMLInputElement).checked).toBe(true);
    });

    it("types a short answer response", async () => {
      vi.useRealTimers();
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockRejectedValue({
        response: { data: { detail: "No submission" }, status: 404 },
      });
      mockSaveDraft.mockResolvedValue(makeSubmission());
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Question 1 of 3");

      // Navigate to Q2 (short answer)
      await user.click(screen.getByText("Next"));
      const textarea = screen.getByPlaceholderText("Student response appears here...");
      await user.type(textarea, "My reasoning");
      expect(textarea).toHaveValue("My reasoning");
    });
  });

  /* ---- Student view: submission flow ---- */
  describe("student view — final submission", () => {
    it("submits successfully and shows submitted review", async () => {
      vi.useRealTimers();
      setupStudentDefaults();
      const submittedResult = makeSubmission({
        status: "SUBMITTED",
        submittedAt: "2025-06-15T12:00:00.000Z",
      });
      mockSubmitFinal.mockResolvedValue(submittedResult);
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Question 1 of 3");

      // Click Submit
      await user.click(screen.getByRole("button", { name: "Submit" }));
      // Dialog appears — wait for Confirm Submit button
      const confirmBtn = await screen.findByRole("button", { name: "Confirm Submit" });
      // Confirm
      await user.click(confirmBtn);

      await waitFor(() => {
        expect(mockSubmitFinal).toHaveBeenCalledOnce();
      });
      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalledWith("Submission sent successfully.");
      });
      // Should show review stage
      await waitFor(() => {
        expect(screen.getByText("Submission Review")).toBeInTheDocument();
      });
    });

    it("shows error toast when submission fails", async () => {
      vi.useRealTimers();
      setupStudentDefaults();
      mockSubmitFinal.mockRejectedValue({
        response: { data: { detail: "Assignment is archived" } },
      });
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Question 1 of 3");
      await user.click(screen.getByRole("button", { name: "Submit" }));
      await user.click(await screen.findByRole("button", { name: "Confirm Submit" }));

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith("Assignment is archived");
      });
    });
  });

  /* ---- Student view: submitted state (hydrated from backend) ---- */
  describe("student view — already submitted", () => {
    it("shows submitted review when submission status is SUBMITTED", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockResolvedValue(
        makeSubmission({ status: "SUBMITTED", submittedAt: "2025-06-15T12:00:00.000Z" })
      );
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await waitFor(() => {
        expect(screen.getByText("Submission Review")).toBeInTheDocument();
      });
      // "Submitted" appears as both status badge and timestamp header — check at least one exists
      expect(screen.getAllByText("Submitted").length).toBeGreaterThan(0);
    });

    it("shows graded badge when status is GRADED", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockResolvedValue(
        makeSubmission({ status: "GRADED", submittedAt: "2025-06-15T12:00:00.000Z", score: 15 })
      );
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await waitFor(() => {
        expect(screen.getByText("Graded")).toBeInTheDocument();
      });
    });

    it("submit button is disabled when already submitted", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockResolvedValue(
        makeSubmission({ status: "SUBMITTED", submittedAt: "2025-06-15T12:00:00.000Z" })
      );
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await waitFor(() => {
        expect(screen.getByText("Submission Review")).toBeInTheDocument();
      });
      // Submit button shouldn't be present in submitted state (review mode)
      expect(screen.queryByRole("button", { name: "Submit" })).not.toBeInTheDocument();
    });
  });

  /* ---- Student view: archived / not-open banners ---- */
  describe("student view — archived and not-open banners", () => {
    it("shows archived banner for STUDENT when assignment is ARCHIVED", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment({ status: "ARCHIVED" }));
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockRejectedValue({
        response: { data: { detail: "No submission" }, status: 404 },
      });
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await waitFor(() => {
        expect(
          screen.getByText(/This assignment has been archived/)
        ).toBeInTheDocument();
      });
    });

    it("shows not-open banner for STUDENT when openAt is in the future", async () => {
      mockGetAssignment.mockResolvedValue(
        makeAssignment({ openAt: "2099-01-01T00:00:00.000Z" })
      );
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockRejectedValue({
        response: { data: { detail: "No submission" }, status: 404 },
      });
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await waitFor(() => {
        expect(screen.getByText(/This assignment opens at/)).toBeInTheDocument();
      });
    });

    it("does NOT show archived banner for non-student viewers", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment({ status: "ARCHIVED" }));
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      // Switch to student view to see the student preview
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      await user.click(screen.getByText("Student View"));
      expect(screen.queryByText(/This assignment has been archived/)).not.toBeInTheDocument();
    });
  });

  /* ---- Student view: draft save indicator ---- */
  describe("student view — draft autosave", () => {
    it("triggers draft save after answer change with debounce", async () => {
      vi.useRealTimers();
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockRejectedValue({
        response: { data: { detail: "No submission" }, status: 404 },
      });
      mockSaveDraft.mockResolvedValue(makeSubmission());
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Question 1 of 3");

      // Click a radio to trigger a change
      await user.click(screen.getByRole("radio", { name: "Option A" }));

      // Wait for debounced save (1s + buffer)
      await waitFor(
        () => {
          expect(mockSaveDraft).toHaveBeenCalled();
        },
        { timeout: 3000 }
      );
    });
  });

  /* ---- Submitted review: score display ---- */
  describe("submitted review — scores", () => {
    it("displays score when graded", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockResolvedValue(
        makeSubmission({ status: "GRADED", submittedAt: "2025-06-15T12:00:00.000Z", score: 15 })
      );
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await waitFor(() => {
        expect(screen.getByText("Score")).toBeInTheDocument();
      });
      expect(screen.getByText("15/18")).toBeInTheDocument();
    });

    it("displays auto points estimate when submitted but not graded", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockResolvedValue(
        makeSubmission({ status: "SUBMITTED", submittedAt: "2025-06-15T12:00:00.000Z" })
      );
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await waitFor(() => {
        expect(screen.getByText("Auto Points (Est.)")).toBeInTheDocument();
      });
    });

    it("shows answered count in submitted review", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockResolvedValue(
        makeSubmission({ status: "SUBMITTED", submittedAt: "2025-06-15T12:00:00.000Z" })
      );
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await waitFor(() => {
        expect(screen.getByText("3/3")).toBeInTheDocument();
      });
    });
  });

  /* ---- No questions ---- */
  describe("no questions template", () => {
    it("shows 'No questions' message when template has no questions", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(
        makeTemplate({ questions: [], questionGroups: [] })
      );
      mockListCourses.mockResolvedValue(makeCourses());
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(
        screen.getByText("No questions in this assignment template.")
      ).toBeInTheDocument();
    });
  });

  /* ---- Researcher view ---- */
  describe("researcher view", () => {
    it("renders in teacher mode by default for RESEARCHER", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="RESEARCHER" viewerId={99} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText("Teacher template view")).toBeInTheDocument();
    });
  });

  /* ---- Multiple choice: select-all variant ---- */
  describe("student view — select-all MC variant", () => {
    it("renders checkboxes for selectAll MC question", async () => {
      vi.useRealTimers();
      const template = makeTemplate();
      (template.questions as any)[0].data.selectAll = true;
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(template);
      mockListCourses.mockResolvedValue(makeCourses());
      mockGetStudentSubmission.mockRejectedValue({
        response: { data: { detail: "No submission" }, status: 404 },
      });
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />
      );
      await screen.findByText("Question 1 of 3");
      // checkboxes instead of radios
      expect(screen.getByText("Select all that apply.")).toBeInTheDocument();
      const checkboxes = screen.getAllByRole("checkbox");
      expect(checkboxes.length).toBe(2);
    });
  });

  /* ---- Teacher preview — Submit (Preview) button flow ---- */
  describe("teacher student preview — submit preview", () => {
    it("clicking Submit (Preview) switches to submitted review", async () => {
      vi.useRealTimers();
      setupTeacherDefaults();
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      await user.click(screen.getByText("Student View"));
      await user.click(screen.getByText("Submit (Preview)"));
      expect(screen.getByText("Submission Review")).toBeInTheDocument();
    });
  });

  /* ---- listCourses failure ---- */
  describe("course list fallback", () => {
    it("handles listCourses failure gracefully", async () => {
      mockGetAssignment.mockResolvedValue(makeAssignment());
      mockGetAssignmentTemplate.mockResolvedValue(makeTemplate());
      mockListCourses.mockRejectedValue(new Error("network"));
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      // Should still load, but show Course #100 fallback
      expect(await screen.findByText("Course #100")).toBeInTheDocument();
    });
  });

  /* ---- Question type formatting ---- */
  describe("question type labels", () => {
    it("formats question types correctly in teacher view", async () => {
      setupTeacherDefaults();
      const Component = await loadComponent();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      expect(screen.getByText(/Multiple Choice/)).toBeInTheDocument();
      expect(screen.getByText(/Short Answer/)).toBeInTheDocument();
      expect(screen.getByText(/Number Scale/)).toBeInTheDocument();
    });
  });

  /* ---- Open date validation ---- */
  describe("teacher — open date validation", () => {
    it("toasts error when open date is missing", async () => {
      vi.useRealTimers();
      setupTeacherDefaults();
      const Component = await loadComponent();
      const user = userEvent.setup();
      render(
        <Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />
      );
      await screen.findByText("Unit Test Assignment");
      // Clear the open-at input
      const openInput = screen.getByLabelText("Open At");
      await user.clear(openInput);
      await user.click(screen.getByText("Save Changes"));

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith(
          "Please provide a valid open date/time."
        );
      });
    });
  });
});
