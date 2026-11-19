import { describe, expect, it } from "vitest";

import {
  forgotSchema,
  friendlyAuthError,
  loginSchema,
  resetSchema,
  safeNext,
  signupSchema,
} from "@/lib/auth-schemas";

describe("signupSchema", () => {
  const ok = {
    name: "Ada",
    email: "ada@example.com",
    password: "longenough1",
    confirm: "longenough1",
  };

  it("accepts a valid form and trims the name", () => {
    expect(signupSchema.parse({ ...ok, name: "  Ada  " }).name).toBe("Ada");
  });

  it.each([
    [{ password: "short", confirm: "short" }, "Use at least 8 characters"],
    [{ confirm: "different1" }, "Passwords do not match"],
    [{ email: "not-an-email" }, "Enter a valid email address"],
    [{ name: "   " }, "Enter your name"],
    [{ password: "x".repeat(129), confirm: "x".repeat(129) }, "Use at most 128 characters"],
  ])("rejects %j", (patch, message) => {
    const r = signupSchema.safeParse({ ...ok, ...patch });
    expect(r.success).toBe(false);
    expect(r.error?.issues.map((i) => i.message)).toContain(message);
  });
});

describe("other schemas", () => {
  it("login needs an email and a password", () => {
    expect(loginSchema.safeParse({ email: "", password: "" }).success).toBe(false);
    expect(loginSchema.safeParse({ email: "a@b.co", password: "x" }).success).toBe(true);
  });
  it("forgot needs a valid email", () => {
    expect(forgotSchema.safeParse({ email: "nope" }).success).toBe(false);
    expect(forgotSchema.safeParse({ email: "a@b.co" }).success).toBe(true);
  });
  it("reset needs matching strong-enough passwords", () => {
    expect(resetSchema.safeParse({ password: "longenough1", confirm: "longenough1" }).success).toBe(
      true,
    );
    expect(resetSchema.safeParse({ password: "longenough1", confirm: "x" }).success).toBe(false);
  });
});

describe("safeNext (open-redirect guard)", () => {
  it.each([
    ["/app/settings", "/app/settings"],
    ["/app?x=1", "/app?x=1"],
    [null, "/app"],
    [undefined, "/app"],
    ["", "/app"],
    ["https://evil.example", "/app"],
    ["//evil.example", "/app"],
    ["/\\evil.example", "/app"],
    ["javascript:alert(1)", "/app"],
    ["app/relative", "/app"],
  ])("%s -> %s", (input, expected) => {
    expect(safeNext(input as string | null | undefined)).toBe(expected);
  });
});

describe("friendlyAuthError", () => {
  it("maps known Supabase codes to plain sentences", () => {
    expect(friendlyAuthError("invalid_credentials", "")).toMatch(/don't match/);
    expect(friendlyAuthError("email_not_confirmed", "")).toMatch(/confirm your email/i);
    expect(friendlyAuthError("user_already_exists", "")).toMatch(/already exists/);
    expect(friendlyAuthError("over_email_send_rate_limit", "")).toMatch(/Too many/);
  });
  it("falls back to the provided message, then a generic one", () => {
    expect(friendlyAuthError("weird_code", "raw message")).toBe("raw message");
    expect(friendlyAuthError(undefined, "")).toMatch(/Something went wrong/);
  });
});
