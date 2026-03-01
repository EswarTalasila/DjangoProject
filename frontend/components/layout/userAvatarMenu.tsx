"use client";

import Link from "next/link";
import { Settings, LogOut } from "lucide-react";
import { logout } from "@/lib/logout";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type UserAvatarMenuProps = {
  name: string;
  username: string;
  role: string;
};

function getInitial(name: string, username: string): string {
  const source = name.trim() || username.trim();
  if (!source) return "U";
  return source.charAt(0).toUpperCase();
}

export function UserAvatarMenu({ name, username, role }: UserAvatarMenuProps) {
  const initial = getInitial(name, username);
  const displayName = name.trim() || username;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="h-8 w-8 rounded-full bg-primary text-primary-foreground font-semibold text-sm flex items-center justify-center hover:ring-2 hover:ring-primary/50 transition-shadow"
          aria-label="User menu"
        >
          {initial}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>
          <div className="flex flex-col">
            <span className="text-sm font-medium">{displayName}</span>
            <span className="text-xs text-muted-foreground">{role}</span>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/dashboard/settings" className="flex items-center gap-2 cursor-pointer">
            <Settings className="h-4 w-4" />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="text-destructive focus:text-destructive cursor-pointer"
          onClick={() => { logout(); }}
        >
          <LogOut className="h-4 w-4 mr-2" />
          Log Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
