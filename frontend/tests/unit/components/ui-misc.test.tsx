import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { HelpTip } from "@/components/ui/help-tip";

/* ------------------------------------------------------------------ */
/*  Separator                                                          */
/* ------------------------------------------------------------------ */
describe("Separator", () => {
  it("renders with data-slot=separator", () => {
    const { container } = render(<Separator />);
    const el = container.querySelector('[data-slot="separator"]');
    expect(el).toBeInTheDocument();
  });

  it("defaults to horizontal orientation", () => {
    const { container } = render(<Separator />);
    const el = container.querySelector('[data-slot="separator"]');
    expect(el).toHaveAttribute("data-orientation", "horizontal");
  });

  it("supports vertical orientation", () => {
    const { container } = render(<Separator orientation="vertical" />);
    const el = container.querySelector('[data-slot="separator"]');
    expect(el).toHaveAttribute("data-orientation", "vertical");
  });

  it("applies custom className", () => {
    const { container } = render(<Separator className="my-sep" />);
    const el = container.querySelector('[data-slot="separator"]');
    expect(el).toHaveClass("my-sep");
  });

  it("is decorative by default", () => {
    const { container } = render(<Separator />);
    const el = container.querySelector('[data-slot="separator"]');
    expect(el).toHaveAttribute("role", "none");
  });

  it("renders as separator role when not decorative", () => {
    const { container } = render(<Separator decorative={false} />);
    const el = container.querySelector('[data-slot="separator"]');
    expect(el).toHaveAttribute("role", "separator");
  });
});

/* ------------------------------------------------------------------ */
/*  Skeleton                                                           */
/* ------------------------------------------------------------------ */
describe("Skeleton", () => {
  it("renders with data-slot=skeleton", () => {
    const { container } = render(<Skeleton />);
    const el = container.querySelector('[data-slot="skeleton"]');
    expect(el).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<Skeleton className="w-10 h-10" />);
    const el = container.querySelector('[data-slot="skeleton"]');
    expect(el).toHaveClass("w-10");
    expect(el).toHaveClass("h-10");
  });

  it("has animate-pulse class", () => {
    const { container } = render(<Skeleton />);
    const el = container.querySelector('[data-slot="skeleton"]');
    expect(el).toHaveClass("animate-pulse");
  });
});

/* ------------------------------------------------------------------ */
/*  Collapsible                                                        */
/* ------------------------------------------------------------------ */
describe("Collapsible", () => {
  it("renders with data-slot=collapsible", () => {
    const { container } = render(
      <Collapsible>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Hidden content</CollapsibleContent>
      </Collapsible>,
    );
    const el = container.querySelector('[data-slot="collapsible"]');
    expect(el).toBeInTheDocument();
  });

  it("renders trigger with data-slot=collapsible-trigger", () => {
    const { container } = render(
      <Collapsible>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>,
    );
    const trigger = container.querySelector('[data-slot="collapsible-trigger"]');
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveTextContent("Toggle");
  });

  it("shows content when open", () => {
    render(
      <Collapsible open>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Visible content</CollapsibleContent>
      </Collapsible>,
    );
    expect(screen.getByText("Visible content")).toBeInTheDocument();
  });

  it("hides content when closed (not in DOM)", () => {
    render(
      <Collapsible open={false}>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Hidden content</CollapsibleContent>
      </Collapsible>,
    );
    // Radix collapsible removes content from DOM when closed
    expect(screen.queryByText("Hidden content")).toBeNull();
  });

  it("toggles content on trigger click", async () => {
    const user = userEvent.setup();
    render(
      <Collapsible>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Toggled content</CollapsibleContent>
      </Collapsible>,
    );
    await user.click(screen.getByText("Toggle"));
    expect(screen.getByText("Toggled content")).toBeVisible();
  });
});

/* ------------------------------------------------------------------ */
/*  HelpTip                                                            */
/* ------------------------------------------------------------------ */
describe("HelpTip", () => {
  it("renders trigger with aria-label", () => {
    render(<HelpTip text="Some help text" />);
    const trigger = screen.getByRole("button", { name: "Show help" });
    expect(trigger).toBeInTheDocument();
  });

  it("has tabIndex=0 for accessibility", () => {
    render(<HelpTip text="Help" />);
    const trigger = screen.getByRole("button", { name: "Show help" });
    expect(trigger).toHaveAttribute("tabindex", "0");
  });
});

/* ------------------------------------------------------------------ */
/*  Sonner / Toaster                                                   */
/* ------------------------------------------------------------------ */
describe("Toaster (sonner)", () => {
  it("renders without errors", async () => {
    vi.doMock("next-themes", () => ({
      useTheme: () => ({ theme: "light" }),
    }));
    vi.resetModules();
    const { Toaster } = await import("@/components/ui/sonner");
    const { container } = render(<Toaster />);
    // The Sonner component renders a section element
    expect(container).toBeTruthy();
  });
});
