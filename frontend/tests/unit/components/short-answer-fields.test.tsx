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
    "@/components/assignment-templates/ShortAnswerFields"
  );
  return imported.default;
}

describe("ShortAnswerFields", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders both checkboxes with labels", async () => {
    const ShortAnswerFields = await loadComponent();
    render(
      <ShortAnswerFields
        data={{ caseSensitive: false, trim: true }}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText("Case Sensitive")).toBeInTheDocument();
    expect(screen.getByText("Trim Whitespace")).toBeInTheDocument();
  });

  it("renders helper text for case sensitive", async () => {
    const ShortAnswerFields = await loadComponent();
    render(
      <ShortAnswerFields
        data={{ caseSensitive: false, trim: true }}
        onChange={mockOnChange}
      />
    );

    expect(
      screen.getByText(/uppercase\/lowercase must match exactly/)
    ).toBeInTheDocument();
  });

  it("renders helper text for trim whitespace", async () => {
    const ShortAnswerFields = await loadComponent();
    render(
      <ShortAnswerFields
        data={{ caseSensitive: false, trim: true }}
        onChange={mockOnChange}
      />
    );

    expect(
      screen.getByText(/Ignores extra spaces/)
    ).toBeInTheDocument();
  });

  it("calls onChange when caseSensitive is toggled", async () => {
    const user = userEvent.setup();
    const ShortAnswerFields = await loadComponent();
    render(
      <ShortAnswerFields
        data={{ caseSensitive: false, trim: true }}
        onChange={mockOnChange}
      />
    );

    const caseSensitiveCheckbox = screen.getByRole("checkbox", {
      name: /case sensitive/i,
    });
    await user.click(caseSensitiveCheckbox);
    expect(mockOnChange).toHaveBeenCalledWith({
      caseSensitive: true,
      trim: true,
    });
  });

  it("calls onChange when trim is toggled", async () => {
    const user = userEvent.setup();
    const ShortAnswerFields = await loadComponent();
    render(
      <ShortAnswerFields
        data={{ caseSensitive: false, trim: true }}
        onChange={mockOnChange}
      />
    );

    const trimCheckbox = screen.getByRole("checkbox", {
      name: /trim whitespace/i,
    });
    await user.click(trimCheckbox);
    expect(mockOnChange).toHaveBeenCalledWith({
      caseSensitive: false,
      trim: false,
    });
  });

  it("defaults caseSensitive to false when undefined", async () => {
    const ShortAnswerFields = await loadComponent();
    render(
      <ShortAnswerFields data={{}} onChange={mockOnChange} />
    );

    const caseSensitiveCheckbox = screen.getByRole("checkbox", {
      name: /case sensitive/i,
    });
    expect(caseSensitiveCheckbox).not.toBeChecked();
  });

  it("defaults trim to true when undefined", async () => {
    const ShortAnswerFields = await loadComponent();
    render(
      <ShortAnswerFields data={{}} onChange={mockOnChange} />
    );

    const trimCheckbox = screen.getByRole("checkbox", {
      name: /trim whitespace/i,
    });
    expect(trimCheckbox).toBeChecked();
  });
});
