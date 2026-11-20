import { execSync } from "node:child_process";

/**
 * Read `npx supabase status` once per run and hand it to the workers through an environment
 * variable (Playwright passes env set here to every worker). Before, each worker ran its own
 * lookup, and under load one could time out and silently skip its specs (LIM-028).
 * Nothing is printed; when the local stack is not running the variable stays unset.
 */
export default function globalSetup() {
  try {
    process.env.E2E_SUPABASE_STATUS = execSync("npx supabase status -o json", {
      cwd: "../..",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 120_000,
    }).toString();
  } catch {
    delete process.env.E2E_SUPABASE_STATUS;
  }
}
