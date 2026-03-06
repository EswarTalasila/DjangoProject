import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { NavGroup } from "@/components/layout/sidebarWrapper";

function setupModuleMocks() {
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: vi.fn() }),
    usePathname: () => "/dashboard",
    useSearchParams: () => new URLSearchParams(),
  }));
}

async function loadComponent() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import("@/components/layout/sidebar");
  return imported.Sidebar;
}

const mockGroups: NavGroup[] = [
  {
    label: "Overview",
    iconName: "Overview",
    links: [{ label: "Dashboard", href: "/dashboard" }],
  },
  {
    label: "Courses",
    iconName: "Courses",
    links: [
      { label: "My Courses", href: "/dashboard/courses" },
      { label: "Registration Codes", href: "/dashboard/codes" },
    ],
  },
  {
    label: "Assessments",
    iconName: "Assessments",
    links: [
      { label: "My Assessments", href: "/dashboard/assessments" },
      { label: "My Rubrics", href: "/dashboard/rubrics" },
    ],
  },
];

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nav element", async () => {
    const Sidebar = await loadComponent();
    const { container } = render(
      <Sidebar role="TEACHER" groups={mockGroups} />
    );

    expect(container.querySelector("nav")).toBeInTheDocument();
  });

  it("renders icon buttons with aria-labels for each group", async () => {
    const Sidebar = await loadComponent();
    render(<Sidebar role="TEACHER" groups={mockGroups} />);

    expect(screen.getByLabelText("Overview")).toBeInTheDocument();
    expect(screen.getByLabelText("Courses")).toBeInTheDocument();
    expect(screen.getByLabelText("Assessments")).toBeInTheDocument();
  });

  it("renders links inside flyout panels", async () => {
    const Sidebar = await loadComponent();
    render(<Sidebar role="TEACHER" groups={mockGroups} />);

    // Links exist in the DOM (in flyout panels) even if visually hidden
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("My Courses")).toBeInTheDocument();
    expect(screen.getByText("Registration Codes")).toBeInTheDocument();
    expect(screen.getByText("My Assessments")).toBeInTheDocument();
    expect(screen.getByText("My Rubrics")).toBeInTheDocument();
  });

  it("renders group labels in flyout panels", async () => {
    const Sidebar = await loadComponent();
    render(<Sidebar role="TEACHER" groups={mockGroups} />);

    // Each group's label appears both as aria-label on button and text in flyout
    const overviewTexts = screen.getAllByText("Overview");
    expect(overviewTexts.length).toBeGreaterThanOrEqual(1);
    const coursesTexts = screen.getAllByText("Courses");
    expect(coursesTexts.length).toBeGreaterThanOrEqual(1);
  });

  it("renders correct href for links", async () => {
    const Sidebar = await loadComponent();
    render(<Sidebar role="TEACHER" groups={mockGroups} />);

    const dashLink = screen.getByText("Dashboard").closest("a");
    expect(dashLink).toHaveAttribute("href", "/dashboard");

    const coursesLink = screen.getByText("My Courses").closest("a");
    expect(coursesLink).toHaveAttribute("href", "/dashboard/courses");
  });

  it("highlights active group when on dashboard", async () => {
    const Sidebar = await loadComponent();
    const { container } = render(
      <Sidebar role="TEACHER" groups={mockGroups} />
    );

    // The active indicator bar should exist for the Overview group (pathname = /dashboard)
    const indicators = container.querySelectorAll(
      ".bg-sidebar-primary"
    );
    expect(indicators.length).toBeGreaterThanOrEqual(1);
  });

  it("renders with RESEARCHER role without errors", async () => {
    const Sidebar = await loadComponent();
    render(<Sidebar role="RESEARCHER" groups={mockGroups} />);

    expect(screen.getByLabelText("Overview")).toBeInTheDocument();
  });

  it("renders with empty groups", async () => {
    const Sidebar = await loadComponent();
    const { container } = render(
      <Sidebar role="STUDENT" groups={[]} />
    );

    expect(container.querySelector("nav")).toBeInTheDocument();
  });
});
