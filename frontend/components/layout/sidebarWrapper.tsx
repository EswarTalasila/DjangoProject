import { redirect } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { getSessionProfile, getSudoCapabilities } from "@/lib/auth-session";

export type Role = "TEACHER" | "RESEARCHER" | "STUDENT";

export type NavItem =
  | { type: "header"; label: string }
  | { type: "divider" }
  | { type: "link"; label: string; href: string };

export type NavLink = { label: string; href: string };

export type NavGroup = {
  label: string;
  iconName: string;
  links: NavLink[];
};

function groupNavItems(items: NavItem[]): NavGroup[] {
  const groups: NavGroup[] = [];
  let current: NavGroup | null = null;

  for (const item of items) {
    if (item.type === "header") {
      if (current) groups.push(current);
      current = {
        label: item.label,
        iconName: item.label,
        links: [],
      };
    } else if (item.type === "link" && current) {
      current.links.push({ label: item.label, href: item.href });
    }
  }
  if (current) groups.push(current);
  return groups;
}

const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  TEACHER: [
    { type: "header", label: "Overview" },
    { type: "link", label: "Dashboard", href: "/dashboard" },

    { type: "divider" },
    { type: "header", label: "Courses" },
    { type: "link", label: "My Courses", href: "/dashboard/courses" },
    { type: "link", label: "Registration Codes", href: "/dashboard/codes" },

    { type: "divider" },
    { type: "header", label: "Assessments" },
    { type: "link", label: "Assessment List", href: "/dashboard/teacher/assessments" },

    { type: "divider" },
    { type: "header", label: "Assignments & Grading" },
    { type: "link", label: "Create Assignment", href: "/dashboard/teacher/assignments/create" },
    { type: "link", label: "Gradebook", href: "/dashboard/teacher/gradebook" },
  ],

  RESEARCHER: [
    { type: "header", label: "Overview" },
    { type: "link", label: "Dashboard", href: "/dashboard" },

    { type: "divider" },
    { type: "header", label: "Assessments" },
    { type: "link", label: "Assessment Data", href: "/dashboard/research/assessments" },

    { type: "divider" },
    { type: "header", label: "Courses" },
    { type: "link", label: "All Courses", href: "/dashboard/courses" },

    { type: "divider" },
    { type: "header", label: "Users" },
    { type: "link", label: "User Management", href: "/dashboard/staff" },

    { type: "divider" },
    { type: "header", label: "Exports" },
    { type: "link", label: "Download Exports", href: "/dashboard/research/exports" },

    { type: "divider" },
    { type: "header", label: "Registration" },
    { type: "link", label: "Registration Codes", href: "/dashboard/codes" },

    { type: "divider" },
    { type: "header", label: "Delegation" },
    { type: "link", label: "Sudo Delegation", href: "/dashboard/sudo" },
  ],

  STUDENT: [
    { type: "header", label: "Overview" },
    { type: "link", label: "Dashboard", href: "/dashboard" },

    { type: "divider" },
    { type: "header", label: "Courses" },
    { type: "link", label: "My Courses", href: "/dashboard/courses" },

    { type: "divider" },
    { type: "header", label: "Assessments" },
    { type: "link", label: "Mood Meter", href: "/dashboard/mood-meter" },
    { type: "link", label: "My Assignments", href: "/dashboard/assignments" },
  ],
};

export async function SidebarWrapper() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect("/login");
  }
  const userRole = profile.role as Role;

  let items = [...(NAV_BY_ROLE[userRole] ?? NAV_BY_ROLE.STUDENT)];

  if (userRole === "RESEARCHER") {
    const sudo = await getSudoCapabilities();
    const canGrantSudo = sudo?.canGrantSudo === true;
    if (!canGrantSudo) {
      items = items.filter(
        (item) =>
          !(item.type === "header" && item.label === "Delegation") &&
          !(item.type === "link" && item.href === "/dashboard/sudo")
      );
      // Remove consecutive dividers that may remain after filtering.
      items = items.filter((item, index) => {
        if (item.type !== "divider") return true;
        const prev = items[index - 1];
        const next = items[index + 1];
        if (!prev || !next) return false;
        return prev.type !== "divider" && next.type !== "divider";
      });
    }
  }
  const groups = groupNavItems(items);
  return <Sidebar role={userRole} groups={groups} />;
}
