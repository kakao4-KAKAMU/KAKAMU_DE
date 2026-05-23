from __future__ import annotations

from unittest.mock import MagicMock

from src.embedding.version_registry import (
    EmbeddingVersion,
    VersionRegistry,
    VersionStatus,
    property_name_for_version,
)


def test_property_name() -> None:
    assert property_name_for_version("1.0") == "plot_embedding_v1_0"


def test_register_version() -> None:
    neo4j = MagicMock()
    reg = VersionRegistry(neo4j)
    reg.register_version(
        EmbeddingVersion("1", "BAAI/bge-m3", 1024, VersionStatus.ACTIVE)
    )
    neo4j.execute_write.assert_called_once()
