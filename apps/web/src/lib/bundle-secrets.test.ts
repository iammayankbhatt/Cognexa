import { describe, expect, it } from "vitest";

import { findSecrets } from "../../scripts/check-bundle-secrets.mjs";

function jwt(payload: object): string {
  const part = (o: object) => Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${part({ alg: "HS256", typ: "JWT" })}.${part(payload)}.c2lnbmF0dXJlLXNpZ25hdHVyZQ`;
}

describe("client bundle secret scan", () => {
  it("flags server secrets and service-role tokens", () => {
    const find = (t: string): string[] => findSecrets(t);
    expect(find(`const k="${jwt({ role: "service_role", iss: "supabase" })}"`)).toEqual([
      "Supabase service-role JWT",
    ]);
    expect(find('x="gsk_' + "a".repeat(30) + '"')).toEqual(["Groq API key"]);
    expect(find("process.env.SUPABASE_SERVICE_ROLE_KEY")).toEqual(["server env var name"]);
    expect(find('u="postgresql://postgres:pw@db.example.com:5432/postgres"')).toEqual([
      "database URL with password",
    ]);
  });

  it("allows the public anon key and ordinary code", () => {
    const find = (t: string): string[] => findSecrets(t);
    expect(find(`const anon="${jwt({ role: "anon", iss: "supabase" })}"`)).toEqual([]);
    expect(find('fetch("https://api.example.com/graph")')).toEqual([]);
  });
});
