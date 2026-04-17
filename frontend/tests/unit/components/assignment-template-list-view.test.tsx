import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockListAssignmentTemplates = vi.fn();
const mockDeleteAssignmentTemplate = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("@/lib/assignment-template-api", () => ({
    listAssignmentTemplates: mockListAssignmentTemplates,
    deleteAssignmentTemplate: mockDeleteAssignmentTemplate,
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assignment-templates/AssignmentTemplateListView"
  );
  return imported.default;
}

async function renderAssignmentTemplateListAndWait(canManage: boolean) {
  const AssignmentTemplateListView = await loadComponent();
  render(<AssignmentTemplateListView canManage={canManage} />);
  await waitFor(() => {
    expect(mockListAssignmentTemplates).toHaveBeenCalledTimes(1);
  });
  await waitFor(() => {
    expect(
      screen.queryByText("Loading assignment templates...")
    ).not.toBeInTheDocument();
  });
}

const mockAssignmentTemplates = [
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
    rubricAssignmentTemplateIds: [],
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
    rubricAssignmentTemplateIds: [],
  },
];

describe("AssignmentTemplateListView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading and manage description when canManage", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    await renderAssignmentTemplateListAndWait(true);

    expect(screen.getByText("Assignment Templates")).toBeInTheDocument();
    expect(
      screen.getByText("Manage assignment templates and their questions.")
    ).toBeInTheDocument();
  });

  it("shows view-only description when canManage is false", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    await renderAssignmentTemplateListAndWait(false);

    expect(
      screen.getByText("View assignment templates and their questions.")
    ).toBeInTheDocument();
  });

  it("shows Create Assignment Template button when canManage", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    await renderAssignmentTemplateListAndWait(true);

    expect(screen.getByText("Create Assignment Template")).toBeInTheDocument();
  });

  it("does not show Create Assignment Template button when not canManage", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={false} />);

    await waitFor(() => {
      expect(
        screen.queryByText("Loading assignment templates...")
      ).not.toBeInTheDocument();
    });
    expect(
      screen.queryByText("Create Assignment Template")
    ).not.toBeInTheDocument();
  });

  it("shows loading state", async () => {
    mockListAssignmentTemplates.mockReturnValueOnce(new Promise(() => {}));
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    expect(
      screen.getByText("Loading assignment templates...")
    ).toBeInTheDocument();
  });

  it("shows empty state when no assignment templates", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(
        screen.getByText("No assignment templates yet.")
      ).toBeInTheDocument();
    });
  });

  it("shows error state on failure", async () => {
    mockListAssignmentTemplates.mockRejectedValueOnce(new Error("fail"));
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load assignment templates.")
      ).toBeInTheDocument();
    });
  });

  it("renders table with assignment template data", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
      expect(screen.getByText("Midterm Review")).toBeInTheDocument();
      expect(screen.getByText("Quiz")).toBeInTheDocument();
      expect(screen.getByText("AUTO")).toBeInTheDocument();
      expect(screen.getByText("MANUAL")).toBeInTheDocument();
    });
  });

  it("renders question count in table", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("1")).toBeInTheDocument();
      expect(screen.getByText("0")).toBeInTheDocument();
    });
  });

  it("shows dash for null category", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("-")).toBeInTheDocument();
    });
  });

  it("shows search input", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    await renderAssignmentTemplateListAndWait(true);

    expect(
      screen.getByPlaceholderText("Search assignment templates...")
    ).toBeInTheDocument();
  });

  it("filters assignment templates by search query", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(
      "Search assignment templates..."
    );
    await user.type(searchInput, "midterm");

    expect(
      screen.queryByText("Week 1 Quiz")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Midterm Review")).toBeInTheDocument();
  });

  it("shows 'No assignment templates match your search.' when filter returns empty", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(
      "Search assignment templates..."
    );
    await user.type(searchInput, "zzzzzz");

    expect(
      screen.getByText("No assignment templates match your search.")
    ).toBeInTheDocument();
  });

  it("navigates to create page when Create Assignment Template is clicked", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce([]);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await user.click(screen.getByText("Create Assignment Template"));
    expect(mockPush).toHaveBeenCalledWith(
      "/dashboard/assignment-templates/new"
    );
  });

  it("navigates to detail page on row click", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Week 1 Quiz"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/assignment-templates/1");
  });

  it("shows edit and delete buttons when canManage", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getAllByText("Edit").length).toBeGreaterThanOrEqual(1);
      expect(
        screen.getAllByText("Delete").length
      ).toBeGreaterThanOrEqual(1);
    });
  });

  it("does not show Actions column when canManage is false", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.queryByText("Actions")).not.toBeInTheDocument();
  });

  it("shows table headers", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

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
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByText("Edit");
    await user.click(editButtons[0]);
    expect(mockPush).toHaveBeenCalledWith(
      "/dashboard/assignment-templates/1/edit"
    );
  });

  it("deletes assignment template successfully and reloads list", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockDeleteAssignmentTemplate.mockResolvedValueOnce(undefined);
    // After delete, list is reloaded
    mockListAssignmentTemplates.mockResolvedValueOnce([mockAssignmentTemplates[1]]);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

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
      expect(mockDeleteAssignmentTemplate).toHaveBeenCalledWith(1);
      expect(mockToastSuccess).toHaveBeenCalledWith("Assignment template deleted.");
    });

    // After reload, only "Midterm Review" should remain
    await waitFor(() => {
      expect(screen.queryByText("Week 1 Quiz")).not.toBeInTheDocument();
      expect(screen.getByText("Midterm Review")).toBeInTheDocument();
    });
  });

  it("shows referenced error when delete returns 409", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockDeleteAssignmentTemplate.mockRejectedValueOnce({
      response: { status: 409, data: { detail: "Assignment template is referenced" } },
    });
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

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
        "Cannot delete — assignment template is referenced by assignments."
      );
    });
  });

  it("shows generic error when delete fails without 409", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockDeleteAssignmentTemplate.mockRejectedValueOnce(new Error("Server error"));
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

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
        "Failed to delete assignment template."
      );
    });
  });

  it("shows delete error with API detail message", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    mockDeleteAssignmentTemplate.mockRejectedValueOnce({
      response: { status: 500, data: { detail: "Custom server error" } },
    });
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

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
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    // Open delete dialog for assignment template 1
    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
    });

    // Try clicking on the row for assignment template 2
    mockPush.mockClear();
    await user.click(screen.getByText("Midterm Review"));

    // Should NOT have navigated because deleteTargetId is set
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("closes delete dialog when Cancel is clicked", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

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
    expect(mockPush).toHaveBeenCalledWith("/dashboard/assignment-templates/1");
  });

  it("shows scoring policy in table", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("STANDARD")).toBeInTheDocument();
      expect(screen.getByText("COMPLETION")).toBeInTheDocument();
    });
  });

  it("does not show edit/delete buttons per row when not canManage", async () => {
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Week 1 Quiz")).toBeInTheDocument();
    });

    expect(screen.queryAllByText("Edit").length).toBe(0);
    expect(screen.queryAllByText("Delete").length).toBe(0);
  });

  it("navigates to detail page on row click for second assignment template", async () => {
    const user = userEvent.setup();
    mockListAssignmentTemplates.mockResolvedValueOnce(mockAssignmentTemplates);
    const AssignmentTemplateListView = await loadComponent();
    render(<AssignmentTemplateListView canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Midterm Review")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Midterm Review"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/assignment-templates/2");
  });
});
