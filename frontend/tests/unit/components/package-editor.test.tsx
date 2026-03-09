import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockListCourses = vi.fn();
const mockGetWorkspace = vi.fn();
const mockUpdateWorkspace = vi.fn();
const mockAddNode = vi.fn();
const mockUpdateNode = vi.fn();
const mockDeleteNode = vi.fn();
const mockValidateWorkspace = vi.fn();
const mockBuildWorkspace = vi.fn();
const mockDownloadArtifact = vi.fn();
const mockReorderNode = vi.fn();
const mockOnBack = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
const mockToastInfo = vi.fn();
const mockTriggerBrowserDownload = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("sonner", () => ({
    toast: {
      success: mockToastSuccess,
      error: mockToastError,
      info: mockToastInfo,
    },
  }));
  vi.doMock("@/lib/course-api", () => ({
    listCourses: mockListCourses,
  }));
  vi.doMock("@/lib/package-api", () => ({
    getWorkspace: mockGetWorkspace,
    updateWorkspace: mockUpdateWorkspace,
    addNode: mockAddNode,
    updateNode: mockUpdateNode,
    deleteNode: mockDeleteNode,
    validateWorkspace: mockValidateWorkspace,
    buildWorkspace: mockBuildWorkspace,
    downloadArtifact: mockDownloadArtifact,
    reorderNode: mockReorderNode,
  }));
  vi.doMock("@/lib/utils", () => ({
    toErrorMessage: (e: unknown) =>
      e instanceof Error ? e.message : "Unknown error",
    triggerBrowserDownload: mockTriggerBrowserDownload,
    cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
  }));
  // Mock child components that are imported from same archive folder
  vi.doMock("@/components/archive/DataCatalog", () => ({
    default: ({ onAddItem }: { onAddItem: (config: unknown) => void }) => (
      <div data-testid="data-catalog">
        <button
          onClick={() =>
            onAddItem({
              label: "Test Roster.csv",
              datasetBinding: "ROSTER",
              bindingCourseId: 1,
            })
          }
        >
          Add from catalog
        </button>
      </div>
    ),
  }));
  vi.doMock("@/components/archive/PackageBuildBar", () => ({
    default: (props: {
      onValidate: () => void;
      onBuild: () => void;
      onDownload: () => void;
      isValidating: boolean;
      isBuilding: boolean;
    }) => (
      <div data-testid="package-build-bar">
        <button onClick={props.onValidate}>
          {props.isValidating ? "Checking..." : "Validate"}
        </button>
        <button onClick={props.onBuild}>
          {props.isBuilding ? "Building..." : "Build Package"}
        </button>
        <button onClick={props.onDownload}>Download</button>
      </div>
    ),
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/archive/PackageEditor");
  return imported.default;
}

const emptyWorkspace = {
  id: 1,
  name: "Test Package",
  description: "A description",
  status: "DRAFT" as const,
  scopeCourseId: null,
  nodes: [],
  createdAt: "2025-01-01T00:00:00Z",
  updatedAt: "2025-01-02T00:00:00Z",
};

const workspaceWithNodes = {
  ...emptyWorkspace,
  nodes: [
    {
      id: 10,
      parentId: null,
      nodeType: "FOLDER" as const,
      label: "Data Folder",
      orderIndex: 0,
      datasetBinding: null,
      bindingCourseId: null,
      filters: null,
      identifiable: false,
      includeAnswers: false,
      sourceType: "LIVE" as const,
      snapshotId: null,
    },
    {
      id: 11,
      parentId: 10,
      nodeType: "FILE" as const,
      label: "Roster.csv",
      orderIndex: 0,
      datasetBinding: "ROSTER" as const,
      bindingCourseId: 1,
      filters: null,
      identifiable: false,
      includeAnswers: false,
      sourceType: "LIVE" as const,
      snapshotId: null,
    },
    {
      id: 12,
      parentId: null,
      nodeType: "FILE" as const,
      label: "Submissions.csv",
      orderIndex: 1,
      datasetBinding: "COURSE_SUBMISSIONS" as const,
      bindingCourseId: 1,
      filters: null,
      identifiable: false,
      includeAnswers: false,
      sourceType: "SNAPSHOT" as const,
      snapshotId: 5,
    },
  ],
};

const mockCourses = [
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

describe("PackageEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListCourses.mockResolvedValue(mockCourses);
  });

  it("renders loading state when workspace is loading", async () => {
    mockGetWorkspace.mockReturnValue(new Promise(() => {}));
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Loading package...")).toBeInTheDocument();
    });
  });

  it("renders 'Package not found' when workspace fails to load", async () => {
    mockGetWorkspace.mockRejectedValueOnce(new Error("Not found"));
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(
        screen.getByText(/Package not found/)
      ).toBeInTheDocument();
    });
  });

  it("renders Back to packages button during loading", async () => {
    mockGetWorkspace.mockReturnValue(new Promise(() => {}));
    mockListCourses.mockReturnValue(new Promise(() => {}));
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(
        screen.getByText("Back to packages")
      ).toBeInTheDocument();
    });
  });

  it("calls onBack when Back to packages button clicked", async () => {
    mockGetWorkspace.mockReturnValue(new Promise(() => {}));
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Back to packages"));
    expect(mockOnBack).toHaveBeenCalledOnce();
  });

  it("renders workspace name and save button after loading", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Save")).toBeInTheDocument();
    });
  });

  it("renders Explorer section after loading", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Explorer")).toBeInTheDocument();
    });
  });

  it("shows empty package message when no nodes", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(
        screen.getByText(
          /Your package is empty/
        )
      ).toBeInTheDocument();
    });
  });

  it("renders Catalog and Properties tabs", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Catalog")).toBeInTheDocument();
      expect(screen.getByText("Properties")).toBeInTheDocument();
    });
  });

  it("renders DataCatalog component", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(screen.getByTestId("data-catalog")).toBeInTheDocument();
    });
  });

  it("renders PackageBuildBar component", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("package-build-bar")
      ).toBeInTheDocument();
    });
  });

  it("renders folder and file nodes in tree", async () => {
    mockGetWorkspace.mockResolvedValueOnce(workspaceWithNodes);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Data Folder")).toBeInTheDocument();
      expect(screen.getByText("Submissions.csv")).toBeInTheDocument();
    });
  });

  it("shows Snapshot badge on snapshot file nodes", async () => {
    mockGetWorkspace.mockResolvedValueOnce(workspaceWithNodes);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Snapshot")).toBeInTheDocument();
    });
  });

  it("calls handleSaveWorkspace when Save clicked", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockUpdateWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Save")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(mockUpdateWorkspace).toHaveBeenCalledWith(1, {
        name: "Test Package",
        description: "A description",
        status: "DRAFT",
      });
    });
  });

  it("shows success toast after saving workspace", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockUpdateWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Save")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith("Package saved.");
    });
  });

  it("calls validateWorkspace when Validate clicked", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockValidateWorkspace.mockResolvedValueOnce({
      valid: true,
      violations: [],
      warnings: [],
      fileCount: 0,
      estimatedRows: 0,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Validate")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Validate"));
    await waitFor(() => {
      expect(mockValidateWorkspace).toHaveBeenCalledWith(1, {
        strictMode: true,
      });
    });
  });

  it("shows success toast when validation passes", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockValidateWorkspace.mockResolvedValueOnce({
      valid: true,
      violations: [],
      warnings: [],
      fileCount: 0,
      estimatedRows: 0,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Validate")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Validate"));
    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith("Package is ready to build!");
    });
  });

  it("shows error toast when validation finds issues", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockValidateWorkspace.mockResolvedValueOnce({
      valid: false,
      violations: [{ code: "ERR", message: "bad" }],
      warnings: [],
      fileCount: 0,
      estimatedRows: 0,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Validate")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Validate"));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Found 1 problem \u2014 see details below."
      );
    });
  });

  it("calls buildWorkspace when Build Package clicked", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockBuildWorkspace.mockResolvedValueOnce({
      id: 1,
      workspaceId: 1,
      status: "COMPLETED",
      strictMode: true,
      mode: "live",
      artifactId: 42,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: null,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Build Package")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Build Package"));
    await waitFor(() => {
      expect(mockBuildWorkspace).toHaveBeenCalledWith(1, {
        strictMode: true,
        includeMetadataFiles: true,
      });
    });
  });

  it("shows success toast when build completes", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockBuildWorkspace.mockResolvedValueOnce({
      id: 1,
      workspaceId: 1,
      status: "COMPLETED",
      strictMode: true,
      mode: "live",
      artifactId: 42,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: null,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Build Package")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Build Package"));
    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith(
        "Package created successfully."
      );
    });
  });

  it("adds node from catalog when catalog add is triggered", async () => {
    mockGetWorkspace.mockResolvedValue(emptyWorkspace);
    mockAddNode.mockResolvedValueOnce({
      id: 20,
      parentId: null,
      nodeType: "FILE",
      label: "Test Roster.csv",
      orderIndex: 0,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Add from catalog")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Add from catalog"));
    await waitFor(() => {
      expect(mockAddNode).toHaveBeenCalledWith(1, expect.objectContaining({
        nodeType: "FILE",
        label: "Test Roster.csv",
        datasetBinding: "ROSTER",
        bindingCourseId: 1,
      }));
    });
  });

  it("shows toast when catalog add succeeds", async () => {
    mockGetWorkspace.mockResolvedValue(emptyWorkspace);
    mockAddNode.mockResolvedValueOnce({
      id: 20,
      parentId: null,
      nodeType: "FILE",
      label: "Test Roster.csv",
      orderIndex: 0,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Add from catalog")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Add from catalog"));
    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith(
        "File added from catalog."
      );
    });
  });

  it("shows error toast when save workspace fails", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockUpdateWorkspace.mockRejectedValueOnce(new Error("Save failed"));
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Save")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Save failed");
    });
  });

  it("shows 'Select an item' message when Properties tab selected with no node", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Properties")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Properties"));
    await waitFor(() => {
      expect(
        screen.getByText(
          "Select an item in the tree to view its properties."
        )
      ).toBeInTheDocument();
    });
  });

  it("shows node properties when a file node is clicked", async () => {
    mockGetWorkspace.mockResolvedValueOnce(workspaceWithNodes);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    // Wait for nodes to render
    await waitFor(() => {
      expect(screen.getByText("Submissions.csv")).toBeInTheDocument();
    });
    // Click file node
    await user.click(screen.getByText("Submissions.csv"));
    // Switch to Properties tab
    await user.click(screen.getByText("Properties"));
    await waitFor(() => {
      expect(screen.getByText("Label")).toBeInTheDocument();
    });
  });

  it("shows folder properties without data source settings", async () => {
    mockGetWorkspace.mockResolvedValueOnce(workspaceWithNodes);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Data Folder")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Data Folder"));
    await user.click(screen.getByText("Properties"));
    await waitFor(() => {
      expect(
        screen.getByText(
          "Data source settings are only available for files."
        )
      ).toBeInTheDocument();
    });
  });

  it("renders the workspace name input with workspace name", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      const nameInput = screen.getByDisplayValue("Test Package");
      expect(nameInput).toBeInTheDocument();
    });
  });

  it("shows Delete Item dialog when delete node button clicked", async () => {
    mockGetWorkspace.mockResolvedValueOnce(workspaceWithNodes);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Data Folder")).toBeInTheDocument();
    });
    // Click node first to select it, then click Properties to see Delete button
    await user.click(screen.getByText("Data Folder"));
    await user.click(screen.getByText("Properties"));
    await waitFor(() => {
      // Find the Delete button in properties panel
      const deleteButtons = screen.getAllByText("Delete");
      expect(deleteButtons.length).toBeGreaterThan(0);
    });
    // Click Delete in properties panel to open confirm dialog
    const propDeleteBtn = screen.getAllByText("Delete").find(
      (el) => el.closest("button")?.className?.includes("destructive")
    );
    if (propDeleteBtn) {
      await user.click(propDeleteBtn);
      await waitFor(() => {
        expect(screen.getByText("Delete Item")).toBeInTheDocument();
      });
    }
  });

  it("renders 'Updated' timestamp", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    await waitFor(() => {
      expect(screen.getByText(/Updated/)).toBeInTheDocument();
    });
  });

  it("shows info toast when build starts", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockBuildWorkspace.mockResolvedValueOnce({
      id: 1,
      workspaceId: 1,
      status: "COMPLETED",
      strictMode: true,
      mode: "live",
      artifactId: 42,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: null,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Build Package")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Build Package"));
    await waitFor(() => {
      expect(mockToastInfo).toHaveBeenCalledWith(
        "Live data sources will be snapshotted automatically at build start."
      );
    });
  });

  it("shows error toast when build returns failed job with error", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockBuildWorkspace.mockResolvedValueOnce({
      id: 1,
      workspaceId: 1,
      status: "FAILED",
      strictMode: true,
      mode: "live",
      artifactId: null,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: "Missing required data",
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Build Package")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Build Package"));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Missing required data");
    });
  });

  it("shows generic error toast when build fails with no message", async () => {
    mockGetWorkspace.mockResolvedValueOnce(emptyWorkspace);
    mockBuildWorkspace.mockResolvedValueOnce({
      id: 1,
      workspaceId: 1,
      status: "FAILED",
      strictMode: true,
      mode: "live",
      artifactId: null,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: null,
    });
    const PackageEditor = await loadComponent();
    render(
      <PackageEditor
        workspaceId={1}
        role="RESEARCHER"
        canExportIdentifiable={true}
        onBack={mockOnBack}
      />
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Build Package")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Build Package"));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        "Package creation failed."
      );
    });
  });
});
