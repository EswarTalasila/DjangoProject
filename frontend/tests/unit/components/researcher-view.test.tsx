import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/dashboard/views/ResearcherView"
  );
  return imported.default;
}

describe("ResearcherView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders dashboard heading", async () => {
    const ResearcherView = await loadComponent();
    render(<ResearcherView />);

    expect(screen.getByText("Researcher Dashboard")).toBeInTheDocument();
  });

  it("renders description text", async () => {
    const ResearcherView = await loadComponent();
    render(<ResearcherView />);

    expect(
      screen.getByText(
        "Build assignment templates, manage teacher-facing setup, and review anonymized analytics."
      )
    ).toBeInTheDocument();
  });

  it("renders Assignment Templates & Rubrics section", async () => {
    const ResearcherView = await loadComponent();
    render(<ResearcherView />);

    expect(
      screen.getByText("Assignment Templates & Rubrics")
    ).toBeInTheDocument();
    expect(screen.getByText("Open Assignment Templates")).toBeInTheDocument();
    expect(screen.getByText("Open Rubrics")).toBeInTheDocument();
  });

  it("renders Teacher Operations section", async () => {
    const ResearcherView = await loadComponent();
    render(<ResearcherView />);

    expect(screen.getByText("Teacher Operations")).toBeInTheDocument();
    expect(screen.getByText("Open User Management")).toBeInTheDocument();
    expect(
      screen.getByText("Open Registration Codes")
    ).toBeInTheDocument();
  });

  it("renders Analytics & Archive section", async () => {
    const ResearcherView = await loadComponent();
    render(<ResearcherView />);

    expect(screen.getByText("Analytics & Archive")).toBeInTheDocument();
    expect(screen.getByText("Open Visualizations")).toBeInTheDocument();
    expect(screen.getByText("Open Archive Manager")).toBeInTheDocument();
  });

  it("has correct link targets", async () => {
    const ResearcherView = await loadComponent();
    render(<ResearcherView />);

    const assignmentTemplatesLink = screen
      .getByText("Open Assignment Templates")
      .closest("a");
    expect(assignmentTemplatesLink).toHaveAttribute(
      "href",
      "/dashboard/assignment-templates"
    );

    const rubricsLink = screen.getByText("Open Rubrics").closest("a");
    expect(rubricsLink).toHaveAttribute("href", "/dashboard/rubrics");

    const staffLink = screen
      .getByText("Open User Management")
      .closest("a");
    expect(staffLink).toHaveAttribute("href", "/dashboard/staff");

    const codesLink = screen
      .getByText("Open Registration Codes")
      .closest("a");
    expect(codesLink).toHaveAttribute("href", "/dashboard/codes");

    const vizLink = screen
      .getByText("Open Visualizations")
      .closest("a");
    expect(vizLink).toHaveAttribute("href", "/dashboard/visualizations");

    const archiveLink = screen
      .getByText("Open Archive Manager")
      .closest("a");
    expect(archiveLink).toHaveAttribute(
      "href",
      "/dashboard/archive-manager"
    );
  });
});
