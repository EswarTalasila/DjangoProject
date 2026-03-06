import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockGetAssessment = vi.fn();
const mockDeleteAssessment = vi.fn();
const mockUpdateAssessment = vi.fn();
const mockListRubrics = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("next/link", () => ({
    default: ({ children, ...props }: any) => (
      <a {...props}>{children}</a>
    ),
  }));
  vi.doMock("@/lib/assessment-api", () => ({
    getAssessment: mockGetAssessment,
    deleteAssessment: mockDeleteAssessment,
    updateAssessment: mockUpdateAssessment,
  }));
  vi.doMock("@/lib/rubric-api", () => ({
    listRubrics: mockListRubrics,
    getRubric: vi.fn(),
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
  vi.doMock("@/components/assessments/RubricTemplatePreviewDrawer", () => ({
    default: ({ open }: any) =>
      open ? <div data-testid="rubric-preview-drawer">Rubric Preview</div> : null,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assessments/AssessmentDetailView"
  );
  return imported.default;
}

const mockAssessment = {
  id: 1,
  title: "Week 1 Quiz",
  category: "Quiz",
  gradingMode: "AUTO" as const,
  scoringPolicy: "STANDARD" as const,
  questions: [
    {
      questionId: 1,
      id: 1,
      type: "MULTIPLE_CHOICE" as const,
      prompt: "What is 2+2?",
      maxPoints: 10,
      autoGradable: true,
      graded: false,
      data: {
        choices: [
          { prompt: "3", score: 0 },
          { prompt: "4", score: 10 },
        ],
        selectAll: false,
      },
      selectAll: false,
      min: null,
      max: null,
      groupId: null,
      rubricId: null,
      gradingStrategy: "AUTO" as const,
    },
    {
      questionId: 2,
      id: 2,
      type: "SHORT_ANSWER" as const,
      prompt: "Name the capital of France",
      maxPoints: 5,
      autoGradable: true,
      graded: false,
      data: { caseSensitive: false, trim: true },
      selectAll: null,
      min: null,
      max: null,
      groupId: null,
      rubricId: null,
      gradingStrategy: "AUTO" as const,
    },
  ],
  questionGroups: [],
  rubricId: null,
  rubricAssessmentIds: [],
};

const mockAssessmentWithGroups = {
  ...mockAssessment,
  id: 2,
  title: "Grouped Assessment",
  gradingMode: "MANUAL" as const,
  questionGroups: [
    { id: 10, name: "Reading", rubricId: 100, orderIndex: 0 },
  ],
  questions: [
    {
      ...mockAssessment.questions[0],
      groupId: 10,
      rubricId: null,
      gradingStrategy: "MANUAL" as const,
    },
    {
      ...mockAssessment.questions[1],
      questionId: 3,
      id: 3,
      groupId: null,
      rubricId: 200,
      gradingStrategy: "MANUAL" as const,
    },
  ],
};

const mockRubrics = [
  {
    id: 100,
    title: "Reading Rubric",
    description: "",
    status: "ACTIVE",
    createdBy: 1,
    createdAt: "2026-01-01",
    updatedAt: "2026-01-01",
    criteria: [],
  },
  {
    id: 200,
    title: "Writing Rubric",
    description: "",
    status: "ACTIVE",
    createdBy: 1,
    createdAt: "2026-01-01",
    updatedAt: "2026-01-01",
    criteria: [],
  },
];

describe("AssessmentDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", async () => {
    mockGetAssessment.mockReturnValueOnce(new Promise(() => {}));
    mockListRubrics.mockReturnValueOnce(new Promise(() => {}));
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    // Loading spinner should be present (Loader2 is an svg)
    expect(document.querySelector(".animate-spin")).toBeTruthy();
  });

  it("shows error state when loading fails", async () => {
    mockGetAssessment.mockRejectedValueOnce(new Error("fail"));
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load assessment.")
      ).toBeInTheDocument();
    });
  });

  it("shows back link on error", async () => {
    mockGetAssessment.mockRejectedValueOnce(new Error("fail"));
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Back to Assessments")
      ).toBeInTheDocument();
    });
  });

  it("renders assessment title and metadata badges", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.getByText("Quiz")).toBeInTheDocument();
    expect(screen.getByText("AUTO")).toBeInTheDocument();
    expect(screen.getByText("Scoring: Standard")).toBeInTheDocument();
  });

  it("shows COMPLETION scoring label", async () => {
    const completionAssessment = {
      ...mockAssessment,
      scoringPolicy: "COMPLETION" as const,
    };
    mockGetAssessment.mockResolvedValueOnce(completionAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Scoring: Completion (100)")
      ).toBeInTheDocument();
    });
  });

  it("renders total points", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Total: 15 pts")).toBeInTheDocument();
    });
  });

  it("renders question cards", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      // Prompts appear multiple times (card title + expanded details)
      expect(screen.getAllByText("What is 2+2?").length).toBeGreaterThanOrEqual(1);
      expect(
        screen.getAllByText("Name the capital of France").length
      ).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows edit and delete buttons when canManage", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.getByText("Edit")).toBeInTheDocument();
    expect(screen.getByText("Delete")).toBeInTheDocument();
  });

  it("does not show edit/delete buttons when not canManage", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={false} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
  });

  it("navigates to edit page when edit button is clicked", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Edit"));
    expect(mockPush).toHaveBeenCalledWith(
      "/dashboard/assessments/1/edit"
    );
  });

  it("shows Template Inspector sidebar", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Template Inspector")
      ).toBeInTheDocument();
    });
  });

  it("shows question details in the inspector when selected", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Inspector should show the question details for the first question
    // "Question 1" appears in both card (Q1) and inspector
    expect(
      screen.getByText("Template Inspector")
    ).toBeInTheDocument();
    // Multiple Choice text appears in the type labels
    const mcTexts = screen.getAllByText("Multiple Choice");
    expect(mcTexts.length).toBeGreaterThanOrEqual(1);
  });

  it("shows Rubric Preview section in sidebar", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Rubric Preview")
      ).toBeInTheDocument();
    });
  });

  it("shows 'no rubric attached' for questions without rubric", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Selected question has no rubric attached.")
      ).toBeInTheDocument();
    });
  });

  it("renders question type labels", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      // Question cards show question type
      const mcTexts = screen.getAllByText("Multiple Choice");
      expect(mcTexts.length).toBeGreaterThanOrEqual(1);
      const saTexts = screen.getAllByText("Short Answer");
      expect(saTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders question point values", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("10 pts")).toBeInTheDocument();
      expect(screen.getByText("5 pts")).toBeInTheDocument();
    });
  });

  it("shows 'No questions' when assessment has no questions", async () => {
    const emptyAssessment = {
      ...mockAssessment,
      questions: [],
    };
    mockGetAssessment.mockResolvedValueOnce(emptyAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No questions in this assessment.")
      ).toBeInTheDocument();
    });
  });

  it("shows grouped question buckets", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Reading")).toBeInTheDocument();
      expect(screen.getByText("Ungrouped")).toBeInTheDocument();
    });
  });

  it("shows question count per bucket", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      // Both buckets have 1 question each
      const counts = screen.getAllByText("1 question(s)");
      expect(counts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows drag hint when canManage", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Drag questions here")
      ).toBeInTheDocument();
    });
  });

  it("does not show drag hint when not canManage", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={false} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });
    expect(
      screen.queryByText("Drag questions here")
    ).not.toBeInTheDocument();
  });

  it("shows expand/collapse toggle on question cards", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      // Should have expand/collapse buttons
      const expandButtons = screen.getAllByLabelText(
        /Collapse question|Expand question/
      );
      expect(expandButtons.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("gracefully handles rubrics loading failure", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockRejectedValueOnce(new Error("fail"));
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    // Should still render the assessment even if rubrics fail
    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });
  });

  it("does not show category badge when category is null", async () => {
    const noCategoryAssessment = {
      ...mockAssessment,
      category: null,
    };
    mockGetAssessment.mockResolvedValueOnce(noCategoryAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });
    expect(screen.queryByText("Quiz")).not.toBeInTheDocument();
  });

  it("shows number scale question details when expanded", async () => {
    const nsAssessment = {
      ...mockAssessment,
      questions: [
        {
          questionId: 1,
          id: 1,
          type: "NUMBER_SCALE" as const,
          prompt: "Rate your experience",
          maxPoints: 5,
          autoGradable: true,
          graded: false,
          data: { min: 1, max: 10, target: 7 },
          selectAll: null,
          min: 1,
          max: 10,
          groupId: null,
          rubricId: null,
          gradingStrategy: "AUTO" as const,
        },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(nsAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      // Prompt appears in card title and expanded details
      const texts = screen.getAllByText("Rate your experience");
      expect(texts.length).toBeGreaterThanOrEqual(1);
    });

    // First question should be expanded by default, showing Number Scale type
    const nsTexts = screen.getAllByText("Number Scale");
    expect(nsTexts.length).toBeGreaterThanOrEqual(1);
  });

  it("deletes assessment successfully", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    mockDeleteAssessment.mockResolvedValueOnce(undefined);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Open delete dialog and confirm
    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this assessment? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^Delete$/ }));

    await waitFor(() => {
      expect(mockDeleteAssessment).toHaveBeenCalledWith(1);
      expect(mockToastSuccess).toHaveBeenCalledWith("Assessment deleted.");
      expect(mockPush).toHaveBeenCalledWith("/dashboard/assessments");
    });
  });

  it("shows error toast when delete fails with 409 (referenced)", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    mockDeleteAssessment.mockRejectedValueOnce({
      response: { status: 409, data: { detail: "Referenced by assignment" } },
    });
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this assessment? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^Delete$/ }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Cannot delete — assessment is referenced by assignments."
      );
    });
  });

  it("shows generic error toast when delete fails without 409", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    mockDeleteAssessment.mockRejectedValueOnce(new Error("Server error"));
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this assessment? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^Delete$/ }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Failed to delete assessment."
      );
    });
  });

  it("collapses an expanded question when toggle is clicked", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // First question is expanded by default; find collapse button and click it
    const collapseBtn = screen.getByLabelText("Collapse question 1");
    await user.click(collapseBtn);

    // After collapsing, the button label should change to "Expand"
    await waitFor(() => {
      expect(screen.getByLabelText("Expand question 1")).toBeInTheDocument();
    });
  });

  it("selects a different question by clicking on it", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Click on Q2 card to select it
    const q2Card = screen.getAllByRole("button").find(
      (btn) => btn.textContent?.includes("Name the capital of France")
    );
    expect(q2Card).toBeDefined();
    await user.click(q2Card!);

    // Inspector should now show Question 2 info
    await waitFor(() => {
      expect(screen.getByText("Question 2")).toBeInTheDocument();
    });
  });

  it("shows multiple choice details with selectAll flag", async () => {
    const selectAllAssessment = {
      ...mockAssessment,
      questions: [
        {
          ...mockAssessment.questions[0],
          data: {
            choices: [
              { prompt: "Option A", score: 5 },
              { prompt: "Option B", score: 5 },
            ],
            selectAll: true,
          },
        },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(selectAllAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("(Select all that apply)")
      ).toBeInTheDocument();
    });
  });

  it("shows 'No choices defined.' for MC with empty choices", async () => {
    const noChoicesAssessment = {
      ...mockAssessment,
      questions: [
        {
          ...mockAssessment.questions[0],
          data: { choices: [], selectAll: false },
        },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(noChoicesAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No choices defined.")
      ).toBeInTheDocument();
    });
  });

  it("shows rubric labels on question cards with group rubric", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      // Q1 inherits rubric from group -> "Rubric: Reading Rubric"
      expect(
        screen.getByText("Rubric: Reading Rubric")
      ).toBeInTheDocument();
      // Q3 has its own rubricId=200 -> "Rubric: Writing Rubric"
      expect(
        screen.getByText("Rubric: Writing Rubric")
      ).toBeInTheDocument();
    });
  });

  it("shows Preview Rubric button on manual questions with rubric", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      const previewButtons = screen.getAllByText("Preview Rubric");
      expect(previewButtons.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("opens rubric preview drawer when Preview Rubric button is clicked", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
    });

    const previewButtons = screen.getAllByText("Preview Rubric");
    await user.click(previewButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId("rubric-preview-drawer")).toBeInTheDocument();
    });
  });

  it("opens rubric preview from sidebar Preview In Drawer button", async () => {
    const user = userEvent.setup();
    // Select Q3 which has rubricId=200, manual grading
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
    });

    // Select Q3 (ungrouped question with rubricId=200)
    const q3Card = screen.getAllByRole("button").find(
      (btn) => btn.textContent?.includes("Name the capital of France")
    );
    if (q3Card) await user.click(q3Card);

    await waitFor(() => {
      expect(screen.getByText("Preview In Drawer")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Preview In Drawer"));

    await waitFor(() => {
      expect(screen.getByTestId("rubric-preview-drawer")).toBeInTheDocument();
    });
  });

  it("shows rubric source in inspector for grouped question", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
    });

    // The first selected question is in group -> source is "Group"
    await waitFor(() => {
      const sourceTexts = screen.getAllByText(/Rubric source:/);
      expect(sourceTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("moves question to a different group via drag and drop", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const updatedAssessment = {
      ...mockAssessmentWithGroups,
      questions: [
        { ...mockAssessmentWithGroups.questions[0], groupId: null },
        mockAssessmentWithGroups.questions[1],
      ],
    };
    mockUpdateAssessment.mockResolvedValueOnce(updatedAssessment);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
    });

    const { fireEvent } = await import("@testing-library/react");
    const dragHandle = screen.getByLabelText("Drag question 1");

    // Provide dataTransfer mock for dragStart
    const mockDataTransfer = { setDragImage: vi.fn(), effectAllowed: "" };
    Object.defineProperty(dragHandle, "dispatchEvent", {
      value: dragHandle.dispatchEvent.bind(dragHandle),
    });
    fireEvent.dragStart(dragHandle, { dataTransfer: mockDataTransfer });

    const ungroupedBucket = screen.getByText("Ungrouped").closest("div[class*='rounded']")!;
    fireEvent.dragOver(ungroupedBucket);
    fireEvent.drop(ungroupedBucket);

    await waitFor(() => {
      expect(mockUpdateAssessment).toHaveBeenCalled();
      expect(mockToastSuccess).toHaveBeenCalledWith(
        "Question moved to Ungrouped."
      );
    });
  });

  it("shows error toast when move question fails", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    mockUpdateAssessment.mockRejectedValueOnce(new Error("fail"));
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
    });

    const { fireEvent } = await import("@testing-library/react");
    const dragHandle = screen.getByLabelText("Drag question 1");

    const mockDataTransfer = { setDragImage: vi.fn(), effectAllowed: "" };
    fireEvent.dragStart(dragHandle, { dataTransfer: mockDataTransfer });

    const ungroupedBucket = screen.getByText("Ungrouped").closest("div[class*='rounded']")!;
    fireEvent.dragOver(ungroupedBucket);
    fireEvent.drop(ungroupedBucket);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Failed to move question between groups."
      );
    });
  });

  it("shows short answer details with caseSensitive and trim", async () => {
    // Make SA question the first one so it is expanded by default
    const saAssessment = {
      ...mockAssessment,
      questions: [
        {
          ...mockAssessment.questions[1],
          questionId: 1,
          data: { caseSensitive: true, trim: false },
        },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(saAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Case Sensitive: Yes")).toBeInTheDocument();
      expect(screen.getByText("Trim Whitespace: No")).toBeInTheDocument();
    });
  });

  it("shows decimal points formatted correctly", async () => {
    const decimalAssessment = {
      ...mockAssessment,
      questions: [
        { ...mockAssessment.questions[0], maxPoints: 7.5 },
        { ...mockAssessment.questions[1], maxPoints: 2.5 },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(decimalAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Total: 10 pts")).toBeInTheDocument();
    });
  });

  it("shows number scale without target", async () => {
    const nsNoTargetAssessment = {
      ...mockAssessment,
      questions: [
        {
          questionId: 1,
          id: 1,
          type: "NUMBER_SCALE" as const,
          prompt: "Rate this",
          maxPoints: 5,
          autoGradable: true,
          graded: false,
          data: { min: 0, max: 10 },
          selectAll: null,
          min: 0,
          max: 10,
          groupId: null,
          rubricId: null,
          gradingStrategy: "AUTO" as const,
        },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(nsNoTargetAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getAllByText("Rate this").length).toBeGreaterThanOrEqual(1);
    });
    // Target should not appear
    expect(screen.queryByText(/Target:/)).not.toBeInTheDocument();
  });

  it("handles question selection via keyboard (Enter key)", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Find Q2 card and focus it, then press Enter
    const q2Card = screen.getAllByRole("button").find(
      (btn) => btn.textContent?.includes("Name the capital of France") && btn.getAttribute("aria-pressed") !== null
    );
    expect(q2Card).toBeDefined();
    q2Card!.focus();
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(screen.getByText("Question 2")).toBeInTheDocument();
    });
  });

  it("shows 'Rubric: Unavailable' for question with rubricId but rubric not in map", async () => {
    const unavailableRubricAssessment = {
      ...mockAssessment,
      gradingMode: "MANUAL" as const,
      questions: [
        {
          ...mockAssessment.questions[0],
          rubricId: 999,
          gradingStrategy: "MANUAL" as const,
        },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(unavailableRubricAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Rubric: Unavailable")).toBeInTheDocument();
    });
  });

  it("shows 'No questions in this group.' for empty bucket when not canManage", async () => {
    const emptyGroupAssessment = {
      ...mockAssessment,
      questionGroups: [
        { id: 10, name: "Empty Group", rubricId: null, orderIndex: 0 },
      ],
      questions: [
        { ...mockAssessment.questions[0], groupId: null },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(emptyGroupAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={false} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No questions in this group.")
      ).toBeInTheDocument();
    });
  });

  it("shows 'Drop a question here.' for empty bucket when canManage", async () => {
    const emptyGroupAssessment = {
      ...mockAssessment,
      questionGroups: [
        { id: 10, name: "Empty Group", rubricId: null, orderIndex: 0 },
      ],
      questions: [
        { ...mockAssessment.questions[0], groupId: null },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(emptyGroupAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No questions in this group. Drop a question here.")
      ).toBeInTheDocument();
    });
  });

  it("shows 'Untitled question' for question with empty prompt", async () => {
    const untitledAssessment = {
      ...mockAssessment,
      questions: [
        { ...mockAssessment.questions[0], prompt: "   " },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(untitledAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      const untitledTexts = screen.getAllByText("Untitled question");
      expect(untitledTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows HYBRID question grading strategy on question card", async () => {
    const hybridAssessment = {
      ...mockAssessment,
      gradingMode: "HYBRID" as const,
      questions: [
        {
          ...mockAssessment.questions[0],
          gradingStrategy: "AUTO" as const,
        },
        {
          ...mockAssessment.questions[1],
          gradingStrategy: "MANUAL" as const,
        },
      ],
    };
    mockGetAssessment.mockResolvedValueOnce(hybridAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      // Should show grading strategy labels
      const autoTexts = screen.getAllByText("Grading: AUTO");
      expect(autoTexts.length).toBeGreaterThanOrEqual(1);
      const manualTexts = screen.getAllByText("Grading: MANUAL");
      expect(manualTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows delete error with detail from API response", async () => {
    const user = userEvent.setup();
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    mockDeleteAssessment.mockRejectedValueOnce({
      response: { status: 500, data: { detail: "Internal failure occurred" } },
    });
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this assessment? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^Delete$/ }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Internal failure occurred");
    });
  });

  it("navigates to rubric view page when canManage is false", async () => {
    const user = userEvent.setup();
    // Use grouped assessment with rubrics; select Q3 which has rubricId=200
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={false} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
    });

    // Select Q3 to see its rubric in sidebar
    const q3Card = screen.getAllByRole("button").find(
      (btn) =>
        btn.textContent?.includes("Name the capital of France") &&
        btn.getAttribute("aria-pressed") !== null
    );
    if (q3Card) await user.click(q3Card);

    // The sidebar should show the rubric title
    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });
  });

  it("shows 'Rubric: None' for auto question without rubric", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessment);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={1} canManage={true} />
    );

    await waitFor(() => {
      const noneLabels = screen.getAllByText("Rubric: None");
      expect(noneLabels.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("handles dragLeave event on bucket", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
    });

    const { fireEvent } = await import("@testing-library/react");
    const dragHandle = screen.getByLabelText("Drag question 1");

    const mockDataTransfer = { setDragImage: vi.fn(), effectAllowed: "" };
    fireEvent.dragStart(dragHandle, { dataTransfer: mockDataTransfer });

    const ungroupedBucket = screen.getByText("Ungrouped").closest("div[class*='rounded']")!;

    // DragOver then DragLeave
    fireEvent.dragOver(ungroupedBucket);
    fireEvent.dragLeave(ungroupedBucket);

    // No errors; component handles gracefully
    expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
  });

  it("handles dragEnd on question card", async () => {
    mockGetAssessment.mockResolvedValueOnce(mockAssessmentWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssessmentDetailView = await loadComponent();
    render(
      <AssessmentDetailView assessmentId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
    });

    const { fireEvent } = await import("@testing-library/react");
    const dragHandle = screen.getByLabelText("Drag question 1");

    const mockDataTransfer = { setDragImage: vi.fn(), effectAllowed: "" };
    fireEvent.dragStart(dragHandle, { dataTransfer: mockDataTransfer });
    fireEvent.dragEnd(dragHandle);

    // Should handle gracefully
    expect(screen.getByText("Grouped Assessment")).toBeInTheDocument();
  });
});
