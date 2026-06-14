"""Ingest payload 공통 타입.

src/ontology/schema.py 와 동일한 구조 규약을 따른다.

설계 원칙
---------
- SRP : ingest payload 들이 공유하는 타입/베이스만 정의한다.
- LSP : 모든 Ingest*Payload 는 IngestPayload 를 상속해 동일한
        직렬화/검증 인터페이스를 보장한다. (ontology.OntologyResult 대응)
- OCP : 신규 payload 는 IngestPayload 상속만으로 확장한다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

JudgeType = Literal["like", "dislike"]


class IngestPayload(BaseModel):
    """모든 ingest payload 의 공통 베이스."""


__all__ = [
    "JudgeType",
    "IngestPayload",
]
