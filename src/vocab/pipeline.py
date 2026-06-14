"""Loader hook: 정규화 실패 항목을 CandidateTerm 으로 관찰."""

from __future__ import annotations

from typing import Optional, Sequence

from src.ontology.schema import Keyword
from src.vocab.candidate_store import CandidateStore
from src.vocab.normalizer import VocabularyNormalizer


class VocabPipeline:
    def __init__(
        self,
        normalizer: VocabularyNormalizer,
        candidate_store: CandidateStore,
    ) -> None:
        self._normalizer = normalizer
        self._store = candidate_store

    def resolve_themes(self, themes: Sequence[str]) -> list[str]:
        out: list[str] = []
        for t in themes:
            canon = self._normalizer.normalize_theme(t)
            if canon:
                out.append(canon)
            else:
                self._store.observe(term=t, normalized=t.lower(), kind="theme")
        return out

    def resolve_moods(self, moods: Sequence[str]) -> list[str]:
        out: list[str] = []
        for m in moods:
            canon = self._normalizer.normalize_mood(m)
            if canon:
                out.append(canon)
            else:
                self._store.observe(term=m, normalized=m.lower(), kind="mood")
        return out

    def resolve_keywords(
        self, keywords: Sequence[Keyword], embeddings: Optional[dict[str, list[float]]] = None
    ) -> list[Keyword]:
        return list(keywords)


__all__ = ["VocabPipeline"]
