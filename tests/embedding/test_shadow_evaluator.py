from __future__ import annotations

from src.embedding.promoter import EmbeddingPromoter
from src.embedding.shadow_evaluator import evaluate_shadow
from src.embedding.version_registry import VersionRegistry


def test_shadow_improves_recall() -> None:
    relevant = [{"a"}]
    active_rank = [["b", "c"]]
    shadow_rank = [["a", "b"]]
    result = evaluate_shadow(
        active_rankings=active_rank,
        shadow_rankings=shadow_rank,
        relevant_sets=relevant,
        k=1,
    )
    assert result.shadow_recall_at_k > result.active_recall_at_k


def test_promoter_threshold() -> None:
    from unittest.mock import MagicMock

    from src.embedding.shadow_evaluator import ShadowEvalResult

    reg = MagicMock(spec=VersionRegistry)
    promoter = EmbeddingPromoter(reg, min_improvement=0.01, min_sample_size=1)
    ok = promoter.should_promote(
        ShadowEvalResult(0.1, 0.2, k=10, sample_size=100)
    )
    assert ok is True
