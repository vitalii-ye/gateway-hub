Discord Bot Service

POST /v1/messages

Request JSON:
{
  "channel_id": "123456789012345678",
  "content": "Optional plain text message content here",
  "embeds": [
    {
      "title": "Level Up!",
      "description": "Builderman just reached Level 50!",
      "color": 5814783,
      "fields": [
        {
          "name": "Reward",
          "value": "⚔️ Mythic Sword Unlocked",
          "inline": true
        }
      ]
    }
  ]
}

GET /v1/guilds/{guild_id}

Checks whether the bot is a member of the guild (used by the gateway's
bot-status endpoint). Response JSON:

{
  "guild_id": "123456789012345678",
  "installed": true
}

Discord answering 403 (Missing Access) or 404 (Unknown Guild) maps to
`installed: false`; any other Discord error is surfaced as a 502.

Env vars:
- DISCORD_BOT_TOKEN (required)
- DISCORD_API_BASE (optional, default https://discord.com/api/v10)
