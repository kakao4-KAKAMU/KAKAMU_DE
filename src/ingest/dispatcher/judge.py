"""Movie / Person 선호 판정 핸들러.

LLM 추출·임베딩 불필요. Loader 의 INTERACTED 관계만 적재한다.
"""

from __future__ import annotations

from typing import Any, Mapping

from src.api.schemas.movie import IngestMovieJudgePayload
from src.api.schemas.person import IngestPersonJudgePayload
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Handler


def build_movie_judge_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestMovieJudgePayload.model_validate(payload)
        loader.judge_movie(
            movie_id=p.movie_id,
            user_id=p.user_id,
            persona_id=p.persona_id,
            judge_type=p.judge_type,
            ts=p.created_at,
        )

    return _handler


def build_person_judge_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestPersonJudgePayload.model_validate(payload)
        loader.judge_person(
            person_id=p.person_id,
            user_id=p.user_id,
            persona_id=p.persona_id,
            judge_type=p.judge_type,
            ts=p.created_at,
        )

    return _handler


__all__ = ["build_movie_judge_handler", "build_person_judge_handler"]
