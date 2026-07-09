"use client";

import { useState } from "react";
import { Plus, Trash2, Pencil, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import type { Rule } from "@/lib/types";

interface RulesPanelProps {
  projectId: string;
  rules: Rule[];
  onCreateRule: (rule: Omit<Rule, "id" | "created_at">) => Promise<void>;
  onUpdateRule: (id: string, projectId: string, updates: Partial<Omit<Rule, "id" | "project_id" | "created_at">>) => Promise<void>;
  onDeleteRule: (id: string, projectId: string) => Promise<void>;
}

export function RulesPanel({ projectId, rules, onCreateRule, onUpdateRule, onDeleteRule }: RulesPanelProps) {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [name, setName] = useState("");
  const [eventType, setEventType] = useState("");
  const [discordChannelId, setDiscordChannelId] = useState("");
  const [messageTemplate, setMessageTemplate] = useState("");

  const resetForm = () => {
    setName("");
    setEventType("");
    setDiscordChannelId("");
    setMessageTemplate("");
    setShowForm(false);
    setEditingId(null);
  };

  const startEdit = (rule: Rule) => {
    setEditingId(rule.id);
    setName(rule.name);
    setEventType(rule.event_type);
    setDiscordChannelId(rule.discord_channel_id);
    setMessageTemplate(rule.message_template);
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!name.trim() || !eventType.trim() || !discordChannelId.trim() || !messageTemplate.trim()) return;
    setLoading(true);
    try {
      if (editingId) {
        await onUpdateRule(editingId, projectId, {
          name: name.trim(),
          event_type: eventType.trim(),
          discord_channel_id: discordChannelId.trim(),
          message_template: messageTemplate.trim(),
        });
      } else {
        await onCreateRule({
          project_id: projectId,
          name: name.trim(),
          event_type: eventType.trim(),
          discord_channel_id: discordChannelId.trim(),
          message_template: messageTemplate.trim(),
          enabled: true,
        });
      }
      resetForm();
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (rule: Rule) => {
    await onUpdateRule(rule.id, projectId, { enabled: !rule.enabled });
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this rule?")) return;
    await onDeleteRule(id, projectId);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="section-title">Rules</p>
        {!showForm && (
          <Button variant="secondary" size="sm" onClick={() => { resetForm(); setShowForm(true); }}>
            <Plus className="w-3.5 h-3.5" />
            Add Rule
          </Button>
        )}
      </div>

      {showForm && (
        <div className="p-3 rounded-lg bg-void/50 border border-border space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label>Rule Name</Label>
              <Input placeholder="VIP Purchase Alert" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <Label>Event Type</Label>
              <Input placeholder="purchase" value={eventType} onChange={(e) => setEventType(e.target.value)} />
            </div>
            <div>
              <Label>Discord Channel ID</Label>
              <Input placeholder="123456789012345678" value={discordChannelId} onChange={(e) => setDiscordChannelId(e.target.value)} />
            </div>
            <div>
              <Label>Message Template</Label>
              <Input placeholder="User {{username}} purchased {{item}}" value={messageTemplate} onChange={(e) => setMessageTemplate(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={resetForm}>Cancel</Button>
            <Button size="sm" onClick={handleSubmit} disabled={loading || !name.trim() || !eventType.trim() || !discordChannelId.trim() || !messageTemplate.trim()}>
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : editingId ? "Update Rule" : "Create Rule"}
            </Button>
          </div>
        </div>
      )}

      {rules.length === 0 && !showForm ? (
        <p className="text-xs text-muted py-2">No rules configured yet</p>
      ) : (
        <div className="space-y-2">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center gap-3 px-3 py-2.5 bg-void/50 rounded-lg border border-border/50 hover:border-border transition-colors"
            >
              <button
                onClick={() => handleToggle(rule)}
                className={`w-8 h-4.5 rounded-full relative transition-colors flex-shrink-0 ${
                  rule.enabled ? "bg-signal/30" : "bg-border"
                }`}
                aria-label={rule.enabled ? "Disable rule" : "Enable rule"}
              >
                <span
                  className={`absolute top-0.75 w-3 h-3 rounded-full transition-transform ${
                    rule.enabled ? "left-4 bg-signal" : "left-0.5 bg-muted"
                  }`}
                />
              </button>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-body font-medium text-text truncate">{rule.name}</p>
                <p className="text-xs text-muted font-mono truncate">
                  {rule.event_type} → {rule.discord_channel_id}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => startEdit(rule)}
                  className="p-1.5 rounded-lg text-muted hover:text-text hover:bg-border transition-colors"
                  aria-label="Edit rule"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleDelete(rule.id)}
                  className="p-1.5 rounded-lg text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
                  aria-label="Delete rule"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
