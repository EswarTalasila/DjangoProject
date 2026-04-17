import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCreateRubric = vi.fn();
const mockUpdateRubric = vi.fn();
const mockGetRubric = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
const mockOnOpenChange = vi.fn();
const mockOnCreated = vi.fn();
const mockOnSaved = vi.fn();
const mockOnOpenFullEditor = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/rubric-api", () => ({
    createRubric: mockCreateRubric,
    updateRubric: mockUpdateRubric,
    getRubric: mockGetRubric,
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
  vi.doMock("@/components/rubrics/CriterionBlock", () => ({
    default: ({ index, criterion, onChange, onRemove }: any) => (
      <div data-testid={`criterion-${index}`}>
        <span>{criterion.title || "Untitled"}</span>
        <button onClick={() => onChange({ ...criterion, title: "Updated" })}>
          update-criterion
        </button>
        <button onClick={onRemove}>remove-criterion</button>
      </div>
    ),
  }));
  vi.doMock("@/components/rubrics/RubricGridPreview", () => ({
    default: ({ title }: any) => (
      <div data-testid="rubric-grid-preview">{title}</div>
    ),
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assignment-templates/RubricQuickBuilderDrawer"
  );
  return imported.default;
}

describe("RubricQuickBuilderDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when closed", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    const { container } = render(
      <RubricQuickBuilderDrawer
        open={false}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.queryByText("Quick Rubric Builder")
    ).not.toBeInTheDocument();
  });

  it("renders create mode title when open", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.getByText("Quick Rubric Builder")
    ).toBeInTheDocument();
  });

  it("renders edit mode title when mode=edit", async () => {
    mockGetRubric.mockResolvedValueOnce({
      id: 1,
      title: "Test Rubric",
      description: "desc",
      criteria: [
        {
          title: "C1",
          description: "",
          weight: 1,
          levels: [{ label: "L1", points: 1, description: "" }],
        },
      ],
    });
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        mode="edit"
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Quick Edit Rubric")
      ).toBeInTheDocument();
    });
  });

  it("renders title and description inputs", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.getByPlaceholderText("Enter rubric title...")
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Optional description")
    ).toBeInTheDocument();
  });

  it("shows tips by default", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.getByText("Each criterion is a grading row.")
    ).toBeInTheDocument();
  });

  it("toggles tips visibility", async () => {
    const user = userEvent.setup();
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    await user.click(screen.getByText("Hide Tips"));
    expect(
      screen.queryByText("Each criterion is a grading row.")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Show Tips")).toBeInTheDocument();
  });

  it("renders initial criterion", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByTestId("criterion-0")).toBeInTheDocument();
  });

  it("adds criterion when Add Criterion is clicked", async () => {
    const user = userEvent.setup();
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    await user.click(screen.getByText("Add Criterion"));
    expect(screen.getByTestId("criterion-1")).toBeInTheDocument();
  });

  it("shows title error when title is empty", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.getByText("Title is required")
    ).toBeInTheDocument();
  });

  it("shows Create Rubric button in create mode", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByText("Create Rubric")).toBeInTheDocument();
  });

  it("shows Save Rubric button in edit mode", async () => {
    mockGetRubric.mockResolvedValueOnce({
      id: 1,
      title: "Test",
      description: "",
      criteria: [
        {
          title: "C1",
          description: "",
          weight: 1,
          levels: [{ label: "L1", points: 1, description: "" }],
        },
      ],
    });
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        mode="edit"
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Save Rubric")).toBeInTheDocument();
    });
  });

  it("shows Cancel button", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("calls onOpenChange(false) when Cancel is clicked", async () => {
    const user = userEvent.setup();
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    await user.click(screen.getByText("Cancel"));
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it("shows Open Full Editor button when callback provided", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        onOpenFullEditor={mockOnOpenFullEditor}
      />
    );

    expect(screen.getByText("Open Full Editor")).toBeInTheDocument();
  });

  it("does not show Open Full Editor when callback not provided", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.queryByText("Open Full Editor")
    ).not.toBeInTheDocument();
  });

  it("shows validation error toast when saving with empty title", async () => {
    const user = userEvent.setup();
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    await user.click(screen.getByText("Create Rubric"));
    expect(mockToastError).toHaveBeenCalledWith("Title is required");
  });

  it("calls toast error on save with empty criterion title", async () => {
    const user = userEvent.setup();

    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreated={mockOnCreated}
        onSaved={mockOnSaved}
      />
    );

    // Fill title but leave criterion title empty
    await user.type(
      screen.getByPlaceholderText("Enter rubric title..."),
      "New Rubric"
    );

    await user.click(screen.getByText("Create Rubric"));

    // Criterion title is empty, so validation should fail
    expect(mockToastError).toHaveBeenCalledWith(
      "Each criterion needs a title"
    );
    expect(mockCreateRubric).not.toHaveBeenCalled();
  });

  it("shows criteria count", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByText("Criteria (1)")).toBeInTheDocument();
  });

  it("renders rubric grid preview", async () => {
    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(
      screen.getByTestId("rubric-grid-preview")
    ).toBeInTheDocument();
  });

  it("loads rubric data in edit mode", async () => {
    mockGetRubric.mockResolvedValueOnce({
      id: 1,
      title: "Existing Rubric",
      description: "A description",
      criteria: [
        {
          title: "Criterion 1",
          description: "desc",
          weight: 2,
          levels: [{ label: "Good", points: 5, description: "" }],
        },
      ],
    });

    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        mode="edit"
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByDisplayValue("Existing Rubric")
      ).toBeInTheDocument();
      expect(
        screen.getByDisplayValue("A description")
      ).toBeInTheDocument();
    });
  });

  it("shows loading state in edit mode", async () => {
    mockGetRubric.mockReturnValueOnce(new Promise(() => {}));

    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        mode="edit"
        rubricId={1}
      />
    );

    expect(screen.getByText("Loading rubric...")).toBeInTheDocument();
  });

  it("shows error toast and closes when edit load fails", async () => {
    mockGetRubric.mockRejectedValueOnce(new Error("fail"));

    const RubricQuickBuilderDrawer = await loadComponent();
    render(
      <RubricQuickBuilderDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        mode="edit"
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Failed to load rubric template."
      );
    });
  });
});
