import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockOnChange = vi.fn();

function setupModuleMocks() {
  vi.doMock("@/lib/assignment-template-api", () => ({}));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import(
    "@/components/assignment-templates/NumberScaleFields"
  );
  return imported.default;
}

describe("NumberScaleFields", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Min, Max, and Target labels", async () => {
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 1, max: 5, target: null }}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText("Min")).toBeInTheDocument();
    expect(screen.getByText("Max")).toBeInTheDocument();
    expect(screen.getByText("Target (optional)")).toBeInTheDocument();
  });

  it("renders with default min=1 and max=5 when undefined", async () => {
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields data={{}} onChange={mockOnChange} />
    );

    const inputs = screen.getAllByRole("spinbutton");
    expect(inputs[0]).toHaveValue(1); // min default
    expect(inputs[1]).toHaveValue(5); // max default
  });

  it("renders provided min and max values", async () => {
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 0, max: 10, target: 5 }}
        onChange={mockOnChange}
      />
    );

    const inputs = screen.getAllByRole("spinbutton");
    expect(inputs[0]).toHaveValue(0);
    expect(inputs[1]).toHaveValue(10);
    expect(inputs[2]).toHaveValue(5);
  });

  it("calls onChange when min is changed", async () => {
    const user = userEvent.setup();
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 1, max: 5, target: null }}
        onChange={mockOnChange}
      />
    );

    const inputs = screen.getAllByRole("spinbutton");
    await user.clear(inputs[0]);
    await user.type(inputs[0], "0");

    expect(mockOnChange).toHaveBeenCalled();
  });

  it("calls onChange when max is changed", async () => {
    const user = userEvent.setup();
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 1, max: 5, target: null }}
        onChange={mockOnChange}
      />
    );

    const inputs = screen.getAllByRole("spinbutton");
    await user.clear(inputs[1]);
    await user.type(inputs[1], "10");

    expect(mockOnChange).toHaveBeenCalled();
  });

  it("calls onChange when target is changed", async () => {
    const user = userEvent.setup();
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 1, max: 5, target: null }}
        onChange={mockOnChange}
      />
    );

    const inputs = screen.getAllByRole("spinbutton");
    await user.type(inputs[2], "3");

    expect(mockOnChange).toHaveBeenCalled();
  });

  it("shows validation error when min >= max", async () => {
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 5, max: 5 }}
        onChange={mockOnChange}
      />
    );

    expect(
      screen.getByText("Min must be less than Max")
    ).toBeInTheDocument();
  });

  it("shows validation error when min > max", async () => {
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 10, max: 5 }}
        onChange={mockOnChange}
      />
    );

    expect(
      screen.getByText("Min must be less than Max")
    ).toBeInTheDocument();
  });

  it("does not show validation error when min < max", async () => {
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 1, max: 5 }}
        onChange={mockOnChange}
      />
    );

    expect(
      screen.queryByText("Min must be less than Max")
    ).not.toBeInTheDocument();
  });

  it("clears target to null when emptied", async () => {
    const user = userEvent.setup();
    const NumberScaleFields = await loadComponent();
    render(
      <NumberScaleFields
        data={{ min: 1, max: 5, target: 3 }}
        onChange={mockOnChange}
      />
    );

    const inputs = screen.getAllByRole("spinbutton");
    await user.clear(inputs[2]);

    // When cleared, target should be set to null
    const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
    expect(lastCall.target).toBeNull();
  });
});
