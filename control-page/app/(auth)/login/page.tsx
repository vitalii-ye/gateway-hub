"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase";
import { Loader2, LogIn } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const supabase = createClient();

  const handleDiscordLogin = async () => {
    setLoading(true);
    setError("");

    const { error } = await supabase.auth.signInWithOAuth({
      provider: "discord",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        scopes: "identify email guilds",
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-void">
      <Card className="w-full max-w-md panel-elevated">
        <CardHeader className="text-center pb-6">
          <div className="w-16 h-16 rounded-xl bg-amber flex items-center justify-center mx-auto mb-4">
            <LogIn className="w-8 h-8 text-void" />
          </div>
          <CardTitle className="text-2xl">Sign in to Gateway Hub</CardTitle>
          <p className="text-muted text-sm mt-1">Use your Discord account to manage apps and API keys</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            variant="secondary"
            className="w-full gap-3"
            onClick={handleDiscordLogin}
            disabled={loading}
          >
            <span className="flex items-center justify-center">

              <p>
                Continue with Discord
              </p>
            </span>

            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          </Button>

          {error && (
            <p className="text-sm text-red-400 text-center" role="alert">{error}</p>
          )}

          <p className="text-xs text-muted text-center">
            By continuing, you agree to our Terms of Service and Privacy Policy
          </p>
        </CardContent>
      </Card>
    </div>
  );
}