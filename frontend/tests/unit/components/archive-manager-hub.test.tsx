import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => "/dashboard/archives",
  }));
  vi.doMock("@/components/archive/QuickExportTab", () => ({
    default: () => <div>QuickExportTab</div>,
  }));
  vi.doMock("@/components/archive/PackageBuilderTab", () => ({
    default: () => <div>PackageBuilderTab</div>,
  }));
  vi.doMock("@/components/archive/DataArchivesTab", () => ({
    default: () => <div>DataArchivesTab</div>,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const mod = await import("@/components/archive/ArchiveManagerHub");
  return mod.default;
}

describe("ArchiveManagerHub", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the header", async () => {
    const ArchiveManagerHub = await loadComponent();
    render(<ArchiveManagerHub role="ADMIN" canExportIdentifiable={true} />);
    expect(screen.getByText("Archive Manager")).toBeInTheDocument();
  });

  it("renders Quick Export and Package Builder tabs", async () => {
    const ArchiveManagerHub = await loadComponent();
    render(<ArchiveManagerHub role="ADMIN" canExportIdentifiable={true} />);
    expect(screen.getByText("Quick Export")).toBeInTheDocument();
    expect(screen.getByText("Package Builder")).toBeInTheDocument();
  });

  it("renders Data Archives tab for ADMIN role", async () => {
    const ArchiveManagerHub = await loadComponent();
    render(<ArchiveManagerHub role="ADMIN" canExportIdentifiable={true} />);
    expect(screen.getByText("Data Archives")).toBeInTheDocument();
  });

  it("renders Data Archives tab for RESEARCHER role", async () => {
    const ArchiveManagerHub = await loadComponent();
    render(<ArchiveManagerHub role="RESEARCHER" canExportIdentifiable={false} />);
    expect(screen.getByText("Data Archives")).toBeInTheDocument();
  });

  it("does NOT render Data Archives tab for TEACHER role", async () => {
    const ArchiveManagerHub = await loadComponent();
    render(<ArchiveManagerHub role="TEACHER" canExportIdentifiable={false} />);
    expect(screen.queryByText("Data Archives")).not.toBeInTheDocument();
  });

  it("renders QuickExportTab content by default", async () => {
    const ArchiveManagerHub = await loadComponent();
    render(<ArchiveManagerHub role="ADMIN" canExportIdentifiable={true} />);
    expect(screen.getByText("QuickExportTab")).toBeInTheDocument();
  });
});
