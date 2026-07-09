"use client";

interface StatusDotProps {
  status: "live" | "idle" | "warning" | "error";
  label?: string;
  size?: "sm" | "md" | "lg";
}

export function StatusDot({ status, label, size = "md" }: StatusDotProps) {
  const sizes = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-3 h-3",
  };

  const statusClasses = {
    live: "bg-signal shadow-[0_0_8px_var(--color-signal)] animate-pulse-signal",
    idle: "bg-muted",
    warning: "bg-amber shadow-[0_0_8px_var(--color-amber)]",
    error: "bg-red-500 shadow-[0_0_8px_rgb(239,68,68)]",
  };

  const labels = {
    live: "Live",
    idle: "Idle",
    warning: "Degraded",
    error: "Error",
  };

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`status-dot ${sizes[size]} ${statusClasses[status]}`} aria-hidden="true" />
      {label && <span className="text-sm font-body text-text">{label}</span>}
      {!label && <span className="sr-only">{labels[status]}</span>}
    </span>
  );
}