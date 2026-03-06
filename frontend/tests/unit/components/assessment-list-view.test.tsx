import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockListAssessments = vi.fn();
const mockDeleteAssessment = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("@/lib/assessment-api", () => ({
    listAssessments: mockListAssessments,
    deleteAssessment: mockDeleteAssessment,
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assessments/AssessmentListView"
  );
  return imported.default;
}

async function renderAssessmentListAndWait(canManage: boolean) {
  const AssessmentListView = await loadComponent();
  render(<AssessmentListView canManage={canManage} />);
  await waitFor(() => {
    expect(mockListAssessments).toHaveBeenCalledTimes(1);
  });
  await waitFor(() => {
    expect(
      screen.queryByText("Loading assessments...")
    ).not.toBeInTheDocument();
  });
}

const mockAssessments = [
  {
    id: 1,
    title: "Week 1 Quiz",
    category: "Quiz",
    gradingMode: "AUTO",
    scoringPolicy: "STANDARD",
    questions: [
      {
        questionId: 1,
        id: 1,
        type: "MULTIPLE_CHOICE",
        prompt: "Q1",
        maxPoints: 10,
        autoGradable: true,
        graded: false,
        data: null,
        selectAll: null,
        min: null,
        max: null,
        groupId: null,
        rubricId: null,
        gradingStrategy: "AUTO",
      },
    ],
    questionGroups: [],
    rubricId: null,
    rubricAssessmentIds: [],
  },
  {
    id: 2,
    title: "Midterm Review",
    category: null,
    gradingMode: "MANUAL",
    scoringPolicy: "COMPLETION",
    questions: [],
    questionGroups: [],
    rubricId: null,
    rubricAssessmentIds: [],
  },
];

describe("AssessmentListView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading and manage description when canManage", async () => {
    mockListAssessments.mockResolvedValueOnce([]);
    await renderAssessmentListAndWait(true);

    expect(screen.getByText("Assessments")).toBeInTheDocument();
    expect(
      screen.getByText("Manage assessments and their questions.")
    ).toBeInTheDocument();
  });

  it("shows view-only description when canManage is false", async () => {
    mockListAssessments.mockResolvedValueOnce([]);
    await renderAssessmentListAndWait(false);

    expect(
      screen.getByText("View assessments and their questions.")
    ).toBeInTheDocument();
  });

  it("shows Create Assessment button when canManage", async () => {
    mockListAssessments.mockResolvedValueOnce([]);
    await renderAssessmentListAndWait(true);

    expect(screen.getByText("Create Assessment")).toBeInTheDocument();
  });

  it("does not show Create Assessment button when not canManage", async () => {
    mockListAssessments.mockResolvedValueOnce([]);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={false} />);

    await waitFor(() => {
      expect(
        screen.queryByText("Loading assessments...")
      ).not.toBeInTheDocument();
    });
    expect(
      screen.queryByText("Create Assessment")
    ).not.toBeInTheDocument();
  });

  it("shows loading state", async () => {
    mockListAssessments.mockReturnValueOnce(new Promise(() => {}));
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    expect(
      screen.getByText("Loading assessments...")
    ).toBeInTheDocument();
  });

  it("shows empty state when no assessments", async () => {
    mockListAssessments.mockResolvedValueOnce([]);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(
        screen.getByText("No assessments yet.")
      ).toBeInTheDocument();
    });
  });

  it("shows error state on failure", async () => {
    mockListAssessments.mockRejectedValueOnce(new Error("fail"));
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load assessments.")
      ).toBeInTheDocument();
    });
  });

  it("renders table with assessment data", async () => {
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
      expect(screen.getByText("Midterm Review")).toBeInTheDocument();
      expect(screen.getByText("Quiz")).toBeInTheDocument();
      expect(screen.getByText("AUTO")).toBeInTheDocument();
      expect(screen.getByText("MANUAL")).toBeInTheDocument();
    });
  });

  it("renders question count in table", async () => {
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("1")).toBeInTheDocument();
      expect(screen.getByText("0")).toBeInTheDocument();
    });
  });

  it("shows dash for null category", async () => {
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("-")).toBeInTheDocument();
    });
  });

  it("shows search input", async () => {
    mockListAssessments.mockResolvedValueOnce([]);
    await renderAssessmentListAndWait(true);

    expect(
      screen.getByPlaceholderText("Search assessments...")
    ).toBeInTheDocument();
  });

  it("filters assessments by search query", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(
      "Search assessments..."
    );
    await user.type(searchInput, "midterm");

    expect(
      screen.queryByText("Week 1 Quiz")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Midterm Review")).toBeInTheDocument();
  });

  it("shows 'No assessments match your search.' when filter returns empty", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(
      "Search assessments..."
    );
    await user.type(searchInput, "zzzzzz");

    expect(
      screen.getByText("No assessments match your search.")
    ).toBeInTheDocument();
  });

  it("navigates to create page when Create Assessment is clicked", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce([]);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await user.click(screen.getByText("Create Assessment"));
    expect(mockPush).toHaveBeenCalledWith(
      "/dashboard/assessments/new"
    );
  });

  it("navigates to detail page on row click", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Week 1 Quiz"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/assessments/1");
  });

  it("shows edit and delete buttons when canManage", async () => {
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getAllByText("Edit").length).toBeGreaterThanOrEqual(1);
      expect(
        screen.getAllByText("Delete").length
      ).toBeGreaterThanOrEqual(1);
    });
  });

  it("does not show Actions column when canManage is false", async () => {
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.queryByText("Actions")).not.toBeInTheDocument();
  });

  it("shows table headers", async () => {
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Title")).toBeInTheDocument();
      expect(screen.getByText("Category")).toBeInTheDocument();
      expect(screen.getByText("Grading Mode")).toBeInTheDocument();
      expect(screen.getByText("Scoring")).toBeInTheDocument();
      expect(screen.getByText("Questions")).toBeInTheDocument();
    });
  });

  it("navigates to edit page when edit button is clicked", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByText("Edit");
    await user.click(editButtons[0]);
    expect(mockPush).toHaveBeenCalledWith(
      "/dashboard/assessments/1/edit"
    );
  });

  it("deletes assessment successfully and reloads list", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    mockDeleteAssessment.mockResolvedValueOnce(undefined);
    // After delete, list is reloaded
    mockListAssessments.mockResolvedValueOnce([mockAssessments[1]]);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Click the first delete button to open dialog
    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[0]);

    // Confirm deletion in dialog
    await waitFor(() => {
      expect(
        screen.getByText(/Are you sure you want to delete/)
      ).toBeInTheDocument();
    });

    // Find the destructive Delete action button inside the dialog
    const confirmButton = screen.getAllByRole("button").find(
      (btn) => btn.textContent === "Delete" && btn !== deleteButtons[0]
    );
    expect(confirmButton).toBeDefined();
    await user.click(confirmButton!);

    await waitFor(() => {
      expect(mockDeleteAssessment).toHaveBeenCalledWith(1);
      expect(mockToastSuccess).toHaveBeenCalledWith("Assessment deleted.");
    });

    // After reload, only "Midterm Review" should remain
    await waitFor(() => {
      expect(screen.queryByText("Week 1 Quiz")).not.toBeInTheDocument();
      expect(screen.getByText("Midterm Review")).toBeInTheDocument();
    });
  });

  it("shows referenced error when delete returns 409", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    mockDeleteAssessment.mockRejectedValueOnce({
      response: { status: 409, data: { detail: "Assessment is referenced" } },
    });
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
    });

    const confirmButton = screen.getAllByRole("button").find(
      (btn) => btn.textContent === "Delete" && btn !== deleteButtons[0]
    );
    await user.click(confirmButton!);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Cannot delete — assessment is referenced by assignments."
      );
    });
  });

  it("shows generic error when delete fails without 409", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    mockDeleteAssessment.mockRejectedValueOnce(new Error("Server error"));
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
    });

    const confirmButton = screen.getAllByRole("button").find(
      (btn) => btn.textContent === "Delete" && btn !== deleteButtons[0]
    );
    await user.click(confirmButton!);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Failed to delete assessment."
      );
    });
  });

  it("shows delete error with API detail message", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    mockDeleteAssessment.mockRejectedValueOnce({
      response: { status: 500, data: { detail: "Custom server error" } },
    });
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
    });

    const confirmButton = screen.getAllByRole("button").find(
      (btn) => btn.textContent === "Delete" && btn !== deleteButtons[0]
    );
    await user.click(confirmButton!);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Custom server error");
    });
  });

  it("does not navigate on row click when delete dialog is open", async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Open delete dialog for assessment 1
    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
    });

    // Try clicking on the row for assessment 2
    mockPush.mockClear();
    await user.click(screen.getByText("Midterm Review"));

    // Should NOT have navigated because deleteTargetId is set
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("closes delete dialog when Cancel is clicked", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Open delete dialog
    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
    });

    // Click Cancel
    await user.click(screen.getByText("Cancel"));

    // Dialog should close; deleteTargetId should be null now
    // Row click should work again
    await user.click(screen.getByText("Week 1 Quiz"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/assessments/1");
  });

  it("shows scoring policy in table", async () => {
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("STANDARD")).toBeInTheDocument();
      expect(screen.getByText("COMPLETION")).toBeInTheDocument();
    });
  });

  it("does not show edit/delete buttons per row when not canManage", async () => {
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.queryAllByText("Edit").length).toBe(0);
    expect(screen.queryAllByText("Delete").length).toBe(0);
  });

  it("navigates to detail page on row click for second assessment", async () => {
    const user = userEvent.setup();
    mockListAssessments.mockResolvedValueOnce(mockAssessments);
    const AssessmentListView = await loadComponent();
    render(<AssessmentListView canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Midterm Review")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Midterm Review"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/assessments/2");
  });
});
