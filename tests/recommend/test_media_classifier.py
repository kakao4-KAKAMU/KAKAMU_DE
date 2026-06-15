"""LLM 기반 매체 분류기 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.recommend.media_classifier import LLMMediaClassifier


def test_llm_classifier_uses_llm_decision() -> None:
    llm = MagicMock()
    llm.chat_json.return_value = {"media_type": "feed"}
    clf = LLMMediaClassifier(llm)
    assert clf.classify("이 영화 어땠어?") == "feed"
    llm.chat_json.assert_called_once()


def test_llm_classifier_returns_movie_decision() -> None:
    llm = MagicMock()
    llm.chat_json.return_value = {"media_type": "movie"}
    clf = LLMMediaClassifier(llm)
    assert clf.classify("재밌는 영화 추천") == "movie"


def test_llm_classifier_defaults_when_llm_raises() -> None:
    llm = MagicMock()
    llm.chat_json.side_effect = RuntimeError("boom")
    clf = LLMMediaClassifier(llm)
    assert clf.classify("후기 피드 보여줘") == "movie"


def test_llm_classifier_defaults_on_invalid_value() -> None:
    llm = MagicMock()
    llm.chat_json.return_value = {"media_type": "podcast"}
    clf = LLMMediaClassifier(llm)
    assert clf.classify("재밌는 영화 추천") == "movie"


def test_llm_classifier_respects_custom_default() -> None:
    llm = MagicMock()
    llm.chat_json.return_value = {}
    clf = LLMMediaClassifier(llm, default="feed")
    assert clf.classify("아무거나") == "feed"


def test_llm_classifier_skips_llm_for_empty_query() -> None:
    llm = MagicMock()
    clf = LLMMediaClassifier(llm)
    assert clf.classify("   ") == "movie"
    llm.chat_json.assert_not_called()
