import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { BuildJob, ValidationResult } from "@/lib/package-api";

const mockOnStrictModeChange = vi.fn();
const mockOnIncludeMetadataFilesChange = vi.fn();
const mockOnValidate = vi.fn();
const mockOnBuild = vi.fn();
const mockOnDownload = vi.fn();

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
  }));
  vi.doMock("sonner", () => ({
    toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/archive/PackageBuildBar");
  return imported.default;
}

const defaultProps = {
  canExportIdentifiable: true,
  role: "RESEARCHER" as const,
  strictMode: true,
  onStrictModeChange: mockOnStrictModeChange,
  includeMetadataFiles: true,
  onIncludeMetadataFilesChange: mockOnIncludeMetadataFilesChange,
  validationResult: null as ValidationResult | null,
  buildResult: null as BuildJob | null,
  isValidating: false,
  isBuilding: false,
  isDownloadingArtifact: false,
  onValidate: mockOnValidate,
  onBuild: mockOnBuild,
  onDownload: mockOnDownload,
};

describe("PackageBuildBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 'Not yet validated' when no validation result", async () => {
    const PackageBuildBar = await loadComponent();
    render(<PackageBuildBar {...defaultProps} />);
    expect(screen.getByText("Not yet validated")).toBeInTheDocument();
  });

  it("renders Validate and Build Package buttons", async () => {
    const PackageBuildBar = await loadComponent();
    render(<PackageBuildBar {...defaultProps} />);
    expect(screen.getByText("Validate")).toBeInTheDocument();
    expect(screen.getByText("Build Package")).toBeInTheDocument();
  });

  it("shows 'Checking...' when isValidating is true", async () => {
    const PackageBuildBar = await loadComponent();
    render(<PackageBuildBar {...defaultProps} isValidating={true} />);
    expect(screen.getByText("Checking...")).toBeInTheDocument();
  });

  it("shows 'Building...' when isBuilding is true", async () => {
    const PackageBuildBar = await loadComponent();
    render(<PackageBuildBar {...defaultProps} isBuilding={true} />);
    expect(screen.getByText("Building...")).toBeInTheDocument();
  });

  it("calls onValidate when Validate button clicked", async () => {
    const PackageBuildBar = await loadComponent();
    render(<PackageBuildBar {...defaultProps} />);
    const user = userEvent.setup();
    await user.click(screen.getByText("Validate"));
    expect(mockOnValidate).toHaveBeenCalledOnce();
  });

  it("calls onBuild when Build Package button clicked", async () => {
    const PackageBuildBar = await loadComponent();
    render(<PackageBuildBar {...defaultProps} />);
    const user = userEvent.setup();
    await user.click(screen.getByText("Build Package"));
    expect(mockOnBuild).toHaveBeenCalledOnce();
  });

  it("shows valid status when validation passes", async () => {
    const PackageBuildBar = await loadComponent();
    const validResult: ValidationResult = {
      valid: true,
      violations: [],
      warnings: [],
      fileCount: 3,
      estimatedRows: 100,
    };
    render(
      <PackageBuildBar {...defaultProps} validationResult={validResult} />
    );
    expect(screen.getByText(/Valid \(3 files/)).toBeInTheDocument();
  });

  it("shows issue count when validation has violations", async () => {
    const PackageBuildBar = await loadComponent();
    const invalidResult: ValidationResult = {
      valid: false,
      violations: [
        { code: "ERR_001", message: "Missing binding" },
        { code: "ERR_002", message: "Empty folder" },
      ],
      warnings: [],
      fileCount: 2,
      estimatedRows: 50,
    };
    render(
      <PackageBuildBar {...defaultProps} validationResult={invalidResult} />
    );
    expect(screen.getByText("2 issues found")).toBeInTheDocument();
  });

  it("shows singular 'issue' when only one violation", async () => {
    const PackageBuildBar = await loadComponent();
    const invalidResult: ValidationResult = {
      valid: false,
      violations: [{ code: "ERR_001", message: "Missing binding" }],
      warnings: [],
      fileCount: 1,
      estimatedRows: 10,
    };
    render(
      <PackageBuildBar {...defaultProps} validationResult={invalidResult} />
    );
    expect(screen.getByText("1 issue found")).toBeInTheDocument();
  });

  it("renders violation details when violations present", async () => {
    const PackageBuildBar = await loadComponent();
    const invalidResult: ValidationResult = {
      valid: false,
      violations: [
        { code: "ERR_001", message: "Missing binding" },
      ],
      warnings: [],
      fileCount: 1,
      estimatedRows: 10,
    };
    render(
      <PackageBuildBar {...defaultProps} validationResult={invalidResult} />
    );
    expect(screen.getByText("Issues")).toBeInTheDocument();
    expect(screen.getByText("[ERR_001] Missing binding")).toBeInTheDocument();
  });

  it("shows Download button when build completed with artifactId", async () => {
    const PackageBuildBar = await loadComponent();
    const buildResult: BuildJob = {
      id: 1,
      workspaceId: 1,
      status: "COMPLETED",
      strictMode: true,
      mode: "live",
      artifactId: 42,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: null,
    };
    render(
      <PackageBuildBar {...defaultProps} buildResult={buildResult} />
    );
    expect(screen.getByText("Download")).toBeInTheDocument();
  });

  it("calls onDownload when Download button clicked", async () => {
    const PackageBuildBar = await loadComponent();
    const buildResult: BuildJob = {
      id: 1,
      workspaceId: 1,
      status: "COMPLETED",
      strictMode: true,
      mode: "live",
      artifactId: 42,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: null,
    };
    render(
      <PackageBuildBar {...defaultProps} buildResult={buildResult} />
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Download"));
    expect(mockOnDownload).toHaveBeenCalledOnce();
  });

  it("does not show Download button for failed build", async () => {
    const PackageBuildBar = await loadComponent();
    const buildResult: BuildJob = {
      id: 1,
      workspaceId: 1,
      status: "FAILED",
      strictMode: true,
      mode: "live",
      artifactId: null as unknown as number,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: "Something went wrong",
    };
    render(
      <PackageBuildBar {...defaultProps} buildResult={buildResult} />
    );
    expect(screen.queryByText("Download")).not.toBeInTheDocument();
  });

  it("shows build result status and error message", async () => {
    const PackageBuildBar = await loadComponent();
    const buildResult: BuildJob = {
      id: 5,
      workspaceId: 1,
      status: "FAILED",
      strictMode: true,
      mode: "live",
      artifactId: null as unknown as number,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: "Build error occurred",
    };
    render(
      <PackageBuildBar {...defaultProps} buildResult={buildResult} />
    );
    expect(screen.getByText("Package #5: FAILED")).toBeInTheDocument();
    expect(screen.getByText("Build error occurred")).toBeInTheDocument();
  });

  it("shows researcher note when canExportIdentifiable is false and role is RESEARCHER", async () => {
    const PackageBuildBar = await loadComponent();
    render(
      <PackageBuildBar
        {...defaultProps}
        canExportIdentifiable={false}
        role="RESEARCHER"
      />
    );
    expect(
      screen.getByText(/Including names and emails is disabled/)
    ).toBeInTheDocument();
  });

  it("does not show researcher note for ADMIN role", async () => {
    const PackageBuildBar = await loadComponent();
    render(
      <PackageBuildBar
        {...defaultProps}
        canExportIdentifiable={false}
        role="ADMIN"
      />
    );
    expect(
      screen.queryByText(/Including names and emails is disabled/)
    ).not.toBeInTheDocument();
  });

  it("renders Build Options collapsible trigger", async () => {
    const PackageBuildBar = await loadComponent();
    render(<PackageBuildBar {...defaultProps} />);
    expect(screen.getByText("Build Options")).toBeInTheDocument();
  });

  it("shows 'Downloading...' when isDownloadingArtifact is true", async () => {
    const PackageBuildBar = await loadComponent();
    const buildResult: BuildJob = {
      id: 1,
      workspaceId: 1,
      status: "COMPLETED",
      strictMode: true,
      mode: "live",
      artifactId: 42,
      createdAt: "2025-01-01",
      finishedAt: "2025-01-01",
      errorMessage: null,
    };
    render(
      <PackageBuildBar
        {...defaultProps}
        buildResult={buildResult}
        isDownloadingArtifact={true}
      />
    );
    expect(screen.getByText("Downloading...")).toBeInTheDocument();
  });
});
