"""FastAPI routers (/chat, /recommend, /ingest, /feedback, /healthz).

SOLID
-----
- SRP : HTTP 핸들러는 입출력 스키마 변환과 도메인 호출만 담당.
- DIP : 모든 도메인 객체는 ``get_container`` 의존성으로 주입된다.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.chat.history import router as chat_history_router
from src.api.routers.chat.list import router as chat_list_router
from src.api.routers.chat.stream import router as chat_stream_router
from src.api.routers.deps import get_app_container
from src.api.routers.feedback.post import router as feedback_router
from src.api.routers.health.healthz import router as healthz_router
from src.api.routers.ingest.comment.create import router as ingest_comment_create_router
from src.api.routers.ingest.comment.delete import router as ingest_comment_delete_router
from src.api.routers.ingest.comment.like import router as ingest_comment_like_router
from src.api.routers.ingest.comment.modify import router as ingest_comment_modify_router
from src.api.routers.ingest.feed.create import router as ingest_feed_create_router
from src.api.routers.ingest.feed.delete import router as ingest_feed_delete_router
from src.api.routers.ingest.feed.like import router as ingest_feed_like_router
from src.api.routers.ingest.feed.modify import router as ingest_feed_modify_router
from src.api.routers.ingest.movie.judge import router as ingest_movie_judge_router
from src.api.routers.ingest.movie.regist import router as ingest_movie_regist_router
from src.api.routers.ingest.person.judge import router as ingest_person_judge_router
from src.api.routers.recommend.post import router as recommend_router

router = APIRouter()
router.include_router(healthz_router)
router.include_router(chat_list_router)
router.include_router(chat_history_router)
router.include_router(chat_stream_router)
router.include_router(recommend_router)
router.include_router(ingest_movie_regist_router)
router.include_router(ingest_movie_judge_router)
router.include_router(ingest_feed_create_router)
router.include_router(ingest_feed_modify_router)
router.include_router(ingest_feed_delete_router)
router.include_router(ingest_feed_like_router)
router.include_router(ingest_comment_create_router)
router.include_router(ingest_comment_modify_router)
router.include_router(ingest_comment_delete_router)
router.include_router(ingest_comment_like_router)
router.include_router(feedback_router)
router.include_router(ingest_person_judge_router)

__all__ = ["get_app_container", "router"]
