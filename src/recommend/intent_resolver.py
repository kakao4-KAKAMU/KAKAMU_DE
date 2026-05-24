"""자연어 질의 → 정규화된 (keywords, themes, moods) 추출.

SOLID
-----
- SRP : token 추출 + vocab 매칭만 담당. LLM/Cypher 호출은 외부에서.
- DIP : VocabularyNormalizer 와 Embedder Protocol 에만 의존한다.

전략
----
1. 룰 기반 부분문자열 매칭 (속도/예측성)
2. (선택) 임베딩 nearest-neighbor 매칭으로 동의어 흡수
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, Optional, Protocol, Sequence

from src.vocab.aliaser import cosine_similarity
from src.vocab.normalizer import VocabularyNormalizer

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class ResolvedIntent:
    """자연어 질의로부터 추출한 정규화 토큰들."""

    keywords: list[str]
    themes: list[str]
    moods: list[str]


_TOKEN_PATTERN = re.compile(r"[\w가-힣]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_PATTERN.findall(text or "")]


class IntentResolver:
    """자연어 질의에서 vocab 토큰을 추출한다.

    Args:
        normalizer: 정규화된 themes/moods/genres 사전.
        embedder: 주어지면 임베딩 기반 NN 매칭으로 동의어 흡수.
        catalog_embeddings: ``[(label, [emb])]`` 형태의 카탈로그 임베딩. 임베딩 모드에서만 사용.
        nn_threshold: nearest-neighbor 코사인 임계.
    """

    def __init__(
        self,
        normalizer: VocabularyNormalizer,
        *,
        embedder: Embedder | None = None,
        catalog_embeddings: dict[str, list[tuple[str, Sequence[float]]]] | None = None,
        nn_threshold: float = 0.8,
    ) -> None:
        self._normalizer = normalizer
        self._embedder = embedder
        self._catalog = catalog_embeddings or {}
        self._nn_threshold = nn_threshold

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def resolve(self, query: str) -> ResolvedIntent:
        tokens = _tokenize(query)
        themes = self._rule_match(tokens, self._normalizer.themes())
        moods = self._rule_match(tokens, self._normalizer.moods())
        genres = self._rule_match(tokens, self._normalizer.genres())

        if self._embedder is not None:
            nn_themes = self._embedding_match(query, self._catalog.get("theme", []))
            nn_moods = self._embedding_match(query, self._catalog.get("mood", []))
            themes = list(dict.fromkeys(themes + nn_themes))
            moods = list(dict.fromkeys(moods + nn_moods))

        keywords = list(dict.fromkeys(tokens + genres))
        return ResolvedIntent(keywords=keywords, themes=themes, moods=moods)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _rule_match(tokens: list[str], catalog: Iterable[str]) -> list[str]:
        token_set = set(tokens)
        joined = " ".join(tokens)
        matched: list[str] = []
        for entry in catalog:
            low = entry.lower()
            if low in token_set or low in joined:
                matched.append(entry)
        return matched

    def _embedding_match(
        self,
        query: str,
        catalog: Sequence[tuple[str, Sequence[float]]],
    ) -> list[str]:
        if not catalog or self._embedder is None:
            return []
        try:
            emb = self._embedder.embed(query)
        except Exception:
            logger.warning("Intent embedding failed", exc_info=True)
            return []
        matches: list[tuple[str, float]] = []
        for name, vec in catalog:
            score = cosine_similarity(emb, vec)
            if score >= self._nn_threshold:
                matches.append((name, score))
        matches.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in matches]


__all__ = ["IntentResolver", "ResolvedIntent"]
