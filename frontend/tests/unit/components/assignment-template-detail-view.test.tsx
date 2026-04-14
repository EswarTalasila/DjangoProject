import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockGetAssignmentTemplate = vi.fn();
const mockDeleteAssignmentTemplate = vi.fn();
const mockUpdateAssignmentTemplate = vi.fn();
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
  vi.doMock("@/lib/assignment-template-api", () => ({
    getAssignmentTemplate: mockGetAssignmentTemplate,
    deleteAssignmentTemplate: mockDeleteAssignmentTemplate,
    updateAssignmentTemplate: mockUpdateAssignmentTemplate,
  }));
  vi.doMock("@/lib/rubric-api", () => ({
    listRubrics: mockListRubrics,
    getRubric: vi.fn(),
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
  vi.doMock("@/components/assignment-templates/RubricTemplatePreviewDrawer", () => ({
    default: ({ open }: any) =>
      open ? <div data-testid="rubric-preview-drawer">Rubric Preview</div> : null,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assignment-templates/AssignmentTemplateDetailView"
  );
  return imported.default;
}

const mockAssignmentTemplate = {
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
  rubricAssignmentTemplateIds: [],
};

const mockAssignmentTemplateWithGroups = {
  ...mockAssignmentTemplate,
  id: 2,
  title: "Grouped AssignmentTemplate",
  gradingMode: "MANUAL" as const,
  questionGroups: [
    { id: 10, name: "Reading", rubricId: 100, orderIndex: 0 },
  ],
  questions: [
    {
      ...mockAssignmentTemplate.questions[0],
      groupId: 10,
      rubricId: null,
      gradingStrategy: "MANUAL" as const,
    },
    {
      ...mockAssignmentTemplate.questions[1],
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

describe("AssignmentTemplateDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", async () => {
    mockGetAssignmentTemplate.mockReturnValueOnce(new Promise(() => {}));
    mockListRubrics.mockReturnValueOnce(new Promise(() => {}));
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    // Loading spinner should be present (Loader2 is an svg)
    expect(document.querySelector(".animate-spin")).toBeTruthy();
  });

  it("shows error state when loading fails", async () => {
    mockGetAssignmentTemplate.mockRejectedValueOnce(new Error("fail"));
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load assignment template.")
      ).toBeInTheDocument();
    });
  });

  it("shows back link on error", async () => {
    mockGetAssignmentTemplate.mockRejectedValueOnce(new Error("fail"));
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Back to assignment templates")
      ).toBeInTheDocument();
    });
  });

  it("renders assignment template title and metadata badges", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.getByText("Quiz")).toBeInTheDocument();
    expect(screen.getByText("AUTO")).toBeInTheDocument();
    expect(screen.getByText("Scoring: Standard")).toBeInTheDocument();
  });

  it("shows COMPLETION scoring label", async () => {
    const completionAssignmentTemplate = {
      ...mockAssignmentTemplate,
      scoringPolicy: "COMPLETION" as const,
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(completionAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Scoring: Completion (100)")
      ).toBeInTheDocument();
    });
  });

  it("renders total points", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Total: 15 pts")).toBeInTheDocument();
    });
  });

  it("renders question cards", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.getByText("Edit")).toBeInTheDocument();
    expect(screen.getByText("Delete")).toBeInTheDocument();
  });

  it("does not show edit/delete buttons when not canManage", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={false} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
  });

  it("navigates to edit page when edit button is clicked", async () => {
    const user = userEvent.setup();
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Edit"));
    expect(mockPush).toHaveBeenCalledWith(
      "/dashboard/assignment-templates/1/edit"
    );
  });

  it("shows Template Inspector sidebar", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Template Inspector")
      ).toBeInTheDocument();
    });
  });

  it("shows question details in the inspector when selected", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Rubric Preview")
      ).toBeInTheDocument();
    });
  });

  it("shows 'no rubric attached' for questions without rubric", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Selected question has no rubric attached.")
      ).toBeInTheDocument();
    });
  });

  it("renders question type labels", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("10 pts")).toBeInTheDocument();
      expect(screen.getByText("5 pts")).toBeInTheDocument();
    });
  });

  it("shows 'No questions' when assignment template has no questions", async () => {
    const emptyAssignmentTemplate = {
      ...mockAssignmentTemplate,
      questions: [],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(emptyAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No questions in this assignment template.")
      ).toBeInTheDocument();
    });
  });

  it("shows grouped question buckets", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Reading")).toBeInTheDocument();
      expect(screen.getByText("Ungrouped")).toBeInTheDocument();
    });
  });

  it("shows question count per bucket", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      // Both buckets have 1 question each
      const counts = screen.getAllByText("1 question(s)");
      expect(counts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows drag hint when canManage", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Drag questions here")
      ).toBeInTheDocument();
    });
  });

  it("does not show drag hint when not canManage", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={false} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });
    expect(
      screen.queryByText("Drag questions here")
    ).not.toBeInTheDocument();
  });

  it("shows expand/collapse toggle on question cards", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockRejectedValueOnce(new Error("fail"));
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    // Should still render the assignment template even if rubrics fail
    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });
  });

  it("does not show category badge when category is null", async () => {
    const noCategoryAssignmentTemplate = {
      ...mockAssignmentTemplate,
      category: null,
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(noCategoryAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });
    expect(screen.queryByText("Quiz")).not.toBeInTheDocument();
  });

  it("shows number scale question details when expanded", async () => {
    const nsAssignmentTemplate = {
      ...mockAssignmentTemplate,
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(nsAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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

  it("deletes assignment template successfully", async () => {
    const user = userEvent.setup();
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    mockDeleteAssignmentTemplate.mockResolvedValueOnce(undefined);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Open delete dialog and confirm
    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this assignment template? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^Delete$/ }));

    await waitFor(() => {
      expect(mockDeleteAssignmentTemplate).toHaveBeenCalledWith(1);
      expect(mockToastSuccess).toHaveBeenCalledWith("Assignment template deleted.");
      expect(mockPush).toHaveBeenCalledWith("/dashboard/assignment-templates");
    });
  });

  it("shows error toast when delete fails with 409 (referenced)", async () => {
    const user = userEvent.setup();
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    mockDeleteAssignmentTemplate.mockRejectedValueOnce({
      response: { status: 409, data: { detail: "Referenced by assignment" } },
    });
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this assignment template? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^Delete$/ }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Cannot delete — assignment template is referenced by assignments."
      );
    });
  });

  it("shows generic error toast when delete fails without 409", async () => {
    const user = userEvent.setup();
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    mockDeleteAssignmentTemplate.mockRejectedValueOnce(new Error("Server error"));
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this assignment template? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^Delete$/ }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Failed to delete assignment template."
      );
    });
  });

  it("collapses an expanded question when toggle is clicked", async () => {
    const user = userEvent.setup();
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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
    const selectAllAssignmentTemplate = {
      ...mockAssignmentTemplate,
      questions: [
        {
          ...mockAssignmentTemplate.questions[0],
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(selectAllAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("(Select all that apply)")
      ).toBeInTheDocument();
    });
  });

  it("shows 'No choices defined.' for MC with empty choices", async () => {
    const noChoicesAssignmentTemplate = {
      ...mockAssignmentTemplate,
      questions: [
        {
          ...mockAssignmentTemplate.questions[0],
          data: { choices: [], selectAll: false },
        },
      ],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(noChoicesAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No choices defined.")
      ).toBeInTheDocument();
    });
  });

  it("shows rubric labels on question cards with group rubric", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      const previewButtons = screen.getAllByText("Preview Rubric");
      expect(previewButtons.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("opens rubric preview drawer when Preview Rubric button is clicked", async () => {
    const user = userEvent.setup();
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
    });

    // The first selected question is in group -> source is "Group"
    await waitFor(() => {
      const sourceTexts = screen.getAllByText(/Rubric source:/);
      expect(sourceTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("moves question to a different group via drag and drop", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const updatedAssignmentTemplate = {
      ...mockAssignmentTemplateWithGroups,
      questions: [
        { ...mockAssignmentTemplateWithGroups.questions[0], groupId: null },
        mockAssignmentTemplateWithGroups.questions[1],
      ],
    };
    mockUpdateAssignmentTemplate.mockResolvedValueOnce(updatedAssignmentTemplate);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
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
      expect(mockUpdateAssignmentTemplate).toHaveBeenCalled();
      expect(mockToastSuccess).toHaveBeenCalledWith(
        "Question moved to Ungrouped."
      );
    });
  });

  it("shows error toast when move question fails", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    mockUpdateAssignmentTemplate.mockRejectedValueOnce(new Error("fail"));
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
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
    const saAssignmentTemplate = {
      ...mockAssignmentTemplate,
      questions: [
        {
          ...mockAssignmentTemplate.questions[1],
          questionId: 1,
          data: { caseSensitive: true, trim: false },
        },
      ],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(saAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Case Sensitive: Yes")).toBeInTheDocument();
      expect(screen.getByText("Trim Whitespace: No")).toBeInTheDocument();
    });
  });

  it("shows decimal points formatted correctly", async () => {
    const decimalAssignmentTemplate = {
      ...mockAssignmentTemplate,
      questions: [
        { ...mockAssignmentTemplate.questions[0], maxPoints: 7.5 },
        { ...mockAssignmentTemplate.questions[1], maxPoints: 2.5 },
      ],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(decimalAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Total: 10 pts")).toBeInTheDocument();
    });
  });

  it("shows number scale without target", async () => {
    const nsNoTargetAssignmentTemplate = {
      ...mockAssignmentTemplate,
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(nsNoTargetAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getAllByText("Rate this").length).toBeGreaterThanOrEqual(1);
    });
    // Target should not appear
    expect(screen.queryByText(/Target:/)).not.toBeInTheDocument();
  });

  it("handles question selection via keyboard (Enter key)", async () => {
    const user = userEvent.setup();
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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
    const unavailableRubricAssignmentTemplate = {
      ...mockAssignmentTemplate,
      gradingMode: "MANUAL" as const,
      questions: [
        {
          ...mockAssignmentTemplate.questions[0],
          rubricId: 999,
          gradingStrategy: "MANUAL" as const,
        },
      ],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(unavailableRubricAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Rubric: Unavailable")).toBeInTheDocument();
    });
  });

  it("shows 'No questions in this group.' for empty bucket when not canManage", async () => {
    const emptyGroupAssignmentTemplate = {
      ...mockAssignmentTemplate,
      questionGroups: [
        { id: 10, name: "Empty Group", rubricId: null, orderIndex: 0 },
      ],
      questions: [
        { ...mockAssignmentTemplate.questions[0], groupId: null },
      ],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(emptyGroupAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={false} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No questions in this group.")
      ).toBeInTheDocument();
    });
  });

  it("shows 'Drop a question here.' for empty bucket when canManage", async () => {
    const emptyGroupAssignmentTemplate = {
      ...mockAssignmentTemplate,
      questionGroups: [
        { id: 10, name: "Empty Group", rubricId: null, orderIndex: 0 },
      ],
      questions: [
        { ...mockAssignmentTemplate.questions[0], groupId: null },
      ],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(emptyGroupAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No questions in this group. Drop a question here.")
      ).toBeInTheDocument();
    });
  });

  it("shows 'Untitled question' for question with empty prompt", async () => {
    const untitledAssignmentTemplate = {
      ...mockAssignmentTemplate,
      questions: [
        { ...mockAssignmentTemplate.questions[0], prompt: "   " },
      ],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(untitledAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      const untitledTexts = screen.getAllByText("Untitled question");
      expect(untitledTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows HYBRID question grading strategy on question card", async () => {
    const hybridAssignmentTemplate = {
      ...mockAssignmentTemplate,
      gradingMode: "HYBRID" as const,
      questions: [
        {
          ...mockAssignmentTemplate.questions[0],
          gradingStrategy: "AUTO" as const,
        },
        {
          ...mockAssignmentTemplate.questions[1],
          gradingStrategy: "MANUAL" as const,
        },
      ],
    };
    mockGetAssignmentTemplate.mockResolvedValueOnce(hybridAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    mockDeleteAssignmentTemplate.mockRejectedValueOnce({
      response: { status: 500, data: { detail: "Internal failure occurred" } },
    });
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this assignment template? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /^Delete$/ }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Internal failure occurred");
    });
  });

  it("navigates to rubric view page when canManage is false", async () => {
    const user = userEvent.setup();
    // Use grouped assignment template with rubrics; select Q3 which has rubricId=200
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={false} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
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
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplate);
    mockListRubrics.mockResolvedValueOnce([]);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={1} canManage={true} />
    );

    await waitFor(() => {
      const noneLabels = screen.getAllByText("Rubric: None");
      expect(noneLabels.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("handles dragLeave event on bucket", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
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
    expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
  });

  it("handles dragEnd on question card", async () => {
    mockGetAssignmentTemplate.mockResolvedValueOnce(mockAssignmentTemplateWithGroups);
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const AssignmentTemplateDetailView = await loadComponent();
    render(
      <AssignmentTemplateDetailView assignmentTemplateId={2} canManage={true} />
    );

    await waitFor(() => {
      expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
    });

    const { fireEvent } = await import("@testing-library/react");
    const dragHandle = screen.getByLabelText("Drag question 1");

    const mockDataTransfer = { setDragImage: vi.fn(), effectAllowed: "" };
    fireEvent.dragStart(dragHandle, { dataTransfer: mockDataTransfer });
    fireEvent.dragEnd(dragHandle);

    // Should handle gracefully
    expect(screen.getByText("Grouped AssignmentTemplate")).toBeInTheDocument();
  });
});
