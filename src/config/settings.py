"""애플리케이션 전역 설정.

SOLID - SRP: 설정 로딩/검증만 담당한다.
SOLID - ISP: LLM generation / embedding / storage 를 별도 Settings 로 분리한다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.limits import (
    DEFAULT_MAX_CHAT_MESSAGE_LENGTH,
    DEFAULT_MAX_INGEST_CONTENT_LENGTH,
    DEFAULT_MAX_RECOMMEND_QUERY_LENGTH,
)

_INSECURE_NEO4J_PASSWORDS = frozenset({"", "neo4j"})
_INSECURE_PG_PASSWORDS = frozenset({"", "postgres"})


class Neo4jSettings(BaseSettings):
    """Neo4j 연결 정보."""

    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: str = Field(default="neo4j")
    database: str = Field(default="neo4j")

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="NEO4J_", extra="ignore"
    )


class PostgresSettings(BaseSettings):
    """PostgreSQL(채팅 이력/메타데이터) 연결 정보."""

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="chatbot")
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PG_", extra="ignore")

    @property
    def dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
    
    def __hash__(self) -> int:
        return hash((self.host, self.port, self.database, self.user, self.password))


class VLLMGenSettings(BaseSettings):
    """vLLM generation 서버 (chat / ontology / judge / cypher planner)."""

    base_url: str = Field(default="http://localhost:8000/v1")
    api_key: str = Field(default="EMPTY")
    model_name: str = Field(default="Qwen/Qwen3-8B-GGUF:Q4_K_M")
    max_tokens: int = Field(default=1024)
    temperature: float = Field(default=0.2)

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="VLLM_GEN_", extra="ignore"
    )


class VLLMEmbedSettings(BaseSettings):
    """vLLM embedding 서버 (BGE-M3 등)."""

    base_url: str = Field(default="http://localhost:8001/v1")
    api_key: str = Field(default="EMPTY")
    model_name: str = Field(default="BAAI/bge-m3")
    cache_size: int = Field(default=4096)

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="VLLM_EMBED_", extra="ignore"
    )


class EmbeddingSettings(BaseSettings):
    """임베딩 메타. Neo4j Vector Index 차원과 일치해야 한다."""

    model_name: str = Field(validation_alias="EMBED__MODEL_NAME", default="BAAI/bge-m3")
    dimension: int = Field(default=1024)
    normalize: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="EMBED_", extra="ignore"
    )


class OntologySettings(BaseSettings):
    """온톨로지 추출/적재 버전."""

    prompt_version: str = Field(default="1.0")
    model_name: str = Field(default="Qwen/Qwen3-8B-GGUF:Q4_K_M")

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ONTOLOGY_", extra="ignore"
    )


class VocabSettings(BaseSettings):
    """자동 어휘 승격 임계."""

    promote_min_count: int = Field(default=50)
    promote_min_days: int = Field(default=7)
    alias_cos_sim: float = Field(default=0.90)
    promote_max_cos_sim: float = Field(default=0.85)

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="VOCAB_", extra="ignore"
    )


class BanditSettings(BaseSettings):
    """추천 bandit 가드레일."""

    baseline_min_share: float = Field(default=0.05)

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="BANDIT_", extra="ignore"
    )


class ApiSecuritySettings(BaseSettings):
    """HTTP API 보안·리소스 가드레일."""

    max_chat_message_length: int = Field(
        default=DEFAULT_MAX_CHAT_MESSAGE_LENGTH, ge=256, le=32_000
    )
    max_recommend_query_length: int = Field(
        default=DEFAULT_MAX_RECOMMEND_QUERY_LENGTH, ge=64, le=8_000
    )
    max_ingest_content_length: int = Field(
        default=DEFAULT_MAX_INGEST_CONTENT_LENGTH, ge=256, le=100_000
    )
    max_request_body_bytes: int = Field(default=1_048_576, ge=1_024)
    rate_limit_rpm_default: int = Field(default=120, ge=1)
    rate_limit_rpm_expensive: int = Field(default=30, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="API_SEC_", extra="ignore"
    )


class EvalSettings(BaseSettings):
    """LLM judge / drift 알람."""

    daily_sample_size: int = Field(
        default=100,
        validation_alias=AliasChoices("JUDGE_DAILY_SAMPLE_SIZE", "daily_sample_size"),
    )
    drift_kl_threshold: float = Field(
        default=0.15,
        validation_alias=AliasChoices("DRIFT_KL_THRESHOLD", "drift_kl_threshold"),
    )
    slack_webhook_url: str = Field(
        default="",
        validation_alias=AliasChoices("EVAL_SLACK_WEBHOOK_URL", "slack_webhook_url"),
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppSettings(BaseSettings):
    """루트 애플리케이션 설정."""

    env: Literal["local", "dev", "stg", "prod"] = Field(
        default="local", validation_alias="APP_ENV"
    )

    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    vllm_gen: VLLMGenSettings = Field(default_factory=VLLMGenSettings)
    vllm_embed: VLLMEmbedSettings = Field(default_factory=VLLMEmbedSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    ontology: OntologySettings = Field(default_factory=OntologySettings)
    vocab: VocabSettings = Field(default_factory=VocabSettings)
    bandit: BanditSettings = Field(default_factory=BanditSettings)
    eval_cfg: EvalSettings = Field(default_factory=EvalSettings)
    api_security: ApiSecuritySettings = Field(default_factory=ApiSecuritySettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _reject_insecure_credentials_in_prod(self) -> Self:
        if self.env not in ("stg", "prod"):
            return self
        if self.neo4j.password in _INSECURE_NEO4J_PASSWORDS:
            raise ValueError(
                "NEO4J_PASSWORD must be set to a non-default value when APP_ENV is stg/prod"
            )
        if self.postgres.password in _INSECURE_PG_PASSWORDS:
            raise ValueError(
                "PG_PASSWORD must be set to a non-default value when APP_ENV is stg/prod"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """싱글톤 설정 반환."""
    return AppSettings()


__all__ = [
    "Neo4jSettings",
    "PostgresSettings",
    "VLLMGenSettings",
    "VLLMEmbedSettings",
    "EmbeddingSettings",
    "OntologySettings",
    "VocabSettings",
    "BanditSettings",
    "ApiSecuritySettings",
    "EvalSettings",
    "AppSettings",
    "get_settings",
]
