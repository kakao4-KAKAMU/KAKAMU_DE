"""임베딩 버전 마이그레이션 dry-run."""

from __future__ import annotations

import logging

from src.config.settings import get_settings
from src.embedding.version_registry import EmbeddingVersion, VersionRegistry, VersionStatus
from src.graph.client import Neo4jClient
from src.graph.cypher_statements import vector_index_statements_for_version

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    with Neo4jClient(settings.neo4j) as neo:
        reg = VersionRegistry(neo)
        active = reg.get_active_version()
        if active is None:
            v1 = EmbeddingVersion(
                name="1",
                model=settings.embedding.model_name,
                dimension=settings.embedding.dimension,
                status=VersionStatus.ACTIVE,
            )
            reg.register_version(v1)
            logger.info("Registered default active version v1")
            active = v1

        shadow = reg.get_shadow_version()
        if shadow is None:
            logger.info("No shadow version configured; dry-run complete")
            return

        stmts = vector_index_statements_for_version(shadow.name, shadow.dimension)
        logger.info("Would create indexes: %s", [s.split()[2] for s in stmts])
        logger.info("Dry-run OK: active=%s shadow=%s", active.name, shadow.name)


if __name__ == "__main__":
    main()
