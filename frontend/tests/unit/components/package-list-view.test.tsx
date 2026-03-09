import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

const mockListWorkspaces = vi.fn();
const mockListCourses = vi.fn();
const mockCreateWorkspace = vi.fn();
const mockDeleteWorkspace = vi.fn();
const mockOnOpenPackage = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("sonner", () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
  vi.doMock("@/lib/package-api", () => ({
    listWorkspaces: mockListWorkspaces,
    createWorkspace: mockCreateWorkspace,
    deleteWorkspace: mockDeleteWorkspace,
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/lib/utils", () => ({
    toErrorMessage: (e: unknown) =>
      e instanceof Error ? e.message : "Unknown error",
    cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/archive/PackageListView");
  return imported.default;
}

async function renderPackageListAndWait() {
  const PackageListView = await loadComponent();
  render(
    <PackageListView
      role="RESEARCHER"
      canExportIdentifiable={true}
      onOpenPackage={mockOnOpenPackage}
    />
  );
  await waitFor(() => {
    expect(
      screen.queryByText("Loading packages...")
    ).not.toBeInTheDocument();
  });
}

const mockPackages = [
  {
    id: 1,
    name: "Test Package",
    description: "A test package",
    status: "DRAFT",
    scopeCourseId: null,
    nodes: [],
    createdAt: "2025-01-01T00:00:00Z",
    updatedAt: "2025-01-02T00:00:00Z",
  },
  {
    id: 2,
    name: "Another Package",
    description: "",
    status: "SEALED",
    scopeCourseId: 1,
    nodes: [],
    createdAt: "2025-01-01T00:00:00Z",
    updatedAt: "2025-01-03T00:00:00Z",
  },
];

const mockCoursesList = [
  {
    id: 1,
    name: "Intro to CS",
    studentCount: 30,
    assignmentIds: [],
    teacherId: 1,
    teacherName: "Prof Smith",
    createdAt: "2025-01-01",
    status: "ACTIVE",
  },
];

describe("PackageListView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", async () => {
    mockListWorkspaces.mockReturnValue(new Promise(() => {}));
    mockListCourses.mockReturnValue(new Promise(() => {}));
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    expect(screen.getByText("Loading packages...")).toBeInTheDocument();
  });

  it("renders empty state when no packages", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce([]);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    await waitFor(() => {
      expect(
        screen.getByText(
          "No packages yet. Create one to organize your data exports."
        )
      ).toBeInTheDocument();
    });
  });

  it("renders package list when packages exist", async () => {
    mockListWorkspaces.mockResolvedValueOnce(mockPackages);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Test Package")).toBeInTheDocument();
      expect(screen.getByText("Another Package")).toBeInTheDocument();
    });
  });

  it("renders description or em dash for packages", async () => {
    mockListWorkspaces.mockResolvedValueOnce(mockPackages);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("A test package")).toBeInTheDocument();
      expect(screen.getByText("\u2014")).toBeInTheDocument();
    });
  });

  it("calls onOpenPackage when package card clicked", async () => {
    mockListWorkspaces.mockResolvedValueOnce(mockPackages);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Test Package")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Test Package"));
    expect(mockOnOpenPackage).toHaveBeenCalledWith(1);
  });

  it("shows Your Packages heading", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce([]);
    await renderPackageListAndWait();
    expect(screen.getByText("Your Packages")).toBeInTheDocument();
  });

  it("shows New Package and Refresh buttons", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce([]);
    await renderPackageListAndWait();
    expect(screen.getByText("New Package")).toBeInTheDocument();
    expect(screen.getByText("Refresh")).toBeInTheDocument();
  });

  it("calls loadData again when Refresh clicked", async () => {
    mockListWorkspaces.mockResolvedValue([]);
    mockListCourses.mockResolvedValue([]);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.queryByText("Loading packages...")).not.toBeInTheDocument();
    });
    await user.click(screen.getByText("Refresh"));
    // listWorkspaces called for initial load + refresh
    await waitFor(() => {
      expect(mockListWorkspaces).toHaveBeenCalledTimes(2);
    });
  });

  it("shows error toast when loading fails", async () => {
    mockListWorkspaces.mockRejectedValueOnce(new Error("Network error"));
    mockListCourses.mockResolvedValueOnce([]);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Network error");
    });
  });

  it("shows delete confirmation dialog with package name", async () => {
    mockListWorkspaces.mockResolvedValueOnce(mockPackages);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Test Package")).toBeInTheDocument();
    });
    // Click delete button (Trash2 icon button)
    const deleteButtons = screen.getAllByTitle("Delete package");
    await user.click(deleteButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("Delete Package")).toBeInTheDocument();
    });
  });

  it("opens create dialog when New Package is clicked", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.queryByText("Loading packages...")).not.toBeInTheDocument();
    });
    await user.click(screen.getByText("New Package"));
    await waitFor(() => {
      expect(screen.getByText("Create a New Package")).toBeInTheDocument();
    });
  });

  it("creates package successfully", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockCreateWorkspace.mockResolvedValueOnce({ id: 42, name: "New Pkg" });
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.queryByText("Loading packages...")).not.toBeInTheDocument();
    });
    await user.click(screen.getByText("New Package"));
    await waitFor(() => {
      expect(screen.getByText("Create a New Package")).toBeInTheDocument();
    });
    await user.type(screen.getByPlaceholderText("My Data Package"), "New Pkg");
    await user.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(mockCreateWorkspace).toHaveBeenCalledWith({
        name: "New Pkg",
        description: undefined,
        scopeCourseId: null,
      });
      expect(mockToastSuccess).toHaveBeenCalledWith("Package created.");
      expect(mockOnOpenPackage).toHaveBeenCalledWith(42);
    });
  });

  it("shows error toast when create package fails", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce([]);
    mockCreateWorkspace.mockRejectedValueOnce(new Error("Create failed"));
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.queryByText("Loading packages...")).not.toBeInTheDocument();
    });
    await user.click(screen.getByText("New Package"));
    await waitFor(() => {
      expect(screen.getByText("Create a New Package")).toBeInTheDocument();
    });
    await user.type(screen.getByPlaceholderText("My Data Package"), "Test");
    await user.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Create failed");
    });
  });

  it("shows error toast when name is empty on create", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce([]);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.queryByText("Loading packages...")).not.toBeInTheDocument();
    });
    await user.click(screen.getByText("New Package"));
    await waitFor(() => {
      expect(screen.getByText("Create a New Package")).toBeInTheDocument();
    });
    // Click Create without entering name
    await user.click(screen.getByText("Create"));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Package name is required.");
    });
  });

  it("deletes package successfully when confirmed", async () => {
    mockListWorkspaces.mockResolvedValueOnce(mockPackages);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockDeleteWorkspace.mockResolvedValueOnce({});
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Test Package")).toBeInTheDocument();
    });
    // Open delete dialog
    const deleteButtons = screen.getAllByTitle("Delete package");
    await user.click(deleteButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("Delete Package")).toBeInTheDocument();
    });
    // Confirm delete
    const confirmDeleteBtn = screen.getAllByText("Delete").find(
      (el) => el.closest("[class*='AlertDialogAction']") || el.closest("button[class*='destructive']")
    );
    if (confirmDeleteBtn) {
      await user.click(confirmDeleteBtn);
    }
    await waitFor(() => {
      expect(mockDeleteWorkspace).toHaveBeenCalledWith(1);
      expect(mockToastSuccess).toHaveBeenCalledWith('"Test Package" deleted.');
    });
  });

  it("shows error toast when delete package fails", async () => {
    mockListWorkspaces.mockResolvedValueOnce(mockPackages);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockDeleteWorkspace.mockRejectedValueOnce(new Error("Delete error"));
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Test Package")).toBeInTheDocument();
    });
    const deleteButtons = screen.getAllByTitle("Delete package");
    await user.click(deleteButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("Delete Package")).toBeInTheDocument();
    });
    const confirmDeleteBtn = screen.getAllByText("Delete").find(
      (el) => el.closest("[class*='AlertDialogAction']") || el.closest("button[class*='destructive']")
    );
    if (confirmDeleteBtn) {
      await user.click(confirmDeleteBtn);
    }
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Delete error");
    });
  });

  it("creates package with description and course", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    mockCreateWorkspace.mockResolvedValueOnce({ id: 50, name: "Full Pkg" });
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.queryByText("Loading packages...")).not.toBeInTheDocument();
    });
    await user.click(screen.getByText("New Package"));
    await waitFor(() => {
      expect(screen.getByText("Create a New Package")).toBeInTheDocument();
    });
    await user.type(screen.getByPlaceholderText("My Data Package"), "Full Pkg");
    await user.type(screen.getByPlaceholderText("Optional description"), "My desc");
    await user.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(mockCreateWorkspace).toHaveBeenCalledWith({
        name: "Full Pkg",
        description: "My desc",
        scopeCourseId: null,
      });
    });
  });

  it("cancels create dialog when Cancel is clicked", async () => {
    mockListWorkspaces.mockResolvedValueOnce([]);
    mockListCourses.mockResolvedValueOnce([]);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.queryByText("Loading packages...")).not.toBeInTheDocument();
    });
    await user.click(screen.getByText("New Package"));
    await waitFor(() => {
      expect(screen.getByText("Create a New Package")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Cancel"));
    // Dialog should close (Create a New Package should not be visible)
    await waitFor(() => {
      expect(screen.queryByText("Create a New Package")).not.toBeInTheDocument();
    });
  });

  it("shows package update date", async () => {
    mockListWorkspaces.mockResolvedValueOnce(mockPackages);
    mockListCourses.mockResolvedValueOnce(mockCoursesList);
    const PackageListView = await loadComponent();
    render(
      <PackageListView
        role="RESEARCHER"
        canExportIdentifiable={true}
        onOpenPackage={mockOnOpenPackage}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Test Package")).toBeInTheDocument();
    });
    // Should show formatted dates from updatedAt
    const dateText = new Date("2025-01-02T00:00:00Z").toLocaleDateString();
    expect(screen.getByText(dateText)).toBeInTheDocument();
  });
});
