import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

function setupModuleMocks() {
  vi.doMock("@/lib/rubric-api", () => ({}));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/rubrics/CriterionBlock");
  return imported.default;
}

describe("CriterionBlock", () => {
  const baseCriterion = {
    title: "Grammar",
    description: "Proper grammar usage",
    weight: 1.5,
    levels: [
      { label: "Excellent", points: 5, description: "No errors" },
      { label: "Good", points: 3, description: "Few errors" },
    ],
  };

  let onChange: ReturnType<typeof vi.fn>;
  let onRemove: ReturnType<typeof vi.fn>;
  let onMoveUp: ReturnType<typeof vi.fn>;
  let onMoveDown: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    onChange = vi.fn();
    onRemove = vi.fn();
    onMoveUp = vi.fn();
    onMoveDown = vi.fn();
  });

  it("renders criterion header with correct index", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={onMoveDown} />
    );
    expect(screen.getByText("Criterion 1")).toBeInTheDocument();
  });

  it("renders title, weight, and description inputs", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    expect(screen.getByDisplayValue("Grammar")).toBeInTheDocument();
    expect(screen.getByDisplayValue("150")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Proper grammar usage")).toBeInTheDocument();
  });

  it("shows levels count", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    expect(screen.getByText("Levels (2)")).toBeInTheDocument();
  });

  it("renders level rows for each level", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    expect(screen.getByDisplayValue("Excellent")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Good")).toBeInTheDocument();
  });

  it("calls onChange when title is changed", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    const titleInput = screen.getByDisplayValue("Grammar");
    fireEvent.change(titleInput, { target: { value: "Spelling" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ title: "Spelling" }));
  });

  it("calls onChange when weight is changed", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    const weightInput = screen.getByDisplayValue("150");
    fireEvent.change(weightInput, { target: { value: "2" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ weight: 0.02 }));
  });

  it("calls onChange when description is changed", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    const descInput = screen.getByDisplayValue("Proper grammar usage");
    fireEvent.change(descInput, { target: { value: "Updated" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ description: "Updated" }));
  });

  it("calls onRemove when trash button is clicked", async () => {
    const CriterionBlock = await loadComponent();
    const user = userEvent.setup();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    // The criterion-level trash button (not the level remove buttons)
    // It's the only button with text-destructive in the header area
    const buttons = screen.getAllByRole("button");
    const trashBtn = buttons.find(
      (b) => b.className.includes("text-destructive") && !b.closest("[class*='flex items-end']")
    );
    expect(trashBtn).toBeDefined();
    await user.click(trashBtn!);
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it("shows move up button when onMoveUp is provided", async () => {
    const CriterionBlock = await loadComponent();
    const user = userEvent.setup();
    render(
      <CriterionBlock index={1} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={onMoveUp} onMoveDown={null} />
    );
    const buttons = screen.getAllByRole("button");
    // First icon button is move up
    await user.click(buttons[0]);
    expect(onMoveUp).toHaveBeenCalledOnce();
  });

  it("shows move down button when onMoveDown is provided", async () => {
    const CriterionBlock = await loadComponent();
    const user = userEvent.setup();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={onMoveDown} />
    );
    const buttons = screen.getAllByRole("button");
    // First icon button is move down when no moveUp
    await user.click(buttons[0]);
    expect(onMoveDown).toHaveBeenCalledOnce();
  });

  it("adds a new level when Add Level is clicked", async () => {
    const CriterionBlock = await loadComponent();
    const user = userEvent.setup();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    const addBtn = screen.getByRole("button", { name: /add level/i });
    await user.click(addBtn);
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.levels).toHaveLength(3);
    expect(lastCall.levels[2]).toEqual({ label: "", points: 0, description: "" });
  });

  it("handles criterion with no levels", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={{ title: "Empty", weight: 1 }} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    expect(screen.getByText("Levels (0)")).toBeInTheDocument();
  });

  it("handles criterion with undefined description", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={{ title: "Test", weight: 1, levels: [] }} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    const descInput = screen.getByPlaceholderText("Optional criterion description...");
    expect(descInput).toHaveValue("");
  });

  it("removes a level via LevelRow onRemove", async () => {
    const CriterionBlock = await loadComponent();
    const user = userEvent.setup();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    // Click the first level's remove button
    const removeButtons = screen.getAllByRole("button", { name: /remove level/i });
    await user.click(removeButtons[0]);
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.levels).toHaveLength(1);
  });

  it("updates a level via LevelRow onChange", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    // Change the first level's label
    const labelInput = screen.getByDisplayValue("Excellent");
    fireEvent.change(labelInput, { target: { value: "Outstanding" } });
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.levels[0].label).toBe("Outstanding");
  });

  it("defaults weight to 1 when non-numeric value entered", async () => {
    const CriterionBlock = await loadComponent();
    render(
      <CriterionBlock index={0} criterion={baseCriterion} onChange={onChange} onRemove={onRemove} onMoveUp={null} onMoveDown={null} />
    );
    const weightInput = screen.getByDisplayValue("150");
    fireEvent.change(weightInput, { target: { value: "" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ weight: 0.01 }));
  });
});
