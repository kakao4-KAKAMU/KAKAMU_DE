from __future__ import annotations

from unittest.mock import MagicMock

from src.embedding.dual_writer import DualEmbeddingWriter
from src.embedding.version_registry import EmbeddingVersion, VersionRegistry, VersionStatus


def test_dual_write_active_and_shadow() -> None:
    neo4j = MagicMock()
    reg = MagicMock(spec=VersionRegistry)
    reg.get_active_version.return_value = EmbeddingVersion(
        "1", "BAAI/bge-m3", 1024, VersionStatus.ACTIVE
    )
    reg.get_shadow_version.return_value = EmbeddingVersion(
        "2", "BAAI/bge-m3", 1024, VersionStatus.SHADOW
    )
    writer = DualEmbeddingWriter(neo4j, reg)
    written = writer.write_movie_plot_embedding("m1", [0.1, 0.2])
    assert len(written) == 2
    assert neo4j.execute_write.call_count == 2
