"use client";

import { Server, Zap, Wifi, Cpu } from "lucide-react";
import { StatusDot } from "@/components/StatusDot";

export function StatusBar() {
  return (
    <header className="h-12 bg-panel/80 backdrop-blur-sm border-b border-border flex items-center justify-between px-4 md:px-6 z-10">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-amber" />
          <span className="font-display font-semibold text-lg text-text">Gateway Hub</span>
        </div>
        <div className="hidden md:flex items-center gap-4 text-xs text-muted">
          <span className="flex items-center gap-1.5">
          </span>
        </div>
      </div>
    </header>
  );
}
