Overview

GatewayHub is a FastAPI-based event ingestion gateway plus an async rules-engine worker. The gateway accepts events, enqueues them in RabbitMQ, and tracks status in Redis. The rules-engine consumes the queue, inflates guild configuration from Redis, evaluates rules, and dispatches actions to a Discord bot microservice which performs Discord API calls.

Current State

The full stack runs locally end-to-end with the Docker Compose setup.

Structure (diagram)

```
gateway-hub/
├── gateway/                # FastAPI ingestion API (auth, rate limit, enqueue + status)
├── rules-engine/           # RabbitMQ worker (rules + dispatch)
├── discord-bot/            # FastAPI bot microservice (send message)
├── control-page/           # Next.js admin dashboard (Supabase auth, projects/rules/keys)
├── shared/                 # Shared config/models across Python services
├── docs/                   # Integration guides (e.g. Roblox)
├── .github/workflows/      # CI: ruff lint, per-service pytest, frontend build
├── docker-compose.yml      # Local dev stack
└── .env                    # Local dev env (copy .env.example and fill in secrets)
```

Runtime Flow

1) Roblox/game server sends event -> gateway (API key auth + per-key rate limit)
2) gateway normalizes the payload, enqueues it to RabbitMQ, and sets event status in Redis
3) rules-engine consumes message, fetches guild rules from Redis, evaluates rules
4) rules-engine calls discord-bot -> discord-bot calls Discord REST API
5) rules-engine writes audit log to Redis and ACKs message

Local Testing (Redis rules + E2E)

Rule storage (per guild):
- Redis key: `guild_rules:{guild_id}`
- Value: JSON object with `rules` list; actions include `channel_id` for Discord delivery

Set a rule in Redis:
```
docker exec -it gateway-hub-redis-1 redis-cli \
  SET guild_rules:${GUILD_ID} \
  '{"rules":[{"event_type":"purchase","conditions":{"data.item":"VIP"},"actions":[{"type":"SEND_MESSAGE","channel_id":"${DISCORD_CHANNEL_ID}","content":"Thanks - VIP purchased"}]}]}'
```

E2E request (public gateway -> queue -> rules-engine -> discord-bot):
```
curl -X POST http://localhost:8000/v1/events \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "purchase",
    "data": {"item": "VIP", "user_id": "123456", "username": "Builderman"}
  }'
```

The gateway resolves `guild_id` from the API key's hashed record in `api_keys`, then maps that project to its `projects.guild_id` internally.

Check event status:
```
curl http://localhost:8000/v1/events/YOUR_EVENT_ID
```

Testing & Linting

- Python tests: `uv run pytest` from each of gateway/, rules-engine/, discord-bot/
- Lint/format: `uvx ruff check .` and `uvx ruff format --check .` from repo root (config in ruff.toml)
- Frontend: `bun run lint` and `bun run build` from control-page/
- CI runs all of the above on push/PR to main (.github/workflows/ci.yml)



Database schemas
rules
```
create table public.rules (
  id uuid not null default gen_random_uuid (),
  project_id uuid not null,
  name text not null,
  event_type text not null,
  discord_channel_id text not null,
  message_template text not null,
  enabled boolean not null default true,
  created_at timestamp with time zone null default now(),
  constraint rules_pkey primary key (id),
  constraint rules_project_id_fkey foreign KEY (project_id) references projects (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists rules_project_id_idx on public.rules using btree (project_id) TABLESPACE pg_default;

create index IF not exists rules_project_id_event_type_idx on public.rules using btree (project_id, event_type) TABLESPACE pg_default;
```

projects
```
create table public.projects (
  id uuid not null default gen_random_uuid (),
  owner_id uuid not null,
  name text null,
  guild_id text not null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint projects_pkey primary key (id),
  constraint projects_owner_id_fkey foreign KEY (owner_id) references auth.users (id) on delete CASCADE
) TABLESPACE pg_default;
```

api_keys
```
create table public.api_keys (
  id uuid not null default gen_random_uuid (),
  project_id uuid not null,
  key_hash text not null,
  label text null,
  created_at timestamp with time zone null default now(),
  last_used_at timestamp with time zone null,
  constraint api_keys_pkey primary key (id),
  constraint api_keys_key_hash_key unique (key_hash),
  constraint api_keys_project_id_fkey foreign KEY (project_id) references projects (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists api_keys_project_id_idx on public.api_keys using btree (project_id) TABLESPACE pg_default;
```

RLS policies
```
-- Protect dashboard data with RLS.
alter table public.projects enable row level security;
alter table public.rules enable row level security;
alter table public.api_keys enable row level security;

-- projects: only the owner can read/write their own project rows.
create policy "projects_select_own"
on public.projects
for select
using (auth.uid() = owner_id);

create policy "projects_insert_own"
on public.projects
for insert
with check (auth.uid() = owner_id);

create policy "projects_update_own"
on public.projects
for update
using (auth.uid() = owner_id)
with check (auth.uid() = owner_id);

create policy "projects_delete_own"
on public.projects
for delete
using (auth.uid() = owner_id);

-- rules: accessible only through the owning project.
create policy "rules_select_own"
on public.rules
for select
using (
  exists (
    select 1
    from public.projects p
    where p.id = rules.project_id
      and p.owner_id = auth.uid()
  )
);

create policy "rules_insert_own"
on public.rules
for insert
with check (
  exists (
    select 1
    from public.projects p
    where p.id = rules.project_id
      and p.owner_id = auth.uid()
  )
);

create policy "rules_update_own"
on public.rules
for update
using (
  exists (
    select 1
    from public.projects p
    where p.id = rules.project_id
      and p.owner_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.projects p
    where p.id = rules.project_id
      and p.owner_id = auth.uid()
  )
);

create policy "rules_delete_own"
on public.rules
for delete
using (
  exists (
    select 1
    from public.projects p
    where p.id = rules.project_id
      and p.owner_id = auth.uid()
  )
);

-- api_keys: only the owning project owner can view/revoke keys.
-- INSERT/UPDATE policies were dropped — key creation and mutation happen
-- only via the Gateway/FastAPI backend using the service-role key (bypasses RLS).
create policy "api_keys_select_own"
on public.api_keys
for select
using (
  exists (
    select 1
    from public.projects p
    where p.id = api_keys.project_id
      and p.owner_id = auth.uid()
  )
);

create policy "api_keys_delete_own"
on public.api_keys
for delete
using (
  exists (
    select 1
    from public.projects p
    where p.id = api_keys.project_id
      and p.owner_id = auth.uid()
  )
);
```

api_keys_public (view)
```
-- Frontend lists keys through this view only — it excludes key_hash.
-- security_invoker = true means RLS applies as the calling user via the
-- existing api_keys_select_own policy, so access control is unchanged.
create view public.api_keys_public
with (security_invoker = true) as
select id, project_id, label, created_at, last_used_at
from public.api_keys;
```

rename_api_key (RPC)
```
-- Lets a user rename a key's label without a bare UPDATE policy that
-- could otherwise expose key_hash to modification. security definer,
-- scoped to keys under the caller's own projects.
create or replace function public.rename_api_key(
  key_id uuid,
  new_label text
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.api_keys
  set label = new_label
  where id = key_id
    and project_id in (
      select id from public.projects where owner_id = auth.uid()
    );
end;
$$;

revoke all on function public.rename_api_key(uuid, text) from public;
grant execute on function public.rename_api_key(uuid, text) to authenticated;
```

Notes:
- The gateway should use the Supabase service-role key so it bypasses RLS entirely.
- Do not rely on anon/publishable access for the gateway query against `api_keys`; that path is meant for trusted server-side access only.
- Frontend key creation/renaming no longer goes through direct table writes: creation is gateway-only (service-role), and label renames go through `rename_api_key`.
