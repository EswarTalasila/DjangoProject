import { redirect } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { getSessionProfile } from "@/lib/auth-session";
import { LucideIcon } from "lucide-react";

export type Role = "TEACHER" | "RESEARCHER" | "STUDENT";

export type NavItem =
  | { type: "header"; label: string }
  | { type: "divider" }
  | { type: "link"; label: string; href: string; icon?: LucideIcon };


const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  TEACHER: [
    { type: "header", label: "Overview" },
    { type: "link", label: "Dashboard", href: "/dashboard" },

    { type: "divider" },
    { type: "header", label: "Courses" },
    { type: "link", label: "My Courses", href: "/dashboard/courses" },
    { type: "link", label: "Registration Codes", href: "/dashboard/codes" },

    //TODO: Further implementation of teacher side is required. They need a way to view students and add students to their course

    { type: "divider" },
    { type: "header", label: "Assessments" },
    { type: "link", label: "Assessment List", href: "/dashboard/teacher/assessments" },
    { type: "link", label: "Self Assessment", href: "/dashboard/teacher/self" },

    { type: "divider" },
    { type: "header", label: "Assignments & Grading" },
    { type: "link", label: "Create Assignment", href: "/dashboard/teacher/assignments/create" },
    { type: "link", label: "Gradebook", href: "/dashboard/teacher/gradebook" },

    { type: "divider" },
    { type: "header", label: "System" },
    { type: "link", label: "Settings", href: "/dashboard/settings" },
  ],

  RESEARCHER: [
    { type: "header", label: "Overview" },
    { type: "link", label: "Dashboard", href: "/dashboard" },

    { type: "divider" },
    { type: "header", label: "Assessments" },
    { type: "link", label: "Assessment Data", href: "/dashboard/research/assessments" },

    { type: "divider" },
    { type: "header", label: "Exports" },
    { type: "link", label: "Download Exports", href: "/dashboard/research/exports" },

    { type: "divider" },
    { type: "header", label: "Registration" },
    { type: "link", label: "Registration Codes", href: "/dashboard/codes" },

    { type: "divider" },
    { type: "header", label: "System" },
    { type: "link", label: "Settings", href: "/dashboard/settings" },
  ],

  STUDENT: [
    { type: "header", label: "Overview" },
    { type: "link", label: "Dashboard", href: "/dashboard" },

    { type: "divider" },
    { type: "header", label: "Assessments" },
    { type: "link", label: "Mood Meter", href: "/dashboard/mood-meter" },
    { type: "link", label: "My Assignments", href: "/dashboard/assignments" },

    { type: "divider" },
    { type: "header", label: "System" },
    { type: "link", label: "Settings", href: "/dashboard/settings" },
  ],
};

export async function SidebarWrapper() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect("/login");
  }
  const userRole = profile.role as Role;

  const items = NAV_BY_ROLE[userRole] ?? NAV_BY_ROLE.STUDENT;
  return <Sidebar role={userRole} items={items} />;
}
