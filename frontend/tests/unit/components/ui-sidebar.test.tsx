import { render, screen, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock use-mobile hook before importing sidebar
vi.mock("@/hooks/use-mobile", () => ({
  useIsMobile: () => false,
}));

import {
  SidebarProvider,
  Sidebar,
  SidebarTrigger,
  SidebarRail,
  SidebarInset,
  SidebarInput,
  SidebarHeader,
  SidebarFooter,
  SidebarSeparator,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupAction,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuAction,
  SidebarMenuBadge,
  SidebarMenuSkeleton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  useSidebar,
} from "@/components/ui/sidebar";

/* ------------------------------------------------------------------ */
/*  Helper to wrap with SidebarProvider                                */
/* ------------------------------------------------------------------ */
function Wrapper({
  children,
  defaultOpen = true,
}: {
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  return <SidebarProvider defaultOpen={defaultOpen}>{children}</SidebarProvider>;
}

/* ------------------------------------------------------------------ */
/*  useSidebar hook                                                    */
/* ------------------------------------------------------------------ */
describe("useSidebar", () => {
  it("throws when used outside SidebarProvider", () => {
    function Bad() {
      useSidebar();
      return null;
    }
    expect(() => render(<Bad />)).toThrow(
      "useSidebar must be used within a SidebarProvider.",
    );
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarProvider                                                    */
/* ------------------------------------------------------------------ */
describe("SidebarProvider", () => {
  it("renders children inside sidebar-wrapper", () => {
    const { container } = render(
      <SidebarProvider>
        <span>Provider child</span>
      </SidebarProvider>,
    );
    const wrapper = container.querySelector('[data-slot="sidebar-wrapper"]');
    expect(wrapper).toBeInTheDocument();
    expect(screen.getByText("Provider child")).toBeInTheDocument();
  });

  it("sets CSS custom properties for sidebar widths", () => {
    const { container } = render(
      <SidebarProvider>
        <span>child</span>
      </SidebarProvider>,
    );
    const wrapper = container.querySelector('[data-slot="sidebar-wrapper"]') as HTMLElement;
    expect(wrapper.style.getPropertyValue("--sidebar-width")).toBe("16rem");
    expect(wrapper.style.getPropertyValue("--sidebar-width-icon")).toBe("3rem");
  });

  it("applies custom className", () => {
    const { container } = render(
      <SidebarProvider className="my-custom">
        <span>child</span>
      </SidebarProvider>,
    );
    const wrapper = container.querySelector('[data-slot="sidebar-wrapper"]');
    expect(wrapper).toHaveClass("my-custom");
  });

  it("responds to keyboard shortcut ctrl+b", () => {
    let hookValue: any;
    function Inspector() {
      hookValue = useSidebar();
      return null;
    }
    render(
      <SidebarProvider defaultOpen={true}>
        <Inspector />
      </SidebarProvider>,
    );
    expect(hookValue.open).toBe(true);

    act(() => {
      fireEvent.keyDown(window, { key: "b", ctrlKey: true });
    });
    expect(hookValue.open).toBe(false);
  });

  it("supports controlled open prop", () => {
    const onOpenChange = vi.fn();
    let hookValue: any;
    function Inspector() {
      hookValue = useSidebar();
      return null;
    }
    render(
      <SidebarProvider open={true} onOpenChange={onOpenChange}>
        <Inspector />
      </SidebarProvider>,
    );
    expect(hookValue.open).toBe(true);
    expect(hookValue.state).toBe("expanded");
  });
});

/* ------------------------------------------------------------------ */
/*  Sidebar                                                            */
/* ------------------------------------------------------------------ */
describe("Sidebar", () => {
  it("renders desktop sidebar with data-slot", () => {
    const { container } = render(
      <Wrapper>
        <Sidebar>
          <span>Sidebar content</span>
        </Sidebar>
      </Wrapper>,
    );
    const el = container.querySelector('[data-slot="sidebar"]');
    expect(el).toBeInTheDocument();
  });

  it("renders collapsible=none variant", () => {
    const { container } = render(
      <Wrapper>
        <Sidebar collapsible="none">
          <span>No collapse</span>
        </Sidebar>
      </Wrapper>,
    );
    const el = container.querySelector('[data-slot="sidebar"]');
    expect(el).toBeInTheDocument();
    expect(screen.getByText("No collapse")).toBeInTheDocument();
  });

  it("sets data-state based on open state", () => {
    const { container } = render(
      <Wrapper defaultOpen={false}>
        <Sidebar>
          <span>collapsed sidebar</span>
        </Sidebar>
      </Wrapper>,
    );
    const el = container.querySelector('[data-slot="sidebar"]');
    expect(el).toHaveAttribute("data-state", "collapsed");
  });

  it("sets data-side and data-variant", () => {
    const { container } = render(
      <Wrapper>
        <Sidebar side="right" variant="floating">
          <span>right float</span>
        </Sidebar>
      </Wrapper>,
    );
    const el = container.querySelector('[data-slot="sidebar"]');
    expect(el).toHaveAttribute("data-side", "right");
    expect(el).toHaveAttribute("data-variant", "floating");
  });

  it("sets data-variant=inset", () => {
    const { container } = render(
      <Wrapper>
        <Sidebar variant="inset">
          <span>inset variant</span>
        </Sidebar>
      </Wrapper>,
    );
    const el = container.querySelector('[data-slot="sidebar"]');
    expect(el).toHaveAttribute("data-variant", "inset");
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarTrigger                                                     */
/* ------------------------------------------------------------------ */
describe("SidebarTrigger", () => {
  it("renders a toggle button", () => {
    render(
      <Wrapper>
        <SidebarTrigger />
      </Wrapper>,
    );
    expect(screen.getByText("Toggle Sidebar")).toBeInTheDocument();
  });

  it("calls toggleSidebar and optional onClick", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    let hookValue: any;
    function Inspector() {
      hookValue = useSidebar();
      return null;
    }
    render(
      <Wrapper defaultOpen={true}>
        <Inspector />
        <SidebarTrigger onClick={onClick} />
      </Wrapper>,
    );
    expect(hookValue.open).toBe(true);
    await user.click(screen.getByRole("button", { name: "Toggle Sidebar" }));
    expect(onClick).toHaveBeenCalled();
    expect(hookValue.open).toBe(false);
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarRail                                                        */
/* ------------------------------------------------------------------ */
describe("SidebarRail", () => {
  it("renders rail button with proper attributes", () => {
    render(
      <Wrapper>
        <SidebarRail />
      </Wrapper>,
    );
    const rail = screen.getByTitle("Toggle Sidebar");
    expect(rail).toHaveAttribute("data-sidebar", "rail");
    expect(rail).toHaveAttribute("tabindex", "-1");
  });

  it("toggles sidebar on click", async () => {
    const user = userEvent.setup();
    let hookValue: any;
    function Inspector() {
      hookValue = useSidebar();
      return null;
    }
    render(
      <Wrapper defaultOpen={true}>
        <Inspector />
        <SidebarRail />
      </Wrapper>,
    );
    expect(hookValue.open).toBe(true);
    await user.click(screen.getByTitle("Toggle Sidebar"));
    expect(hookValue.open).toBe(false);
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarInset                                                       */
/* ------------------------------------------------------------------ */
describe("SidebarInset", () => {
  it("renders main element with data-slot", () => {
    const { container } = render(
      <Wrapper>
        <SidebarInset>
          <span>Main content</span>
        </SidebarInset>
      </Wrapper>,
    );
    const el = container.querySelector('[data-slot="sidebar-inset"]');
    expect(el).toBeInTheDocument();
    expect(el?.tagName).toBe("MAIN");
    expect(screen.getByText("Main content")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <Wrapper>
        <SidebarInset className="inset-custom">child</SidebarInset>
      </Wrapper>,
    );
    expect(container.querySelector('[data-slot="sidebar-inset"]')).toHaveClass("inset-custom");
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarInput                                                       */
/* ------------------------------------------------------------------ */
describe("SidebarInput", () => {
  it("renders an input with data-sidebar=input", () => {
    const { container } = render(
      <Wrapper>
        <SidebarInput placeholder="Search" />
      </Wrapper>,
    );
    const input = screen.getByPlaceholderText("Search");
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("data-sidebar", "input");
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarHeader / SidebarFooter / SidebarContent                     */
/* ------------------------------------------------------------------ */
describe("SidebarHeader", () => {
  it("renders with data-sidebar=header", () => {
    const { container } = render(
      <Wrapper>
        <SidebarHeader>
          <span>Header</span>
        </SidebarHeader>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="header"]');
    expect(el).toBeInTheDocument();
    expect(screen.getByText("Header")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <Wrapper>
        <SidebarHeader className="hdr">H</SidebarHeader>
      </Wrapper>,
    );
    expect(container.querySelector('[data-sidebar="header"]')).toHaveClass("hdr");
  });
});

describe("SidebarFooter", () => {
  it("renders with data-sidebar=footer", () => {
    const { container } = render(
      <Wrapper>
        <SidebarFooter>
          <span>Footer</span>
        </SidebarFooter>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="footer"]');
    expect(el).toBeInTheDocument();
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });
});

describe("SidebarContent", () => {
  it("renders with data-sidebar=content", () => {
    const { container } = render(
      <Wrapper>
        <SidebarContent>
          <span>Content area</span>
        </SidebarContent>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="content"]');
    expect(el).toBeInTheDocument();
    expect(screen.getByText("Content area")).toBeInTheDocument();
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarSeparator                                                   */
/* ------------------------------------------------------------------ */
describe("SidebarSeparator", () => {
  it("renders with data-sidebar=separator", () => {
    const { container } = render(
      <Wrapper>
        <SidebarSeparator />
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="separator"]');
    expect(el).toBeInTheDocument();
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarGroup / SidebarGroupLabel / SidebarGroupAction / Content    */
/* ------------------------------------------------------------------ */
describe("SidebarGroup", () => {
  it("renders with data-sidebar=group", () => {
    const { container } = render(
      <Wrapper>
        <SidebarGroup>
          <span>Group</span>
        </SidebarGroup>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="group"]');
    expect(el).toBeInTheDocument();
  });
});

describe("SidebarGroupLabel", () => {
  it("renders label text", () => {
    const { container } = render(
      <Wrapper>
        <SidebarGroupLabel>Navigation</SidebarGroupLabel>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="group-label"]');
    expect(el).toHaveTextContent("Navigation");
  });

  it("renders as Slot when asChild=true", () => {
    render(
      <Wrapper>
        <SidebarGroupLabel asChild>
          <h3>Custom heading</h3>
        </SidebarGroupLabel>
      </Wrapper>,
    );
    expect(screen.getByText("Custom heading").tagName).toBe("H3");
  });
});

describe("SidebarGroupAction", () => {
  it("renders button with data-sidebar=group-action", () => {
    const { container } = render(
      <Wrapper>
        <SidebarGroupAction>Add</SidebarGroupAction>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="group-action"]');
    expect(el).toBeInTheDocument();
    expect(el?.tagName).toBe("BUTTON");
  });

  it("renders as Slot when asChild=true", () => {
    render(
      <Wrapper>
        <SidebarGroupAction asChild>
          <a href="/add">Add link</a>
        </SidebarGroupAction>
      </Wrapper>,
    );
    expect(screen.getByText("Add link").tagName).toBe("A");
  });
});

describe("SidebarGroupContent", () => {
  it("renders with data-sidebar=group-content", () => {
    const { container } = render(
      <Wrapper>
        <SidebarGroupContent>
          <span>Group content</span>
        </SidebarGroupContent>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="group-content"]');
    expect(el).toBeInTheDocument();
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarMenu / SidebarMenuItem                                      */
/* ------------------------------------------------------------------ */
describe("SidebarMenu", () => {
  it("renders ul with data-sidebar=menu", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <li>Item</li>
        </SidebarMenu>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu"]');
    expect(el).toBeInTheDocument();
    expect(el?.tagName).toBe("UL");
  });
});

describe("SidebarMenuItem", () => {
  it("renders li with data-sidebar=menu-item", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <span>Menu item</span>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-item"]');
    expect(el).toBeInTheDocument();
    expect(el?.tagName).toBe("LI");
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarMenuButton                                                  */
/* ------------------------------------------------------------------ */
describe("SidebarMenuButton", () => {
  it("renders button with data attributes", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton>Click me</SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    const btn = container.querySelector('[data-sidebar="menu-button"]');
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveAttribute("data-active", "false");
    expect(btn).toHaveAttribute("data-size", "default");
  });

  it("sets isActive=true", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton isActive>Active</SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    const btn = container.querySelector('[data-sidebar="menu-button"]');
    expect(btn).toHaveAttribute("data-active", "true");
  });

  it("supports size=sm and variant=outline", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="sm" variant="outline">
              Small
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    const btn = container.querySelector('[data-sidebar="menu-button"]');
    expect(btn).toHaveAttribute("data-size", "sm");
  });

  it("supports size=lg", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg">Large</SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    const btn = container.querySelector('[data-sidebar="menu-button"]');
    expect(btn).toHaveAttribute("data-size", "lg");
  });

  it("wraps in tooltip when tooltip string is given", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="Hint">With tooltip</SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    // Should still render the button
    expect(screen.getByText("With tooltip")).toBeInTheDocument();
  });

  it("wraps in tooltip when tooltip is an object", () => {
    render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip={{ children: "Hint obj" }}>
              Obj tooltip
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    expect(screen.getByText("Obj tooltip")).toBeInTheDocument();
  });

  it("renders as child element when asChild=true", () => {
    render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild>
              <a href="/home">Home link</a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    expect(screen.getByText("Home link").tagName).toBe("A");
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarMenuAction                                                  */
/* ------------------------------------------------------------------ */
describe("SidebarMenuAction", () => {
  it("renders button with data-sidebar=menu-action", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuAction>Action</SidebarMenuAction>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-action"]');
    expect(el).toBeInTheDocument();
  });

  it("applies showOnHover class variant", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuAction showOnHover>Hover action</SidebarMenuAction>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-action"]');
    expect(el).toBeInTheDocument();
  });

  it("renders as child when asChild=true", () => {
    render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuAction asChild>
              <a href="/act">Action link</a>
            </SidebarMenuAction>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    expect(screen.getByText("Action link").tagName).toBe("A");
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarMenuBadge                                                   */
/* ------------------------------------------------------------------ */
describe("SidebarMenuBadge", () => {
  it("renders badge with data-sidebar=menu-badge", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuBadge>5</SidebarMenuBadge>
          </SidebarMenuItem>
        </SidebarMenu>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-badge"]');
    expect(el).toHaveTextContent("5");
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarMenuSkeleton                                                */
/* ------------------------------------------------------------------ */
describe("SidebarMenuSkeleton", () => {
  it("renders skeleton without icon by default", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenuSkeleton />
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-skeleton"]');
    expect(el).toBeInTheDocument();
    const icon = container.querySelector('[data-sidebar="menu-skeleton-icon"]');
    expect(icon).toBeNull();
    const text = container.querySelector('[data-sidebar="menu-skeleton-text"]');
    expect(text).toBeInTheDocument();
  });

  it("renders skeleton with icon when showIcon=true", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenuSkeleton showIcon />
      </Wrapper>,
    );
    const icon = container.querySelector('[data-sidebar="menu-skeleton-icon"]');
    expect(icon).toBeInTheDocument();
  });
});

/* ------------------------------------------------------------------ */
/*  SidebarMenuSub / SidebarMenuSubItem / SidebarMenuSubButton         */
/* ------------------------------------------------------------------ */
describe("SidebarMenuSub", () => {
  it("renders sub menu ul", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenuSub>
          <li>Sub item</li>
        </SidebarMenuSub>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-sub"]');
    expect(el).toBeInTheDocument();
    expect(el?.tagName).toBe("UL");
  });
});

describe("SidebarMenuSubItem", () => {
  it("renders li with data-sidebar=menu-sub-item", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenuSub>
          <SidebarMenuSubItem>
            <span>Sub</span>
          </SidebarMenuSubItem>
        </SidebarMenuSub>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-sub-item"]');
    expect(el).toBeInTheDocument();
  });
});

describe("SidebarMenuSubButton", () => {
  it("renders anchor by default with data attributes", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenuSub>
          <SidebarMenuSubItem>
            <SidebarMenuSubButton href="/sub">Sub button</SidebarMenuSubButton>
          </SidebarMenuSubItem>
        </SidebarMenuSub>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-sub-button"]');
    expect(el).toBeInTheDocument();
    expect(el?.tagName).toBe("A");
    expect(el).toHaveAttribute("data-size", "md");
    expect(el).toHaveAttribute("data-active", "false");
  });

  it("supports size=sm and isActive=true", () => {
    const { container } = render(
      <Wrapper>
        <SidebarMenuSub>
          <SidebarMenuSubItem>
            <SidebarMenuSubButton size="sm" isActive>
              Active sm
            </SidebarMenuSubButton>
          </SidebarMenuSubItem>
        </SidebarMenuSub>
      </Wrapper>,
    );
    const el = container.querySelector('[data-sidebar="menu-sub-button"]');
    expect(el).toHaveAttribute("data-size", "sm");
    expect(el).toHaveAttribute("data-active", "true");
  });

  it("renders as child element when asChild=true", () => {
    render(
      <Wrapper>
        <SidebarMenuSub>
          <SidebarMenuSubItem>
            <SidebarMenuSubButton asChild>
              <button>Custom sub</button>
            </SidebarMenuSubButton>
          </SidebarMenuSubItem>
        </SidebarMenuSub>
      </Wrapper>,
    );
    expect(screen.getByText("Custom sub").tagName).toBe("BUTTON");
  });
});
