import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockGetRubric = vi.fn();
const mockDeleteRubric = vi.fn();
const mockArchiveRubric = vi.fn();
const mockToast = { success: vi.fn(), error: vi.fn() };

function setupModuleMocks() {
  vi.doMock("sonner", () => ({ toast: mockToast }));
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("@/lib/rubric-api", () => ({
    getRubric: mockGetRubric,
    deleteRubric: mockDeleteRubric,
    archiveRubric: mockArchiveRubric,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/rubrics/RubricDetailView");
  return imported.default;
}

const mockRubric = {
  id: 1,
  title: "Writing Rubric",
  description: "Rubric for evaluating writing assignments",
  status: "ACTIVE",
  createdBy: 1,
  createdAt: "2026-01-10T00:00:00Z",
  updatedAt: "2026-01-10T00:00:00Z",
  criteria: [
    {
      id: 1,
      title: "Grammar",
      description: "Proper grammar use",
      orderIndex: 0,
      weight: 1,
      levels: [
        {
          id: 1,
          label: "Excellent",
          points: 5,
          description: "No errors",
          orderIndex: 0,
        },
        {
          id: 2,
          label: "Good",
          points: 3,
          description: "Few errors",
          orderIndex: 1,
        },
      ],
    },
  ],
};

describe("RubricDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading spinner initially", async () => {
    mockGetRubric.mockReturnValueOnce(new Promise(() => {}));
    const RubricDetailView = await loadComponent();
    const { container } = render(
      <RubricDetailView rubricId={1} canManage={true} />
    );

    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("renders rubric title and status after loading", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    });
  });

  it("renders rubric description", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(
        screen.getByText("Rubric for evaluating writing assignments")
      ).toBeInTheDocument();
    });
  });

  it("shows back to rubrics link", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Back to Rubrics")).toBeInTheDocument();
    });
  });

  it("shows criteria section with count", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Criteria (1)")).toBeInTheDocument();
    });
  });

  it("renders criterion card with title, weight, and levels", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Criterion 1")).toBeInTheDocument();
      expect(screen.getByText("Grammar")).toBeInTheDocument();
      expect(screen.getByText("Weight: 1")).toBeInTheDocument();
      expect(screen.getByText("Excellent")).toBeInTheDocument();
      expect(screen.getByText("Good")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  it("shows management buttons (edit, archive, delete) for canManage", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Edit")).toBeInTheDocument();
      expect(screen.getByText("Archive")).toBeInTheDocument();
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });
  });

  it("does not show management buttons when canManage is false", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });
    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    expect(screen.queryByText("Archive")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
  });

  it("shows error state on load failure", async () => {
    mockGetRubric.mockRejectedValueOnce(new Error("Network error"));
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load rubric.")
      ).toBeInTheDocument();
    });
  });

  it("shows empty criteria message when no criteria", async () => {
    mockGetRubric.mockResolvedValueOnce({
      ...mockRubric,
      criteria: [],
    });
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(
        screen.getByText("No criteria defined in this rubric.")
      ).toBeInTheDocument();
    });
  });

  it("does not show archive button for ARCHIVED rubric", async () => {
    mockGetRubric.mockResolvedValueOnce({
      ...mockRubric,
      status: "ARCHIVED",
    });
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("ARCHIVED")).toBeInTheDocument();
    });
    expect(screen.queryByText("Archive")).not.toBeInTheDocument();
  });

  it("shows not found state when rubric is null after load", async () => {
    mockGetRubric.mockResolvedValueOnce(null);
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Rubric not found.")).toBeInTheDocument();
    });
  });

  it("archives rubric successfully when archive button is clicked", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    mockArchiveRubric.mockResolvedValueOnce(undefined);
    // After archive, loadRubric is called again
    mockGetRubric.mockResolvedValueOnce({
      ...mockRubric,
      status: "ARCHIVED",
    });
    const RubricDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Archive"));

    await waitFor(() => {
      expect(mockArchiveRubric).toHaveBeenCalledWith(1);
    });
    expect(mockToast.success).toHaveBeenCalledWith("Rubric archived.");
  });

  it("shows error toast when archive fails", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    mockArchiveRubric.mockRejectedValueOnce({
      response: { data: { detail: "Archive failed" } },
    });
    const RubricDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Archive"));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Archive failed");
    });
  });

  it("shows fallback error toast when archive fails without detail", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    mockArchiveRubric.mockRejectedValueOnce(new Error("network"));
    const RubricDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Archive"));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "Failed to archive rubric."
      );
    });
  });

  it("navigates to edit page when edit button is clicked", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    const RubricDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Edit"));

    expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics/1/edit");
  });

  it("deletes rubric successfully via alert dialog", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    mockDeleteRubric.mockResolvedValueOnce(undefined);
    const RubricDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    // Open delete dialog
    await user.click(screen.getByText("Delete"));

    // Confirm in dialog
    await waitFor(() => {
      expect(
        screen.getByText("Are you sure you want to delete this rubric? This action cannot be undone.")
      ).toBeInTheDocument();
    });

    // Click the destructive Delete action button in dialog
    const deleteButtons = screen.getAllByText("Delete");
    const confirmButton = deleteButtons[deleteButtons.length - 1];
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockDeleteRubric).toHaveBeenCalledWith(1);
    });
    expect(mockToast.success).toHaveBeenCalledWith("Rubric deleted.");
    expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics");
  });

  it("shows referenced error when delete returns 409", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    mockDeleteRubric.mockRejectedValueOnce({
      response: { data: { detail: "Referenced by assignment templates" }, status: 409 },
    });
    const RubricDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText(/Are you sure you want to delete/)
      ).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[deleteButtons.length - 1]);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "Cannot delete — rubric is referenced by assignment templates."
      );
    });
  });

  it("shows generic error when delete fails without 409", async () => {
    mockGetRubric.mockResolvedValueOnce(mockRubric);
    mockDeleteRubric.mockRejectedValueOnce(new Error("server error"));
    const RubricDetailView = await loadComponent();
    const user = userEvent.setup();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Delete"));
    await waitFor(() => {
      expect(
        screen.getByText(/Are you sure you want to delete/)
      ).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete");
    await user.click(deleteButtons[deleteButtons.length - 1]);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        "Failed to delete rubric."
      );
    });
  });

  it("shows no levels message when criterion has empty levels", async () => {
    mockGetRubric.mockResolvedValueOnce({
      ...mockRubric,
      criteria: [
        {
          id: 2,
          title: "Content",
          description: "",
          orderIndex: 0,
          weight: 2,
          levels: [],
        },
      ],
    });
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("No levels defined.")).toBeInTheDocument();
    });
  });

  it("shows dash for level without description", async () => {
    mockGetRubric.mockResolvedValueOnce({
      ...mockRubric,
      criteria: [
        {
          id: 1,
          title: "Grammar",
          description: null,
          orderIndex: 0,
          weight: 1,
          levels: [
            {
              id: 1,
              label: "Pass",
              points: 1,
              description: "",
              orderIndex: 0,
            },
          ],
        },
      ],
    });
    const RubricDetailView = await loadComponent();
    render(<RubricDetailView rubricId={1} canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("-")).toBeInTheDocument();
    });
  });
});
