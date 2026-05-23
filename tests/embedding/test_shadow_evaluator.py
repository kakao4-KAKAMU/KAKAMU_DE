"""Tests for shadow evaluator and promoter."""

from __future__ import annotations

from src.embedding.promoter import PromotionThresholds, promote_shadow_if_ready, should_promote
from src.embedding.shadow_evaluator import SampleQuery, evaluate_shadow_vs_active, in_memory_retriever
from src.embedding.version_registry import EmbeddingVersionRegistry
from tests.embedding.test_version_registry import FakeStore


def test_shadow_beats_active_recall() -> None:
    corpus = {
        "1": {
            "a": [1.0, 0.0],
            "b": [0.0, 1.0],
        },
        "2": {
            "a": [1.0, 0.0],
            "b": [0.9, 0.1],
        },
    }
    retriever = in_memory_retriever(corpus)
    queries = [
        SampleQuery("q1", [1.0, 0.0], frozenset({"a"})),
    ]
    result = evaluate_shadow_vs_active(
        queries,
        active_version="1",
        shadow_version="2",
        k=1,
        retriever=retriever,
    )
    assert result.active.recall_at_k == 1.0
    assert result.shadow.recall_at_k == 1.0
    assert should_promote(result, PromotionThresholds(min_recall_delta=0.0))


def test_promote_updates_registry() -> None:
    from src.config.settings import EmbeddingSettings
    from src.embedding.shadow_evaluator import ShadowEvalResult, VersionRecall

    store = FakeStore()
    registry = EmbeddingVersionRegistry(store, settings=EmbeddingSettings(dimension=1024))
    registry.register_version("1", role="active")
    registry.register_version("2", role="shadow")
    result = ShadowEvalResult(
        active=VersionRecall("1", 0.5, 1, 2),
        shadow=VersionRecall("2", 0.7, 2, 2),
        k=10,
    )
    promoted = promote_shadow_if_ready(
        result,
        registry,
        thresholds=PromotionThresholds(min_recall_delta=0.1, min_shadow_recall=0.6),
    )
    assert promoted is not None
    assert promoted.version == "2"
    assert promoted.role == "active"
