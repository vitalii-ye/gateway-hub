"use client";

import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: string;
  children: ReactNode;
  position?: "top" | "bottom" | "left" | "right";
}

export function Tooltip({ content, children, position = "top" }: TooltipProps) {
  const [visible, setVisible] = useState(false);

  const positions = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  const arrows = {
    top: "top-full left-1/2 -translate-x-1/2 border-t-amber",
    bottom: "bottom-full left-1/2 -translate-x-1/2 border-b-amber",
    left: "left-full top-1/2 -translate-y-1/2 border-l-amber",
    right: "right-full top-1/2 -translate-y-1/2 border-r-amber",
  };

  return (
    <div className="relative inline-block" onMouseEnter={() => setVisible(true)} onMouseLeave={() => setVisible(false)}>
      {children}
      {visible && (
        <div
          className={cn(
            "fixed z-50 px-2 py-1.5 text-xs font-body text-void bg-amber rounded shadow-elevated whitespace-nowrap animate-fade-in pointer-events-none",
            positions[position]
          )}
          style={{ transformOrigin: position }}
        >
          {content}
          <div
            className={cn(
              "absolute w-0 h-0 border-4 border-transparent",
              arrows[position]
            )}
          />
        </div>
      )}
    </div>
  );
}