import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGetRubric = vi.fn();
const mockOnOpenChange = vi.fn();
const mockOnEditRubric = vi.fn();
const mockOnOpenFullEditor = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/rubric-api", () => ({
    getRubric: mockGetRubric,
  }));
  vi.doMock("@/components/rubrics/RubricGridPreview", () => ({
    default: ({ title, criteria }: any) => (
      <div data-testid="rubric-grid-preview">
        {title} - {criteria?.length ?? 0} criteria
      </div>
    ),
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assessments/RubricTemplatePreviewDrawer"
  );
  return imported.default;
}

const mockRubric = {
  id: 1,
  title: "Test Rubric",
  description: "A test description",
  status: "ACTIVE",
  createdBy: 1,
  createdAt: "2026-01-01",
  updatedAt: "2026-01-01",
  criteria: [
    {
      id: 1,
      title: "Grammar",
      description: "Check grammar",
      orderIndex: 0,
      weight: 1,
      levels: [
        {
          id: 1,
          label: "Good",
          points: 5,
          description: "",
          orderIndex: 0,
        },
      ],
    },
  ],
};

describe("RubricTemplatePreviewDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows title and description when open", async () => {
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={null}
      />
    );

    expect(
      screen.getByText("Rubric Template Preview")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Review rubric criteria and scoring levels before attaching."
      )
    ).toBeInTheDocument();
  });

  it("shows select rubric message when rubricId is null", async () => {
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={null}
      />
    );

    expect(
      screen.getByText("Select a rubric first to preview it.")
    ).toBeInTheDocument();
  });

  it("shows loading state when fetching rubric", async () => {
    mockGetRubric.mockReturnValueOnce(new Promise(() => {}));
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
      />
    );

    expect(screen.getByText("Loading rubric...")).toBeInTheDocument();
  });

  it("renders rubric details when loaded", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Test Rubric")).toBeInTheDocument();
      expect(
        screen.getByText("A test description")
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Status: ACTIVE/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Criteria: 1/)
      ).toBeInTheDocument();
    });
  });

  it("renders rubric grid preview when loaded", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("rubric-grid-preview")
      ).toBeInTheDocument();
    });
  });

  it("shows error state when loading fails", async () => {
    mockGetRubric.mockRejectedValueOnce(new Error("network error"));
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load rubric template.")
      ).toBeInTheDocument();
    });
  });

  it("shows Edit in Drawer button when onEditRubric provided", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
        onEditRubric={mockOnEditRubric}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Edit in Drawer")
      ).toBeInTheDocument();
    });
  });

  it("calls onEditRubric when Edit in Drawer is clicked", async () => {
    const user = userEvent.setup();
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
        onEditRubric={mockOnEditRubric}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Edit in Drawer")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByText("Edit in Drawer"));
    expect(mockOnEditRubric).toHaveBeenCalledWith(1);
  });

  it("shows Open Full Editor button when onOpenFullEditor provided", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
        onOpenFullEditor={mockOnOpenFullEditor}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Open Full Editor")
      ).toBeInTheDocument();
    });
  });

  it("calls onOpenFullEditor when button clicked", async () => {
    const user = userEvent.setup();
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
        onOpenFullEditor={mockOnOpenFullEditor}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText("Open Full Editor")
      ).toBeInTheDocument();
    });

    await user.click(screen.getByText("Open Full Editor"));
    expect(mockOnOpenFullEditor).toHaveBeenCalledWith(1);
  });

  it("does not show action buttons when no callbacks provided", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Test Rubric")).toBeInTheDocument();
    });

    expect(
      screen.queryByText("Edit in Drawer")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Open Full Editor")
    ).not.toBeInTheDocument();
  });

  it("does not render rubric content when not open", async () => {
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={false}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
      />
    );

    expect(
      screen.queryByText("Rubric Template Preview")
    ).not.toBeInTheDocument();
  });

  it("renders rubric without description", async () => {
    const rubricNoDesc = { ...mockRubric, description: "" };
    mockGetRubric.mockResolvedValueOnce(rubricNoDesc);
    const RubricTemplatePreviewDrawer = await loadComponent();
    render(
      <RubricTemplatePreviewDrawer
        open={true}
        onOpenChange={mockOnOpenChange}
        rubricId={1}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Test Rubric")).toBeInTheDocument();
    });

    // Description paragraph should not be rendered
    expect(
      screen.queryByText("A test description")
    ).not.toBeInTheDocument();
  });
});
