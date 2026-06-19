"""Promote shadow embedding version to active when evaluation thresholds are met."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.embedding.shadow_evaluator import ShadowEvalResult
from src.embedding.version_registry import EmbeddingVersion, EmbeddingVersionRegistry


@dataclass(frozen=True)
class PromotionThresholds:
    """Minimum improvement and absolute shadow quality for promotion."""

    min_recall_delta: float = 0.01
    min_shadow_recall: float = 0.0


def should_promote(
    result: ShadowEvalResult,
    thresholds: PromotionThresholds | None = None,
) -> bool:
    cfg = thresholds or PromotionThresholds()
    return (
        result.shadow.recall_at_k >= cfg.min_shadow_recall
        and result.recall_delta >= cfg.min_recall_delta
    )


def promote_shadow_if_ready(
    result: ShadowEvalResult,
    registry: EmbeddingVersionRegistry,
    *,
    thresholds: PromotionThresholds | None = None,
) -> Optional[EmbeddingVersion]:
    """Promote shadow → active in Neo4j when metrics pass thresholds."""
    if not should_promote(result, thresholds):
        return None
    return registry.promote_shadow_to_active(result.shadow.version)


__all__ = [
    "PromotionThresholds",
    "promote_shadow_if_ready",
    "should_promote",
]
