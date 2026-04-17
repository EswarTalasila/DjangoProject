import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockBack = vi.fn();
const mockGetAssignment = vi.fn();
const mockGetAssignmentContent = vi.fn();
const mockUpdateAssignment = vi.fn();
const mockArchiveAssignment = vi.fn();
const mockRestoreAssignment = vi.fn();
const mockListCourses = vi.fn();
const mockGetStudentSubmission = vi.fn();
const mockSaveDraft = vi.fn();
const mockSubmitFinal = vi.fn();
const mockToast = { success: vi.fn(), error: vi.fn() };

function makeAssignment(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    title: "Unit Test Assignment",
    assignmentTemplateId: 10,
    assignmentTemplateTitle: "Assignment Template Alpha",
    audienceType: "COURSE",
    courseId: 100,
    targetTeacherId: null,
    openAt: "2026-01-01T00:00:00.000Z",
    dueAt: "2026-02-01T00:00:00.000Z",
    status: "ACTIVE",
    ...overrides,
  };
}

function makeContent(overrides: Record<string, unknown> = {}) {
  return {
    id: 10,
    title: "Assignment Template Alpha",
    assignmentId: 1,
    assignmentTemplateId: 10,
    assignmentTemplateTitle: "Assignment Template Alpha",
    category: "Exit Ticket",
    gradingMode: "HYBRID",
    scoringPolicy: "STANDARD",
    submissionMode: "DIGITAL",
    rubricId: 51,
    questionGroups: [{ id: 1, name: "Group A", rubricId: null, orderIndex: 0 }],
    teacherCriteria: [],
    questions: [
      {
        questionId: 101,
        id: 101,
        type: "MULTIPLE_CHOICE",
        prompt: "Pick the correct answer",
        maxPoints: 5,
        autoGradable: true,
        graded: false,
        image: null,
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
        orderIndex: 0,
        origin: "TEMPLATE",
        lockedFromSource: true,
        sourceQuestionId: 201,
      },
      {
        questionId: 102,
        id: 102,
        type: "SHORT_ANSWER",
        prompt: "Explain your reasoning",
        maxPoints: 10,
        autoGradable: false,
        graded: false,
        image: null,
        data: { trim: true, caseSensitive: false },
        selectAll: null,
        min: null,
        max: null,
        groupId: 1,
        rubricId: null,
        gradingStrategy: "MANUAL",
        orderIndex: 1,
        origin: "TEMPLATE",
        lockedFromSource: true,
        sourceQuestionId: 202,
      },
      {
        questionId: 103,
        id: 103,
        type: "NUMBER_SCALE",
        prompt: "Rate 1-10",
        maxPoints: 3,
        autoGradable: true,
        graded: false,
        image: null,
        data: { min: 1, max: 10, target: 7 },
        selectAll: null,
        min: 1,
        max: 10,
        groupId: null,
        rubricId: null,
        gradingStrategy: "AUTO",
        orderIndex: 2,
        origin: "TEMPLATE",
        lockedFromSource: true,
        sourceQuestionId: 203,
      },
    ],
    ...overrides,
  };
}

function makeCourses() {
  return [
    {
      id: 100,
      name: "Science 101",
      studentCount: 30,
      assignmentIds: [1],
      teacherId: 5,
      teacherName: "Prof X",
      createdAt: null,
      status: "ACTIVE",
    },
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
      { questionId: 101, type: "MULTIPLE_CHOICE", data: { selected: [0] }, score: null },
      { questionId: 102, type: "SHORT_ANSWER", data: { text: "draft text" }, score: null },
      { questionId: 103, type: "NUMBER_SCALE", data: { val: 5 }, score: null },
    ],
    ...overrides,
  };
}

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
    getAssignmentContent: mockGetAssignmentContent,
    updateAssignment: mockUpdateAssignment,
    archiveAssignment: mockArchiveAssignment,
    restoreAssignment: mockRestoreAssignment,
  }));

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
  const imported = await import("@/components/assignments/AssignmentDetailView");
  return imported.default;
}

function setupTeacherDefaults() {
  mockGetAssignment.mockResolvedValue(makeAssignment());
  mockGetAssignmentContent.mockResolvedValue(makeContent());
  mockListCourses.mockResolvedValue(makeCourses());
}

function setupStudentDefaults(submissionOverrides: Record<string, unknown> = {}) {
  mockGetAssignment.mockResolvedValue(makeAssignment());
  mockGetAssignmentContent.mockResolvedValue(makeContent());
  mockListCourses.mockResolvedValue(makeCourses());
  mockGetStudentSubmission.mockResolvedValue(makeSubmission(submissionOverrides));
}

describe("AssignmentDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a spinner while assignment data is loading", async () => {
    mockGetAssignment.mockReturnValue(new Promise(() => {}));
    const Component = await loadComponent();

    render(<Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />);

    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("shows an error message when the assignment load fails", async () => {
    mockGetAssignment.mockRejectedValue({
      response: { data: { detail: "Not found" }, status: 404 },
    });
    const Component = await loadComponent();

    render(<Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />);

    expect(await screen.findByText("Not found")).toBeInTheDocument();
    expect(screen.getByText("Back to Assignments")).toBeInTheDocument();
  });

  it("renders assignment metadata and a teacher-facing overview for teacher view", async () => {
    setupTeacherDefaults();
    const Component = await loadComponent();

    render(<Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />);

    expect(await screen.findByText("Unit Test Assignment")).toBeInTheDocument();
    expect(screen.getAllByText(/Assignment Template Alpha/).length).toBeGreaterThan(0);
    expect(screen.getByText("Science 101")).toBeInTheDocument();
    expect(screen.getByText("Teacher view")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Edit assignment" })).toHaveAttribute(
      "href",
      "/dashboard/assignments/1/edit",
    );
    expect(screen.getByText("Assignment questions")).toBeInTheDocument();
    expect(screen.getByText("Pick the correct answer")).toBeInTheDocument();
  });

  it("archives and restores the assignment through the manage panel", async () => {
    vi.useRealTimers();
    setupTeacherDefaults();
    mockArchiveAssignment.mockResolvedValue(makeAssignment({ status: "ARCHIVED" }));
    mockRestoreAssignment.mockResolvedValue(makeAssignment({ status: "ACTIVE" }));
    const Component = await loadComponent();
    const user = userEvent.setup();

    render(<Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />);

    await screen.findByText("Unit Test Assignment");
    await user.click(screen.getByRole("button", { name: "Archive" }));
    await user.click(await screen.findByRole("button", { name: "Confirm Archive" }));

    await waitFor(() => expect(mockArchiveAssignment).toHaveBeenCalledWith(1));
    await waitFor(() => expect(mockToast.success).toHaveBeenCalledWith("Assignment archived."));

    await user.click(await screen.findByRole("button", { name: "Confirm Restore" }));

    await waitFor(() => expect(mockRestoreAssignment).toHaveBeenCalledWith(1));
    await waitFor(() => expect(mockToast.success).toHaveBeenCalledWith("Assignment restored."));
  });

  it("switches teachers into student preview mode", async () => {
    vi.useRealTimers();
    setupTeacherDefaults();
    const Component = await loadComponent();
    const user = userEvent.setup();

    render(<Component assignmentId={1} canMutate={true} viewerRole="TEACHER" viewerId={5} />);

    await screen.findByText("Unit Test Assignment");
    await user.click(screen.getByText("Student View"));

    expect(screen.getByText("Student preview")).toBeInTheDocument();
    expect(screen.getByText("Question 1 of 3")).toBeInTheDocument();
    expect(screen.getByText("Submit (Preview)")).toBeInTheDocument();
  });

  it("hydrates the student preview from an existing submission", async () => {
    setupStudentDefaults();
    const Component = await loadComponent();

    render(<Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />);

    expect(await screen.findByText("Student preview")).toBeInTheDocument();
    expect(screen.getByText("In Progress")).toBeInTheDocument();
    const radio = screen.getAllByRole("radio")[0] as HTMLInputElement;
    expect(radio.checked).toBe(true);
  });

  it("falls back to not started when no student submission exists yet", async () => {
    mockGetAssignment.mockResolvedValue(makeAssignment());
    mockGetAssignmentContent.mockResolvedValue(makeContent());
    mockListCourses.mockResolvedValue(makeCourses());
    mockGetStudentSubmission.mockRejectedValue({
      response: { data: { detail: "Submission not found" }, status: 404 },
    });
    const Component = await loadComponent();

    render(<Component assignmentId={1} canMutate={false} viewerRole="STUDENT" viewerId={42} />);

    expect(await screen.findByText("Not Started")).toBeInTheDocument();
  });
});
