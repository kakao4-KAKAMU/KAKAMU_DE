"""유사 표제어 alias 자동 흡수."""

from __future__ import annotations

import math
from typing import Optional, Sequence


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class TermAliaser:
    def __init__(self, *, alias_threshold: float = 0.90) -> None:
        self._threshold = alias_threshold

    def find_alias(
        self,
        candidate_embedding: Sequence[float],
        catalog: list[tuple[str, Sequence[float]]],
    ) -> Optional[str]:
        best_name: Optional[str] = None
        best_score = -1.0
        for name, emb in catalog:
            score = cosine_similarity(candidate_embedding, emb)
            if score > best_score:
                best_score = score
                best_name = name
        if best_score >= self._threshold:
            return best_name
        return None


__all__ = ["TermAliaser", "cosine_similarity"]
