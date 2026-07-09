export interface Project {
  id: string;
  owner_id: string;
  name: string;
  guild_id: string;
  created_at: string;
  updated_at: string;
}

export interface Rule {
  id: string;
  project_id: string;
  name: string;
  event_type: string;
  discord_channel_id: string;
  message_template: string;
  enabled: boolean;
  created_at: string;
}

export interface ApiKey {
  id: string;
  project_id: string;
  label: string | null;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyWithRaw extends ApiKey {
  raw_key?: string;
}

export interface BotStatus {
  project_id: string;
  guild_id: string | null;
  installed: boolean;
}
