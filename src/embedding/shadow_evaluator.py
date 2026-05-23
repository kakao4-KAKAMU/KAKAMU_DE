"""Shadow 임베딩 Recall@K 비교 (오프라인/샘플)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShadowEvalResult:
    active_recall_at_k: float
    shadow_recall_at_k: float
    k: int
    sample_size: int

    @property
    def improvement(self) -> float:
        return self.shadow_recall_at_k - self.active_recall_at_k


def recall_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for item in top if item in relevant)
    return hits / min(len(relevant), k)


def evaluate_shadow(
    *,
    active_rankings: list[list[str]],
    shadow_rankings: list[list[str]],
    relevant_sets: list[set[str]],
    k: int = 10,
) -> ShadowEvalResult:
    if len(active_rankings) != len(shadow_rankings):
        raise ValueError("ranking lists length mismatch")

    n = len(active_rankings)
    active_sum = 0.0
    shadow_sum = 0.0
    for i in range(n):
        active_sum += recall_at_k(relevant_sets[i], active_rankings[i], k)
        shadow_sum += recall_at_k(relevant_sets[i], shadow_rankings[i], k)

    return ShadowEvalResult(
        active_recall_at_k=active_sum / max(n, 1),
        shadow_recall_at_k=shadow_sum / max(n, 1),
        k=k,
        sample_size=n,
    )


__all__ = ["ShadowEvalResult", "evaluate_shadow", "recall_at_k"]
