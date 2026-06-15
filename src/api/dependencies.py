"""FastAPI 의존성 컨테이너 (싱글턴).

SOLID
-----
- SRP : 어플리케이션 전역 객체의 생성/캐싱만 담당.
- DIP : 라우터/노드들은 본 모듈의 getter 에만 의존한다.
- 테스트에서는 ``app.dependency_overrides`` 또는 ``set_*`` 헬퍼로 mock 주입.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from src.chat.feedback import FeedbackRecorder
from src.chat.graph import build_chat_graph
from src.chat.nodes import ChatGraphDependencies
from src.config.settings import AppSettings, get_settings
from src.embedding.version_registry import EmbeddingVersionRegistry
from src.embedding.vllm_embedding import VLLMEmbeddingClient
from src.graph.client import Neo4jClient
from src.graph.loader import OntologyLoader
from src.graph.template_executor import TemplateExecutor
from src.graph.templates import build_default_registry
from src.ingest.outbox_writer import OutboxWriter
from src.llm.vllm_client import VLLMChatClient
from src.persistence.chat_history import ChatHistoryStore
from src.recommend.bandit import ThompsonBandit
from src.recommend.bandit_store import BanditStore
from src.recommend.intent_resolver import IntentResolver
from src.recommend.media_classifier import LLMMediaClassifier
from src.recommend.policy import RecommendPolicy
from src.vocab.normalizer import VocabularyNormalizer


@dataclass
class AppContainer:
    """Application lifecycle 동안 공유되는 객체 모음."""

    settings: AppSettings
    neo4j: Neo4jClient
    llm: VLLMChatClient
    embedder: VLLMEmbeddingClient
    policy: RecommendPolicy
    template_executor: TemplateExecutor
    intent_resolver: IntentResolver
    chat_history: ChatHistoryStore
    outbox: OutboxWriter
    chat_graph: object  # CompiledGraph
    feedback_recorder: FeedbackRecorder


_container: Optional[AppContainer] = None


@lru_cache(maxsize=1)
def _build_vocab_normalizer() -> VocabularyNormalizer:
    from pathlib import Path

    library = Path(__file__).resolve().parents[2] / "docs" / "genre_theme_mood_library.md"
    if library.is_file():
        return VocabularyNormalizer.from_library_md(library)
    return VocabularyNormalizer(themes=set(), moods=set(), genres=set())


def build_container(checkpointer: Optional[object] = None) -> AppContainer:
    """프로덕션용 의존성 빌더."""

    settings = get_settings()
    neo4j = Neo4jClient(settings.neo4j)
    llm = VLLMChatClient(settings.vllm_gen)
    embedder = VLLMEmbeddingClient(settings.vllm_embed, settings.embedding)

    bandit_store = BanditStore(settings.postgres)
    bandit = ThompsonBandit(store=bandit_store)
    policy = RecommendPolicy(bandit=bandit, settings=settings.bandit)

    template_registry = build_default_registry()
    template_executor = TemplateExecutor(template_registry, neo4j)

    intent_resolver = IntentResolver(_build_vocab_normalizer())

    embedding_registry = EmbeddingVersionRegistry(neo4j, settings=settings.embedding)
    chat_history = ChatHistoryStore(settings.postgres)
    outbox = OutboxWriter(settings.postgres)
    # OntologyLoader 는 outbox worker 가 사용 (FastAPI 경로는 enqueue 만 호출).
    _loader = OntologyLoader(neo4j, embedding_registry=embedding_registry)  # noqa: F841

    chat_deps = ChatGraphDependencies(
        embedder=embedder,
        intent_resolver=intent_resolver,
        policy=policy,
        template_executor=template_executor,
        llm=llm,
        history=chat_history,
        media_classifier=LLMMediaClassifier(llm),
    )
    chat_graph = build_chat_graph(chat_deps, checkpointer=checkpointer)
    feedback_recorder = FeedbackRecorder(policy)

    return AppContainer(
        settings=settings,
        neo4j=neo4j,
        llm=llm,
        embedder=embedder,
        policy=policy,
        template_executor=template_executor,
        intent_resolver=intent_resolver,
        chat_history=chat_history,
        outbox=outbox,
        chat_graph=chat_graph,
        feedback_recorder=feedback_recorder,
    )


def set_container(container: Optional[AppContainer]) -> None:
    """테스트용: 외부에서 주입한 container 로 덮어쓴다."""
    global _container
    _container = container


def get_container() -> AppContainer:
    """전역 container 반환. 없으면 build_container 로 lazy 초기화."""
    global _container
    if _container is None:
        _container = build_container()
    return _container


__all__ = [
    "AppContainer",
    "build_container",
    "get_container",
    "set_container",
]
