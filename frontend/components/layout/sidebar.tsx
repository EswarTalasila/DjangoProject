"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Cookies from "js-cookie";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  CheckSquare,
  Settings,
  LogOut
} from "lucide-react";

import type { Role, NavItem } from "@/components/layout/sidebarWrapper";

type SidebarProps = {
  role: Role;
  items: NavItem[];
};

export function Sidebar({ role, items }: SidebarProps) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full border-r bg-[#bad28f] text-[#754d28] w-64">
      {/* Logo Area */}
      <div className="p-6 h-16 flex items-center border-b border-[#a9c17f]">
        <h1 className="text-xl font-bold tracking-tight text-[#754d28]">
          EE Lab <span className="text-[#754d28]">Hub</span>
        </h1>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        {items.map((item, idx) => {
          if (item.type === "divider") {
            return <div key={`div-${idx}`} className="my-3 border-t border-[#a9c17f]" />;
          }

          if (item.type === "header") {
            return (
              <div
                key={`hdr-${idx}`}
                className="px-2 pt-2 pb-1 text-xs font-semibold uppercase tracking-wider text-[#754d28]/80"
              >
                {item.label}
              </div>
            );
          }

          const isActive =
            pathname === item.href || pathname.startsWith(`${item.href}/`);

          const Icon =
            item.icon ??
            (item.href.includes("course")
              ? BookOpen
              : item.href.includes("assess")
              ? FileText
              : item.href.includes("grade")
              ? CheckSquare
              : item.href.includes("setting")
              ? Settings
              : LayoutDashboard);

          return (
            <Link key={item.href} href={item.href} passHref>
              <Button
                variant="ghost"
                className={cn(
                  "w-full justify-start gap-3 transition-colors",
                  isActive
                    ? "bg-[#a9c17f] text-[#754d28]"
                    : "text-[#754d28] hover:bg-[#a9c17f]"
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Button>
            </Link>
          );
        })}
      </nav>

      {/* Bottom Actions (Logout) */}
      <div className="p-4 border-t border-[#a9c17f]">
        <Button 
          variant="ghost" 
          className="w-full justify-start gap-3 text-red-600 hover:bg-[#a9c17f]"
          onClick={async () => {
            try {
              await api.post("/auth/session-revocations", {});
            } catch {
              // Continue logout UX even if backend session revocation fails.
            } finally {
             Cookies.remove("user_name");
             window.location.href = "/login";
            }
          }}
        >
          <LogOut className="h-5 w-5" />
          Log Out
        </Button>
      </div>
    </div>
  );
}
