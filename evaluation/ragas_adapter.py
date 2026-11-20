"""RAGAs judge LLM and embeddings backed by Cognexa's provider layer (CLAUDE.md rule 1: every
LLM call goes through app/llm, so retries, fallback and metering apply to evaluation too).

Checked against ragas 0.4.4: BaseRagasLLM needs generate_text / agenerate_text / is_finished
(returning a langchain LLMResult), BaseRagasEmbeddings needs (a)embed_query / (a)embed_documents.
Needs the optional `eval` dependency group.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any

from langchain_core.outputs import Generation, LLMResult
from ragas.embeddings.base import BaseRagasEmbeddings
from ragas.llms.base import BaseRagasLLM

from app.llm.embeddings import EmbeddingProvider
from app.llm.router import LLMRouter
from app.llm.types import Message


def _run(coro: Any) -> Any:
    """Run a coroutine from sync code, even when an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class RouterRagasLLM(BaseRagasLLM):  # type: ignore[misc]
    def __init__(self, router: LLMRouter, max_tokens: int = 1024) -> None:
        super().__init__()
        self.router = router
        self.max_tokens = max_tokens
        self.calls = 0
        self.tokens = 0

    async def agenerate_text(
        self,
        prompt: Any,
        n: int = 1,
        temperature: float | None = 0.01,
        stop: list[str] | None = None,
        callbacks: Any = None,
    ) -> LLMResult:
        text = prompt.to_string() if hasattr(prompt, "to_string") else str(prompt)
        generations = []
        for _ in range(max(1, n)):
            result = await self.router.complete(
                [Message("user", text)],
                temperature=0.0 if temperature is None else float(temperature),
                max_tokens=self.max_tokens,
            )
            self.calls += 1
            self.tokens += result.tokens_in + result.tokens_out
            generations.append(Generation(text=result.text))
        return LLMResult(generations=[generations])

    def generate_text(
        self,
        prompt: Any,
        n: int = 1,
        temperature: float = 0.01,
        stop: list[str] | None = None,
        callbacks: Any = None,
    ) -> LLMResult:
        result: LLMResult = _run(self.agenerate_text(prompt, n, temperature, stop, callbacks))
        return result

    def is_finished(self, response: LLMResult) -> bool:
        return True


class ProviderRagasEmbeddings(BaseRagasEmbeddings):  # type: ignore[misc]
    def __init__(self, provider: EmbeddingProvider) -> None:
        super().__init__()
        self.provider = provider

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self.provider.embed(list(texts))

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.provider.embed([text]))[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = _run(self.aembed_documents(texts))
        return out

    def embed_query(self, text: str) -> list[float]:
        out: list[float] = _run(self.aembed_query(text))
        return out


def ragas_scores(
    records: list[dict[str, Any]], llm: LLMRouter, embedder: EmbeddingProvider
) -> list[dict[str, float | None]]:
    """Faithfulness, answer relevancy, context precision and recall (with the reference answer)
    for each record, in order. NaN scores (judge output unusable) become None."""
    import math

    from ragas import EvaluationDataset, evaluate
    from ragas.metrics._answer_relevance import AnswerRelevancy
    from ragas.metrics._context_precision import LLMContextPrecisionWithReference
    from ragas.metrics._context_recall import LLMContextRecall
    from ragas.metrics._faithfulness import Faithfulness

    dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": r["question"],
                "response": r["answer"],
                "retrieved_contexts": [c["text"] for c in r["contexts"]] or [""],
                "reference": r.get("reference_answer") or "",
            }
            for r in records
        ]
    )
    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(),
            AnswerRelevancy(),
            LLMContextPrecisionWithReference(),
            LLMContextRecall(),
        ],
        llm=RouterRagasLLM(llm),
        embeddings=ProviderRagasEmbeddings(embedder),
        show_progress=False,
        raise_exceptions=False,
    )
    rows = result.to_pandas().to_dict(orient="records")
    names = {
        "faithfulness": "faithfulness",
        "answer_relevancy": "answer_relevancy",
        "llm_context_precision_with_reference": "context_precision",
        "context_recall": "context_recall",
    }
    out: list[dict[str, float | None]] = []
    for row in rows:
        scores: dict[str, float | None] = {}
        for col, name in names.items():
            v = row.get(col)
            scores[name] = (
                None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
            )
        out.append(scores)
    return out
