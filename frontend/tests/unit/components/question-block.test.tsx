import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockOnChange = vi.fn();
const mockOnRemove = vi.fn();
const mockOnMoveUp = vi.fn();
const mockOnMoveDown = vi.fn();

let capturedSelectProps: Record<string, { onValueChange?: (v: string) => void; value?: string }> = {};

function setupModuleMocks() {
  vi.doMock("@/lib/assignment-template-api", () => ({}));
}

function setupModuleMocksWithSelectCapture() {
  vi.doMock("@/lib/assignment-template-api", () => ({}));
  vi.doMock("@/components/ui/select", () => ({
    Select: ({ children, onValueChange, value }: { children: React.ReactNode; onValueChange?: (v: string) => void; value?: string }) => {
      capturedSelectProps[value || ""] = { onValueChange, value };
      return <div data-testid={`select-${value}`}>{children}</div>;
    },
    SelectContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    SelectItem: ({ children, value }: { children: React.ReactNode; value: string }) => (
      <option value={value}>{children}</option>
    ),
    SelectTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    SelectValue: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/assignment-templates/QuestionBlock");
  return imported.default;
}

async function loadComponentWithSelectCapture() {
  vi.resetModules();
  capturedSelectProps = {};
  setupModuleMocksWithSelectCapture();
  const imported = await import("@/components/assignment-templates/QuestionBlock");
  return imported.default;
}

const baseQuestion = {
  type: "MULTIPLE_CHOICE" as const,
  prompt: "What is 2+2?",
  maxPoints: 10,
  data: { choices: [{ prompt: "4", score: 10 }], selectAll: false },
  gradingStrategy: "AUTO" as const,
};

describe("QuestionBlock", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders question number heading", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Question 1")).toBeInTheDocument();
  });

  it("renders prompt input with value", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(
      screen.getByDisplayValue("What is 2+2?")
    ).toBeInTheDocument();
  });

  it("renders max points input", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // Max points input is a number input
    const numberInputs = screen.getAllByRole("spinbutton");
    const maxPointsInput = numberInputs.find(
      (input) => (input as HTMLInputElement).value === "10"
    );
    expect(maxPointsInput).toBeDefined();
  });

  it("renders remove button", async () => {
    const user = userEvent.setup();
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // Find the trash/remove button (destructive style)
    const removeButton = screen
      .getAllByRole("button")
      .find((btn) => btn.classList.contains("text-destructive"));
    expect(removeButton).toBeDefined();
    await user.click(removeButton!);
    expect(mockOnRemove).toHaveBeenCalled();
  });

  it("renders move up button when provided", async () => {
    const user = userEvent.setup();
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={1}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={mockOnMoveUp}
        onMoveDown={null}
      />
    );

    // Move up button should exist - it uses ChevronUp icon
    // There should be 3 buttons total: move up, remove
    const buttons = screen.getAllByRole("button");
    // First icon button should be move up
    await user.click(buttons[0]);
    expect(mockOnMoveUp).toHaveBeenCalled();
  });

  it("renders move down button when provided", async () => {
    const user = userEvent.setup();
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={mockOnMoveDown}
      />
    );

    const buttons = screen.getAllByRole("button");
    await user.click(buttons[0]);
    expect(mockOnMoveDown).toHaveBeenCalled();
  });

  it("does not render move up when null", async () => {
    const QuestionBlock = await loadComponent();
    const { container } = render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // Only remove button in the header area
    const headerButtons = container.querySelectorAll(
      ".flex.items-center.gap-1 button"
    );
    // Should only have the remove button
    expect(headerButtons).toHaveLength(1);
  });

  it("calls onChange when prompt is modified", async () => {
    const user = userEvent.setup();
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    const promptInput = screen.getByPlaceholderText(
      "Enter question prompt..."
    );
    await user.type(promptInput, "!");

    expect(mockOnChange).toHaveBeenCalled();
    const lastCall =
      mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
    expect(lastCall.prompt).toContain("!");
  });

  it("renders MCQ fields for MULTIPLE_CHOICE type", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // MCQ should show Choices label
    expect(screen.getByText("Choices")).toBeInTheDocument();
  });

  it("renders SHORT_ANSWER fields", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={{
          type: "SHORT_ANSWER",
          prompt: "Name the capital",
          maxPoints: 5,
          data: { caseSensitive: false, trim: true },
        }}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Case Sensitive")).toBeInTheDocument();
    expect(screen.getByText("Trim Whitespace")).toBeInTheDocument();
  });

  it("renders NUMBER_SCALE fields", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={{
          type: "NUMBER_SCALE",
          prompt: "Rate from 1-10",
          maxPoints: 10,
          data: { min: 1, max: 10, target: null },
        }}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Min")).toBeInTheDocument();
    expect(screen.getByText("Max")).toBeInTheDocument();
  });

  it("shows grading strategy selector when gradingMode is HYBRID", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="HYBRID"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Grading Strategy")).toBeInTheDocument();
  });

  it("does not show grading strategy selector for AUTO mode", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(
      screen.queryByText("Grading Strategy")
    ).not.toBeInTheDocument();
  });

  it("renders group options in the question group selector", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[
          { clientKey: "g1", name: "Reading Group", rubricId: null },
        ]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Question Group")).toBeInTheDocument();
  });

  it("renders Type, Prompt, and Max Points labels", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Type")).toBeInTheDocument();
    expect(screen.getByText("Prompt")).toBeInTheDocument();
    expect(screen.getByText("Max Points")).toBeInTheDocument();
  });

  it("calls onChange with updated maxPoints when max points input changes", async () => {
    const user = userEvent.setup();
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={{ ...baseQuestion, maxPoints: 0 }}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    const numberInputs = screen.getAllByRole("spinbutton");
    // Find the maxPoints input (value "0" from the QuestionBlock, not from MCQ score inputs)
    const maxPointsInput = numberInputs[0] as HTMLInputElement;
    await user.type(maxPointsInput, "5");

    expect(mockOnChange).toHaveBeenCalled();
    const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
    expect(lastCall.maxPoints).toBe(5);
  });

  it("renders both move up and move down buttons when both provided", async () => {
    const user = userEvent.setup();
    const QuestionBlock = await loadComponent();
    const { container } = render(
      <QuestionBlock
        index={1}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={mockOnMoveUp}
        onMoveDown={mockOnMoveDown}
      />
    );

    // Header area should have: move up, move down, and remove buttons
    const headerButtons = container.querySelectorAll(
      ".flex.items-center.gap-1 button"
    );
    expect(headerButtons).toHaveLength(3);

    // Click move up
    await user.click(headerButtons[0] as HTMLElement);
    expect(mockOnMoveUp).toHaveBeenCalled();

    // Click move down
    await user.click(headerButtons[1] as HTMLElement);
    expect(mockOnMoveDown).toHaveBeenCalled();
  });

  it("renders question with higher index", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={4}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Question 5")).toBeInTheDocument();
  });

  it("does not show grading strategy for MANUAL mode", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="MANUAL"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.queryByText("Grading Strategy")).not.toBeInTheDocument();
  });

  it("renders with undefined data gracefully for MCQ", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={{
          type: "MULTIPLE_CHOICE" as const,
          prompt: "Test",
          maxPoints: 5,
          data: undefined,
        }}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Question 1")).toBeInTheDocument();
    expect(screen.getByText("Choices")).toBeInTheDocument();
  });

  it("renders with undefined data for SHORT_ANSWER", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={{
          type: "SHORT_ANSWER" as const,
          prompt: "What?",
          maxPoints: 5,
          data: undefined,
        }}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Case Sensitive")).toBeInTheDocument();
  });

  it("renders with undefined data for NUMBER_SCALE", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={{
          type: "NUMBER_SCALE" as const,
          prompt: "Rate?",
          maxPoints: 10,
          data: undefined,
        }}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Min")).toBeInTheDocument();
  });

  it("renders question group selector with 'No group' by default", async () => {
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={{
          ...baseQuestion,
          groupClientKey: undefined,
        }}
        gradingMode="AUTO"
        groupOptions={[
          { clientKey: "g1", name: "Group A", rubricId: null },
        ]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    expect(screen.getByText("Question Group")).toBeInTheDocument();
  });

  it("renders maxPoints as 0 when input is cleared to empty", async () => {
    const user = userEvent.setup();
    const QuestionBlock = await loadComponent();
    render(
      <QuestionBlock
        index={0}
        question={{ ...baseQuestion, maxPoints: 10 }}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    const numberInputs = screen.getAllByRole("spinbutton");
    const maxPointsInput = numberInputs.find(
      (input) => (input as HTMLInputElement).value === "10"
    ) as HTMLInputElement;
    await user.clear(maxPointsInput);
    // Typing non-numeric should result in 0
    await user.type(maxPointsInput, "abc");

    const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
    expect(lastCall.maxPoints).toBe(0);
  });

  it("calls handleTypeChange when the type select is changed to SHORT_ANSWER", async () => {
    const QuestionBlock = await loadComponentWithSelectCapture();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // The type select has value "MULTIPLE_CHOICE"
    const typeSelectProps = capturedSelectProps["MULTIPLE_CHOICE"];
    expect(typeSelectProps).toBeDefined();
    typeSelectProps.onValueChange!("SHORT_ANSWER");

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "SHORT_ANSWER",
        data: { caseSensitive: false, trim: true },
      })
    );
  });

  it("calls handleTypeChange when the type select is changed to NUMBER_SCALE", async () => {
    const QuestionBlock = await loadComponentWithSelectCapture();
    render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    const typeSelectProps = capturedSelectProps["MULTIPLE_CHOICE"];
    typeSelectProps.onValueChange!("NUMBER_SCALE");

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "NUMBER_SCALE",
        data: { min: 1, max: 5, target: null },
      })
    );
  });

  it("sets groupClientKey to undefined when 'No group' is selected", async () => {
    const QuestionBlock = await loadComponentWithSelectCapture();
    render(
      <QuestionBlock
        index={0}
        question={{ ...baseQuestion, groupClientKey: "g1" }}
        gradingMode="AUTO"
        groupOptions={[
          { clientKey: "g1", name: "Group A", rubricId: null },
        ]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // The group select has value "g1" (since groupClientKey is "g1")
    const groupSelectProps = capturedSelectProps["g1"];
    expect(groupSelectProps).toBeDefined();
    groupSelectProps.onValueChange!("__NONE__");

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        groupClientKey: undefined,
      })
    );
  });

  it("sets groupClientKey when a group is selected", async () => {
    const QuestionBlock = await loadComponentWithSelectCapture();
    render(
      <QuestionBlock
        index={0}
        question={{ ...baseQuestion, groupClientKey: undefined }}
        gradingMode="AUTO"
        groupOptions={[
          { clientKey: "g1", name: "Group A", rubricId: null },
        ]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // The group select has value "__NONE__" (since groupClientKey is undefined)
    const groupSelectProps = capturedSelectProps["__NONE__"];
    expect(groupSelectProps).toBeDefined();
    groupSelectProps.onValueChange!("g1");

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        groupClientKey: "g1",
      })
    );
  });

  it("calls onChange with gradingStrategy when grading strategy select changes in HYBRID mode", async () => {
    const QuestionBlock = await loadComponentWithSelectCapture();
    render(
      <QuestionBlock
        index={0}
        question={{ ...baseQuestion, gradingStrategy: "AUTO" }}
        gradingMode="HYBRID"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // The grading strategy select has value "AUTO"
    // But the type select also has value "MULTIPLE_CHOICE" and the group select has "__NONE__"
    // The grading strategy select uses question.gradingStrategy ?? 'AUTO' = 'AUTO'
    // Since there are two selects with value 'AUTO' (type=MULTIPLE_CHOICE, group=__NONE__, strategy=AUTO)
    // The capturedSelectProps will overwrite. Let's find the right one.
    // Type select: value="MULTIPLE_CHOICE", Group select: value="__NONE__", Strategy select: value="AUTO"
    const strategySelectProps = capturedSelectProps["AUTO"];
    expect(strategySelectProps).toBeDefined();
    strategySelectProps.onValueChange!("MANUAL");

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        gradingStrategy: "MANUAL",
      })
    );
  });

  it("calls handleDataChange when MCQ data changes via sub-component", async () => {
    const QuestionBlock = await loadComponentWithSelectCapture();
    const { container } = render(
      <QuestionBlock
        index={0}
        question={baseQuestion}
        gradingMode="AUTO"
        groupOptions={[]}
        onChange={mockOnChange}
        onRemove={mockOnRemove}
        onMoveUp={null}
        onMoveDown={null}
      />
    );

    // The MCQ sub-component's selectAll checkbox triggers handleDataChange
    // Find the selectAll checkbox
    const checkbox = screen.getByRole("checkbox", { name: /select all that apply/i });
    const user = userEvent.setup();
    await user.click(checkbox);

    expect(mockOnChange).toHaveBeenCalled();
    const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
    // handleDataChange should pass the updated data through onChange
    expect(lastCall.data).toBeDefined();
  });
});
