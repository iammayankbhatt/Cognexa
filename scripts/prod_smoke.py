"""Production smoke test: the automated half of docs/DEPLOYMENT.md "Verify" (the rest is manual).

Public checks (no account needed):
  /health, /health/deep (Postgres AND Neo4j ok), CORS allows the web origin and rejects others,
  protected routes answer 401 with the error envelope, the public concept graph is seeded,
  the web app's landing page loads.
Signed-in checks (when SMOKE_EMAIL and SMOKE_PASSWORD are set; use a confirmed TEST account):
  /me, the canonical recursion question in graphrag mode brings call_stack into the trace,
  the quota meter goes up by one, recommendations and the knowledge map load. The test thread is
  deleted afterwards.

Secrets are read from the environment only and never printed:
  SMOKE_EMAIL, SMOKE_PASSWORD   a confirmed test account on the production Supabase project
  SUPABASE_URL                  https://<project-ref>.supabase.co
  SUPABASE_ANON_KEY             the publishable/anon key (the one the web app uses)

Usage:
  uv run --project apps/api python scripts/prod_smoke.py \
      --api https://cognexa-api.onrender.com --web https://cognexa.vercel.app [--report out.md]
Exit code 0 only when every check passed. The first request may take about a minute while the
free Render instance wakes up.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

CANONICAL = (
    "Why does my recursive function crash for big inputs with maximum recursion depth exceeded?"
)
EXPECTED_CONCEPT = "call_stack"
BOGUS_ORIGIN = "https://not-cognexa.example"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def parse_sse(lines: Iterable[str]) -> list[tuple[str, dict[str, Any]]]:
    """Parse `event:` / `data:` blocks (the tutor stream) into (event, json) pairs."""
    events: list[tuple[str, dict[str, Any]]] = []
    name, data = "message", []
    for raw in lines:
        line = raw.rstrip("\r")
        if not line:
            if data:
                events.append((name, json.loads("\n".join(data))))
            name, data = "message", []
        elif line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].strip())
    if data:
        events.append((name, json.loads("\n".join(data))))
    return events


def is_error_envelope(body: Any, code: str | None = None) -> bool:
    err = body.get("error") if isinstance(body, dict) else None
    return (
        isinstance(err, dict)
        and {"code", "message", "request_id"} <= set(err)
        and (code is None or err["code"] == code)
    )


class Smoke:
    def __init__(self, client: httpx.Client, api: str, web: str | None) -> None:
        self.c = client
        self.api = api.rstrip("/")
        self.web = web.rstrip("/") if web else None
        self.results: list[Check] = []

    def check(self, name: str, fn: Callable[[], str]) -> bool:
        try:
            detail = fn()
            self.results.append(Check(name, True, detail))
            return True
        except Exception as exc:  # a failed check must never stop the others
            self.results.append(Check(name, False, f"{type(exc).__name__}: {exc}"[:300]))
            return False

    # ------------------------------------------------------------------ public
    def wake(self) -> str:
        last: Exception | None = None
        for _ in range(12):  # a sleeping free instance takes about a minute
            try:
                r = self.c.get(f"{self.api}/health", timeout=20)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    return f"HTTP {r.status_code}"
            except httpx.HTTPError as exc:
                last = exc
            time.sleep(5)
        raise RuntimeError(f"API did not answer /health ({last})")

    def deep_health(self) -> str:
        r = self.c.get(f"{self.api}/health/deep", timeout=60)
        body = r.json()
        deps = body.get("dependencies", {})
        states = {k: v.get("status") for k, v in deps.items()}
        if body.get("status") != "ok" or set(states.values()) != {"ok"}:
            raise AssertionError(f"degraded: {states}")
        return ", ".join(f"{k} {v.get('latency_ms')} ms" for k, v in deps.items())

    def cors(self) -> str:
        if not self.web:
            raise AssertionError("--web not given")
        headers = {"Access-Control-Request-Method": "GET"}
        good = self.c.options(f"{self.api}/me", headers={**headers, "Origin": self.web})
        if good.headers.get("access-control-allow-origin") != self.web:
            raise AssertionError(f"web origin not allowed (HTTP {good.status_code})")
        bad = self.c.options(f"{self.api}/me", headers={**headers, "Origin": BOGUS_ORIGIN})
        if bad.headers.get("access-control-allow-origin"):
            raise AssertionError("a foreign origin is allowed")
        return "web origin allowed, foreign origin rejected"

    def auth_required(self) -> str:
        r = self.c.get(f"{self.api}/me")
        if r.status_code != 401 or not is_error_envelope(r.json()):
            raise AssertionError(f"HTTP {r.status_code}: {r.text[:120]}")
        return "401 with error envelope"

    def graph_seeded(self) -> str:
        r = self.c.get(f"{self.api}/graph")
        r.raise_for_status()
        body = r.json()
        nodes, edges = len(body["nodes"]), len(body["edges"])
        if nodes < 10 or edges < 10:
            raise AssertionError(f"only {nodes} concepts / {edges} edges: seed Neo4j")
        return f"{nodes} concepts, {edges} edges"

    def landing(self) -> str:
        if not self.web:
            raise AssertionError("--web not given")
        r = self.c.get(self.web, follow_redirects=True, timeout=30)
        if r.status_code != 200 or "Cognexa" not in r.text:
            raise AssertionError(f"HTTP {r.status_code}")
        return f"HTTP 200, {len(r.content) // 1024} KB"

    # ------------------------------------------------------------------ signed in
    def sign_in(self, supabase_url: str, anon_key: str, email: str, password: str) -> str:
        r = self.c.post(
            f"{supabase_url.rstrip('/')}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": anon_key},
            json={"email": email, "password": password},
        )
        if r.status_code != 200:
            raise AssertionError(f"sign-in failed (HTTP {r.status_code})")
        token = r.json()["access_token"]
        self.c.headers["Authorization"] = f"Bearer {token}"
        return "password grant ok"

    def me(self) -> str:
        r = self.c.get(f"{self.api}/me")
        r.raise_for_status()
        return f"role {r.json()['role']}"

    def usage_today(self) -> int:
        r = self.c.get(f"{self.api}/me/usage")
        r.raise_for_status()
        return int(r.json()["today"]["ai_requests"])

    def tutor(self) -> str:
        before = self.usage_today()
        r = self.c.post(f"{self.api}/tutor/threads", json={"title": "prod smoke test"})
        r.raise_for_status()
        thread = r.json()["id"]
        try:
            with self.c.stream(
                "POST",
                f"{self.api}/tutor/threads/{thread}/messages",
                json={"content": CANONICAL, "mode": "graphrag"},
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                events = parse_sse(resp.iter_lines())
        finally:
            self.c.delete(f"{self.api}/tutor/threads/{thread}")
        names = [e for e, _ in events]
        if "error" in names:
            raise AssertionError(f"stream error: {dict(events)['error']}")
        trace = next((d for e, d in events if e == "trace"), None)
        if trace is None or "done" not in names:
            raise AssertionError(f"incomplete stream: {names[:8]}")
        ids = [c["id"] for c in trace.get("concepts", [])]
        if EXPECTED_CONCEPT not in ids:
            raise AssertionError(f"{EXPECTED_CONCEPT} not in trace concepts {ids}")
        tokens = sum(1 for e in names if e == "token")
        after = self.usage_today()
        if after != before + 1:
            raise AssertionError(f"quota meter {before} -> {after} (expected +1)")
        return f"{EXPECTED_CONCEPT} in trace ({len(ids)} concepts), {tokens} tokens, quota +1"

    def recommendations(self) -> str:
        r = self.c.get(f"{self.api}/recommendations")
        r.raise_for_status()
        return "HTTP 200"

    def knowledge_map(self) -> str:
        r = self.c.get(f"{self.api}/graph/mastery")
        r.raise_for_status()
        return f"{len(r.json().get('nodes', []))} nodes"

    # ------------------------------------------------------------------ run
    def run(self, creds: dict[str, str] | None) -> list[Check]:
        if not self.check("API awake (/health)", self.wake):
            return self.results
        self.check("Deep health: Postgres + Neo4j", self.deep_health)
        self.check("CORS", self.cors)
        self.check("Protected routes need sign-in", self.auth_required)
        self.check("Concept graph seeded (/graph)", self.graph_seeded)
        self.check("Web landing page", self.landing)
        if creds is None:
            self.results.append(
                Check("Signed-in checks", False, "skipped: SMOKE_EMAIL / SMOKE_PASSWORD not set")
            )
            return self.results
        if self.check(
            "Sign in (Supabase password grant)",
            lambda: self.sign_in(
                creds["supabase_url"], creds["anon_key"], creds["email"], creds["password"]
            ),
        ):
            self.check("/me", self.me)
            self.check("Tutor: canonical recursion question", self.tutor)
            self.check("Recommendations", self.recommendations)
            self.check("Knowledge map (/graph/mastery)", self.knowledge_map)
        return self.results


def credentials_from_env() -> dict[str, str] | None:
    names = {
        "email": "SMOKE_EMAIL",
        "password": "SMOKE_PASSWORD",
        "supabase_url": "SUPABASE_URL",
        "anon_key": "SUPABASE_ANON_KEY",
    }
    values = {k: os.environ.get(v, "").strip() for k, v in names.items()}
    if not values["email"] or not values["password"]:
        return None
    missing = [names[k] for k, v in values.items() if not v or v == "REPLACE_ME"]
    if missing:
        raise SystemExit(f"Set {', '.join(missing)} for the signed-in checks.")
    return values


def render(results: list[Check], api: str, web: str | None) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    lines = [
        f"Production smoke test, {stamp}",
        f"API: {api}  Web: {web or '-'}",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.name} | {'PASS' if r.ok else 'FAIL'} | {r.detail.replace('|', '/')} |")
    passed = sum(r.ok for r in results)
    lines += ["", f"{passed}/{len(results)} checks passed."]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--api", required=True, help="API base URL")
    parser.add_argument("--web", help="web app URL (also the CORS origin to test)")
    parser.add_argument("--report", type=Path, help="also write the result table to this file")
    args = parser.parse_args()
    creds = credentials_from_env()
    with httpx.Client(timeout=30, headers={"User-Agent": "cognexa-prod-smoke"}) as client:
        results = Smoke(client, args.api, args.web).run(creds)
    text = render(results, args.api, args.web)
    print(text)
    if args.report:
        args.report.write_text(text + "\n", encoding="utf-8")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
