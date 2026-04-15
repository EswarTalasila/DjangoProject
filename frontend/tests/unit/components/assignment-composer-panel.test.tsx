import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AssignmentComposerPanel from "@/components/assignments/AssignmentComposerPanel";

const {
  mockAddAssignmentQuestion,
  mockAddAssignmentTeacherCriterion,
  mockListReusableAssignmentImages,
  mockUploadAssignmentQuestionImage,
  mockReuseAssignmentQuestionImage,
  mockDeleteAssignmentQuestionImage,
  mockGetRubric,
  mockToastSuccess,
  mockToastError,
} = vi.hoisted(() => ({
  mockAddAssignmentQuestion: vi.fn(),
  mockAddAssignmentTeacherCriterion: vi.fn(),
  mockListReusableAssignmentImages: vi.fn(),
  mockUploadAssignmentQuestionImage: vi.fn(),
  mockReuseAssignmentQuestionImage: vi.fn(),
  mockDeleteAssignmentQuestionImage: vi.fn(),
  mockGetRubric: vi.fn(),
  mockToastSuccess: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { success: mockToastSuccess, error: mockToastError },
}));

vi.mock("@/lib/assignment-api", () => ({
  addAssignmentQuestion: mockAddAssignmentQuestion,
  addAssignmentTeacherCriterion: mockAddAssignmentTeacherCriterion,
  listReusableAssignmentImages: mockListReusableAssignmentImages,
  uploadAssignmentQuestionImage: mockUploadAssignmentQuestionImage,
  reuseAssignmentQuestionImage: mockReuseAssignmentQuestionImage,
  deleteAssignmentQuestionImage: mockDeleteAssignmentQuestionImage,
}));

vi.mock("@/lib/rubric-api", () => ({
  getRubric: mockGetRubric,
}));

vi.mock("@/components/media/ImagePicker", () => ({
  default: ({
    onBrowse,
    onUpload,
    onSelect,
    onRemove,
  }: {
    onBrowse?: () => Promise<unknown[]>;
    onUpload?: (file: File) => Promise<unknown>;
    onSelect: (image: unknown) => Promise<void> | void;
    onRemove: () => Promise<void> | void;
  }) => (
    <div data-testid="mock-image-picker">
      <button
        type="button"
        onClick={async () => {
          const images = (await onBrowse?.()) ?? [];
          if (images[0]) {
            await onSelect(images[0]);
          }
        }}
      >
        reuse-image
      </button>
      <button
        type="button"
        onClick={async () => {
          if (!onUpload) return;
          await onUpload(new File(["demo"], "demo.png", { type: "image/png" }));
        }}
      >
        upload-image
      </button>
      <button type="button" onClick={() => void onRemove()}>
        remove-image
      </button>
    </div>
  ),
}));

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
        type: "SHORT_ANSWER",
        prompt: "Researcher prompt",
        maxPoints: 5,
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
        orderIndex: 0,
        origin: "TEMPLATE",
        lockedFromSource: true,
        sourceQuestionId: 201,
      },
      {
        questionId: 102,
        id: 102,
        type: "SHORT_ANSWER",
        prompt: "Teacher prompt",
        maxPoints: 2,
        autoGradable: false,
        graded: false,
        image: null,
        data: { trim: true, caseSensitive: false },
        selectAll: null,
        min: null,
        max: null,
        groupId: null,
        rubricId: null,
        gradingStrategy: "MANUAL",
        orderIndex: 1,
        origin: "TEACHER_ADDITION",
        lockedFromSource: false,
        sourceQuestionId: null,
      },
    ],
    ...overrides,
  };
}

describe("AssignmentComposerPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetRubric.mockResolvedValue({
      id: 51,
      title: "Locked Research Rubric",
      description: "Researcher-defined rubric context.",
      status: "ACTIVE",
      createdBy: 1,
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: "2026-01-01T00:00:00Z",
      criteria: [
        {
          id: 900,
          title: "Evidence quality",
          description: "Use source-backed reasoning.",
          orderIndex: 0,
          weight: 3,
          levels: [],
        },
      ],
    });
  });

  it("renders locked researcher content, rubric context, and teacher additions", async () => {
    render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={makeContent()}
        canCompose={true}
        onContentChange={vi.fn()}
      />,
    );

    expect(screen.getByText("Researcher Template")).toBeInTheDocument();
    expect(screen.getByText("Locked source content")).toBeInTheDocument();
    expect(screen.getByText("Teacher Additions")).toBeInTheDocument();
    expect(screen.getByText("Researcher prompt")).toBeInTheDocument();
    expect(screen.getByText("Teacher prompt")).toBeInTheDocument();
    expect(screen.getByText("Template rubric stays locked")).toBeInTheDocument();
    expect(await screen.findByText("Locked Research Rubric")).toBeInTheDocument();
    expect(screen.getByText("Evidence quality")).toBeInTheDocument();
  });

  it("adds a teacher-authored question and notifies the parent", async () => {
    const nextContent = makeContent({
      questions: [
        ...makeContent().questions,
        {
          questionId: 103,
          id: 103,
          type: "NUMBER_SCALE",
          prompt: "Teacher follow-up",
          maxPoints: 4,
          autoGradable: true,
          graded: false,
          image: null,
          data: { min: 1, max: 5, target: null },
          selectAll: null,
          min: 1,
          max: 5,
          groupId: null,
          rubricId: null,
          gradingStrategy: "AUTO",
          orderIndex: 2,
          origin: "TEACHER_ADDITION",
          lockedFromSource: false,
          sourceQuestionId: null,
        },
      ],
    });
    mockAddAssignmentQuestion.mockResolvedValue(nextContent);
    const onContentChange = vi.fn();
    const user = userEvent.setup();

    render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={makeContent()}
        canCompose={true}
        onContentChange={onContentChange}
      />,
    );

    await user.clear(screen.getByLabelText("Prompt"));
    await user.type(screen.getByLabelText("Prompt"), "Teacher follow-up");
    await user.clear(screen.getByLabelText("Points"));
    await user.type(screen.getByLabelText("Points"), "4");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() =>
      expect(mockAddAssignmentQuestion).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          type: "SHORT_ANSWER",
          prompt: "Teacher follow-up",
          maxPoints: 4,
        }),
      ),
    );
    expect(onContentChange).toHaveBeenCalledWith(nextContent);
  });

  it("adds a teacher-authored rubric criterion", async () => {
    const nextContent = makeContent({
      teacherCriteria: [
        {
          id: 701,
          title: "Local rigor",
          description: "Check for local classroom expectations.",
          weight: 2,
          orderIndex: 0,
        },
      ],
    });
    mockAddAssignmentTeacherCriterion.mockResolvedValue(nextContent);
    const onContentChange = vi.fn();
    const user = userEvent.setup();

    render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={makeContent()}
        canCompose={true}
        onContentChange={onContentChange}
      />,
    );

    await user.type(screen.getByLabelText("Criterion title"), "Local rigor");
    await user.type(
      screen.getByLabelText("Description"),
      "Check for local classroom expectations.",
    );
    await user.clear(screen.getByLabelText("Weight"));
    await user.type(screen.getByLabelText("Weight"), "2");
    await user.click(screen.getByRole("button", { name: /add criterion/i }));

    await waitFor(() =>
      expect(mockAddAssignmentTeacherCriterion).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          title: "Local rigor",
          description: "Check for local classroom expectations.",
          weight: 2,
        }),
      ),
    );
    expect(onContentChange).toHaveBeenCalledWith(nextContent);
  });

  it("reuses, uploads, and removes teacher-question images through the assignment APIs", async () => {
    mockListReusableAssignmentImages.mockResolvedValue([
      {
        id: "img-1",
        url: "/img.png",
        originalFilename: "img.png",
        mimeType: "image/png",
        sizeBytes: 1024,
      },
    ]);
    mockReuseAssignmentQuestionImage.mockResolvedValue({
      id: "img-1",
      url: "/img.png",
      originalFilename: "img.png",
      mimeType: "image/png",
      sizeBytes: 1024,
    });
    mockUploadAssignmentQuestionImage.mockResolvedValue({
      id: "img-2",
      url: "/img-2.png",
      originalFilename: "img-2.png",
      mimeType: "image/png",
      sizeBytes: 2048,
    });
    mockDeleteAssignmentQuestionImage.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={makeContent()}
        canCompose={true}
        onContentChange={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "reuse-image" }));
    await waitFor(() => expect(mockListReusableAssignmentImages).toHaveBeenCalledWith(1));
    await waitFor(() =>
      expect(mockReuseAssignmentQuestionImage).toHaveBeenCalledWith(1, 102, "img-1"),
    );

    await user.click(screen.getByRole("button", { name: "upload-image" }));
    await waitFor(() =>
      expect(mockUploadAssignmentQuestionImage).toHaveBeenCalledWith(
        1,
        102,
        expect.any(File),
      ),
    );

    await user.click(screen.getByRole("button", { name: "remove-image" }));
    await waitFor(() => expect(mockDeleteAssignmentQuestionImage).toHaveBeenCalledWith(1, 102));
  });
});
