Rules Engine Worker

Consumes events from RabbitMQ, inflates guild config from Redis, evaluates rules, dispatches actions to the Discord bot service over HTTP, writes an audit log entry, and ACKs the message only after success.

On a Redis cache miss, the worker automatically loads the guild's project and enabled rules from Supabase, converts them into the Redis `guild_rules:{guild_id}` format, caches the result, and continues processing.

Redis keys used (defaults):
- Guild rules: `guild_rules:{guild_id}` (JSON)
- Event status: `event_status:{event_id}`
- Audit log list: `audit_logs:{guild_id}` (RPUSH JSON entries)

Guild rules JSON format (minimal):
```json
{
  "rules": [
    {
      "event_type": "purchase",
      "conditions": {"data.item": "VIP"},
      "actions": [
        {"type": "SEND_MESSAGE", "channel_id": "111", "content": "Thanks — {{username}} purchased {{item}}!"}
      ]
    }
  ]
}
```

`SEND_MESSAGE` is currently the only implemented action type; other actions in
a rule are skipped. Message templates support the placeholders `{{guild_id}}`,
`{{event_type}}`, `{{item}}`, `{{user_id}}`, and `{{username}}` (missing data
fields render as empty strings). Additional action types (e.g. role grants,
rich embeds) are on the roadmap.

Required env vars:

- `SUPABASE_URL`, `SUPABASE_KEY` (server-side key; used for the cache-miss fallback)
- `REDIS_URL` (plus optional `REDIS_*_PREFIX` overrides)
- `RABBITMQ_URL` or `RABBITMQ_HOST` / `RABBITMQ_PORT` / `RABBITMQ_USER` / `RABBITMQ_PASSWORD`
- `DISCORD_BOT_URL` (and optional `DISCORD_BOT_EXECUTE_PATH`, `DISCORD_BOT_TIMEOUT_SECONDS`)
- Optional: `WORKER_PREFETCH` (default 10), `LOG_LEVEL` (default INFO),
  `REDIS_GUILD_RULES_TTL_SECONDS` (default 60) — how long cached guild rules
  live before the worker re-reads Supabase, so dashboard rule changes
  propagate without a restart (empty disables expiry)

Run tests:

```bash
uv run pytest
```
