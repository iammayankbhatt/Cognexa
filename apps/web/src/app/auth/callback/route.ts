import { NextResponse, type NextRequest } from "next/server";

import { safeNext } from "@/lib/auth-schemas";
import { createSupabaseServer } from "@/lib/supabase/server";

/**
 * Landing point for email-confirmation links, password-recovery links and Google OAuth.
 * Exchanges the one-time `code` for a session cookie, then sends the user on.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;
  const code = searchParams.get("code");
  const next = safeNext(searchParams.get("next"));
  const fail = (reason: string) => NextResponse.redirect(`${origin}/login?error=${reason}`);

  if (searchParams.get("error")) return fail("auth_callback_failed");
  if (!code) return fail("auth_callback_failed");

  const supabase = await createSupabaseServer();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return fail("auth_link_expired");
  return NextResponse.redirect(`${origin}${next}`);
}
