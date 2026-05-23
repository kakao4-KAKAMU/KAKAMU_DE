"""Outbox ingest worker CLI."""

from __future__ import annotations

import argparse
import asyncio
import logging

from src.ingest.dispatcher import default_dispatcher
from src.ingest.worker import IngestWorker

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    worker = IngestWorker(default_dispatcher())
    if args.once:
        n = worker.run_once()
        logging.info("Processed %d rows", n)
    else:
        asyncio.run(worker.run_loop(concurrency=args.concurrency))


if __name__ == "__main__":
    main()
