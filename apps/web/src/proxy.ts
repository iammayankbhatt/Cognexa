import { NextResponse, type NextRequest } from "next/server";

import { authConfigured } from "@/lib/env";
import { updateSession } from "@/lib/supabase/proxy-session";

const PROTECTED = ["/app", "/admin"];
const GUEST_ONLY = ["/login", "/signup", "/forgot-password"];

const matches = (path: string, prefixes: string[]) =>
  prefixes.some((p) => path === p || path.startsWith(`${p}/`));

/**
 * Optimistic route protection (Next.js 16 "proxy", formerly middleware). It only decides
 * redirects from a verified session; the API re-checks the JWT and role on every request, so
 * this is a convenience, never the security boundary. /admin additionally checks the role
 * in the admin layout via GET /me.
 */
export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!authConfigured()) {
    // No Supabase configured: protected pages cannot work, so say so on the sign-in page.
    if (matches(pathname, PROTECTED)) {
      const url = new URL("/login", request.url);
      url.searchParams.set("error", "auth_not_configured");
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  const session = await updateSession(request);
  const signedIn = session.claims !== null;

  if (matches(pathname, PROTECTED) && !signedIn) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname + request.nextUrl.search);
    return NextResponse.redirect(url);
  }
  if (matches(pathname, GUEST_ONLY) && signedIn) {
    return NextResponse.redirect(new URL("/app", request.url));
  }
  return session.response();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
