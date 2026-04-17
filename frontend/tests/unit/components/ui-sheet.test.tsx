import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
  SheetClose,
} from "@/components/ui/sheet";

/* ------------------------------------------------------------------ */
/*  SheetHeader / SheetFooter                                          */
/* ------------------------------------------------------------------ */
describe("SheetHeader", () => {
  it("renders children and applies data-slot", () => {
    const { container } = render(
      <SheetHeader>
        <span>Header child</span>
      </SheetHeader>,
    );
    const el = container.querySelector('[data-slot="sheet-header"]');
    expect(el).toBeInTheDocument();
    expect(screen.getByText("Header child")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<SheetHeader className="my-class">H</SheetHeader>);
    expect(container.querySelector('[data-slot="sheet-header"]')).toHaveClass("my-class");
  });
});

describe("SheetFooter", () => {
  it("renders children and applies data-slot", () => {
    const { container } = render(
      <SheetFooter>
        <span>Footer child</span>
      </SheetFooter>,
    );
    const el = container.querySelector('[data-slot="sheet-footer"]');
    expect(el).toBeInTheDocument();
    expect(screen.getByText("Footer child")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<SheetFooter className="foot-class">F</SheetFooter>);
    expect(container.querySelector('[data-slot="sheet-footer"]')).toHaveClass("foot-class");
  });
});

/* ------------------------------------------------------------------ */
/*  Sheet open / close                                                 */
/* ------------------------------------------------------------------ */
describe("Sheet (open/close)", () => {
  it("renders content when open", () => {
    render(
      <Sheet open>
        <SheetContent>
          <SheetTitle>My title</SheetTitle>
          <SheetDescription>My description</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByText("My title")).toBeInTheDocument();
    expect(screen.getByText("My description")).toBeInTheDocument();
  });

  it("renders content with side=left", () => {
    render(
      <Sheet open>
        <SheetContent side="left">
          <SheetTitle>Left Sheet</SheetTitle>
          <SheetDescription>Left side content</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByText("Left Sheet")).toBeInTheDocument();
  });

  it("renders content with side=top", () => {
    render(
      <Sheet open>
        <SheetContent side="top">
          <SheetTitle>Top Sheet</SheetTitle>
          <SheetDescription>Top desc</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByText("Top Sheet")).toBeInTheDocument();
  });

  it("renders content with side=bottom", () => {
    render(
      <Sheet open>
        <SheetContent side="bottom">
          <SheetTitle>Bottom Sheet</SheetTitle>
          <SheetDescription>Bottom desc</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByText("Bottom Sheet")).toBeInTheDocument();
  });

  it("hides close button when showCloseButton=false", () => {
    render(
      <Sheet open>
        <SheetContent showCloseButton={false}>
          <SheetTitle>No Close</SheetTitle>
          <SheetDescription>No close button</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.queryByRole("button", { name: "Close" })).toBeNull();
  });

  it("shows close button by default", () => {
    render(
      <Sheet open>
        <SheetContent>
          <SheetTitle>Has Close</SheetTitle>
          <SheetDescription>Close btn visible</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  });

  it("opens when trigger is clicked", async () => {
    const user = userEvent.setup();
    render(
      <Sheet>
        <SheetTrigger>Open Sheet</SheetTrigger>
        <SheetContent>
          <SheetTitle>Opened</SheetTitle>
          <SheetDescription>Now visible</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.queryByText("Opened")).toBeNull();
    await user.click(screen.getByText("Open Sheet"));
    expect(screen.getByText("Opened")).toBeInTheDocument();
  });
});
