"""Notional pricing, so we can report "what this would cost at scale" on free tiers.

Prices are US dollars per 1M tokens and live in app_settings under `llm.pricing` (editable by
admins). No model ids are hard-coded: the table maps whatever model ids are configured in env to a
price, and `default` covers every model without its own entry.
"""

from __future__ import annotations

from typing import Any

DEFAULT_PRICING: dict[str, Any] = {
    "default": {"input_per_1m": 0.5, "output_per_1m": 1.5},
    "models": {},  # e.g. {"<model id from env>": {"input_per_1m": 0.1, "output_per_1m": 0.3}}
}


def estimate_cost(
    model: str, tokens_in: int, tokens_out: int, pricing: dict[str, Any] | None = None
) -> float:
    table = pricing or DEFAULT_PRICING
    models = table.get("models") or {}
    rate = models.get(model) or table.get("default") or DEFAULT_PRICING["default"]
    try:
        cost = (
            tokens_in * float(rate.get("input_per_1m", 0)) / 1_000_000
            + tokens_out * float(rate.get("output_per_1m", 0)) / 1_000_000
        )
    except (TypeError, ValueError, AttributeError):
        return 0.0
    return round(max(cost, 0.0), 6)
