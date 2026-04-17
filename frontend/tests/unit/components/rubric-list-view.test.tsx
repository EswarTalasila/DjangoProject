import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const mockListRubrics = vi.fn();
const mockDeleteRubric = vi.fn();
const mockArchiveRubric = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush }),
    useSearchParams: () => new URLSearchParams(),
  }));
  vi.doMock("@/lib/rubric-api", () => ({
    listRubrics: mockListRubrics,
    deleteRubric: mockDeleteRubric,
    archiveRubric: mockArchiveRubric,
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/rubrics/RubricListView");
  return imported.default;
}

async function renderRubricListAndWait(canManage: boolean) {
  const RubricListView = await loadComponent();
  render(<RubricListView canManage={canManage} />);
  await waitFor(() => {
    expect(mockListRubrics).toHaveBeenCalledTimes(1);
  });
  await waitFor(() => {
    expect(
      screen.queryByText("Loading rubrics...")
    ).not.toBeInTheDocument();
  });
}

const mockRubrics = [
  {
    id: 1,
    title: "Writing Rubric",
    description: "For essays",
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
        levels: [],
      },
      {
        id: 2,
        title: "Content",
        description: "Quality of content",
        orderIndex: 1,
        weight: 2,
        levels: [],
      },
    ],
  },
  {
    id: 2,
    title: "Math Rubric",
    description: "For math tests",
    status: "ARCHIVED",
    createdBy: 1,
    createdAt: "2026-01-05T00:00:00Z",
    updatedAt: "2026-01-05T00:00:00Z",
    criteria: [],
  },
];

describe("RubricListView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading and manage description for canManage", async () => {
    mockListRubrics.mockResolvedValueOnce([]);
    await renderRubricListAndWait(true);

    expect(screen.getByText("Rubrics")).toBeInTheDocument();
    expect(
      screen.getByText("Manage rubrics and their grading criteria.")
    ).toBeInTheDocument();
  });

  it("shows view-only description when canManage is false", async () => {
    mockListRubrics.mockResolvedValueOnce([]);
    await renderRubricListAndWait(false);

    expect(
      screen.getByText("View rubrics and their grading criteria.")
    ).toBeInTheDocument();
  });

  it("shows Create Rubric button when canManage is true", async () => {
    mockListRubrics.mockResolvedValueOnce([]);
    await renderRubricListAndWait(true);

    expect(screen.getByText("Create Rubric")).toBeInTheDocument();
  });

  it("does not show Create Rubric button when canManage is false", async () => {
    mockListRubrics.mockResolvedValueOnce([]);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={false} />);

    await waitFor(() => {
      expect(
        screen.queryByText("Loading rubrics...")
      ).not.toBeInTheDocument();
    });
    expect(screen.queryByText("Create Rubric")).not.toBeInTheDocument();
  });

  it("shows loading state", async () => {
    mockListRubrics.mockReturnValueOnce(new Promise(() => {}));
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    expect(screen.getByText("Loading rubrics...")).toBeInTheDocument();
  });

  it("shows empty state when no rubrics", async () => {
    mockListRubrics.mockResolvedValueOnce([]);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("No rubrics yet.")).toBeInTheDocument();
    });
  });

  it("renders rubric table with data", async () => {
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
      expect(screen.getByText("Math Rubric")).toBeInTheDocument();
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
      expect(screen.getByText("ARCHIVED")).toBeInTheDocument();
    });
  });

  it("shows criteria count", async () => {
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // Writing rubric has 2 criteria
      expect(screen.getByText("0")).toBeInTheDocument(); // Math rubric has 0 criteria
    });
  });

  it("shows error state on failure", async () => {
    mockListRubrics.mockRejectedValueOnce(new Error("Network error"));
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load rubrics.")
      ).toBeInTheDocument();
    });
  });

  it("shows search input", async () => {
    mockListRubrics.mockResolvedValueOnce([]);
    await renderRubricListAndWait(true);

    expect(
      screen.getByPlaceholderText("Search rubrics...")
    ).toBeInTheDocument();
  });

  it("shows action buttons (edit, delete, archive) when canManage", async () => {
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getAllByText("Edit").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Delete").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("does not show Actions column when canManage is false", async () => {
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });
    expect(screen.queryByText("Actions")).not.toBeInTheDocument();
  });

  it("filters rubrics by search query", async () => {
    const user = userEvent.setup();
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search rubrics...");
    await user.type(searchInput, "Writing");

    expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    expect(screen.queryByText("Math Rubric")).not.toBeInTheDocument();
  });

  it("shows 'No rubrics match your search.' when filter yields no results", async () => {
    const user = userEvent.setup();
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search rubrics...");
    await user.type(searchInput, "xyznotfound");

    expect(screen.getByText("No rubrics match your search.")).toBeInTheDocument();
  });

  it("navigates to rubric detail on row click", async () => {
    const user = userEvent.setup();
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Writing Rubric"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics/1");
  });

  it("navigates to create rubric page when Create Rubric is clicked", async () => {
    const user = userEvent.setup();
    mockListRubrics.mockResolvedValueOnce([]);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.queryByText("Loading rubrics...")).not.toBeInTheDocument();
    });

    await user.click(screen.getByText("Create Rubric"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics/new");
  });

  it("navigates to edit page when Edit button is clicked", async () => {
    const user = userEvent.setup();
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByText("Edit");
    await user.click(editButtons[0]);
    expect(mockPush).toHaveBeenCalledWith("/dashboard/rubrics/1/edit");
  });

  it("shows archive button for ACTIVE rubrics only", async () => {
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    // Archive button should appear for ACTIVE rubric (Writing Rubric) but not ARCHIVED (Math Rubric)
    const archiveButtons = screen.getAllByText("Archive");
    expect(archiveButtons).toHaveLength(1);
  });

  it("calls archiveRubric and shows success toast when archive is clicked", async () => {
    const user = userEvent.setup();
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    mockArchiveRubric.mockResolvedValueOnce({});
    mockListRubrics.mockResolvedValueOnce([]); // reload
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    const archiveButton = screen.getByText("Archive");
    await user.click(archiveButton);

    await waitFor(() => {
      expect(mockArchiveRubric).toHaveBeenCalledWith(1);
      expect(mockToastSuccess).toHaveBeenCalledWith("Rubric archived.");
    });
  });

  it("shows error toast when archive fails", async () => {
    const user = userEvent.setup();
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    mockArchiveRubric.mockRejectedValueOnce(new Error("fail"));
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Archive"));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Failed to archive rubric.");
    });
  });

  it("opens delete confirmation when delete button is clicked", async () => {
    const user = userEvent.setup();
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    // Find and click the delete button (the one with destructive class)
    const deleteButtons = screen.getAllByText("Delete").filter(
      (el) => el.closest("button")?.classList.contains("text-destructive")
    );
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Delete Rubric")).toBeInTheDocument();
      expect(
        screen.getByText(/Are you sure you want to delete/)
      ).toBeInTheDocument();
    });
  });

  it("deletes rubric successfully when confirm is clicked", async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    mockDeleteRubric.mockResolvedValueOnce({});
    mockListRubrics.mockResolvedValueOnce([]); // reload after delete
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    // Open delete dialog for first rubric
    const deleteButtons = screen.getAllByText("Delete").filter(
      (el) => el.closest("button")?.classList.contains("text-destructive")
    );
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Delete Rubric")).toBeInTheDocument();
    });

    // Click the confirm Delete button inside the dialog (AlertDialogAction)
    const allDeleteBtns = screen.getAllByRole("button").filter(
      (btn) => btn.textContent?.trim() === "Delete"
    );
    // The last "Delete" button should be the dialog confirmation
    const dialogDeleteBtn = allDeleteBtns[allDeleteBtns.length - 1];
    await user.click(dialogDeleteBtn);

    await waitFor(() => {
      expect(mockDeleteRubric).toHaveBeenCalledWith(1);
      expect(mockToastSuccess).toHaveBeenCalledWith("Rubric deleted.");
    });
  });

  it("shows 409 conflict error when deleting referenced rubric", async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    mockDeleteRubric.mockRejectedValueOnce({
      response: { status: 409, data: { detail: "Referenced by assignment templates" } },
    });
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete").filter(
      (el) => el.closest("button")?.classList.contains("text-destructive")
    );
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Delete Rubric")).toBeInTheDocument();
    });

    const allDeleteBtns = screen.getAllByRole("button").filter(
      (btn) => btn.textContent?.trim() === "Delete"
    );
    const dialogDeleteBtn = allDeleteBtns[allDeleteBtns.length - 1];
    await user.click(dialogDeleteBtn);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Cannot delete — rubric is referenced by assignment templates."
      );
    });
  });

  it("shows generic error when delete fails without 409", async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    mockDeleteRubric.mockRejectedValueOnce({
      response: { status: 500, data: { detail: "Internal error" } },
    });
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete").filter(
      (el) => el.closest("button")?.classList.contains("text-destructive")
    );
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Delete Rubric")).toBeInTheDocument();
    });

    const allDeleteBtns = screen.getAllByRole("button").filter(
      (btn) => btn.textContent?.trim() === "Delete"
    );
    const dialogDeleteBtn = allDeleteBtns[allDeleteBtns.length - 1];
    await user.click(dialogDeleteBtn);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Internal error");
    });
  });

  it("shows ARCHIVED status badge with correct style", async () => {
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      const archivedBadge = screen.getByText("ARCHIVED");
      expect(archivedBadge.className).toContain("bg-status-warning-bg");
    });
  });

  it("shows ACTIVE status badge with correct style", async () => {
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={true} />);

    await waitFor(() => {
      const activeBadge = screen.getByText("ACTIVE");
      expect(activeBadge.className).toContain("bg-status-success-bg");
    });
  });

  it("does not show edit/delete/archive buttons when canManage is false", async () => {
    mockListRubrics.mockResolvedValueOnce(mockRubrics);
    const RubricListView = await loadComponent();
    render(<RubricListView canManage={false} />);

    await waitFor(() => {
      expect(screen.getByText("Writing Rubric")).toBeInTheDocument();
    });

    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
    expect(screen.queryByText("Archive")).not.toBeInTheDocument();
  });
});
