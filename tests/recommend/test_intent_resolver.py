"""IntentResolver rule + embedding match."""

from __future__ import annotations

from src.recommend.intent_resolver import IntentResolver
from src.vocab.normalizer import VocabularyNormalizer


def _make_normalizer() -> VocabularyNormalizer:
    return VocabularyNormalizer(
        themes={"복수", "성장"},
        moods={"잔잔한", "긴장감"},
        genres={"드라마", "스릴러"},
    )


def test_resolve_rule_match_korean() -> None:
    resolver = IntentResolver(_make_normalizer())
    intent = resolver.resolve("잔잔한 성장 드라마 추천해줘")
    assert "성장" in intent.themes
    assert "잔잔한" in intent.moods
    assert "드라마" in intent.keywords


def test_resolve_no_match_returns_tokens_only() -> None:
    resolver = IntentResolver(_make_normalizer())
    intent = resolver.resolve("주말에 볼 영화 추천")
    assert intent.themes == []
    assert intent.moods == []
    assert "추천" in intent.keywords


class _StubEmbedder:
    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0]


def test_resolve_embedding_nn_adds_synonym() -> None:
    resolver = IntentResolver(
        _make_normalizer(),
        embedder=_StubEmbedder(),
        catalog_embeddings={
            "theme": [("성장", [1.0, 0.0]), ("복수", [0.0, 1.0])],
        },
        nn_threshold=0.9,
    )
    intent = resolver.resolve("뭔가 보고 싶다")
    assert "성장" in intent.themes
    assert "복수" not in intent.themes
