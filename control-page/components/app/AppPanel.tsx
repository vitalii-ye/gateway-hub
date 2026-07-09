"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Copy, ExternalLink, RefreshCw, RotateCcw, Settings, Trash2, Zap, Key } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Dropdown, DropdownItem, DropdownDivider } from "@/components/ui/Dropdown";
import { Tooltip } from "@/components/ui/Tooltip";
import { StatusDot } from "@/components/StatusDot";
import { KeyCardEject } from "@/components/KeyCardEject";
import { RulesPanel } from "@/components/app/RulesPanel";
import { validateSnowflake } from "@/lib/utils";
import { getBotStatus } from "@/lib/data";
import type { Project, Rule, ApiKey, BotStatus } from "@/lib/types";

const DISCORD_CLIENT_ID = process.env.NEXT_PUBLIC_DISCORD_CLIENT_ID;
// View Channel (1024) + Send Messages (2048) + Embed Links (16384)
const BOT_INVITE_PERMISSIONS = "19456";

interface AppPanelProps {
  project: Project;
  rules: Rule[];
  apiKeys: ApiKey[];
  onUpdateConfig: (id: string, config: Partial<Pick<Project, "name" | "guild_id">>) => Promise<void>;
  onRotateKey: (projectId: string, label?: string) => Promise<string | undefined>;
  onDeleteApp: (id: string) => void;
  onCreateRule: (rule: Omit<Rule, "id" | "created_at">) => Promise<void>;
  onUpdateRule: (id: string, projectId: string, updates: Partial<Omit<Rule, "id" | "project_id" | "created_at">>) => Promise<void>;
  onDeleteRule: (id: string, projectId: string) => Promise<void>;
  onCreateApiKey: (projectId: string, label?: string) => Promise<string | undefined>;
  onDeleteApiKey: (id: string, projectId: string) => Promise<void>;
}

export function AppPanel({
  project,
  rules,
  apiKeys,
  onUpdateConfig,
  onRotateKey,
  onDeleteApp,
  onCreateRule,
  onUpdateRule,
  onDeleteRule,
  onCreateApiKey,
  onDeleteApiKey,
}: AppPanelProps) {
  const [expanded, setExpanded] = useState(true);
  const [showKeyCard, setShowKeyCard] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [guildId, setGuildId] = useState(project.guild_id || "");
  const [guildIdError, setGuildIdError] = useState("");
  const [rotating, setRotating] = useState(false);
  const [showKeyLabel, setShowKeyLabel] = useState(false);
  const [keyLabel, setKeyLabel] = useState("");
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [botStatusLoading, setBotStatusLoading] = useState(true);
  const [botStatusError, setBotStatusError] = useState("");
  const [botStatusRefreshTick, setBotStatusRefreshTick] = useState(0);

  useEffect(() => {
    if (!expanded) return;
    let cancelled = false;
    (async () => {
      try {
        const status = await getBotStatus(project.id);
        if (cancelled) return;
        setBotStatus(status);
        setBotStatusError("");
      } catch (err) {
        if (cancelled) return;
        setBotStatus(null);
        setBotStatusError(err instanceof Error ? err.message : "Failed to check bot status");
      } finally {
        if (!cancelled) setBotStatusLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [expanded, project.id, botStatusRefreshTick]);

  const refreshBotStatus = () => {
    setBotStatusLoading(true);
    setBotStatusRefreshTick((tick) => tick + 1);
  };

  const handleGuildIdChange = (value: string) => {
    setGuildId(value);
    setGuildIdError(value && !validateSnowflake(value) ? "Must be a 17–19 digit Discord snowflake" : "");
  };

  const handleSaveConfig = async () => {
    if (guildId && guildIdError) return;
    await onUpdateConfig(project.id, { guild_id: guildId });
    refreshBotStatus();
  };

  const inviteUrl =
    DISCORD_CLIENT_ID && project.guild_id
      ? `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&scope=bot&permissions=${BOT_INVITE_PERMISSIONS}&guild_id=${project.guild_id}&disable_guild_select=true`
      : null;

  const handleRotateKey = async () => {
    setRotating(true);
    try {
      const rawKey = await onRotateKey(project.id, keyLabel || undefined);
      if (rawKey) {
        setNewKey(rawKey);
        setShowKeyCard(true);
      }
    } finally {
      setRotating(false);
      setKeyLabel("");
      setShowKeyLabel(false);
    }
  };

  const handleCreateNewKey = async () => {
    const rawKey = await onCreateApiKey(project.id, keyLabel || undefined);
    if (rawKey) {
      setNewKey(rawKey);
      setShowKeyCard(true);
    }
    setKeyLabel("");
    setShowKeyLabel(false);
  };

  const displayKey = apiKeys.length > 0 ? "••••••••••••••••" : "No key";

  if (!expanded) {
    return (
      <div className="panel overflow-hidden animate-fade-in">
        <div className="app-panel-header">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <button
              onClick={() => setExpanded(true)}
              className="p-1.5 rounded-lg text-muted hover:text-text hover:bg-border transition-colors"
              aria-label="Expand"
            >
              <ChevronDown className="w-5 h-5 rotate-180" />
            </button>
            <div className="min-w-0">
              <p className="font-body font-medium text-text truncate">{project.name}</p>
              <p className="text-xs text-muted font-mono">{project.guild_id || "No guild"}</p>
            </div>
          </div>
          <StatusDot status="idle" label="Collapsed" size="sm" />
        </div>
      </div>
    );
  }

  return (
    <div className="panel overflow-hidden animate-scale-in">
      <div className="app-panel-header">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            onClick={() => setExpanded(false)}
            className="p-1.5 rounded-lg text-muted hover:text-text hover:bg-border transition-colors flex-shrink-0"
            aria-label="Collapse"
          >
            <ChevronDown className="w-5 h-5" />
          </button>
          <div className="min-w-0 flex-1">
            <p className="font-body font-semibold text-text truncate">{project.name}</p>
            <p className="text-xs text-muted font-mono">{project.guild_id || "No guild configured"}</p>
          </div>
          <div className="flex items-center gap-2">
            {botStatus ? (
              botStatus.installed ? (
                <StatusDot status="live" label="Active" size="sm" />
              ) : (
                <StatusDot status="warning" label="Bot missing" size="sm" />
              )
            ) : (
              <StatusDot status="idle" label={botStatusError ? "Unknown" : "—"} size="sm" />
            )}
            <Dropdown
              trigger={<button className="p-1.5 rounded-lg text-muted hover:text-text hover:bg-border transition-colors" aria-label="More options"><Settings className="w-5 h-5" /></button>}
              content={
                <>
                  <DropdownItem onClick={() => setShowKeyLabel(true)}>
                    <Key className="w-4 h-4 mr-2" />
                    New API Key
                  </DropdownItem>
                  <DropdownItem onClick={handleRotateKey} disabled={rotating || apiKeys.length === 0}>
                    <Zap className="w-4 h-4 mr-2" />
                    Rotate Key
                  </DropdownItem>
                  <DropdownDivider />
                  <DropdownItem onClick={() => onDeleteApp(project.id)} destructive>
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete App
                  </DropdownItem>
                </>
              }
              align="right"
            />
          </div>
        </div>
      </div>

      <div className="app-panel-section">
        <p className="section-title">API Key</p>
        {apiKeys.length === 0 ? (
          <div className="text-center py-4">
            <p className="text-sm text-muted mb-3">No API key yet</p>
            <Button onClick={() => setShowKeyLabel(true)} size="sm">
              <Key className="w-4 h-4" />
              Create API Key
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            {apiKeys.map((k) => (
              <div key={k.id} className="flex items-center gap-3">
                <div className="relative flex-1">
                  <code className="key-code w-full">{k.label ? `${k.label}: ` : ""}{displayKey}</code>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <Tooltip content="Copy key (raw key only available at creation)" position="top">
                      <button
                        className="flex items-center p-1.5 rounded-lg text-muted hover:text-text hover:bg-border transition-colors"
                        aria-label="Info"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </Tooltip>
                  </div>
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => onDeleteApiKey(k.id, project.id)}
                  className="whitespace-nowrap"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={handleRotateKey} disabled={rotating} className="whitespace-nowrap">
                <RotateCcw className="w-3.5 h-3.5" />
                Rotate Key
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="app-panel-section">
        <p className="section-title">Configuration</p>
        <div className="grid gap-4">
          <div>
            <Label htmlFor={`guild-${project.id}`}>Guild ID (Discord Server)</Label>
            <Input
              id={`guild-${project.id}`}
              type="text"
              placeholder="123456789012345678"
              value={guildId}
              onChange={(e) => handleGuildIdChange(e.target.value)}
              aria-describedby={guildIdError ? `guild-error-${project.id}` : undefined}
            />
            {guildIdError && (
              <p id={`guild-error-${project.id}`} className="mt-1.5 text-xs text-red-400" role="alert">
                {guildIdError}
              </p>
            )}
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {botStatusLoading ? (
              <StatusDot status="idle" label="Checking bot…" size="sm" />
            ) : botStatusError ? (
              <StatusDot status="error" label="Status unavailable" size="sm" />
            ) : botStatus?.installed ? (
              <StatusDot status="live" label="Bot installed" size="sm" />
            ) : (
              <StatusDot status="warning" label="Bot not in server" size="sm" />
            )}
            <Tooltip content="Re-check bot status" position="top">
              <button
                onClick={refreshBotStatus}
                disabled={botStatusLoading}
                className="p-1.5 rounded-lg text-muted hover:text-text hover:bg-border transition-colors disabled:opacity-50"
                aria-label="Re-check bot status"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${botStatusLoading ? "animate-spin" : ""}`} />
              </button>
            </Tooltip>
          </div>
          <div className="flex items-center gap-2">
            {!botStatusLoading && !botStatus?.installed && project.guild_id && (
              inviteUrl ? (
                <Button
                  variant="secondary"
                  onClick={() => window.open(inviteUrl, "_blank", "noopener,noreferrer")}
                >
                  <ExternalLink className="w-4 h-4" />
                  Add bot to server
                </Button>
              ) : (
                <Tooltip content="NEXT_PUBLIC_DISCORD_CLIENT_ID is not configured" position="top">
                  <span>
                    <Button variant="secondary" disabled>
                      <ExternalLink className="w-4 h-4" />
                      Add bot to server
                    </Button>
                  </span>
                </Tooltip>
              )
            )}
            <Button onClick={handleSaveConfig} disabled={!!guildIdError}>
              Save Config
            </Button>
          </div>
        </div>
      </div>

      <div className="app-panel-section">
        <RulesPanel
          projectId={project.id}
          rules={rules}
          onCreateRule={onCreateRule}
          onUpdateRule={onUpdateRule}
          onDeleteRule={onDeleteRule}
        />
      </div>

      {showKeyLabel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-void/60 backdrop-blur-sm animate-fade-in" onClick={() => { setShowKeyLabel(false); setKeyLabel(""); }}>
          <div className="w-full max-w-sm bg-panel border border-border rounded-xl p-6 shadow-lg animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-body font-medium text-text mb-3">Label for new API key (optional)</p>
            <Input
              placeholder="e.g. Production"
              value={keyLabel}
              onChange={(e) => setKeyLabel(e.target.value)}
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="ghost" onClick={() => { setShowKeyLabel(false); setKeyLabel(""); }}>Cancel</Button>
              <Button onClick={handleCreateNewKey}>Create Key</Button>
            </div>
          </div>
        </div>
      )}

      {showKeyCard && (
        <KeyCardEject
          apiKey={newKey}
          label={`${project.name} — New API Key`}
          onClose={() => {
            setShowKeyCard(false);
            setNewKey("");
          }}
          onCopy={() => {}}
        />
      )}
    </div>
  );
}
