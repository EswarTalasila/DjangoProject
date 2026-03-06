import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

describe("Tabs", () => {
  it("renders tabs with data-slot and horizontal orientation by default", () => {
    const { container } = render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">Tab A</TabsTrigger>
          <TabsTrigger value="b">Tab B</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Content A</TabsContent>
        <TabsContent value="b">Content B</TabsContent>
      </Tabs>,
    );
    const root = container.querySelector('[data-slot="tabs"]');
    expect(root).toBeInTheDocument();
    expect(root).toHaveAttribute("data-orientation", "horizontal");
  });

  it("renders the active tab content", () => {
    render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">Tab A</TabsTrigger>
          <TabsTrigger value="b">Tab B</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Content A</TabsContent>
        <TabsContent value="b">Content B</TabsContent>
      </Tabs>,
    );
    expect(screen.getByText("Content A")).toBeInTheDocument();
  });

  it("switches tab content on click", async () => {
    const user = userEvent.setup();
    render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">Tab A</TabsTrigger>
          <TabsTrigger value="b">Tab B</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Content A</TabsContent>
        <TabsContent value="b">Content B</TabsContent>
      </Tabs>,
    );
    await user.click(screen.getByText("Tab B"));
    expect(screen.getByText("Content B")).toBeInTheDocument();
  });

  it("supports vertical orientation", () => {
    const { container } = render(
      <Tabs defaultValue="a" orientation="vertical">
        <TabsList>
          <TabsTrigger value="a">Tab A</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Content A</TabsContent>
      </Tabs>,
    );
    const root = container.querySelector('[data-slot="tabs"]');
    expect(root).toHaveAttribute("data-orientation", "vertical");
  });

  it("applies custom className to Tabs root", () => {
    const { container } = render(
      <Tabs defaultValue="a" className="custom-tabs">
        <TabsList>
          <TabsTrigger value="a">A</TabsTrigger>
        </TabsList>
        <TabsContent value="a">C</TabsContent>
      </Tabs>,
    );
    const root = container.querySelector('[data-slot="tabs"]');
    expect(root).toHaveClass("custom-tabs");
  });
});

describe("TabsList", () => {
  it("renders with data-slot=tabs-list and default variant", () => {
    const { container } = render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">A</TabsTrigger>
        </TabsList>
        <TabsContent value="a">C</TabsContent>
      </Tabs>,
    );
    const list = container.querySelector('[data-slot="tabs-list"]');
    expect(list).toBeInTheDocument();
    expect(list).toHaveAttribute("data-variant", "default");
  });

  it("supports variant=line", () => {
    const { container } = render(
      <Tabs defaultValue="a">
        <TabsList variant="line">
          <TabsTrigger value="a">A</TabsTrigger>
        </TabsList>
        <TabsContent value="a">C</TabsContent>
      </Tabs>,
    );
    const list = container.querySelector('[data-slot="tabs-list"]');
    expect(list).toHaveAttribute("data-variant", "line");
  });

  it("applies custom className", () => {
    const { container } = render(
      <Tabs defaultValue="a">
        <TabsList className="list-class">
          <TabsTrigger value="a">A</TabsTrigger>
        </TabsList>
        <TabsContent value="a">C</TabsContent>
      </Tabs>,
    );
    const list = container.querySelector('[data-slot="tabs-list"]');
    expect(list).toHaveClass("list-class");
  });
});

describe("TabsTrigger", () => {
  it("renders with data-slot=tabs-trigger", () => {
    const { container } = render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">A</TabsTrigger>
        </TabsList>
        <TabsContent value="a">C</TabsContent>
      </Tabs>,
    );
    const trigger = container.querySelector('[data-slot="tabs-trigger"]');
    expect(trigger).toBeInTheDocument();
  });
});

describe("TabsContent", () => {
  it("renders with data-slot=tabs-content", () => {
    const { container } = render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">A</TabsTrigger>
        </TabsList>
        <TabsContent value="a" className="content-class">
          Content here
        </TabsContent>
      </Tabs>,
    );
    const content = container.querySelector('[data-slot="tabs-content"]');
    expect(content).toBeInTheDocument();
    expect(content).toHaveClass("content-class");
  });
});
