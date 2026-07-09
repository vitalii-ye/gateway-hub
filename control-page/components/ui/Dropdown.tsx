"use client";

import { useState, useRef, useEffect, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { MoreHorizontal, ChevronDown } from "lucide-react";

interface DropdownProps {
  trigger: ReactNode;
  content: ReactNode;
  align?: "left" | "right";
}

export function Dropdown({ trigger, content, align = "right" }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={dropdownRef} className="relative inline-block">
      <div onClick={() => setOpen(!open)} className="flex items-center gap-1">
        {trigger}
      </div>

      {open && (
        <div
          className={cn(
            "fixed z-50 mt-1.5 min-w-[160px] bg-panel border border-border rounded-lg shadow-elevated animate-scale-in",
            align === "right" ? "right-0" : "left-0"
          )}
          role="menu"
        >
          {content}
        </div>
      )}
    </div>
  );
}

interface DropdownItemProps {
  onClick?: () => void;
  children: ReactNode;
  destructive?: boolean;
  disabled?: boolean;
}

export function DropdownItem({ onClick, children, destructive, disabled }: DropdownItemProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex w-full items-center px-3 py-2 text-left text-sm font-body transition-colors",
        "hover:bg-border focus:bg-border focus:outline-none",
        destructive ? "text-red-400" : "text-text",
        disabled ? "opacity-50 pointer-events-none" : ""
      )}
      role="menuitem"
    >
      {children}
    </button>
  );
}

export function DropdownDivider() {
  return <hr className="my-1 border-border" role="separator" />;
}