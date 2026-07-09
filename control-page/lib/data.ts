import { createClient } from "@/lib/supabase";
import type { Project, Rule, ApiKey, ApiKeyWithRaw, BotStatus } from "@/lib/types";

const supabase = createClient();

const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL!;

// ── Projects ──────────────────────────────────────────────────────────

export async function getProjects(): Promise<Project[]> {
  const { data, error } = await supabase
    .from("projects")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) throw error;
  return data ?? [];
}

export async function getProject(id: string): Promise<Project | null> {
  const { data, error } = await supabase
    .from("projects")
    .select("*")
    .eq("id", id)
    .single();

  if (error) throw error;
  return data;
}

export async function createProject(name: string, guildId: string): Promise<Project> {
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) throw new Error("Not authenticated");

  const { data, error } = await supabase
    .from("projects")
    .insert({
      name,
      guild_id: guildId,
      owner_id: user.id,
    })
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function updateProject(
  id: string,
  updates: Partial<Pick<Project, "name" | "guild_id">>
): Promise<Project> {
  const { data, error } = await supabase
    .from("projects")
    .update({ ...updates, updated_at: new Date().toISOString() })
    .eq("id", id)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function deleteProject(id: string): Promise<void> {
  const { error } = await supabase.from("projects").delete().eq("id", id);
  if (error) throw error;
}

// ── Rules ─────────────────────────────────────────────────────────────

export async function getRules(projectId: string): Promise<Rule[]> {
  const { data, error } = await supabase
    .from("rules")
    .select("*")
    .eq("project_id", projectId)
    .order("created_at", { ascending: false });

  if (error) throw error;
  return data ?? [];
}

export async function createRule(
  rule: Omit<Rule, "id" | "created_at">
): Promise<Rule> {
  const { data, error } = await supabase
    .from("rules")
    .insert(rule)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function updateRule(
  id: string,
  updates: Partial<Omit<Rule, "id" | "project_id" | "created_at">>
): Promise<Rule> {
  const { data, error } = await supabase
    .from("rules")
    .update(updates)
    .eq("id", id)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function deleteRule(id: string): Promise<void> {
  const { error } = await supabase.from("rules").delete().eq("id", id);
  if (error) throw error;
}

// ── API Keys ──────────────────────────────────────────────────────────

export async function getApiKeys(projectId: string): Promise<ApiKey[]> {
  const { data, error } = await supabase
    .from("api_keys_public")
    .select("*")
    .eq("project_id", projectId)
    .order("created_at", { ascending: false });

  if (error) throw error;
  return data ?? [];
}

export async function createApiKey(
  projectId: string,
  label?: string
): Promise<ApiKeyWithRaw> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) throw new Error("Not authenticated");

  const response = await fetch(
    `${GATEWAY_URL}/v1/projects/${projectId}/api-keys`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ label: label ?? null }),
    }
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Failed to create API key");
  }

  return response.json();
}

export async function getBotStatus(projectId: string): Promise<BotStatus> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) throw new Error("Not authenticated");

  const response = await fetch(
    `${GATEWAY_URL}/v1/projects/${projectId}/bot-status`,
    {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
    }
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Failed to check bot status");
  }

  return response.json();
}

export async function deleteApiKey(id: string): Promise<void> {
  const { error } = await supabase.from("api_keys").delete().eq("id", id);
  if (error) throw error;
}
