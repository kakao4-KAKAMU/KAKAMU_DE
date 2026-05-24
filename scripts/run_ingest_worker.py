"""Outbox ingest worker CLI.

기본값은 production dispatcher (실제 Extractor + Embedder + Loader 연결).
``--mock`` 플래그로 mock dispatcher 사용 (테스트/로컬 smoke).
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from src.embedding.vllm_embedding import VLLMEmbeddingClient
from src.embedding.version_registry import EmbeddingVersionRegistry
from src.graph.client import Neo4jClient
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher import (
    IngestDispatcher,
    build_production_dispatcher,
    default_dispatcher,
)
from src.ingest.worker import IngestWorker
from src.llm.vllm_client import VLLMChatClient

logging.basicConfig(level=logging.INFO)


def _build_production_dispatcher() -> IngestDispatcher:
    neo4j = Neo4jClient()
    registry = EmbeddingVersionRegistry(neo4j)
    loader = OntologyLoader(neo4j, embedding_registry=registry)
    return build_production_dispatcher(
        llm=VLLMChatClient(),
        embedder=VLLMEmbeddingClient(),
        loader=loader,
        neo4j=neo4j,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock dispatcher (no real LLM / Neo4j writes).",
    )
    args = parser.parse_args()

    dispatcher = default_dispatcher() if args.mock else _build_production_dispatcher()
    worker = IngestWorker(dispatcher)
    if args.once:
        n = worker.run_once()
        logging.info("Processed %d rows", n)
    else:
        asyncio.run(worker.run_loop(concurrency=args.concurrency))


if __name__ == "__main__":
    main()
