"use client";

import { useState, useRef, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  CheckSquare,
  KeyRound,
  LibraryBig,
  Shield,
  Users,
  TrendingUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { Role, NavGroup } from "@/components/layout/sidebarWrapper";

const GROUP_ICONS: Record<string, LucideIcon> = {
  Overview: LayoutDashboard,
  Courses: BookOpen,
  Assessments: FileText,
  "Assignments & Grading": CheckSquare,
  Registration: KeyRound,
  Analytics: TrendingUp,
  Exports: LibraryBig,
  Users: Users,
  Delegation: Shield,
};

type SidebarProps = {
  role: Role;
  groups: NavGroup[];
};

export function Sidebar({ role, groups }: SidebarProps) {
  const pathname = usePathname();
  const [hoveredGroup, setHoveredGroup] = useState<string | null>(null);
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isLinkActive = useCallback(
    (href: string) =>
      href === "/dashboard"
        ? pathname === "/dashboard"
        : pathname === href || pathname.startsWith(`${href}/`),
    [pathname]
  );

  const isGroupActive = useCallback(
    (group: NavGroup) => group.links.some((link) => isLinkActive(link.href)),
    [isLinkActive]
  );

  const handleMouseEnter = (label: string) => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    setHoveredGroup(label);
  };

  const handleMouseLeave = () => {
    hoverTimeoutRef.current = setTimeout(() => setHoveredGroup(null), 150);
  };

  return (
    <nav
      className="relative flex flex-col h-full bg-sidebar"
      style={{ width: 60 }}
    >
      <div className="flex flex-col gap-1 py-4">
        {groups.map((group) => {
          const active = isGroupActive(group);
          const isOpen = hoveredGroup === group.label;
          const Icon = GROUP_ICONS[group.iconName] ?? LayoutDashboard;

          return (
            <div
              key={group.label}
              className="relative"
              onMouseEnter={() => handleMouseEnter(group.label)}
              onMouseLeave={handleMouseLeave}
            >
              {/* Icon tab */}
              <button
                className={cn(
                  "flex items-center justify-center w-full h-11",
                  "text-sidebar-foreground/70 transition-colors duration-150",
                  active && "text-sidebar-foreground bg-sidebar-accent",
                  !active && "hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                )}
                aria-label={group.label}
              >
                <Icon className="h-5 w-5" />
              </button>

              {/* Active indicator bar */}
              {active && (
                <div className="absolute left-0 top-1 bottom-1 w-[3px] rounded-r bg-sidebar-primary" />
              )}

              {/* Flyout panel */}
              <div
                className={cn(
                  "absolute left-full top-0 ml-0 min-w-[180px] z-50",
                  "bg-sidebar border border-sidebar-border rounded-r-lg shadow-lg",
                  "transition-all duration-200 ease-out origin-left",
                  isOpen
                    ? "opacity-100 scale-x-100 pointer-events-auto"
                    : "opacity-0 scale-x-0 pointer-events-none"
                )}
              >
                <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/60 border-b border-sidebar-border">
                  {group.label}
                </div>
                <div className="py-1">
                  {group.links.map((link) => {
                    const linkActive = isLinkActive(link.href);
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        className={cn(
                          "block px-3 py-2 text-sm transition-colors",
                          linkActive
                            ? "text-sidebar-accent-foreground bg-sidebar-accent"
                            : "text-sidebar-foreground/80 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                        )}
                      >
                        {link.label}
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </nav>
  );
}
