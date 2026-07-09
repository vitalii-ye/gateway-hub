"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase";
import { StatusBar } from "@/components/layout/StatusBar";
// import { Rail } from "@/components/layout/Rail";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [user, setUser] = useState<{
    email?: string;
    user_metadata?: { full_name?: string; avatar_url?: string };
  } | null>(null);
  const [loading, setLoading] = useState(true);

  const supabase = createClient();

  const signOut = async () => {
    await supabase.auth.signOut();
    window.location.href = "/login";
  };

  // In a real app, this would use a proper auth state listener
  // For now, we'll check session on mount
  // The actual auth check happens in the server component

  return (
    <div className="flex h-screen overflow-hidden">
      <StatusBar />
      <div className="flex-1 flex overflow-hidden">
        {/*<Rail user={user} onSignOut={signOut} />*/}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}