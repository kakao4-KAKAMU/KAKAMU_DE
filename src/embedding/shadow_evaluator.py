"""Compare Recall@K between active and shadow embedding versions (mockable retriever)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

RetrieverFn = Callable[[str, Sequence[float], int], list[str]]


@dataclass(frozen=True)
class SampleQuery:
    """Evaluation query with ground-truth relevant movie IDs."""

    query_id: str
    query_embedding: Sequence[float]
    relevant_movie_ids: frozenset[str]


@dataclass(frozen=True)
class VersionRecall:
    version: str
    recall_at_k: float
    hits: int
    total: int


@dataclass(frozen=True)
class ShadowEvalResult:
    active: VersionRecall
    shadow: VersionRecall
    k: int

    @property
    def recall_delta(self) -> float:
        return self.shadow.recall_at_k - self.active.recall_at_k


class VersionRetriever(Protocol):
    def retrieve(self, version: str, query_embedding: Sequence[float], k: int) -> list[str]: ...


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def in_memory_retriever(
    corpus: dict[str, dict[str, Sequence[float]]],
) -> RetrieverFn:
    """Build a retriever from version -> movie_id -> embedding (for tests)."""

    def retrieve(version: str, query_embedding: Sequence[float], k: int) -> list[str]:
        movies = corpus.get(version, {})
        scored = [
            (mid, _cosine(query_embedding, vec))
            for mid, vec in movies.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [mid for mid, _ in scored[:k]]

    return retrieve


def recall_at_k(retrieved: Sequence[str], relevant: frozenset[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = retrieved[:k]
    hits = sum(1 for mid in top if mid in relevant)
    return hits / len(relevant)


def evaluate_shadow_vs_active(
    queries: Sequence[SampleQuery],
    *,
    active_version: str,
    shadow_version: str,
    k: int = 10,
    retriever: RetrieverFn | VersionRetriever | None = None,
) -> ShadowEvalResult:
    if retriever is None:
        raise ValueError("retriever is required (inject mock or Neo4j-backed implementation)")

    def _retrieve(version: str, emb: Sequence[float], top_k: int) -> list[str]:
        if hasattr(retriever, "retrieve"):
            return retriever.retrieve(version, emb, top_k)  # type: ignore[union-attr]
        return retriever(version, emb, top_k)  # type: ignore[misc]

    active_hits = 0
    shadow_hits = 0
    total_relevant = 0

    for q in queries:
        rel_count = len(q.relevant_movie_ids)
        if rel_count == 0:
            continue
        total_relevant += rel_count
        active_ids = _retrieve(active_version, q.query_embedding, k)
        shadow_ids = _retrieve(shadow_version, q.query_embedding, k)
        active_hits += sum(1 for mid in active_ids[:k] if mid in q.relevant_movie_ids)
        shadow_hits += sum(1 for mid in shadow_ids[:k] if mid in q.relevant_movie_ids)

    denom = max(total_relevant, 1)
    active_recall = active_hits / denom
    shadow_recall = shadow_hits / denom

    return ShadowEvalResult(
        active=VersionRecall(
            version=active_version,
            recall_at_k=active_recall,
            hits=active_hits,
            total=total_relevant,
        ),
        shadow=VersionRecall(
            version=shadow_version,
            recall_at_k=shadow_recall,
            hits=shadow_hits,
            total=total_relevant,
        ),
        k=k,
    )


__all__ = [
    "SampleQuery",
    "ShadowEvalResult",
    "VersionRecall",
    "VersionRetriever",
    "evaluate_shadow_vs_active",
    "in_memory_retriever",
    "recall_at_k",
]
