import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

function setupModuleMocks() {
  vi.doMock("@/lib/rubric-api", () => ({}));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/rubrics/RubricGridPreview");
  return imported.default;
}

describe("RubricGridPreview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty message when no criteria are provided", async () => {
    const RubricGridPreview = await loadComponent();
    render(<RubricGridPreview criteria={[]} />);
    expect(screen.getByText("Add criteria to see the rubric grid preview.")).toBeInTheDocument();
  });

  it("renders default title", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[{ title: "Grammar", weight: 1, levels: [{ label: "Good", points: 3, description: "" }] }]}
      />
    );
    expect(screen.getByText("Live Rubric Grid Preview")).toBeInTheDocument();
  });

  it("renders custom title", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[{ title: "Grammar", weight: 1, levels: [{ label: "Good", points: 3, description: "" }] }]}
        title="Custom Title"
      />
    );
    expect(screen.getByText("Custom Title")).toBeInTheDocument();
  });

  it("renders criterion titles in the table", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          { title: "Grammar", weight: 1, levels: [{ label: "Good", points: 3, description: "" }] },
          { title: "Spelling", weight: 2, levels: [{ label: "Fair", points: 2, description: "" }] },
        ]}
      />
    );
    expect(screen.getByText("Grammar")).toBeInTheDocument();
    expect(screen.getByText("Spelling")).toBeInTheDocument();
  });

  it("shows weighted max total", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          { title: "C1", weight: 2, levels: [{ label: "L1", points: 5, description: "" }] },
          { title: "C2", weight: 1, levels: [{ label: "L1", points: 3, description: "" }] },
        ]}
      />
    );
    // 2*5 + 1*3 = 13
    expect(screen.getByText("Weighted max total: 13.00 points")).toBeInTheDocument();
  });

  it("renders level labels and points", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          {
            title: "C1",
            weight: 1,
            levels: [
              { label: "Excellent", points: 5, description: "Top marks" },
              { label: "Good", points: 3, description: "" },
            ],
          },
        ]}
      />
    );
    expect(screen.getByText("Excellent")).toBeInTheDocument();
    expect(screen.getByText("5 pts")).toBeInTheDocument();
    expect(screen.getByText("Good")).toBeInTheDocument();
    expect(screen.getByText("3 pts")).toBeInTheDocument();
    expect(screen.getByText("Top marks")).toBeInTheDocument();
  });

  it("renders level description when present", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          {
            title: "C1",
            weight: 1,
            levels: [{ label: "L1", points: 1, description: "Some description" }],
          },
        ]}
      />
    );
    expect(screen.getByText("Some description")).toBeInTheDocument();
  });

  it("shows dash for missing levels when criteria have different level counts", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          {
            title: "C1",
            weight: 1,
            levels: [
              { label: "L1", points: 5, description: "" },
              { label: "L2", points: 3, description: "" },
            ],
          },
          {
            title: "C2",
            weight: 1,
            levels: [{ label: "L1", points: 2, description: "" }],
          },
        ]}
      />
    );
    // C2 only has 1 level but maxLevels is 2, so a "-" should appear
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("shows fallback label when level label is empty", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          {
            title: "C1",
            weight: 1,
            levels: [{ label: "", points: 1, description: "" }],
          },
        ]}
      />
    );
    // "Level 1" appears both as column header and as fallback label in the cell
    expect(screen.getAllByText("Level 1").length).toBeGreaterThanOrEqual(2);
  });

  it("shows fallback criterion title when criterion title is empty", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          {
            title: "",
            weight: 1,
            levels: [{ label: "L1", points: 1, description: "" }],
          },
        ]}
      />
    );
    expect(screen.getByText("Criterion 1")).toBeInTheDocument();
  });

  it("displays criterion description when provided", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          {
            title: "C1",
            description: "Criterion desc here",
            weight: 1,
            levels: [{ label: "L1", points: 1, description: "" }],
          },
        ]}
      />
    );
    expect(screen.getByText("Criterion desc here")).toBeInTheDocument();
  });

  it("displays criterion weight value", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          {
            title: "C1",
            weight: 2.5,
            levels: [{ label: "L1", points: 1, description: "" }],
          },
        ]}
      />
    );
    expect(screen.getByText("2.5")).toBeInTheDocument();
  });

  it("handles criteria with no levels", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[{ title: "Empty Criterion", weight: 1 }]}
      />
    );
    expect(screen.getByText("Empty Criterion")).toBeInTheDocument();
    expect(screen.getByText("Weighted max total: 0.00 points")).toBeInTheDocument();
  });

  it("renders level column headers", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[
          {
            title: "C1",
            weight: 1,
            levels: [
              { label: "A", points: 5, description: "" },
              { label: "B", points: 3, description: "" },
              { label: "C", points: 1, description: "" },
            ],
          },
        ]}
      />
    );
    // Column headers
    expect(screen.getByText("Level 1")).toBeInTheDocument();
    expect(screen.getByText("Level 2")).toBeInTheDocument();
    expect(screen.getByText("Level 3")).toBeInTheDocument();
  });

  it("renders table header cells", async () => {
    const RubricGridPreview = await loadComponent();
    render(
      <RubricGridPreview
        criteria={[{ title: "C1", weight: 1, levels: [{ label: "L1", points: 1, description: "" }] }]}
      />
    );
    expect(screen.getByText("Criterion")).toBeInTheDocument();
    expect(screen.getByText("Weight")).toBeInTheDocument();
  });
});
