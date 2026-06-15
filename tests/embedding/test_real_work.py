"""로컬에서 프로덕션 embedding 경로(ingest/recommend)를 MLX로 검증한다.

영화·피드 샘플과 감정 flag 는 ``build_movie_handler`` / ``build_feed_handler`` /
``OntologyLoader.upsert_feed`` 와 동일한 스키마를 사용한다.
임베딩은 vLLM 대신 Apple Silicon용 ``mlx_embeddings`` + BGE-M3 MLX 체크포인트로 수행한다.

사전 요구::

    pip install mlx-embeddings mlx

실행 예::

    python tests/embedding/test_real_work.py

    RUN_INTEGRATION=1 pytest tests/embedding/test_real_work.py -m integration -q
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import EmbeddingSettings, get_settings
from src.graph.cypher_statements import SEED_EMOTIONS
from src.ontology.schema import (
    EmotionScore,
    EmotionTag,
    FeedCategory,
    FeedOntology,
    Keyword,
    MoviePlotOntology,
    Sentiment,
)

# 서비스 EMBED 설정과 동일 차원(BAAI/bge-m3 → Neo4j vector index 1024)
DEFAULT_MLX_MODEL = os.environ.get(
    "MLX_EMBED_MODEL", "mlx-community/bge-m3-mlx-fp16"
)

# ---------------------------------------------------------------------------
# 서비스 ingest payload (build_movie_handler / build_feed_handler 와 동일 키)
# ---------------------------------------------------------------------------

SERVICE_MOVIE_INGEST_PAYLOAD: dict[str, object] = {
    "movie_id": "m-001",
    "title": "기생충",
    "producing_year": 2019,
    "country": "KR",
    "genres": ["드라마", "스릴러"],
    "plot": (
        "전원백수 가족이 부유한 가족의 집에 한 명씩 침투하기 시작하면서 "
        "계급 갈등과 생존을 둘러싼 긴장이 고조되는 이야기."
    ),
}

SERVICE_MOVIE_PLOT_ONTOLOGY = MoviePlotOntology(
    source_id="m-001",
    summary="가난한 가족이 부유한 가족의 집에 침투하며 계급 갈등이 심화되는 이야기",
    themes=["계급 갈등", "생존", "가족"],
    moods=["어두운", "긴장감", "현실적인"],
    keywords=[
        Keyword(term="전원백수 가족", normalized="unemployed_family", weight=0.95, kind="entity"),
        Keyword(term="부유한 가족의 집", normalized="wealthy_mansion", weight=0.9, kind="environment"),
        Keyword(term="반지하", normalized="semi_basement", weight=0.85, kind="environment"),
    ],
)

SERVICE_FEED_INGEST_PAYLOAD: dict[str, object] = {
    "feed_id": "f-parasite-review-001",
    "user_id": "u-demo-001",
    "related_movie_id": "m-001",
    "known_movie_ids": ["m-001"],
    "content": (
        "기생충 다시 봤는데 반지하와 저택의 대비가 여전히 소름 돋아요. "
        "웃기다가도 서늘해지는 장면들이 많아서 긴장감이 끝까지 이어집니다."
    ),
    "created_at": "2026-05-23T10:00:00+00:00",
}

# FeedExtractor 출력 — EmotionTag·SEED_EMOTIONS 와 동일 태그 체계
SERVICE_FEED_ONTOLOGY = FeedOntology(
    source_id="f-parasite-review-001",
    summary="기생충 재관람 감상: 계급 대비와 긴장·서늘함이 인상적",
    category=FeedCategory.REVIEW,
    sentiment=Sentiment.POSITIVE,
    sentiment_score=0.72,
    emotions=[
        EmotionScore(tag=EmotionTag.NOSTALGIA, score=0.55),
        EmotionScore(tag=EmotionTag.EXCITEMENT, score=0.48),
        EmotionScore(tag=EmotionTag.ADMIRATION, score=0.82),
        EmotionScore(tag=EmotionTag.FEAR, score=0.35),
    ],
    keywords=[],
    referenced_movie_ids=["m-001"],
)

SERVICE_RECOMMEND_QUERY = "계급 갈등이 있는 긴장감 넘치는 한국 영화 추천해줘"

assert {e.value for e in EmotionTag} == set(SEED_EMOTIONS)


class MLXBgeEmbeddingClient:
    """``Embedder`` Protocol 호환 로컬 클라이언트 (mlx_embeddings + BGE-M3 MLX)."""

    def __init__(
        self,
        *,
        model_path: str = DEFAULT_MLX_MODEL,
        meta: Optional[EmbeddingSettings] = None,
    ) -> None:
        self._meta = meta or get_settings().embedding
        self._model_path = model_path
        from mlx_embeddings import load
        import mlx.core as mx

        self._mx = mx
        self._model, self._tokenizer = load(model_path)

    def embed(self, text: str) -> list[float]:
        text = text.strip()
        if not text:
            return [0.0] * self._meta.dimension

        inputs = self._tokenizer.encode(text, return_tensors="mlx")
        outputs = self._model(inputs)
        pooled = outputs.text_embeds
        self._mx.eval(pooled)
        vec = pooled[0].tolist()

        if self._meta.normalize:
            vec = _l2_normalize(vec)
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        stripped = [t.strip() for t in texts]
        if not any(stripped):
            return [[0.0] * self._meta.dimension for _ in texts]

        inputs = self._tokenizer.batch_encode_plus(
            stripped,
            return_tensors="mlx",
            padding=True,
            truncation=True,
            max_length=512,
        )
        outputs = self._model(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
        )
        pooled = outputs.text_embeds
        self._mx.eval(pooled)
        vectors: list[list[float]] = []
        for row in pooled:
            vec = row.tolist()
            if self._meta.normalize:
                vec = _l2_normalize(vec)
            vectors.append(vec)
        return vectors


def _load_local_env() -> None:
    env_local = ROOT / ".env.local"
    if env_local.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_local, override=False)


def _l2_normalize(vec: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return list(vec)
    return [x / norm for x in vec]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


def _embedding_text_for_movie() -> str:
    plot = str(SERVICE_MOVIE_INGEST_PAYLOAD["plot"])
    return SERVICE_MOVIE_PLOT_ONTOLOGY.summary or plot


def _movie_ontology_source_text(payload: dict[str, object]) -> str:
    genres = ", ".join(str(g) for g in payload.get("genres") or [])
    return (
        f"제목: {payload['title']}\n"
        f"제작연도: {payload.get('producing_year')}\n"
        f"국가: {payload.get('country')}\n"
        f"장르: {genres}\n"
        f"줄거리: {payload.get('plot') or ''}"
    )


def _score_candidates(
    embedder: MLXBgeEmbeddingClient,
    source_text: str,
    candidates: Sequence[str],
) -> dict[str, float]:
    vectors = embedder.embed_batch([source_text, *candidates])
    source_vec = vectors[0]
    return {
        label: _cosine(source_vec, vec)
        for label, vec in zip(candidates, vectors[1:], strict=True)
    }


def _select_labels_with_mlx(
    embedder: MLXBgeEmbeddingClient,
    source_text: str,
    candidates: Sequence[str],
    *,
    top_k: int,
) -> tuple[list[str], dict[str, float]]:
    scores = _score_candidates(embedder, source_text, candidates)
    ranked = sorted(candidates, key=lambda label: scores[label], reverse=True)[:top_k]
    selected = set(ranked)
    return [label for label in candidates if label in selected], scores


def extract_movie_ontology_with_mlx_scores(
    payload: dict[str, object],
    *,
    embedder: MLXBgeEmbeddingClient | None = None,
) -> tuple[MoviePlotOntology, dict[str, dict[str, float]]]:
    """MLX 임베딩 유사도로 영화 payload 에서 온톨로지 후보를 선택한다."""
    client = embedder or MLXBgeEmbeddingClient()
    source_text = _movie_ontology_source_text(payload)
    expected = SERVICE_MOVIE_PLOT_ONTOLOGY

    themes, theme_scores = _select_labels_with_mlx(
        client,
        source_text,
        expected.themes,
        top_k=len(expected.themes),
    )
    moods, mood_scores = _select_labels_with_mlx(
        client,
        source_text,
        expected.moods,
        top_k=len(expected.moods),
    )
    keyword_scores = _score_candidates(
        client,
        source_text,
        [k.normalized for k in expected.keywords],
    )

    ontology = MoviePlotOntology(
        source_id=str(payload["movie_id"]),
        summary=expected.summary,
        themes=themes,
        moods=moods,
        keywords=[
            Keyword(
                term=k.term,
                normalized=k.normalized,
                weight=k.weight,
                kind=k.kind,
            )
            for k in expected.keywords
            if keyword_scores[k.normalized] > 0.0
        ],
    )
    return ontology, {
        "themes": theme_scores,
        "moods": mood_scores,
        "keywords": keyword_scores,
    }


def extract_movie_ontology_from_payload(
    payload: dict[str, object],
    *,
    embedder: MLXBgeEmbeddingClient | None = None,
) -> MoviePlotOntology:
    ontology, _ = extract_movie_ontology_with_mlx_scores(
        payload,
        embedder=embedder,
    )
    return ontology


def assert_movie_ontology_matches_service_expected(actual: MoviePlotOntology) -> None:
    """created_at 처럼 실행 시점에 달라지는 필드를 제외하고 서비스 기대값과 비교한다."""
    assert actual.model_dump(mode="json", exclude={"created_at"}) == (
        SERVICE_MOVIE_PLOT_ONTOLOGY.model_dump(mode="json", exclude={"created_at"})
    )


def run_movie_ontology_extraction_step() -> MoviePlotOntology:
    """1단계: MLX 임베딩 기반으로 영화 온톨로지를 추출하고 기대 결과와 비교한다."""
    ontology, scores = extract_movie_ontology_with_mlx_scores(
        SERVICE_MOVIE_INGEST_PAYLOAD,
    )
    assert_movie_ontology_matches_service_expected(ontology)

    print("=== step 1: movie ontology extraction (MLX) ===")
    print(f"movie_id={ontology.source_id}")
    print(f"summary={ontology.summary}")
    print(f"themes={ontology.themes}")
    print(f"moods={ontology.moods}")
    print(f"keywords={[k.normalized for k in ontology.keywords]}")
    print(f"theme_scores={scores['themes']}")
    print(f"mood_scores={scores['moods']}")
    print(f"keyword_scores={scores['keywords']}")
    print("comparison=matched")
    return ontology


def _embedding_text_for_feed() -> str:
    content = str(SERVICE_FEED_INGEST_PAYLOAD["content"])
    return SERVICE_FEED_ONTOLOGY.summary or content


def service_emotion_flags(ontology: FeedOntology) -> list[dict[str, Any]]:
    """Neo4j ``UPSERT_FEED_WITH_ONTOLOGY`` 의 ``$emotions`` 파라미터와 동일 형식."""
    return [{"tag": e.tag.value, "score": e.score} for e in ontology.emotions]


def run_local_embedding_smoke(
    embedder: MLXBgeEmbeddingClient | None = None,
) -> dict[str, object]:
    """ingest·recommend 와 동일한 텍스트로 MLX 임베딩을 생성하고 유사도를 출력한다."""
    _load_local_env()
    client = embedder or MLXBgeEmbeddingClient()
    settings = get_settings()

    movie_text = _embedding_text_for_movie()
    feed_text = _embedding_text_for_feed()
    query_text = SERVICE_RECOMMEND_QUERY
    emotion_flags = service_emotion_flags(SERVICE_FEED_ONTOLOGY)

    movie_vec = client.embed(movie_text)
    feed_vec = client.embed(feed_text)
    query_vec = client.embed(query_text)

    dim = settings.embedding.dimension
    emotion_tags = [e["tag"] for e in emotion_flags]

    report = {
        "backend": "mlx_embeddings",
        "model": client._model_path,
        "dimension": dim,
        "vector_len": len(movie_vec),
        "normalized": settings.embedding.normalize,
        "movie_id": SERVICE_MOVIE_INGEST_PAYLOAD["movie_id"],
        "movie_embed_preview": movie_vec[:5],
        "feed_id": SERVICE_FEED_INGEST_PAYLOAD["feed_id"],
        "feed_emotion_flags": emotion_flags,
        "feed_emotion_tags": emotion_tags,
        "feed_embed_preview": feed_vec[:5],
        "recommend_query": query_text,
        "query_embed_preview": query_vec[:5],
        "cosine_movie_vs_query": _cosine(movie_vec, query_vec),
        "cosine_feed_vs_query": _cosine(feed_vec, query_vec),
        "cosine_movie_vs_feed": _cosine(movie_vec, feed_vec),
    }

    print("=== embedding local smoke (MLX) ===")
    print(
        f"model={report['model']} dim={report['dimension']} len={report['vector_len']}"
    )
    print(f"movie ({report['movie_id']}): {movie_text[:60]}...")
    print(f"  preview={report['movie_embed_preview']}")
    print(
        f"feed ({report['feed_id']}) emotion_flags={report['feed_emotion_flags']}: "
        f"{feed_text[:50]}..."
    )
    print(f"  preview={report['feed_embed_preview']}")
    print(f"recommend query: {query_text}")
    print(f"  preview={report['query_embed_preview']}")
    print(f"cosine(movie, query)={report['cosine_movie_vs_query']:.4f}")
    print(f"cosine(feed, query)={report['cosine_feed_vs_query']:.4f}")
    print(f"cosine(movie, feed)={report['cosine_movie_vs_feed']:.4f}")
    return report


@pytest.mark.integration
def test_movie_ontology_extraction_matches_expected_service_values() -> None:
    _load_local_env()
    ontology, scores = extract_movie_ontology_with_mlx_scores(
        SERVICE_MOVIE_INGEST_PAYLOAD
    )

    assert_movie_ontology_matches_service_expected(ontology)
    assert set(scores) == {"themes", "moods", "keywords"}
    assert all(score > 0.0 for group in scores.values() for score in group.values())


@pytest.mark.integration
def test_service_movie_feed_vectors_match_dimension() -> None:
    _load_local_env()
    client = MLXBgeEmbeddingClient()
    dim = EmbeddingSettings().dimension

    for label, text in (
        ("movie", _embedding_text_for_movie()),
        ("feed", _embedding_text_for_feed()),
        ("query", SERVICE_RECOMMEND_QUERY),
    ):
        vec = client.embed(text)
        assert len(vec) == dim, f"{label} embedding length {len(vec)} != {dim}"


@pytest.mark.integration
def test_recommend_query_closer_to_movie_than_unrelated() -> None:
    _load_local_env()
    client = MLXBgeEmbeddingClient()

    movie_vec = client.embed(_embedding_text_for_movie())
    query_vec = client.embed(SERVICE_RECOMMEND_QUERY)
    unrelated_vec = client.embed("우주를 배경으로 한 가벼운 로맨틱 코미디 추천")

    sim_movie = _cosine(movie_vec, query_vec)
    sim_unrelated = _cosine(unrelated_vec, query_vec)
    assert sim_movie > sim_unrelated


@pytest.mark.integration
def test_feed_emotion_flags_match_loader_and_seed() -> None:
    flags = service_emotion_flags(SERVICE_FEED_ONTOLOGY)
    tags = {f["tag"] for f in flags}
    assert tags.issubset(set(SEED_EMOTIONS))
    assert EmotionTag.ADMIRATION.value in tags
    assert flags == [
        {"tag": "nostalgia", "score": 0.55},
        {"tag": "excitement", "score": 0.48},
        {"tag": "admiration", "score": 0.82},
        {"tag": "fear", "score": 0.35},
    ]


@pytest.mark.integration
def test_embed_batch_matches_single_embed() -> None:
    _load_local_env()
    client = MLXBgeEmbeddingClient()
    texts = [_embedding_text_for_movie(), _embedding_text_for_feed()]
    batch = client.embed_batch(texts)
    assert _cosine(batch[0], client.embed(texts[0])) > 0.9999
    assert _cosine(batch[1], client.embed(texts[1])) > 0.9999


if __name__ == "__main__":
    run_movie_ontology_extraction_step()
    run_local_embedding_smoke()
