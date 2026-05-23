"""분포 drift 감지."""

from __future__ import annotations

import math
from collections import Counter
from typing import Mapping, Sequence


def kl_divergence(p: Mapping[str, float], q: Mapping[str, float], eps: float = 1e-9) -> float:
    keys = set(p.keys()) | set(q.keys())
    s = 0.0
    for k in keys:
        pk = p.get(k, 0.0) + eps
        qk = q.get(k, 0.0) + eps
        s += pk * math.log(pk / qk)
    return s


def keyword_distribution(keywords: Sequence[str]) -> dict[str, float]:
    if not keywords:
        return {}
    c = Counter(keywords)
    total = sum(c.values())
    return {k: v / total for k, v in c.items()}


class DriftDetector:
    def __init__(self, *, kl_threshold: float = 0.15) -> None:
        self._kl_threshold = kl_threshold
        self._baseline: dict[str, float] | None = None

    def set_baseline(self, keywords: Sequence[str]) -> None:
        self._baseline = keyword_distribution(keywords)

    def check(self, keywords: Sequence[str]) -> tuple[bool, float]:
        if self._baseline is None:
            self.set_baseline(keywords)
            return False, 0.0
        current = keyword_distribution(keywords)
        kl = kl_divergence(current, self._baseline)
        return kl > self._kl_threshold, kl


__all__ = ["DriftDetector", "kl_divergence", "keyword_distribution"]
