"""Keyword-distribution drift: KL divergence, failure rate, mean cos_sim."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class DriftMetrics:
    kl_divergence: float
    failure_rate: float
    mean_cos_sim: float
    sample_size: int


def _normalize(counter: Counter[str], vocab: set[str]) -> dict[str, float]:
    total = sum(counter.values())
    if total == 0:
        n = max(len(vocab), 1)
        return {k: 1.0 / n for k in vocab}
    return {k: counter.get(k, 0) / total for k in vocab}


def keyword_distribution(keywords: Iterable[str]) -> Counter[str]:
    return Counter(k.strip().lower() for k in keywords if k and k.strip())


def kl_divergence(p: Mapping[str, float], q: Mapping[str, float], *, eps: float = 1e-9) -> float:
    """KL(P || Q) over shared support."""
    keys = set(p) | set(q)
    div = 0.0
    for k in keys:
        pk = max(p.get(k, 0.0), eps)
        qk = max(q.get(k, 0.0), eps)
        div += pk * math.log(pk / qk)
    return div


def compute_drift_metrics(
    *,
    baseline_keywords: Sequence[str],
    current_keywords: Sequence[str],
    cos_sims: Sequence[float],
    failed_flags: Sequence[bool],
) -> DriftMetrics:
    """Compare baseline vs current keyword bags and aggregate run quality."""
    n = len(cos_sims)
    if n != len(failed_flags):
        raise ValueError("cos_sims and failed_flags length mismatch")

    base_ctr = keyword_distribution(baseline_keywords)
    cur_ctr = keyword_distribution(current_keywords)
    vocab = set(base_ctr) | set(cur_ctr)
    p = _normalize(base_ctr, vocab)
    q = _normalize(cur_ctr, vocab)
    kl = kl_divergence(p, q)

    failures = sum(1 for f in failed_flags if f)
    failure_rate = failures / n if n else 0.0
    mean_cos = sum(cos_sims) / n if n else 0.0

    return DriftMetrics(
        kl_divergence=kl,
        failure_rate=failure_rate,
        mean_cos_sim=mean_cos,
        sample_size=n,
    )


__all__ = [
    "DriftMetrics",
    "keyword_distribution",
    "kl_divergence",
    "compute_drift_metrics",
]
