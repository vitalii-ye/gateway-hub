"use client";

import { useEffect, useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { AppPanel } from "@/components/app/AppPanel";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import type { Project, Rule, ApiKey } from "@/lib/types";
import {
  getProjects,
  createProject,
  updateProject,
  deleteProject,
  getRules,
  createRule,
  updateRule,
  deleteRule,
  getApiKeys,
  createApiKey,
  deleteApiKey,
} from "@/lib/data";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [rulesByProject, setRulesByProject] = useState<Record<string, Rule[]>>({});
  const [keysByProject, setKeysByProject] = useState<Record<string, ApiKey[]>>({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAppName, setNewAppName] = useState("");
  const [newAppGuildId, setNewAppGuildId] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getProjects();
        if (cancelled) return;
        setProjects(data);

        const rules: Record<string, Rule[]> = {};
        const keys: Record<string, ApiKey[]> = {};
        await Promise.all(
          data.map(async (p) => {
            rules[p.id] = await getRules(p.id);
            keys[p.id] = await getApiKeys(p.id);
          })
        );
        if (cancelled) return;
        setRulesByProject(rules);
        setKeysByProject(keys);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load projects");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleCreateApp = async () => {
    if (!newAppName.trim()) return;
    setCreating(true);
    setError("");
    try {
      const project = await createProject(newAppName.trim(), newAppGuildId.trim());
      setProjects([project, ...projects]);
      setRulesByProject((prev) => ({ ...prev, [project.id]: [] }));
      setKeysByProject((prev) => ({ ...prev, [project.id]: [] }));
      setNewAppName("");
      setNewAppGuildId("");
      setShowCreateModal(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create project");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateConfig = async (id: string, config: Partial<Pick<Project, "name" | "guild_id">>) => {
    try {
      const updated = await updateProject(id, config);
      setProjects(projects.map((p) => (p.id === id ? updated : p)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update project");
    }
  };

  const handleRotateKey = async (projectId: string, label?: string) => {
    try {
      const existing = keysByProject[projectId] || [];
      for (const k of existing) {
        await deleteApiKey(k.id);
      }
      const newKey = await createApiKey(projectId, label);
      setKeysByProject((prev) => ({
        ...prev,
        [projectId]: [newKey],
      }));
      return newKey.raw_key;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to rotate key");
      return undefined;
    }
  };

  const handleCreateApiKey = async (projectId: string, label?: string) => {
    try {
      const newKey = await createApiKey(projectId, label);
      setKeysByProject((prev) => ({
        ...prev,
        [projectId]: [newKey, ...(prev[projectId] || [])],
      }));
      return newKey.raw_key;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create key");
      return undefined;
    }
  };

  const handleDeleteApiKey = async (id: string, projectId: string) => {
    try {
      await deleteApiKey(id);
      setKeysByProject((prev) => ({
        ...prev,
        [projectId]: (prev[projectId] || []).filter((k) => k.id !== id),
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete key");
    }
  };

  const handleDeleteApp = async (id: string) => {
    if (!confirm("Delete this app? This will also delete all rules and API keys. This action cannot be undone.")) return;
    try {
      await deleteProject(id);
      setProjects(projects.filter((p) => p.id !== id));
      setRulesByProject((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      setKeysByProject((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete project");
    }
  };

  const handleCreateRule = async (rule: Omit<Rule, "id" | "created_at">) => {
    try {
      const created = await createRule(rule);
      setRulesByProject((prev) => ({
        ...prev,
        [rule.project_id]: [created, ...(prev[rule.project_id] || [])],
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create rule");
    }
  };

  const handleUpdateRule = async (id: string, projectId: string, updates: Partial<Omit<Rule, "id" | "project_id" | "created_at">>) => {
    try {
      const updated = await updateRule(id, updates);
      setRulesByProject((prev) => ({
        ...prev,
        [projectId]: (prev[projectId] || []).map((r) => (r.id === id ? updated : r)),
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update rule");
    }
  };

  const handleDeleteRule = async (id: string, projectId: string) => {
    try {
      await deleteRule(id);
      setRulesByProject((prev) => ({
        ...prev,
        [projectId]: (prev[projectId] || []).filter((r) => r.id !== id),
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete rule");
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display font-bold text-2xl md:text-3xl text-text">Apps</h1>
          <p className="text-muted text-sm mt-1">Manage your game integrations and API keys</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <span className="flex flex-row items-center gap-2">
            <Plus className="w-4 h-4" />
            <p>New App</p>
          </span>
        </Button>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-muted animate-spin" />
        </div>
      ) : (
        <div className="space-y-4" role="list" aria-label="Applications">
          {projects.length === 0 ? (
            <Card className="text-center py-12">
              <CardContent className="pt-6">
                <div className="w-16 h-16 rounded-xl bg-amber/10 flex items-center justify-center mx-auto mb-4">
                  <Plus className="w-8 h-8 text-amber" />
                </div>
                <h3 className="text-lg font-medium text-text mb-2">No apps yet</h3>
                <p className="text-muted text-sm mb-6">Create your first app to get an API key for your game server</p>
                <Button onClick={() => setShowCreateModal(true)}>
                  <Plus className="w-4 h-4" />
                  Create App
                </Button>
              </CardContent>
            </Card>
          ) : (
            projects.map((project) => (
              <AppPanel
                key={project.id}
                project={project}
                rules={rulesByProject[project.id] || []}
                apiKeys={keysByProject[project.id] || []}
                onUpdateConfig={handleUpdateConfig}
                onRotateKey={handleRotateKey}
                onDeleteApp={handleDeleteApp}
                onCreateRule={handleCreateRule}
                onUpdateRule={handleUpdateRule}
                onDeleteRule={handleDeleteRule}
                onCreateApiKey={handleCreateApiKey}
                onDeleteApiKey={handleDeleteApiKey}
              />
            ))
          )}
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-void/60 backdrop-blur-sm animate-fade-in" onClick={() => setShowCreateModal(false)}>
          <Card className="w-full max-w-md animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <CardHeader>
              <CardTitle>Create New App</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
              <div>
                <Label htmlFor="app-name">App Name</Label>
                <Input
                  id="app-name"
                  placeholder="My Roblox Game"
                  value={newAppName}
                  onChange={(e) => setNewAppName(e.target.value)}
                  autoFocus
                />
              </div>
              <div>
                <Label htmlFor="app-guild">Guild ID (Discord Server)</Label>
                <Input
                  id="app-guild"
                  placeholder="123456789012345678"
                  value={newAppGuildId}
                  onChange={(e) => setNewAppGuildId(e.target.value)}
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCreateApp} disabled={creating || !newAppName.trim()}>
                  {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create App"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
