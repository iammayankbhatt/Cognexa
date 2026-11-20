/**
 * HTTP security headers for every page (Phase 13). Used by next.config.ts.
 *
 * The CSP has no nonces: nonces need every page to be rendered per request, which is
 * incompatible with Partial Prerendering (cacheComponents), so inline scripts are allowed and
 * everything else is locked to this site, the API and Supabase (DEC-064).
 */

export interface HeaderOptions {
  dev: boolean;
  apiUrl?: string;
  supabaseUrl?: string;
}

/** "https://x.supabase.co/path" -> "https://x.supabase.co"; invalid or placeholder -> null. */
export function originOf(url: string | undefined): string | null {
  if (!url || url.trim() === "" || url.trim() === "REPLACE_ME") return null;
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.origin : null;
  } catch {
    return null;
  }
}

/** A deployment talks to an HTTPS API; local runs (dev or `next start`) use plain http. */
export function servedOverHttps(apiUrl: string | undefined): boolean {
  return originOf(apiUrl)?.startsWith("https://") ?? false;
}

export function contentSecurityPolicy({ dev, apiUrl, supabaseUrl }: HeaderOptions): string {
  const api = originOf(apiUrl);
  const supabase = originOf(supabaseUrl);
  const connect = ["'self'"];
  if (api) connect.push(api);
  if (supabase) connect.push(supabase, supabase.replace(/^http/, "ws")); // auth + realtime
  const directives = [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'", // KaTeX and component inline styles
    "img-src 'self' blob: data:", // knowledge-map PNG export
    "font-src 'self' data:", // next/font is self-hosted; KaTeX ships data: fonts
    `connect-src ${connect.join(" ")}`,
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ];
  // Only when deployed over HTTPS: upgrading would break plain-http localhost calls.
  if (servedOverHttps(apiUrl)) directives.push("upgrade-insecure-requests");
  return directives.join("; ");
}

export function securityHeaders(opts: HeaderOptions): { key: string; value: string }[] {
  const headers = [
    { key: "Content-Security-Policy", value: contentSecurityPolicy(opts) },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    {
      key: "Permissions-Policy",
      value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    },
    { key: "Cross-Origin-Opener-Policy", value: "same-origin-allow-popups" }, // Google sign-in
  ];
  // HSTS only where the site is served over HTTPS (Vercel); never on localhost.
  if (servedOverHttps(opts.apiUrl)) {
    headers.push({
      key: "Strict-Transport-Security",
      value: "max-age=63072000; includeSubDomains",
    });
  }
  return headers;
}
