"use client";

import Link from "next/link";

import { LayoutGrid, LogOut, User, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import {usePathname} from "next/navigation";

interface RailProps {
  user?: { email?: string; user_metadata?: { full_name?: string; avatar_url?: string } } | null;
  onSignOut: () => void;
}

export function Rail({ user, onSignOut }: RailProps) {
  const pathname = usePathname();

  const navItems = [{ href: "/dashboard", label: "Apps", icon: LayoutGrid }];

  return (
    <aside className="w-64 bg-panel rounded-r-lg flex flex-col h-full sticky top-12">
      <div className="p-4 border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-3" aria-label="Gateway Hub">
          <div className="w-8 h-8 rounded-lg bg-amber flex items-center justify-center">
            <Zap className="w-5 h-5 text-void" />
          </div>
          <span className="font-display font-bold text-xl text-text">Gateway Hub</span>
        </Link>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto" aria-label="Main navigation">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rail-item",
                isActive && "rail-item-active"
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <item.icon className="w-5 h-5" aria-hidden="true" />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-border space-y-2">

        {user && (
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0">
              {user.user_metadata?.avatar_url ? (
                <img src={user.user_metadata.avatar_url} alt="" className="w-8 h-8 rounded-full" />
              ) : (
                <User className="w-4 h-4 text-amber" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text truncate">
                {user.user_metadata?.full_name || user.email?.split("@")[0] || "User"}
              </p>
              <p className="text-xs text-muted truncate">{user.email}</p>
            </div>
          </div>
        )}

        <Button className="w-full" onClick={onSignOut}>
          <span className="flex items-center justify-center gap-2">
            <LogOut className="w-4 h-4" />
            <p>Sign Out</p>
          </span>
        </Button>
      </div>
    </aside>
  );
}
