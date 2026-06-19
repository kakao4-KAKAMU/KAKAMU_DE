"""Neo4j embedding 속성 명명 규칙.

패턴
----
- legacy/base: ``{prefix}_embedding``  (예: ``summary_embedding``, ``plot_embedding``)
- versioned  : ``{prefix}_embedding_v{n}`` (예: ``summary_embedding_v2``)
"""

from __future__ import annotations

from typing import Sequence


BASE_SUMMARY_EMBEDDING = "summary_embedding"
BASE_PLOT_EMBEDDING = "plot_embedding"


def normalize_version(version: str) -> str:
    return version.replace(".", "_")


def summary_embedding_property(version: str) -> str:
    """Feed/Comment 버전별 summary embedding 속성명."""
    return f"{BASE_SUMMARY_EMBEDDING}_v{normalize_version(version)}"


def plot_embedding_property(version: str) -> str:
    """Movie 버전별 plot embedding 속성명."""
    return f"{BASE_PLOT_EMBEDDING}_v{normalize_version(version)}"


def versioned_embedding_property(base_property: str, version: str) -> str:
    """임의 base embedding 속성의 버전 suffix 를 붙인다."""
    return f"{base_property}_v{normalize_version(version)}"


def build_embedding_set_clause(
    node_var: str,
    base_property: str,
    param_name: str,
    version_properties: Sequence[str] | None = None,
) -> str:
    """SET 절용 ``n.base = $param, n.base_v1 = $param, ...`` 조각을 생성한다."""
    props = [base_property, *(version_properties or [])]
    return ",\n    ".join(
        f"{node_var}.{prop} = ${param_name}" for prop in props
    )


__all__ = [
    "BASE_PLOT_EMBEDDING",
    "BASE_SUMMARY_EMBEDDING",
    "build_embedding_set_clause",
    "normalize_version",
    "plot_embedding_property",
    "summary_embedding_property",
    "versioned_embedding_property",
]
