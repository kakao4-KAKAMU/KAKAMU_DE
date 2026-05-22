"""애플리케이션 전역 설정.

SOLID - SRP: 설정 로딩/검증만 담당한다.
SOLID - OCP: 새 컴포넌트(다른 LLM 백엔드 등) 추가 시 별도 Settings를 분리해 확장한다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseSettings):
    """Neo4j 연결 정보."""

    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: str = Field(default="neo4j")
    database: str = Field(default="neo4j")

    model_config = SettingsConfigDict(env_prefix="NEO4J_", extra="ignore")


class PostgresSettings(BaseSettings):
    """PostgreSQL(채팅 이력/메타데이터) 연결 정보."""

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="chatbot")
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")

    model_config = SettingsConfigDict(env_prefix="PG_", extra="ignore")

    @property
    def dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class VLLMSettings(BaseSettings):
    """vLLM 추론 서버 설정.

    - PagedAttention + KVCache 효율을 위해 prefix-caching, chunked-prefill 사용
    - 동일 user_id 의 system + persona prefix 를 prefix-cache 로 재사용한다.
    """

    base_url: str = Field(default="http://localhost:8000/v1")
    api_key: str = Field(default="EMPTY")
    model_name: str = Field(default="Qwen/Qwen2.5-7B-Instruct")
    max_tokens: int = Field(default=1024)
    temperature: float = Field(default=0.2)

    enable_prefix_caching: bool = Field(default=True)
    enable_chunked_prefill: bool = Field(default=True)
    gpu_memory_utilization: float = Field(default=0.9)
    block_size: int = Field(default=16)

    model_config = SettingsConfigDict(env_prefix="VLLM_", extra="ignore")


class EmbeddingSettings(BaseSettings):
    """임베딩 모델 설정. Neo4j Vector Index 의 차원과 일치해야 한다."""

    model_name: str = Field(default="BAAI/bge-m3")
    dimension: int = Field(default=1024)
    normalize: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="EMBED_", extra="ignore")


class AppSettings(BaseSettings):
    """루트 애플리케이션 설정."""

    env: Literal["local", "dev", "stg", "prod"] = Field(default="local")
    log_level: str = Field(default="INFO")

    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    vllm: VLLMSettings = Field(default_factory=VLLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """싱글톤 설정 반환."""
    return AppSettings()
