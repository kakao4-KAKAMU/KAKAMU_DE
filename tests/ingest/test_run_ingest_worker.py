from __future__ import annotations

from unittest.mock import MagicMock, patch

from scripts import run_ingest_worker


def test_production_dispatcher_initializes_neo4j_schema() -> None:
    settings = MagicMock()
    settings.embedding.dimension = 1024
    neo4j = MagicMock()
    dispatcher = MagicMock()

    with (
        patch.object(run_ingest_worker, "get_settings", return_value=settings),
        patch.object(run_ingest_worker, "Neo4jClient", return_value=neo4j) as neo4j_cls,
        patch.object(run_ingest_worker, "EmbeddingVersionRegistry") as registry_cls,
        patch.object(run_ingest_worker, "OntologyLoader") as loader_cls,
        patch.object(run_ingest_worker, "VLLMChatClient") as chat_cls,
        patch.object(run_ingest_worker, "VLLMEmbeddingClient") as embedding_cls,
        patch.object(
            run_ingest_worker,
            "build_production_dispatcher",
            return_value=dispatcher,
        ) as dispatcher_builder,
    ):
        result = run_ingest_worker._build_production_dispatcher()

    assert result is dispatcher
    neo4j_cls.assert_called_once_with(settings.neo4j)
    neo4j.init_schema.assert_called_once_with(embedding_dim=1024)
    registry_cls.assert_called_once_with(neo4j, settings=settings.embedding)
    chat_cls.assert_called_once_with(settings.vllm_gen)
    embedding_cls.assert_called_once_with(settings.vllm_embed, settings.embedding)
    loader_cls.assert_called_once_with(neo4j, embedding_registry=registry_cls.return_value)
    dispatcher_builder.assert_called_once_with(
        llm=chat_cls.return_value,
        embedder=embedding_cls.return_value,
        loader=loader_cls.return_value,
        neo4j=neo4j,
        embedding_registry=registry_cls.return_value,
    )
