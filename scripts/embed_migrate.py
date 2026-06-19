#!/usr/bin/env python3
"""Versioned embedding migration: registry, re-embed outbox enqueue, promotion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import get_settings
from src.embedding.reembed_planner import (
    ReembedEntityType,
    count_reembed_candidates_by_type,
    enqueue_reembed_jobs,
    fetch_reembed_candidates,
)
from src.embedding.version_registry import (
    EmbeddingVersionRegistry,
    get_active_version,
    plot_embedding_property,
    register_version,
)
from src.graph.client import Neo4jClient
from src.graph.cypher_statements import vector_index_statements_for_version
from src.ingest.outbox_writer import OutboxWriter


def _count_movies(client: Neo4jClient) -> int:
    rows = client.execute_read("MATCH (m:Movie) RETURN count(m) AS cnt")
    return int(rows[0]["cnt"]) if rows else 0


def _count_legacy_embeddings(client: Neo4jClient) -> int:
    rows = client.execute_read(
        "MATCH (m:Movie) WHERE m.plot_embedding IS NOT NULL RETURN count(m) AS cnt"
    )
    return int(rows[0]["cnt"]) if rows else 0


def _parse_entity_types(raw: str) -> list[ReembedEntityType]:
    allowed: set[ReembedEntityType] = {"movie", "feed", "comment"}
    selected = [part.strip().lower() for part in raw.split(",") if part.strip()]
    if not selected:
        raise ValueError("At least one entity type is required: movie, feed, comment")
    invalid = [t for t in selected if t not in allowed]
    if invalid:
        raise ValueError(f"Unsupported entity types: {', '.join(invalid)}")
    return selected  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Versioned embedding migration (registry / re-embed outbox / promotion)",
    )
    parser.add_argument(
        "--target-version",
        default="2",
        help="Shadow/target version id to plan (default: 2)",
    )
    parser.add_argument(
        "--register",
        dest="regist",
        default=False,
        action="store_true",
        help="Register shadow version on :EmbeddingVersionMeta",
    )
    parser.add_argument(
        "--will-activate-target-version",
        default=False,
        action="store_true",
        help="Promote shadow version to active",
    )
    parser.add_argument(
        "--enqueue-reembed",
        default=False,
        action="store_true",
        help="Enqueue movie/feed/comment summary re-embedding jobs to ingest_outbox",
    )
    parser.add_argument(
        "--reembed-entity-types",
        default="movie,feed,comment",
        help="Comma-separated entity types to re-embed (default: movie,feed,comment)",
    )
    parser.add_argument(
        "--reembed-missing-target-only",
        default=False,
        action="store_true",
        help="For movies, enqueue only rows missing plot_embedding_v{target_version}",
    )
    parser.add_argument(
        "--reembed-limit",
        type=int,
        default=None,
        help="Optional cap on re-embed candidates (smoke test)",
    )
    args = parser.parse_args()

    settings = get_settings()
    dim = settings.embedding.dimension
    target_prop = plot_embedding_property(args.target_version)
    entity_types = _parse_entity_types(args.reembed_entity_types)

    print("=== Versioned embedding migration ===")
    print(f"Embedding dimension : {dim}")
    print(f"Target property     : Movie.{target_prop}")
    print(f"Re-embed entities   : {', '.join(entity_types)}")
    print()

    with Neo4jClient() as client:
        if args.regist:
            register_version(
                args.target_version,
                role="shadow",
                model_name=settings.embedding.model_name,
                dimension=settings.embedding.dimension,
                client=client,
                settings=settings,
            )
            print(f"Registered shadow version {args.target_version!r}")

        movie_count = _count_movies(client)
        legacy_count = _count_legacy_embeddings(client)
        active = get_active_version(client)
        registry = EmbeddingVersionRegistry(client)
        shadow = registry.get_shadow_version()

        if args.will_activate_target_version:
            promoted = registry.promote_shadow_to_active(args.target_version)
            print(
                "Promoted shadow version "
                f"{args.target_version!r} to active: "
                f"{promoted.version if promoted else '(none)'}"
            )

        candidates = fetch_reembed_candidates(
            client,
            entity_types=entity_types,
            target_version=args.target_version,
            missing_target_only=args.reembed_missing_target_only,
            limit=args.reembed_limit,
        )
        candidate_counts = count_reembed_candidates_by_type(candidates)

        print(f"Movies in graph              : {movie_count}")
        print(f"Movies with plot_embedding   : {legacy_count}")
        print(f"Active version (registry)    : {active.version if active else '(none)'}")
        print(f"Shadow version (registry)    : {shadow.version if shadow else '(none)'}")
        print()
        print("Re-embed candidates (Neo4j summary + prior embedding):")
        print(f"  movie   : {candidate_counts['movie']:,}")
        print(f"  feed    : {candidate_counts['feed']:,}")
        print(f"  comment : {candidate_counts['comment']:,}")
        print(f"  total   : {len(candidates):,}")
        print()

        if args.enqueue_reembed:
            report = enqueue_reembed_jobs(
                candidates,
                target_version=args.target_version,
                writer=OutboxWriter(settings.postgres),
                embedding_settings=settings.embedding,
            )
            print("Enqueued ingest_outbox jobs:")
            for aggregate_type, count in report.enqueued.items():
                if count:
                    print(f"  {aggregate_type}: {count:,}")
            print(f"  total: {report.total:,}")
            print()
            print(
                "Run the ingest worker to process embedding jobs, e.g.\n"
                "  python scripts/run_ingest_worker.py"
            )
        else:
            print("Re-embed enqueue skipped (pass --enqueue-reembed to write ingest_outbox).")

        print()
        print("Planned vector index DDL:")
        for stmt in vector_index_statements_for_version(args.target_version, dim):
            print(stmt.strip())
        print()
        print("Recommended flow:")
        print(f"  1. REGISTER shadow version {args.target_version!r} (--register)")
        print(
            "  2. ENQUEUE re-embed jobs from Neo4j summaries "
            "(--enqueue-reembed; worker embeds via ingest_outbox)"
        )
        print(f"  3. CREATE VECTOR INDEX movie_plot_vec_{args.target_version}")
        print("  4. EVALUATE Recall@K (shadow vs active)")
        print("  5. PROMOTE shadow → active when threshold met (--will-activate-target-version)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
