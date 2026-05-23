"""CandidateTerm 자동 승격."""

from __future__ import annotations

import logging
from typing import Sequence

from src.config.settings import VocabSettings, get_settings
from src.graph.client import Neo4jClient
from src.vocab.aliaser import TermAliaser, cosine_similarity
from src.vocab.candidate_store import CandidateStore

logger = logging.getLogger(__name__)

PROMOTE_THEME = """
MERGE (t:Theme {name: $name})
WITH t
MATCH (c:CandidateTerm {normalized: $normalized, kind: $kind})
DETACH DELETE c
"""

PROMOTE_MOOD = """
MERGE (m:Mood {name: $name})
WITH m
MATCH (c:CandidateTerm {normalized: $normalized, kind: $kind})
DETACH DELETE c
"""

ADD_ALIAS = """
MATCH (n) WHERE (n:Theme OR n:Mood) AND n.name = $canonical
SET n.aliases = coalesce(n.aliases, []) + $alias
WITH n
MATCH (c:CandidateTerm {normalized: $normalized, kind: $kind})
DETACH DELETE c
"""


class VocabPromoter:
    def __init__(
        self,
        neo4j: Neo4jClient,
        store: CandidateStore,
        *,
        settings: VocabSettings | None = None,
    ) -> None:
        self._neo4j = neo4j
        self._store = store
        self._settings = settings or get_settings().vocab
        self._aliaser = TermAliaser(alias_threshold=self._settings.alias_cos_sim)

    def run_batch(
        self,
        catalog_embeddings: list[tuple[str, Sequence[float]]],
    ) -> dict[str, int]:
        stats = {"promoted": 0, "aliased": 0, "skipped": 0}
        candidates = self._store.list_promotion_candidates(
            min_count=self._settings.promote_min_count,
            min_days=self._settings.promote_min_days,
        )
        for cand in candidates:
            normalized = cand["normalized"]
            kind = cand["kind"]
            emb = cand.get("embedding") or []
            if emb and catalog_embeddings:
                alias = self._aliaser.find_alias(emb, catalog_embeddings)
                if alias:
                    self._neo4j.execute_write(
                        ADD_ALIAS,
                        {
                            "canonical": alias,
                            "alias": normalized,
                            "normalized": normalized,
                            "kind": kind,
                        },
                    )
                    stats["aliased"] += 1
                    continue
                max_sim = max(
                    cosine_similarity(emb, c_emb) for _, c_emb in catalog_embeddings
                )
                if max_sim >= self._settings.promote_max_cos_sim:
                    stats["skipped"] += 1
                    continue

            name = normalized
            if kind == "mood":
                self._neo4j.execute_write(
                    PROMOTE_MOOD,
                    {"name": name, "normalized": normalized, "kind": kind},
                )
            else:
                self._neo4j.execute_write(
                    PROMOTE_THEME,
                    {"name": name, "normalized": normalized, "kind": kind},
                )
            stats["promoted"] += 1
        logger.info("Vocab promotion batch: %s", stats)
        return stats


__all__ = ["VocabPromoter"]
