"""Neo4j 기본 스키마 정의 (Cypher 상수).

- Constraints  : 노드 unique identity 보장
- Indexes      : 단일 속성 lookup 인덱스
- Fulltext     : 한국어/영문 키워드 검색용
- Vector Index : embedding 기반 의미 검색용 (Neo4j 5.13+ 의 native vector index)

설계 원칙
---------
- SRP: 본 모듈은 "스키마 DDL 문자열" 만 책임진다.
- OCP: 새로운 노드/관계가 생기면 list 에 append 만으로 확장한다.
- 멱등성: 모든 statement 는 `IF NOT EXISTS` 또는 동등한 가드를 가진다.
"""

from __future__ import annotations

from typing import Final, List, Sequence

# ---------------------------------------------------------------------------
# 1. Node uniqueness constraints (Neo4j 5.x 문법)
# ---------------------------------------------------------------------------
NODE_CONSTRAINTS: Final[List[str]] = [
    "CREATE CONSTRAINT movie_id_unique IF NOT EXISTS FOR (m:Movie)    REQUIRE m.movie_id   IS UNIQUE",
    "CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person)  REQUIRE p.person_id  IS UNIQUE",
    "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User)      REQUIRE u.user_id    IS UNIQUE",
    "CREATE CONSTRAINT feed_id_unique IF NOT EXISTS FOR (f:Feed)      REQUIRE f.feed_id    IS UNIQUE",
    "CREATE CONSTRAINT comment_id_unique IF NOT EXISTS FOR (c:Comment) REQUIRE c.comment_id IS UNIQUE",
    "CREATE CONSTRAINT genre_name_unique IF NOT EXISTS FOR (g:Genre)  REQUIRE g.name       IS UNIQUE",
    "CREATE CONSTRAINT theme_name_unique IF NOT EXISTS FOR (t:Theme)  REQUIRE t.name       IS UNIQUE",
    "CREATE CONSTRAINT mood_name_unique  IF NOT EXISTS FOR (m:Mood)   REQUIRE m.name       IS UNIQUE",
    "CREATE CONSTRAINT keyword_norm_unique IF NOT EXISTS FOR (k:Keyword) REQUIRE k.normalized IS UNIQUE",
    "CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT emotion_tag_unique IF NOT EXISTS FOR (e:Emotion) REQUIRE e.tag      IS UNIQUE",
    "CREATE CONSTRAINT country_code_unique IF NOT EXISTS FOR (c:Country) REQUIRE c.code    IS UNIQUE",
    "CREATE CONSTRAINT embedding_version_unique IF NOT EXISTS FOR (e:EmbeddingVersionMeta) REQUIRE e.version IS UNIQUE",
    "CREATE CONSTRAINT embedding_version_property_unique IF NOT EXISTS FOR (e:EmbeddingVersionMeta) REQUIRE e.property_key IS UNIQUE",
]

# ---------------------------------------------------------------------------
# 2. B-Tree (Range) Indexes : 단일 속성 lookup 가속
# ---------------------------------------------------------------------------
NODE_PROPERTY_INDEXES: Final[List[str]] = [
    "CREATE INDEX movie_year_idx   IF NOT EXISTS FOR (m:Movie)   ON (m.producing_year)",
    "CREATE INDEX movie_country_idx IF NOT EXISTS FOR (m:Movie)  ON (m.country)",
    "CREATE INDEX feed_created_idx IF NOT EXISTS FOR (f:Feed)    ON (f.created_at)",
    "CREATE INDEX comment_created_idx IF NOT EXISTS FOR (c:Comment) ON (c.created_at)",
    "CREATE INDEX user_created_idx IF NOT EXISTS FOR (u:User)    ON (u.created_at)",
    "CREATE INDEX feed_sentiment_idx IF NOT EXISTS FOR (f:Feed)  ON (f.sentiment_score)",
    "CREATE INDEX embedding_version_role_idx IF NOT EXISTS FOR (e:EmbeddingVersionMeta) ON (e.role)",
    "CREATE INDEX embedding_version_dimension_idx IF NOT EXISTS FOR (e:EmbeddingVersionMeta) ON (e.dimension)",
    "CREATE INDEX embedding_version_model_idx IF NOT EXISTS FOR (e:EmbeddingVersionMeta) ON (e.model_name)",
    "CREATE INDEX embedding_version_created_idx IF NOT EXISTS FOR (e:EmbeddingVersionMeta) ON (e.created_at)",
]

# ---------------------------------------------------------------------------
# 3. Fulltext Indexes : keyword 기반 검색
# ---------------------------------------------------------------------------
FULLTEXT_INDEXES: Final[List[str]] = [
    """
    CREATE FULLTEXT INDEX movie_text_ft IF NOT EXISTS
    FOR (m:Movie) ON EACH [m.title, m.plot_summary]
    OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }
    """,
    """
    CREATE FULLTEXT INDEX feed_text_ft IF NOT EXISTS
    FOR (f:Feed) ON EACH [f.summary]
    OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }
    """,
    """
    CREATE FULLTEXT INDEX comment_text_ft IF NOT EXISTS
    FOR (c:Comment) ON EACH [c.summary]
    OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }
    """,
    """
    CREATE FULLTEXT INDEX keyword_text_ft IF NOT EXISTS
    FOR (k:Keyword) ON EACH [k.term, k.normalized]
    OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }
    """,
]


def vector_index_statements_for_version(
    version: str, embedding_dim: int, *, label: str = "Movie", base_prop: str = "plot_embedding"
) -> List[str]:
    """버전별 vector index (예: plot_embedding_v1)."""
    prop = f"{base_prop}_v{version.replace('.', '_')}"
    index_name = f"movie_plot_vec_{version.replace('.', '_')}"
    return [
        f"""
        CREATE VECTOR INDEX {index_name} IF NOT EXISTS
        FOR (m:{label}) ON (m.{prop})
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
    ]


def vector_index_statements(embedding_dim: int) -> List[str]:
    """semantic 검색용 Native Vector Index.

    Args:
        embedding_dim: 임베딩 모델 차원 (BGE-M3 = 1024, MiniLM = 384 등).
    """

    return [
        f"""
        CREATE VECTOR INDEX movie_plot_vec IF NOT EXISTS
        FOR (m:Movie) ON (m.plot_embedding)
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """,
        f"""
        CREATE VECTOR INDEX feed_summary_vec IF NOT EXISTS
        FOR (f:Feed) ON (f.summary_embedding)
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """,
        f"""
        CREATE VECTOR INDEX comment_summary_vec IF NOT EXISTS
        FOR (c:Comment) ON (c.summary_embedding)
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """,
    ]


# ---------------------------------------------------------------------------
# 4. 시드 데이터 (선택): 분류 체계의 standard label set
#    - LLM 출력이 free-text 으로 흔들리지 않도록 표준 노드를 미리 심는다.
# ---------------------------------------------------------------------------
SEED_CATEGORIES: Final[List[str]] = [
    "review", "recommendation", "question", "discussion",
    "news", "spoiler", "theory", "comparison", "meta", "off_topic",
]

SEED_EMOTIONS: Final[List[str]] = [
    "joy", "sadness", "anger", "fear", "disgust", "surprise",
    "nostalgia", "empathy", "excitement", "boredom", "confusion", "admiration",
]

SEED_MERGE_CATEGORY: Final[str] = """
UNWIND $categories AS name
MERGE (c:Category {name: name})
ON CREATE SET c.created_at = datetime()
"""

SEED_MERGE_EMOTION: Final[str] = """
UNWIND $emotions AS tag
MERGE (e:Emotion {tag: tag})
ON CREATE SET e.created_at = datetime()
"""


# ---------------------------------------------------------------------------
# 5. Upsert (MERGE) statements - 온톨로지 적재용
# ---------------------------------------------------------------------------

# 영화 본체 + 줄거리 온톨로지 적재 (legacy: 단일 plot_embedding 컬럼).
# 신규 ingest 경로는 ``build_upsert_movie_with_ontology(embedding_props=...)``
# 로 active+shadow 컬럼을 동시에 SET 한다.
UPSERT_MOVIE_WITH_ONTOLOGY: Final[str] = """
MERGE (m:Movie {movie_id: $movie_id})
SET m.title          = $title,
    m.producing_year = $producing_year,
    m.country        = $country,
    m.plot_raw       = $plot_raw,
    m.plot_summary   = $plot_summary,
    m.plot_embedding = $plot_embedding,
    m.updated_at     = datetime()

// Genre
WITH m
UNWIND $genres AS gname
  MERGE (g:Genre {name: gname})
  MERGE (m)-[:HAS_GENRE]->(g)

// Theme
WITH m
UNWIND $themes AS tname
  MERGE (t:Theme {name: tname})
  MERGE (m)-[:HAS_THEME]->(t)

// Mood
WITH m
UNWIND $moods AS mdname
  MERGE (md:Mood {name: mdname})
  MERGE (m)-[:HAS_MOOD]->(md)

// Keywords (semantic + keyword anchor)
WITH m
UNWIND $keywords AS kw
  MERGE (k:Keyword {normalized: kw.normalized})
    ON CREATE SET k.kind = kw.kind, k.term = kw.term
  MERGE (m)-[r:MENTIONS]->(k)
    SET r.weight = kw.weight
"""


def build_upsert_movie_with_ontology(
    embedding_properties: Sequence[str] | None = None,
) -> str:
    """버전화된 plot_embedding 속성을 동시에 SET 하는 UPSERT Cypher 를 생성한다.

    Args:
        embedding_properties: ``plot_embedding`` 외 추가로 SET 할 임베딩 속성 키들.
            예: ``["plot_embedding_v1", "plot_embedding_v2"]``.

    Note:
        모든 추가 속성은 동일한 ``$plot_embedding`` 파라미터로 채워진다.
        (다중 임베딩 모델을 동시에 사용하려면 별도 dual-writer 경로 사용.)
    """

    extra = embedding_properties or []
    extra_lines = "".join(f",\n    m.{prop}      = $plot_embedding" for prop in extra)

    return f"""
MERGE (m:Movie {{movie_id: $movie_id}})
SET m.title          = $title,
    m.producing_year = $producing_year,
    m.country        = $country,
    m.plot_raw       = $plot_raw,
    m.plot_summary   = $plot_summary,
    m.plot_embedding = $plot_embedding{extra_lines},
    m.updated_at     = datetime()

// Genre
WITH m
UNWIND $genres AS gname
  MERGE (g:Genre {{name: gname}})
  MERGE (m)-[:HAS_GENRE]->(g)

// Theme
WITH m
UNWIND $themes AS tname
  MERGE (t:Theme {{name: tname}})
  MERGE (m)-[:HAS_THEME]->(t)

// Mood
WITH m
UNWIND $moods AS mdname
  MERGE (md:Mood {{name: mdname}})
  MERGE (m)-[:HAS_MOOD]->(md)

// Keywords (semantic + keyword anchor)
WITH m
UNWIND $keywords AS kw
  MERGE (k:Keyword {{normalized: kw.normalized}})
    ON CREATE SET k.kind = kw.kind, k.term = kw.term
  MERGE (m)-[r:MENTIONS]->(k)
    SET r.weight = kw.weight
"""


UPSERT_FEED_WITH_ONTOLOGY: Final[str] = """
MERGE (u:User {user_id: $author_id})
MERGE (f:Feed {feed_id: $feed_id})
SET f.content_raw       = $content_raw,
    f.summary           = $summary,
    f.summary_embedding = $summary_embedding,
    f.sentiment         = $sentiment,
    f.sentiment_score   = $sentiment_score,
    f.contains_spoiler  = $contains_spoiler,
    f.toxicity_score    = $toxicity_score,
    f.created_at        = coalesce(f.created_at, $created_at),
    f.updated_at        = datetime()
MERGE (f)-[:WRITTEN_BY]->(u)

// related movie (optional)
WITH f
CALL {
  WITH f
  WITH f WHERE $related_movie_id IS NOT NULL
  MATCH (m:Movie {movie_id: $related_movie_id})
  MERGE (f)-[:ABOUT_MOVIE]->(m)
  RETURN count(*) AS _
}

// categories
WITH f
UNWIND $categories AS cname
  MERGE (c:Category {name: cname})
  MERGE (f)-[:HAS_CATEGORY]->(c)

// emotions
WITH f
UNWIND $emotions AS e
  MERGE (em:Emotion {tag: e.tag})
  MERGE (f)-[r:HAS_EMOTION]->(em)
    SET r.score = e.score

// keywords
WITH f
UNWIND $keywords AS kw
  MERGE (k:Keyword {normalized: kw.normalized})
    ON CREATE SET k.kind = kw.kind, k.term = kw.term
  MERGE (f)-[r:MENTIONS]->(k)
    SET r.weight = kw.weight
"""


UPSERT_COMMENT_WITH_ONTOLOGY: Final[str] = """
MERGE (u:User {user_id: $author_id})
MERGE (parent:Feed {feed_id: $feed_id})
MERGE (c:Comment {comment_id: $comment_id})
SET c.content_raw       = $content_raw,
    c.summary           = $summary,
    c.summary_embedding = $summary_embedding,
    c.sentiment         = $sentiment,
    c.sentiment_score   = $sentiment_score,
    c.contains_spoiler  = $contains_spoiler,
    c.toxicity_score    = $toxicity_score,
    c.created_at        = coalesce(c.created_at, $created_at),
    c.updated_at        = datetime()
MERGE (c)-[:ON_FEED]->(parent)
MERGE (c)-[:WRITTEN_BY]->(u)

// emotions
WITH c
UNWIND $emotions AS e
  MERGE (em:Emotion {tag: e.tag})
  MERGE (c)-[r:HAS_EMOTION]->(em)
    SET r.score = e.score

// keywords
WITH c
UNWIND $keywords AS kw
  MERGE (k:Keyword {normalized: kw.normalized})
    ON CREATE SET k.kind = kw.kind, k.term = kw.term
  MERGE (c)-[r:MENTIONS]->(k)
    SET r.weight = kw.weight
"""


# ---------------------------------------------------------------------------
# 6. Hybrid Retrieval Cypher (semantic + keyword)
# ---------------------------------------------------------------------------

HYBRID_MOVIE_RECOMMEND: Final[
    str
] = """
// 1) Vector similarity 계산 (index 자동 활용)
MATCH (m:Movie)
WHERE m.plot_embedding IS NOT NULL
WITH m, vector.similarity.cosine(m.plot_embedding, $query_embedding) AS vec_score
ORDER BY vec_score DESC
LIMIT $vec_top_k

// 2) Keyword/Theme/Mood 부스트
OPTIONAL MATCH (m)-[:MENTIONS]->(k:Keyword)
WHERE k.normalized IN $query_keywords
WITH m, vec_score, count(DISTINCT k) AS kw_hits

OPTIONAL MATCH (m)-[:HAS_THEME]->(t:Theme)
WHERE t.name IN $query_themes
WITH m, vec_score, kw_hits, count(DISTINCT t) AS theme_hits

OPTIONAL MATCH (m)-[:HAS_MOOD]->(md:Mood)
WHERE md.name IN $query_moods
WITH m, vec_score, kw_hits, theme_hits, count(DISTINCT md) AS mood_hits

// 3) User preference 가중치 (선택)
OPTIONAL MATCH (u:User {user_id: $user_id})-[p:PREFERS]->(x)
WHERE x:Genre OR x:Theme OR x:Keyword
OPTIONAL MATCH (m)-[:HAS_GENRE|HAS_THEME|MENTIONS]->(x)
WITH m, vec_score, kw_hits, theme_hits, mood_hits,
     coalesce(sum(p.weight), 0.0) AS user_pref_score

// 4) 최종 스코어 산출 (가중 합)
WITH m,
     (0.55 * vec_score)
   + (0.15 * (1.0 - exp(-toFloat(kw_hits))))
   + (0.10 * (1.0 - exp(-toFloat(theme_hits))))
   + (0.05 * (1.0 - exp(-toFloat(mood_hits))))
   + (0.15 * tanh(user_pref_score)) AS score
ORDER BY score DESC
LIMIT $top_k

RETURN m.movie_id      AS movie_id,
       m.title         AS title,
       m.plot_summary  AS plot_summary,
       score
"""

HYBRID_MOVIE_RECOMMEND_WEIGHTED: Final[
    str
] = """
// 1) 후보군을 넉넉하게 확보 (vec_top_k * 버퍼 배수)
MATCH (m:Movie)
WHERE m.plot_embedding IS NOT NULL
WITH m, vector.similarity.cosine(m.plot_embedding, $query_embedding) AS vec_score
ORDER BY vec_score DESC
LIMIT toInteger($vec_top_k * 5)   -- ← 필터 손실 보정용 버퍼

// 2) toxicity 필터 (기존과 동일한 위치)
WITH m, vec_score
WHERE coalesce(m.toxicity_score, 0.0) <= $max_toxicity

// 3) Keyword / Theme / Mood 부스트
OPTIONAL MATCH (m)-[:MENTIONS]->(k:Keyword)
WHERE k.normalized IN $query_keywords
WITH m, vec_score, count(DISTINCT k) AS kw_hits

OPTIONAL MATCH (m)-[:HAS_THEME]->(t:Theme)
WHERE t.name IN $query_themes
WITH m, vec_score, kw_hits, count(DISTINCT t) AS theme_hits

OPTIONAL MATCH (m)-[:HAS_MOOD]->(md:Mood)
WHERE md.name IN $query_moods
WITH m, vec_score, kw_hits, theme_hits, count(DISTINCT md) AS mood_hits

// 4) User preference 가중치
OPTIONAL MATCH (u:User {user_id: $user_id})-[p:PREFERS]->(x)
WHERE x:Genre OR x:Theme OR x:Keyword
OPTIONAL MATCH (m)-[:HAS_GENRE|HAS_THEME|MENTIONS]->(x)
WITH m, vec_score, kw_hits, theme_hits, mood_hits,
     coalesce(sum(p.weight), 0.0) AS user_pref_score

// 5) 최종 스코어 산출
WITH m,
     ($w_vec   * vec_score)
   + ($w_kw    * (1.0 - exp(-toFloat(kw_hits))))
   + ($w_theme * (1.0 - exp(-toFloat(theme_hits))))
   + ($w_mood  * (1.0 - exp(-toFloat(mood_hits))))
   + ($w_user  * tanh(user_pref_score)) AS score
ORDER BY score DESC
LIMIT $top_k

RETURN m.movie_id     AS movie_id,
       m.title        AS title,
       m.plot_summary AS plot_summary,
       score
"""


__all__ = [
    "NODE_CONSTRAINTS",
    "NODE_PROPERTY_INDEXES",
    "FULLTEXT_INDEXES",
    "vector_index_statements",
    "SEED_CATEGORIES",
    "SEED_EMOTIONS",
    "SEED_MERGE_CATEGORY",
    "SEED_MERGE_EMOTION",
    "UPSERT_MOVIE_WITH_ONTOLOGY",
    "UPSERT_FEED_WITH_ONTOLOGY",
    "UPSERT_COMMENT_WITH_ONTOLOGY",
    "HYBRID_MOVIE_RECOMMEND",
    "HYBRID_MOVIE_RECOMMEND_WEIGHTED",
    "build_upsert_movie_with_ontology",
    "vector_index_statements_for_version",
]
