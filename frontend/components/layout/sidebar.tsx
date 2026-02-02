"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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

const navItems = [
  { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { title: "Courses", href: "/courses", icon: BookOpen },
  { title: "Assessments", href: "/assessments", icon: FileText },
  { title: "Grading", href: "/grading", icon: CheckSquare },
  { title: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full border-r bg-green-900 text-white w-64">
      {/* Logo Area */}
      <div className="p-6 h-16 flex items-center border-b border-green-800">
        <h1 className="text-xl font-bold tracking-tight text-white">
          EE Lab <span className="text-green-400">Hub</span>
        </h1>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        {navItems.map((item) => (
          <Link key={item.href} href={item.href} passHref>
            <Button
              variant="ghost"
              className={cn(
                "w-full justify-start gap-3 transition-colors",
                // Active State: Blue text + Darker background
                pathname === item.href || pathname.startsWith(`${item.href}/`)
                  ? "bg-green-800 text-green-400" 
                  : "text-green-600 hover:bg-green-800 hover:text-white"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.title}
            </Button>
          </Link>
        ))}
      </nav>

      {/* Bottom Actions (Logout) */}
      <div className="p-4 border-t border-green-800">
        <Button 
          variant="ghost" 
          className="w-full justify-start gap-3 text-red-400 hover:bg-green-800 hover:text-red-300"
          onClick={() => {
             // We will implement real logout logic later
             window.location.href = "/login";
          }}
        >
          <LogOut className="h-5 w-5" />
          Log Out
        </Button>
      </div>
    </div>
  );
}