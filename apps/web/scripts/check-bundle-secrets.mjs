#!/usr/bin/env node
/**
 * Fails if anything that looks like a server-side secret ended up in the browser bundle
 * (.next/static). Run after `npm run build` (CI does). Prints file names and the kind of match,
 * never the matched text.
 *
 * Usage: node scripts/check-bundle-secrets.mjs [dir]
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const dir = process.argv[2] ?? ".next/static";

/** @type {[string, RegExp][]} */
const PATTERNS = [
  ["Supabase secret key", /\bsb_secret_[A-Za-z0-9_-]{10,}/],
  ["Groq API key", /\bgsk_[A-Za-z0-9]{20,}/],
  ["Google API key", /\bAIza[0-9A-Za-z_-]{35}\b/],
  ["private key", /-----BEGIN [A-Z ]*PRIVATE KEY-----/],
  [
    "server env var name",
    /\b(SUPABASE_SERVICE_ROLE_KEY|SUPABASE_JWT_SECRET|GROQ_API_KEY|GEMINI_API_KEY|NEO4J_PASSWORD|DATABASE_URL)\b/,
  ],
  ["database URL with password", /postgres(?:ql)?:\/\/[^:\s"'/]+:[^@\s"']+@/],
];
const JWT = /\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g;

/** A JWT is only a problem if it is a service-role token (the anon key is public by design). */
function serviceRoleJwt(text) {
  for (const m of text.matchAll(JWT)) {
    try {
      const payload = JSON.parse(Buffer.from(m[0].split(".")[1], "base64url").toString("utf8"));
      if (payload.role === "service_role") return true;
    } catch {
      /* not a JWT */
    }
  }
  return false;
}

function* files(root) {
  for (const name of readdirSync(root)) {
    const path = join(root, name);
    if (statSync(path).isDirectory()) yield* files(path);
    else if (/\.(js|mjs|json|html|txt|map)$/.test(name)) yield path;
  }
}

/**
 * @param {string} text
 * @returns {string[]} the kinds of secret found (never the text itself)
 */
export function findSecrets(text) {
  const hits = PATTERNS.filter(([, re]) => re.test(text)).map(([kind]) => kind);
  if (serviceRoleJwt(text)) hits.push("Supabase service-role JWT");
  return hits;
}

const isMain = (process.argv[1] ?? "").replaceAll("\\", "/").endsWith("/check-bundle-secrets.mjs");
if (isMain) {
  let scanned = 0;
  const problems = [];
  try {
    for (const path of files(dir)) {
      scanned += 1;
      for (const kind of findSecrets(readFileSync(path, "utf8"))) problems.push(`${path}: ${kind}`);
    }
  } catch (err) {
    console.error(`Cannot scan ${dir}: ${err.message}. Run npm run build first.`);
    process.exit(2);
  }
  if (scanned === 0) {
    console.error(`No files found in ${dir}. Run npm run build first.`);
    process.exit(2);
  }
  if (problems.length) {
    console.error(`Possible secrets in the client bundle:\n${problems.join("\n")}`);
    process.exit(1);
  }
  console.log(`OK: no secrets in ${scanned} client bundle files.`);
}
