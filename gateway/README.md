(Gateway service)

POST /v1/events

Example request:

```bash
curl -X POST http://localhost:8000/v1/events \
	-H "X-API-Key: gwh_apikey" \
	-H "Content-Type: application/json" \
	-d '{
		"eventType": "purchase",
		"data": {
			"item": "VIP",
			"user_id": "123456",
			"username": "Builderman"
		}
	}'
```

The gateway resolves the public API key to `projects.guild_id` using Supabase server-side credentials, stores the event status in Redis, then publishes the normalized payload to RabbitMQ for the rules engine.

GET /v1/projects/{project_id}/bot-status

Used by the dashboard. Requires a Supabase user JWT (`Authorization: Bearer <token>`); the caller must own the project (`404` otherwise). Returns whether the Discord bot is installed in the project's guild:

```json
{"project_id": "…", "guild_id": "…", "installed": true}
```

`guild_id` is `null` (and `installed` is `false`) when the project has no guild configured. The check is proxied to the discord-bot service: `502` if it answers with an error, `503` if it is unreachable.

Required env vars:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `REDIS_URL`
- `RABBITMQ_URL` or `RABBITMQ_HOST` / `RABBITMQ_PORT` / `RABBITMQ_USER` / `RABBITMQ_PASSWORD`

Optional env vars:

- `RATE_LIMIT_MAX_REQUESTS` — maximum number of `POST /v1/events` requests allowed per API key within the rate-limit window (default: `60`)
- `RATE_LIMIT_WINDOW_SECONDS` — length of the rate-limit window in seconds (default: `60`)
- `DISCORD_BOT_URL` — base URL of the discord-bot service, used for bot-status checks (default: `http://discord-bot:8001`)
- `DISCORD_BOT_TIMEOUT_SECONDS` — timeout for discord-bot calls (default: `10`)

Requests over the limit receive a `429` response with a `Retry-After` header set to the window length.
