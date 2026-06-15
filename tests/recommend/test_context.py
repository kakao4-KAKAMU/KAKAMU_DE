"""추천 Persona 컨텍스트 유틸 테스트."""

from __future__ import annotations

from src.recommend.context import (
    bandit_context_key,
    build_hybrid_recommend_params,
    resolve_persona_id,
)


def test_resolve_persona_id_prefers_header() -> None:
    assert resolve_persona_id(header="header_p", body="body_p") == "header_p"


def test_resolve_persona_id_falls_back_to_body() -> None:
    assert resolve_persona_id(header=None, body="body_p") == "body_p"


def test_resolve_persona_id_returns_none_when_missing() -> None:
    assert resolve_persona_id(header=None, body=None) is None


def test_bandit_context_key_with_persona() -> None:
    assert bandit_context_key("u1", "movie_buff") == "u1:movie_buff"


def test_bandit_context_key_without_persona() -> None:
    assert bandit_context_key("u1", None) == "u1"


def test_build_hybrid_recommend_params_includes_persona_id() -> None:
    params = build_hybrid_recommend_params(
        user_id="u1",
        persona_id="movie_buff",
        query_embedding=[0.1],
        query_keywords=["a"],
        query_themes=["b"],
        query_moods=["c"],
        top_k=5,
        vec_top_k=10,
        max_toxicity=0.5,
        weights={"w_vec": 0.5, "w_kw": 0.1, "w_theme": 0.1, "w_mood": 0.1, "w_user": 0.2},
    )
    assert params["persona_id"] == "movie_buff"
    assert params["user_id"] == "u1"
    assert params["w_vec"] == 0.5
