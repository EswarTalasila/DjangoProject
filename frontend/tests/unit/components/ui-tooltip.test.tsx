import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";

import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";

beforeAll(() => {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

describe("TooltipProvider", () => {
  it("renders children", () => {
    render(
      <TooltipProvider>
        <span>Provider child</span>
      </TooltipProvider>,
    );
    expect(screen.getByText("Provider child")).toBeInTheDocument();
  });
});

describe("Tooltip", () => {
  it("renders trigger", () => {
    render(
      <Tooltip>
        <TooltipTrigger>Hover me</TooltipTrigger>
        <TooltipContent>Tooltip text</TooltipContent>
      </Tooltip>,
    );
    expect(screen.getByText("Hover me")).toBeInTheDocument();
  });

  it("renders trigger with data-slot=tooltip-trigger", () => {
    const { container } = render(
      <Tooltip>
        <TooltipTrigger>Hover</TooltipTrigger>
        <TooltipContent>Tip</TooltipContent>
      </Tooltip>,
    );
    const trigger = container.querySelector('[data-slot="tooltip-trigger"]');
    expect(trigger).toBeInTheDocument();
  });

  it("renders content when open", () => {
    const { container } = render(
      <Tooltip open>
        <TooltipTrigger>Hover</TooltipTrigger>
        <TooltipContent>Visible tip</TooltipContent>
      </Tooltip>,
    );
    const content = document.querySelector('[data-slot="tooltip-content"]');
    expect(content).toBeInTheDocument();
    expect(content).toHaveTextContent("Visible tip");
  });

  it("applies custom className to content", () => {
    render(
      <Tooltip open>
        <TooltipTrigger>Hover</TooltipTrigger>
        <TooltipContent className="tip-custom">Custom tip</TooltipContent>
      </Tooltip>,
    );
    const content = document.querySelector('[data-slot="tooltip-content"]');
    expect(content).toHaveClass("tip-custom");
    expect(content).toHaveTextContent("Custom tip");
  });
});
