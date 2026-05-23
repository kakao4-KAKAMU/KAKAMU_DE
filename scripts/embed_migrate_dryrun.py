#!/usr/bin/env python3
"""Dry-run report for versioned embedding migration (no writes)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import get_settings
from src.embedding.version_registry import (
    EmbeddingVersionRegistry,
    get_active_version,
    plot_embedding_property,
)
from src.graph.client import Neo4jClient
from src.graph.cypher_statements import vector_index_statements_for_version


def _count_movies(client: Neo4jClient) -> int:
    rows = client.execute_read("MATCH (m:Movie) RETURN count(m) AS cnt")
    return int(rows[0]["cnt"]) if rows else 0


def _count_legacy_embeddings(client: Neo4jClient) -> int:
    rows = client.execute_read(
        "MATCH (m:Movie) WHERE m.plot_embedding IS NOT NULL RETURN count(m) AS cnt"
    )
    return int(rows[0]["cnt"]) if rows else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Versioned embedding migration dry-run")
    parser.add_argument(
        "--target-version",
        default="2",
        help="Shadow/target version id to plan (default: 2)",
    )
    args = parser.parse_args()

    settings = get_settings()
    dim = settings.embedding.dimension
    target_prop = plot_embedding_property(args.target_version)

    print("=== Versioned embedding migration (DRY RUN) ===")
    print(f"Embedding dimension : {dim}")
    print(f"Target property     : Movie.{target_prop}")
    print()

    with Neo4jClient() as client:
        movie_count = _count_movies(client)
        legacy_count = _count_legacy_embeddings(client)
        active = get_active_version(client)
        registry = EmbeddingVersionRegistry(client)
        shadow = registry.get_shadow_version()

        print(f"Movies in graph              : {movie_count}")
        print(f"Movies with plot_embedding   : {legacy_count}")
        print(f"Active version (registry)    : {active.version if active else '(none)'}")
        print(f"Shadow version (registry)    : {shadow.version if shadow else '(none)'}")
        print()
        print("Planned vector index DDL:")
        for stmt in vector_index_statements_for_version(args.target_version, dim):
            print(stmt.strip())
        print()
        print("Planned steps (not executed):")
        print(f"  1. REGISTER shadow version {args.target_version!r} on :EmbeddingVersionMeta")
        print(f"  2. DUAL-WRITE embeddings to {target_prop} (+ active property)")
        print(f"  3. CREATE VECTOR INDEX movie_plot_vec_{args.target_version}")
        print(f"  4. EVALUATE Recall@K (shadow vs active)")
        print(f"  5. PROMOTE shadow → active when threshold met")
        print()
        print("No Cypher writes were performed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
