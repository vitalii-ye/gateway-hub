"use client";

import { useEffect, useState } from "react";
import { Copy, X, Key } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/Tooltip";

interface KeyCardEjectProps {
  apiKey: string;
  label?: string;
  onClose: () => void;
  onCopy: () => void;
}

export function KeyCardEject({ apiKey, label = "API Key", onClose, onCopy }: KeyCardEjectProps) {
  const [copied, setCopied] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (copied) {
      const timer = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [copied]);

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    onCopy();
    setCopied(true);
  };

  const maskedKey = apiKey.length > 20 ? apiKey.slice(0, 12) + "..." + apiKey.slice(-8) : apiKey;

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center px-4 py-6 sm:px-6 pointer-events-none animate-slide-in",
        visible && "pointer-events-auto"
      )}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={label}
    >
      <div
        className="fixed inset-0 bg-void/60 backdrop-blur-sm pointer-events-auto"
        onClick={(e) => e.stopPropagation()}
      />
      <div
        className={cn(
          "relative w-full max-w-md bg-panel border border-amber/30 rounded-2xl shadow-key-card overflow-hidden",
          "transform transition-all duration-500 ease-out",
          "p-5 sm:p-6",
          visible ? "opacity-100 translate-y-0 scale-100" : "opacity-0 translate-y-4 scale-95"
        )}
        onClick={(e) => e.stopPropagation()}
        style={{ pointerEvents: "auto" }}
      >
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-amber/20 via-amber to-amber/20" />

        <div className="flex items-start justify-between gap-4 mb-5">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-amber/10 border border-amber/20 flex items-center justify-center shrink-0">
              <Key className="w-4 h-4 text-amber" />
            </div>
            <div>
              <p className="text-[11px] font-body text-muted uppercase tracking-[0.18em]">{label}</p>
              <p className="text-base font-body text-text font-semibold mt-0.5">Live Key</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-muted hover:text-text hover:bg-border transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="mb-5 flex items-center gap-3 rounded-xl border border-border bg-void px-4 py-3.5">
          <code className="min-w-0 flex-1 font-mono text-sm sm:text-base text-text select-all cursor-pointer break-all" onClick={handleCopy}>
            {maskedKey}
          </code>
          <Tooltip content={copied ? "Copied!" : "Copy to clipboard"} position="top">
            <button
              onClick={handleCopy}
              className={cn(
                "shrink-0 p-1.5 rounded-lg transition-all border border-border/60",
                copied ? "bg-signal/20 text-signal" : "text-muted hover:text-text hover:bg-border"
              )}
              aria-label={copied ? "Copied" : "Copy key"}
            >
              <Copy className="w-4 h-4" />
            </button>
          </Tooltip>
        </div>

        <div className="flex items-center gap-3 text-xs text-muted mb-6">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
            <span>Active — Use immediately in your game server</span>
          </span>
        </div>

        <button
          onClick={onClose}
          className="w-full px-4 py-3 bg-amber/10 border border-amber/30 text-amber font-body font-medium rounded-xl hover:bg-amber/20 transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  );
}