"""Admin evaluation console API over runs stored by evaluation/ragas_eval.py --push."""

from __future__ import annotations

import json

from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401

pytestmark = requires_postgres


async def seed_run(e: Env) -> str:
    summary = {
        "table": {"graphrag": {"all": {"n": 2, "prerequisite_hit_rate": 1.0}}},
        "headline_pairs": [{"metric": "prerequisite_hit", "pairs": 1}],
        "overall_pairs": [],
    }
    run_id = await e.db.fetchval(
        "insert into eval_runs (name, config, summary, finished_at) values ($1, $2, $3, now()) "
        "returning id",
        "fake-run", json.dumps({"fake": True}), json.dumps(summary),
    )  # fmt: skip
    for item, mode, cat, ctx in (
        ("ts-023", "graphrag", "unnamed_prerequisite", ["recursion", "call_stack"]),
        ("ts-023", "plain_rag", "unnamed_prerequisite", ["recursion"]),
        ("ts-001", "graphrag", "direct", ["bst"]),
    ):
        await e.db.execute(
            "insert into eval_results (run_id, item_id, mode, question, answer, contexts, metrics, "
            "latency_ms, tokens_in, tokens_out) values ($1, $2, $3, $4, 'an answer', $5, $6, 10, 3, 4)",
            run_id, item, mode, f"question {item}",
            json.dumps([{"concept_id": c, "kind": "overview"} for c in ctx]),
            json.dumps({"category": cat, "gold_concepts": ["x"], "gold_prerequisites": ["call_stack"],
                        "prerequisite_hit": 1.0 if "call_stack" in ctx else 0.0}),
        )  # fmt: skip
    return str(run_id)


async def test_admin_evaluation_runs_and_items(env: Env) -> None:  # noqa: F811
    _, student = await env.user("s@example.com")
    _, reviewer = await env.user("r@example.com", role="reviewer")
    run_id = await seed_run(env)
    assert (await env.client.get("/admin/evaluation/runs", headers=student)).status_code == 403
    runs = (await env.client.get("/admin/evaluation/runs", headers=reviewer)).json()["items"]
    assert runs[0]["name"] == "fake-run" and runs[0]["results"] == 3 and "headline" not in runs[0]
    run = (await env.client.get(f"/admin/evaluation/runs/{run_id}", headers=reviewer)).json()
    assert run["headline"]["graphrag"]["all"]["prerequisite_hit_rate"] == 1.0
    assert run["config"] == {"fake": True}
    items = (
        await env.client.get(f"/admin/evaluation/runs/{run_id}/items", headers=reviewer)
    ).json()
    assert items["total"] == 2
    ts023 = next(i for i in items["items"] if i["item_id"] == "ts-023")
    assert set(ts023["modes"]) == {"graphrag", "plain_rag"}
    assert ts023["modes"]["graphrag"]["context_concepts"] == ["recursion", "call_stack"]
    assert ts023["modes"]["plain_rag"]["metrics"]["prerequisite_hit"] == 0.0
    assert ts023["modes"]["graphrag"]["tokens"] == 7
    only = await env.client.get(f"/admin/evaluation/runs/{run_id}/items", headers=reviewer,
                                params={"category": "direct"})  # fmt: skip
    assert [i["item_id"] for i in only.json()["items"]] == ["ts-001"]
    missing = "00000000-0000-0000-0000-000000000000"
    assert (
        await env.client.get(f"/admin/evaluation/runs/{missing}", headers=reviewer)
    ).status_code == 404
