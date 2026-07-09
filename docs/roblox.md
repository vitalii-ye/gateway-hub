Create a server side script
```
-- ServerScriptService/GatewayHubClient (ModuleScript)
local HttpService = game:GetService("HttpService")

local GatewayHubClient = {}
print("hi-script")
local GATEWAY_URL = "<URL_TO_GATEWAY>/v1/events}"
local API_KEY = "<GENERATED_API_KEY>"

function GatewayHubClient.sendEvent(eventType: string, data: {[string]: any})
	local payload = {
		eventType = eventType,
		data = data,
	}

	local success, result = pcall(function()
		return HttpService:RequestAsync({
			Url = GATEWAY_URL,
			Method = "POST",
			Headers = {
				["X-API-Key"] = API_KEY,
				["Content-Type"] = "application/json",
			},
			Body = HttpService:JSONEncode(payload),
		})
	end)

	if not success then
		warn("[GatewayHub] request failed:", result)
		return false
	end

	if not result.Success then
		warn("[GatewayHub] non-2xx response:", result.StatusCode, result.Body)
		return false
	end

	return true
end

return GatewayHubClient
```


Create a script (inside ClickDetector of Object, for instance) which will trigger the event
```
-- This script's location: Workspace/Part/ClickDetector/Script
local GatewayHubClient = require(game.ServerScriptService.GatewayHubClient)
local clickDetector = script.Parent -- the ClickDetector this script lives inside

clickDetector.MouseClick:Connect(function(player)
	print("[Test] Clicked by", player.Name)

	local success = GatewayHubClient.sendEvent("purchase", {
		item = "VIP",
		user_id = tostring(player.UserId),
		username = player.Name,
	})

	if success then
		print("[Test] Purchase event sent for", player.Name)
	else
		print("[Test] Purchase event FAILED for", player.Name)
	end
end)
```