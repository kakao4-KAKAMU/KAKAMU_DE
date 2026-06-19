"""Outbox ingest worker CLI.

기본값은 production dispatcher (실제 Extractor + Embedder + Loader 연결).
``--mock`` 플래그로 mock dispatcher 사용 (테스트/로컬 smoke).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from src.config.settings import get_settings
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
    settings = get_settings()
    neo4j = Neo4jClient(settings.neo4j)
    neo4j.init_schema(embedding_dim=settings.embedding.dimension)
    registry = EmbeddingVersionRegistry(neo4j, settings=settings.embedding)
    loader = OntologyLoader(neo4j, embedding_registry=registry)
    return build_production_dispatcher(
        llm=VLLMChatClient(settings.vllm_gen),
        embedder=VLLMEmbeddingClient(settings.vllm_embed, settings.embedding),
        loader=loader,
        neo4j=neo4j,
        embedding_registry=registry,
    )


async def _run_loop_with_shutdown(
    worker: IngestWorker,
    *,
    concurrency: int,
) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_shutdown(signum: int) -> None:
        logging.info("Received signal %s, shutting down ingest worker", signum)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _request_shutdown, sig)

    try:
        await worker.run_loop(concurrency=concurrency, stop_event=stop_event)
    finally:
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGTERM)


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
        try:
            n = worker.run_once()
            logging.info("Processed %d rows", n)
        finally:
            worker.release_in_flight()
    else:
        asyncio.run(_run_loop_with_shutdown(worker, concurrency=args.concurrency))


if __name__ == "__main__":
    main()
