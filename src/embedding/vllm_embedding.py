"""vLLM OpenAI-compatible embedding 클라이언트 + LRU 캐시.

SOLID - SRP: 임베딩 호출/캐시만 담당.
DIP: 상위 모듈은 본 클래스 인터페이스에만 의존.
"""

from __future__ import annotations

import hashlib
import logging
import time
import subprocess
from collections import OrderedDict
from typing import Optional, Sequence

from openai import OpenAI

from src.config.settings import EmbeddingSettings, VLLMEmbedSettings, get_settings

logger = logging.getLogger(__name__)


class _LRUCache:
    def __init__(self, maxsize: int) -> None:
        self._maxsize = maxsize
        self._data: OrderedDict[str, list[float]] = OrderedDict()

    def get(self, key: str) -> list[float] | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def set(self, key: str, value: list[float]) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)


def _cache_key(text: str, model: str) -> str:
    return hashlib.sha256(f"{model}:{text}".encode()).hexdigest()


def _l2_normalize(vec: Sequence[float]) -> list[float]:
    import math

    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return list(vec)
    return [x / norm for x in vec]


# class VLLMEmbeddingClient:
#     """vLLM /v1/embeddings 호출. 실패 시 sentence-transformers fallback."""

#     def __init__(
#         self,
#         embed_settings: Optional[VLLMEmbedSettings] = None,
#         meta: Optional[EmbeddingSettings] = None,
#     ) -> None:
#         app = get_settings()
#         self._embed = embed_settings or app.vllm_embed
#         self._meta = meta or app.embedding
#         self._client = OpenAI(
#             base_url=self._embed.base_url,
#             api_key=self._embed.api_key,
#         )
#         self._cache = _LRUCache(self._embed.cache_size)
#         self._st_model = None

#     def embed(self, text: str) -> list[float]:
#         text = text.strip()
#         if not text:
#             return [0.0] * self._meta.dimension

#         key = _cache_key(text, self._embed.model_name)
#         cached = self._cache.get(key)
#         if cached is not None:
#             return cached

#         resp = self._client.embeddings.create(
#             model=self._embed.model_name,
#             input=text,
#         )
#         vec = list(resp.data[0].embedding)

#         if self._meta.normalize:
#             vec = _l2_normalize(vec)

#         self._cache.set(key, vec)
#         return vec

#     def embed_batch(self, texts: list[str]) -> list[list[float]]:
#         return [self.embed(t) for t in texts]



# __all__ = ["VLLMEmbeddingClient"]

class VLLMEmbeddingClient:
    """vLLM /v1/embeddings 호출. 실패 시 sentence-transformers fallback."""

    def __init__(
        self,
        embed_settings: Optional[VLLMEmbedSettings] = None,
        meta: Optional[EmbeddingSettings] = None,
    ) -> None:
        app = get_settings()
        self._embed = embed_settings or app.vllm_embed
        self._meta = meta or app.embedding
        self._client = OpenAI(
            base_url=self._embed.base_url, # 예: http://localhost:8000/v1
            api_key=self._embed.api_key,
        )
        self._cache = _LRUCache(self._embed.cache_size)
        self._st_model = None

    def _get_local_gpu_vram(self) -> str:
        """로컬 장비의 nvidia-smi를 호출하여 실제 GPU VRAM 사용량을 MB 단위로 가져옵니다."""
        try:
            # nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True
            )
            vram_mb = result.stdout.strip().split('\n')[0] # 멀티 GPU일 경우 첫 번째 GPU(혹은 매핑된 GPU) 기준
            return f"{vram_mb} MB"
        except Exception as e:
            return "N/A"

    def embed(self, text: str) -> list[float]:
        text = text.strip()
        if not text:
            return [0.0] * self._meta.dimension

        key = _cache_key(text, self._embed.model_name)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        # === [벤치마크 시작] ===
        start_time = time.time()

        resp = self._client.embeddings.create(
            model=self._embed.model_name,
            input=text,
        )
        
        # === [벤치마크 종료 및 지표 계산] ===
        latency_ms = (time.time() - start_time) * 1000
        
        # 응답 객체에서 토큰 수 추출 (vLLM 호환 API 기준)
        tokens = resp.usage.prompt_tokens if hasattr(resp, "usage") and resp.usage else 0
        
        # 로컬 GPU 메모리 조회
        local_vram = self._get_local_gpu_vram()
        
        logger.info(
            f"[Embed Benchmark] Model: {self._embed.model_name:18s} | "
            f"Latency: {latency_ms:6.2f} ms | "
            f"Tokens: {tokens:4d} | "
            f"Local VRAM: {local_vram}"
        )

        vec = list(resp.data[0].embedding)

        if self._meta.normalize:
            vec = _l2_normalize(vec)

        self._cache.set(key, vec)
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # 배치 처리 시 전체 지표를 보고 싶다면 이 부분을 수정해도 됩니다.
        return [self.embed(t) for t in texts]

__all__ = ["VLLMEmbeddingClient"]