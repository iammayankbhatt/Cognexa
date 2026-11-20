import { describe, expect, it } from "vitest";

import { contentSecurityPolicy, originOf, securityHeaders } from "@/lib/security-headers";

const prod = {
  dev: false,
  apiUrl: "https://cognexa-api.onrender.com/",
  supabaseUrl: "https://abcd.supabase.co",
};

function header(list: { key: string; value: string }[], key: string) {
  return list.find((h) => h.key === key)?.value;
}

describe("security headers", () => {
  it("extracts origins and ignores placeholders", () => {
    expect(originOf("https://abcd.supabase.co/auth/v1")).toBe("https://abcd.supabase.co");
    expect(originOf("REPLACE_ME")).toBeNull();
    expect(originOf("")).toBeNull();
    expect(originOf("javascript:alert(1)")).toBeNull();
  });

  it("locks connections to the site, the API and Supabase in production", () => {
    const csp = contentSecurityPolicy(prod);
    expect(csp).toContain(
      "connect-src 'self' https://cognexa-api.onrender.com https://abcd.supabase.co wss://abcd.supabase.co",
    );
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("upgrade-insecure-requests");
    expect(csp).not.toContain("unsafe-eval");
  });

  it("allows eval only in development and never upgrades plain-http localhost", () => {
    const csp = contentSecurityPolicy({
      dev: true,
      apiUrl: "http://localhost:8000",
      supabaseUrl: "http://127.0.0.1:54321",
    });
    expect(csp).toContain("'unsafe-eval'");
    expect(csp).toContain("ws://127.0.0.1:54321");
    expect(csp).not.toContain("upgrade-insecure-requests");
    // a local production build (`next start`) talks to http://localhost too
    expect(contentSecurityPolicy({ dev: false, apiUrl: "http://localhost:8000" })).not.toContain(
      "upgrade-insecure-requests",
    );
  });

  it("sends HSTS only for HTTPS deployments and always denies framing", () => {
    expect(header(securityHeaders(prod), "Strict-Transport-Security")).toMatch(/max-age=\d+/);
    const local = securityHeaders({ dev: false, apiUrl: "http://localhost:8000" });
    expect(header(local, "Strict-Transport-Security")).toBeUndefined();
    expect(header(local, "X-Frame-Options")).toBe("DENY");
    expect(header(local, "X-Content-Type-Options")).toBe("nosniff");
    expect(header(local, "Referrer-Policy")).toBe("strict-origin-when-cross-origin");
  });
});
