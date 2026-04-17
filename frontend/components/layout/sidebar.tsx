"use client";

import { useState, useRef, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Menu,
  X,
  LayoutDashboard,
  BookOpen,
  FileText,
  CheckSquare,
  KeyRound,
  Shield,
  Users,
  TrendingUp,
  Archive,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

import type { Role, NavGroup } from "@/components/layout/sidebarWrapper";

const GROUP_ICONS: Record<string, LucideIcon> = {
  Overview: LayoutDashboard,
  Courses: BookOpen,
  "Assignment Templates": FileText,
  "Assignments & Grading": CheckSquare,
  Registration: KeyRound,
  Analytics: TrendingUp,
  Exports: Archive,
  "Data & Exports": Archive,
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
  const [mobileOpen, setMobileOpen] = useState(false);
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
    <>
      <div className="fixed left-3 top-3 z-40 md:hidden">
        <Button
          type="button"
          variant="secondary"
          size="icon"
          className="h-10 w-10 rounded-full border border-sidebar-border/60 bg-sidebar text-sidebar-foreground shadow-sm"
          aria-label="Open navigation menu"
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>

      <Dialog open={mobileOpen} onOpenChange={setMobileOpen}>
        <DialogContent
          showCloseButton={false}
          className="!left-0 !top-0 !h-dvh !max-h-dvh !w-[18rem] !max-w-[18rem] !translate-x-0 !translate-y-0 overflow-hidden rounded-none border-r border-sidebar-border bg-sidebar p-0 text-sidebar-foreground sm:!max-w-[18rem]"
        >
          <DialogTitle className="sr-only">Navigation menu</DialogTitle>
          <div className="flex items-center justify-between border-b border-sidebar-border px-4 py-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-sidebar-foreground/60">
                Ready, Set, Resilience
              </p>
              <p className="mt-1 text-sm font-semibold text-sidebar-foreground">
                Navigation
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-full text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              aria-label="Close navigation menu"
              onClick={() => setMobileOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          <div className="flex max-h-[calc(100dvh-5rem)] flex-col gap-4 overflow-y-auto px-3 py-4">
            {groups.map((group) => {
              const Icon = GROUP_ICONS[group.iconName] ?? LayoutDashboard;
              return (
                <section
                  key={group.label}
                  className="rounded-2xl border border-sidebar-border/60 bg-sidebar-accent/20 p-2"
                >
                  <div className="mb-2 flex items-center gap-2 px-2 py-1">
                    <Icon className="h-4 w-4 text-sidebar-foreground/70" />
                    <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sidebar-foreground/60">
                      {group.label}
                    </span>
                  </div>
                  <div className="space-y-1">
                    {group.links.map((link) => {
                      const linkActive = isLinkActive(link.href);
                      return (
                        <Link
                          key={link.href}
                          href={link.href}
                          onClick={() => setMobileOpen(false)}
                          className={cn(
                            "block rounded-xl px-3 py-3 text-sm font-medium transition-colors",
                            linkActive
                              ? "bg-sidebar-primary text-sidebar-primary-foreground"
                              : "text-sidebar-foreground/85 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                          )}
                        >
                          {link.label}
                        </Link>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        </DialogContent>
      </Dialog>

      <nav
        className="relative hidden h-full flex-col bg-sidebar md:flex"
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
                <button
                  className={cn(
                    "flex h-11 w-full items-center justify-center",
                    "text-sidebar-foreground/70 transition-colors duration-150",
                    active && "bg-sidebar-accent text-sidebar-foreground",
                    !active && "hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
                  )}
                  aria-label={group.label}
                >
                  <Icon className="h-5 w-5" />
                </button>

                {active && (
                  <div className="absolute left-0 top-1 bottom-1 w-[3px] rounded-r bg-sidebar-primary" />
                )}

                <div
                  className={cn(
                    "absolute left-full top-0 z-50 ml-0 min-w-[180px]",
                    "origin-left rounded-r-lg border border-sidebar-border bg-sidebar shadow-lg",
                    "transition-all duration-200 ease-out",
                    isOpen
                      ? "pointer-events-auto scale-x-100 opacity-100"
                      : "pointer-events-none scale-x-0 opacity-0",
                  )}
                >
                  <div className="border-b border-sidebar-border px-3 py-2 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/60">
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
                              ? "bg-sidebar-accent text-sidebar-accent-foreground"
                              : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
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
    </>
  );
}
