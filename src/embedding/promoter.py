"""Shadow → Active 승격 정책."""

from __future__ import annotations

from src.embedding.shadow_evaluator import ShadowEvalResult
from src.embedding.version_registry import VersionRegistry


class EmbeddingPromoter:
    def __init__(
        self,
        registry: VersionRegistry,
        *,
        min_improvement: float = 0.02,
        min_sample_size: int = 50,
    ) -> None:
        self._registry = registry
        self._min_improvement = min_improvement
        self._min_sample_size = min_sample_size

    def should_promote(self, result: ShadowEvalResult) -> bool:
        if result.sample_size < self._min_sample_size:
            return False
        return result.improvement >= self._min_improvement

    def promote_if_ready(self, result: ShadowEvalResult, shadow_name: str) -> bool:
        if not self.should_promote(result):
            return False
        self._registry.promote_shadow_to_active(shadow_name)
        return True


__all__ = ["EmbeddingPromoter"]
