import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockOnChange = vi.fn();

async function loadComponent() {
  vi.resetModules();
  const imported = await import("@/components/questions/MoodMeterInput");
  return imported.default;
}

describe("MoodMeterInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the prompt copy and all four quadrant titles", async () => {
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    expect(
      screen.getByText(
        /How are you feeling\? Select the mood that best describes you right now\./
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("High Energy \u00B7 Low Pleasantness")
    ).toBeInTheDocument();
    expect(
      screen.getByText("High Energy \u00B7 High Pleasantness")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Low Energy \u00B7 Low Pleasantness")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Low Energy \u00B7 High Pleasantness")
    ).toBeInTheDocument();
  });

  it("renders all 20 mood buttons across the 4 quadrants", async () => {
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    const moodNames = [
      "Angry",
      "Frustrated",
      "Anxious",
      "Irritated",
      "Stressed",
      "Excited",
      "Energized",
      "Motivated",
      "Proud",
      "Joyful",
      "Sad",
      "Tired",
      "Bored",
      "Lonely",
      "Down",
      "Calm",
      "Relaxed",
      "Content",
      "Grateful",
      "Peaceful",
    ];
    for (const name of moodNames) {
      expect(
        screen.getByRole("button", { name })
      ).toBeInTheDocument();
    }
    expect(screen.getAllByRole("button")).toHaveLength(20);
  });

  it("emits the exact MoodSelection shape on click (camelCase keys)", async () => {
    const user = userEvent.setup();
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    await user.click(screen.getByRole("button", { name: "Angry" }));

    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith({
      quadrant: "highEnergyLowPleasantness",
      moodName: "Angry",
      row: 0,
      col: 0,
    });
  });

  it("emits the correct payload for a high-energy high-pleasantness mood", async () => {
    const user = userEvent.setup();
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    await user.click(screen.getByRole("button", { name: "Joyful" }));

    expect(mockOnChange).toHaveBeenCalledWith({
      quadrant: "highEnergyHighPleasantness",
      moodName: "Joyful",
      row: 4,
      col: 8,
    });
  });

  it("emits the correct payload for a low-energy low-pleasantness mood", async () => {
    const user = userEvent.setup();
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    await user.click(screen.getByRole("button", { name: "Sad" }));

    expect(mockOnChange).toHaveBeenCalledWith({
      quadrant: "lowEnergyLowPleasantness",
      moodName: "Sad",
      row: 5,
      col: 0,
    });
  });

  it("emits the correct payload for a low-energy high-pleasantness mood", async () => {
    const user = userEvent.setup();
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    await user.click(screen.getByRole("button", { name: "Peaceful" }));

    expect(mockOnChange).toHaveBeenCalledWith({
      quadrant: "lowEnergyHighPleasantness",
      moodName: "Peaceful",
      row: 9,
      col: 8,
    });
  });

  it("renders the selected mood summary line when value is provided", async () => {
    const MoodMeterInput = await loadComponent();
    render(
      <MoodMeterInput
        value={{
          quadrant: "highEnergyHighPleasantness",
          moodName: "Excited",
          row: 0,
          col: 5,
        }}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText(/Selected:/)).toBeInTheDocument();
    // The summary renders the mood name inside a bold span alongside its emoji.
    // Match the bold span specifically so it doesn't collide with the button label.
    const summary = screen.getByText(/Excited/i, { selector: "span.font-bold" });
    expect(summary).toBeInTheDocument();
  });

  it("does not render the summary line when value is null", async () => {
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    expect(screen.queryByText(/Selected:/)).not.toBeInTheDocument();
  });

  it("disables every mood button when disabled is true", async () => {
    const MoodMeterInput = await loadComponent();
    render(
      <MoodMeterInput
        value={null}
        onChange={mockOnChange}
        disabled
      />
    );

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(20);
    for (const button of buttons) {
      expect(button).toBeDisabled();
    }
  });

  it("does not invoke onChange when clicking a disabled mood button", async () => {
    const user = userEvent.setup();
    const MoodMeterInput = await loadComponent();
    render(
      <MoodMeterInput
        value={null}
        onChange={mockOnChange}
        disabled
      />
    );

    await user.click(screen.getByRole("button", { name: "Angry" }));
    expect(mockOnChange).not.toHaveBeenCalled();
  });

  it("does not disable buttons when disabled prop is omitted (defaults to false)", async () => {
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    const buttons = screen.getAllByRole("button");
    for (const button of buttons) {
      expect(button).not.toBeDisabled();
    }
  });

  it("marks the button matching the controlled value as selected (visual contract)", async () => {
    const MoodMeterInput = await loadComponent();
    render(
      <MoodMeterInput
        value={{
          quadrant: "lowEnergyHighPleasantness",
          moodName: "Calm",
          row: 5,
          col: 5,
        }}
        onChange={mockOnChange}
      />
    );

    const selectedButton = screen.getByRole("button", { name: "Calm" });
    // The selected button swaps to the bg-foreground / text-background combo in
    // MoodMeterInput.tsx — guard the current visual contract so a future rewrite
    // is a conscious break rather than a silent regression.
    expect(selectedButton.className).toContain("bg-foreground");
    expect(selectedButton.className).toContain("text-background");

    const unselectedButton = screen.getByRole("button", { name: "Joyful" });
    expect(unselectedButton.className).not.toContain("bg-foreground");
  });

  it("re-emits selection (no internal lockout) when the same mood is clicked twice", async () => {
    const user = userEvent.setup();
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    const button = screen.getByRole("button", { name: "Content" });
    await user.click(button);
    await user.click(button);

    expect(mockOnChange).toHaveBeenCalledTimes(2);
    expect(mockOnChange).toHaveBeenLastCalledWith({
      quadrant: "lowEnergyHighPleasantness",
      moodName: "Content",
      row: 7,
      col: 9,
    });
  });

  it("switches selection when a different mood button is clicked", async () => {
    const user = userEvent.setup();
    const MoodMeterInput = await loadComponent();
    render(<MoodMeterInput value={null} onChange={mockOnChange} />);

    await user.click(screen.getByRole("button", { name: "Tired" }));
    await user.click(screen.getByRole("button", { name: "Motivated" }));

    expect(mockOnChange).toHaveBeenCalledTimes(2);
    expect(mockOnChange).toHaveBeenNthCalledWith(1, {
      quadrant: "lowEnergyLowPleasantness",
      moodName: "Tired",
      row: 6,
      col: 2,
    });
    expect(mockOnChange).toHaveBeenNthCalledWith(2, {
      quadrant: "highEnergyHighPleasantness",
      moodName: "Motivated",
      row: 2,
      col: 9,
    });
  });
});
