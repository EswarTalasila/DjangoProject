import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { LevelInput } from "@/lib/rubric-api";

function setupModuleMocks() {
  vi.doMock("@/lib/rubric-api", () => ({}));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/rubrics/LevelRow");
  return imported.default;
}

describe("LevelRow", () => {
  const baseLevel = { label: "Good", points: 3, description: "Solid work" };
  let onChange: ReturnType<typeof vi.fn<(updated: LevelInput) => void>>;
  let onRemove: ReturnType<typeof vi.fn<() => void>>;

  beforeEach(() => {
    vi.clearAllMocks();
    onChange = vi.fn<(updated: LevelInput) => void>();
    onRemove = vi.fn<() => void>();
  });

  it("renders label, points, and description inputs", async () => {
    const LevelRow = await loadComponent();
    render(<LevelRow index={0} level={baseLevel} onChange={onChange} onRemove={onRemove} />);

    expect(screen.getByPlaceholderText("Level 1 label")).toHaveValue("Good");
    expect(screen.getByDisplayValue("3")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Optional description")).toHaveValue("Solid work");
  });

  it("calls onChange when label is changed", async () => {
    const LevelRow = await loadComponent();
    render(<LevelRow index={0} level={baseLevel} onChange={onChange} onRemove={onRemove} />);

    const labelInput = screen.getByPlaceholderText("Level 1 label");
    fireEvent.change(labelInput, { target: { value: "Excellent" } });

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ label: "Excellent" }));
  });

  it("calls onChange when points is changed", async () => {
    const LevelRow = await loadComponent();
    render(<LevelRow index={0} level={baseLevel} onChange={onChange} onRemove={onRemove} />);

    const pointsInput = screen.getByDisplayValue("3");
    fireEvent.change(pointsInput, { target: { value: "5" } });

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ points: 5 }));
  });

  it("calls onChange when description is changed", async () => {
    const LevelRow = await loadComponent();
    render(<LevelRow index={0} level={baseLevel} onChange={onChange} onRemove={onRemove} />);

    const descInput = screen.getByPlaceholderText("Optional description");
    fireEvent.change(descInput, { target: { value: "New desc" } });

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ description: "New desc" }));
  });

  it("calls onRemove when remove button is clicked", async () => {
    const LevelRow = await loadComponent();
    const user = userEvent.setup();
    render(<LevelRow index={0} level={baseLevel} onChange={onChange} onRemove={onRemove} />);

    const removeBtn = screen.getByRole("button", { name: /remove level/i });
    await user.click(removeBtn);
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it("uses correct placeholder for different index", async () => {
    const LevelRow = await loadComponent();
    render(<LevelRow index={2} level={{ label: "", points: 0, description: "" }} onChange={onChange} onRemove={onRemove} />);
    expect(screen.getByPlaceholderText("Level 3 label")).toBeInTheDocument();
  });

  it("handles level with undefined description", async () => {
    const LevelRow = await loadComponent();
    render(<LevelRow index={0} level={{ label: "Test", points: 1 }} onChange={onChange} onRemove={onRemove} />);
    const descInput = screen.getByPlaceholderText("Optional description");
    expect(descInput).toHaveValue("");
  });

  it("defaults points to 0 when non-numeric value entered", async () => {
    const LevelRow = await loadComponent();
    render(<LevelRow index={0} level={baseLevel} onChange={onChange} onRemove={onRemove} />);

    const pointsInput = screen.getByDisplayValue("3");
    fireEvent.change(pointsInput, { target: { value: "" } });

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ points: 0 }));
  });
});
