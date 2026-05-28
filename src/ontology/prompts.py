"""온톨로지 매핑 프롬프트.

LLM/SLM 에게 비정형 텍스트(영화 줄거리 / 피드 / 댓글) 를 입력해
`schema.py` 에 정의된 Pydantic 스키마와 1:1 로 매핑되는 JSON 을 생성하도록 한다.

설계 원칙
---------
- SRP: 본 모듈은 "프롬프트 텍스트" 만 책임진다. (호출/파싱은 extractor 의 책임)
- OCP: 프롬프트 변형이 필요할 경우 builder 함수를 추가해 확장한다. 기존 상수는 수정하지 않는다.
- DIP: extractor 는 본 모듈의 빌더 함수에만 의존하고, 내부 문자열 포맷에는 의존하지 않는다.

프롬프트 공통 규칙
------------------
1. 출력은 반드시 단일 JSON 객체. 코드블록(```) 금지. 설명/사족 금지.
2. 스키마에 없는 필드는 생성 금지. 누락 필드는 빈 배열/기본값으로 채운다.
3. semantic / keyword 양쪽이 균형되도록 keywords 는 정규화 표제어와 표면형을 모두 보존한다.
4. 한국어 원문은 한국어로 요약하되, 키워드 normalized 는 한국어 표제어로 통일한다.
5. 추정 불가/근거 없는 정보는 비워둔다(환각 금지).

vLLM prefix-cache 친화 설계
---------------------------
- 시스템 프롬프트는 user 와 무관하게 모든 호출에서 동일하게 유지(상수)되어야 한다.
- 그래야 vLLM 의 PagedAttention prefix-cache 가 KV-block 재사용을 극대화할 수 있다.
- 사용자/문서 의존적인 부분은 messages 의 user role 에만 배치한다.
"""

from __future__ import annotations

from textwrap import dedent
from typing import Final

# ---------------------------------------------------------------------------
# 공통 시스템 프롬프트 (prefix-cache friendly: 호출마다 동일)
# ---------------------------------------------------------------------------

ONTOLOGY_SYSTEM_PROMPT: Final[str] = dedent(
    """
    너는 영화/피드/댓글 텍스트를 지식그래프 온톨로지로 변환하는
    "Movie Knowledge Ontology Mapper" 다.

    [출력 원칙]
    1. 출력은 단일 JSON 객체. 코드펜스/주석/접두문장 금지.
    2. 스키마에 없는 키를 추가하지 말 것.
    3. 모든 필수 필드는 반드시 채우되, 모르면 빈 배열/기본값/빈 문자열 사용.
    4. 추측/환각 금지. 원문에서 직접 근거를 찾을 수 없는 정보는 추출하지 말 것.
    5. JSON 의 문자열 값에는 줄바꿈 대신 공백을 사용.

    [정규화 규칙]
    - keywords[*].term      : 원문 표면형 그대로(띄어쓰기 정리만).
    - keywords[*].normalized: 표제어. 동의어/표기 통일(예: "느와르"/"누아르" → "누아르").
    - 인물명은 "성+이름" 한국식 표기 우선. 영어 원어가 명확하면 영어 그대로.
    - 장르/테마/무드는 한국어 표제어로 통일.

    [semantic vs keyword 균형]
    - keywords.kind 는 다음 중 하나: entity/concept/theme/mood/trope/object/location/other.
    - semantic anchor 가 되는 추상 개념(theme/mood) 과
      검색 anchor 가 되는 구체 표현(entity/object/location) 을 모두 골고루 추출한다.
    - 한 문서당 keywords 는 5~15개를 권장한다(중요도 weight 로 가중).
    """
).strip()


# ---------------------------------------------------------------------------
# 1. Movie Plot Ontology 프롬프트
# ---------------------------------------------------------------------------

_MOVIE_PLOT_SCHEMA_HINT: Final[str] = dedent(
    """
    [출력 JSON 스키마]
    {
      "schema_version": "1.0",
      "source_id": "<movie_id>",
      "language": "ko",
      "summary": "<2~3문장 요약>",
      "themes": ["<주제 표제어>", ...],
      "moods": ["<분위기 표제어>", ...],
      "tropes": ["<트로프 식별자(snake_case)>", ...],
      "keywords": [
        {
          "term": "<원문 표면형>",
          "normalized": "<정규화 표제어>",
          "weight": 0.0~1.0,
          "kind": "entity|concept|theme|mood|trope|object|location|other"
        }, ...
      ],
      "characters": ["<역할/이름>", ...],
      "locations": ["<배경 시대/공간>", ...],
      "target_audience": ["family|teen|adult|cinephile|...", ...]
      "toxicity_score": 0.0~1.0
    }
    """
).strip()


_MOVIE_PLOT_GUIDE: Final[str] = dedent(
    """
    [Movie Plot 전용 가이드]
    - summary 는 줄거리의 인과(원인→사건→결말) 가 드러나도록 작성한다.
    - 단, 영화의 결말 spoiler 라 판단되는 경우 결말 표현은 추상화한다.
    - themes 는 인간 보편 주제(예: 복수/성장/사랑/구원/정체성/가족/계급).
    - moods 는 정서적 톤(예: 잔잔한/긴장감/몽환적/유머러스/비극적/희망적).
    - tropes 는 영화/장르 클리셰의 식별자. snake_case 로 통일.
      (예: time_loop, anti_hero, found_family, redemption_arc)
    - keywords.kind 분포 가이드:
        theme/mood 합쳐 30~40%,
        entity(인물/단체)/location/object 합쳐 40~50%,
    - toxicity_score 는 욕설/공격성/혐오표현 수위(0.1~1.0).
    """
).strip()


def build_movie_plot_messages(
    *,
    movie_id: str,
    title: str,
    producing_year: int | None,
    country: str | None,
    genres: list[str] | None,
    plot: str,
) -> list[dict[str, str]]:
    """영화 줄거리 → MoviePlotOntology 매핑용 messages 생성.

    Args:
        movie_id: 영화 고유 ID. 결과 JSON 의 source_id 로 들어간다.
        title: 영화 제목.
        producing_year: 제작연도(없으면 None).
        country: 제작국가(없으면 None).
        genres: TMDB/KMDB 의 장르명 리스트.
        plot: 정제 대상이 되는 짧은 줄거리 원문.

    Returns:
        OpenAI/vLLM Chat Completions 호환 messages 리스트.
    """

    user_payload = dedent(
        f"""
        [영화 메타]
        - movie_id      : {movie_id}
        - title         : {title}
        - producing_year: {producing_year if producing_year is not None else "unknown"}
        - country       : {country or "unknown"}
        - genres        : {", ".join(genres) if genres else "unknown"}

        [원문 줄거리]
        \"\"\"
        {plot.strip()}
        \"\"\"

        {_MOVIE_PLOT_GUIDE}

        {_MOVIE_PLOT_SCHEMA_HINT}

        위 스키마에 정확히 맞춘 JSON 만 출력하라.
        """
    ).strip()

    return [
        {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
        {"role": "user", "content": user_payload},
    ]


# ---------------------------------------------------------------------------
# 2. Feed Ontology 프롬프트
# ---------------------------------------------------------------------------


_FEED_SCHEMA_HINT: Final[str] = dedent(
    """
    [출력 JSON 스키마]
    {
      "schema_version": "1.0",
      "source_id": "<feed_id>",
      "language": "ko",
      "summary": "<1~2문장 요약>",
      "categories": ["review|recommendation|question|discussion|news|spoiler|theory|comparison|meta|off_topic", ...],
      "sentiment": "very_negative|negative|neutral|positive|very_positive",
      "sentiment_score": -1.0~1.0,
      "emotions": [
        {"tag": "joy|sadness|anger|fear|disgust|surprise|nostalgia|empathy|excitement|boredom|confusion|admiration",
         "score": 0.0~1.0}, ...
      ],
      "keywords": [
        {"term": "...", "normalized": "...", "weight": 0.0~1.0,
         "kind": "entity|concept|theme|mood|trope|object|location|other"}, ...
      ],
      "referenced_movie_ids": ["<movie_id>", ...],
      "referenced_person_names": ["<감독/배우 등>", ...],
      "contains_spoiler": true|false,
      "toxicity_score": 0.0~1.0
    }
    """
).strip()


_FEED_GUIDE: Final[str] = dedent(
    """
    [Feed 전용 가이드]
    - categories 는 다중 선택 가능. 명백히 1개라면 1개만 선택.
    - sentiment_score 와 sentiment 는 일관되어야 한다.
        very_negative ≈ -1.0 ~ -0.6
        negative      ≈ -0.6 ~ -0.2
        neutral       ≈ -0.2 ~ +0.2
        positive      ≈ +0.2 ~ +0.6
        very_positive ≈ +0.6 ~ +1.0
    - emotions 는 본문에서 명확히 드러난 감정 1~5개만 선택. 점수는 강도.
    - referenced_movie_ids 는 입력 메타의 known_movie_ids 에 포함된 ID 만 사용한다.
      메타에 없는 영화는 referenced_person_names 또는 keywords 로 처리.
    - contains_spoiler: 결말/반전을 직접 서술하면 true.
    - toxicity_score: 욕설/공격성/혐오표현 수위.
    """
).strip()


def build_feed_messages(
    *,
    feed_id: str,
    author_id: str,
    related_movie_id: str | None,
    known_movie_ids: list[str] | None,
    content: str,
) -> list[dict[str, str]]:
    """피드 본문 → FeedOntology 매핑용 messages.

    Args:
        feed_id: 피드 고유 ID.
        author_id: 작성자 user_id.
        related_movie_id: 피드가 명시적으로 연결한 영화 ID (있으면).
        known_movie_ids: 본문에서 참조 가능한 후보 movie_id 들(검색기로 사전 매칭한 결과).
        content: 정제 대상 피드 본문.
    """

    user_payload = dedent(
        f"""
        [피드 메타]
        - feed_id          : {feed_id}
        - author_id        : {author_id}
        - related_movie_id : {related_movie_id or "none"}
        - known_movie_ids  : {", ".join(known_movie_ids) if known_movie_ids else "none"}

        [원문 본문]
        \"\"\"
        {content.strip()}
        \"\"\"

        {_FEED_GUIDE}

        {_FEED_SCHEMA_HINT}

        위 스키마에 정확히 맞춘 JSON 만 출력하라.
        """
    ).strip()

    return [
        {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
        {"role": "user", "content": user_payload},
    ]


# ---------------------------------------------------------------------------
# 3. Comment Ontology 프롬프트
# ---------------------------------------------------------------------------


_COMMENT_SCHEMA_HINT: Final[str] = dedent(
    """
    [출력 JSON 스키마]
    {
      "schema_version": "1.0",
      "source_id": "<comment_id>",
      "language": "ko",
      "summary": "<1문장 요약>",
      "intents": ["agree|disagree|question|answer|recommend|critique|appreciation|joke|spoiler_warning|off_topic", ...],
      "sentiment": "very_negative|negative|neutral|positive|very_positive",
      "sentiment_score": -1.0~1.0,
      "emotions": [{"tag": "<EmotionTag>", "score": 0.0~1.0}, ...],
      "keywords": [{"term": "...", "normalized": "...", "weight": 0.0~1.0, "kind": "..."}],
      "targets_user_id": "<user_id 또는 null>",
      "contains_spoiler": true|false,
      "toxicity_score": 0.0~1.0
    }
    """
).strip()


_COMMENT_GUIDE: Final[str] = dedent(
    """
    [Comment 전용 가이드]
    - 댓글은 짧을 수 있으므로 summary 는 원문이 1문장이면 원문을 그대로 사용해도 된다.
    - intents 다중 선택 가능. 의문문이면 question, "동의/공감" 표현이면 agree.
    - 다른 사용자(@언급/대댓글) 를 향한 경우 targets_user_id 를 채운다.
      mentioned_user_ids 메타에 후보가 있는 경우 그 중에서만 선택.
    - keywords 는 5개를 넘기지 않는다(짧은 텍스트에 과추출 금지).
    """
).strip()


def build_comment_messages(
    *,
    comment_id: str,
    feed_id: str,
    author_id: str,
    mentioned_user_ids: list[str] | None,
    parent_feed_summary: str | None,
    content: str,
) -> list[dict[str, str]]:
    """댓글 본문 → CommentOntology 매핑용 messages.

    Args:
        comment_id: 댓글 ID.
        feed_id: 부모 피드 ID.
        author_id: 댓글 작성자.
        mentioned_user_ids: @멘션된 후보 user_id 목록.
        parent_feed_summary: 부모 피드의 정제 요약(맥락 보강용). 없으면 None.
        content: 댓글 원문.
    """

    user_payload = dedent(
        f"""
        [댓글 메타]
        - comment_id        : {comment_id}
        - feed_id           : {feed_id}
        - author_id         : {author_id}
        - mentioned_user_ids: {", ".join(mentioned_user_ids) if mentioned_user_ids else "none"}

        [부모 피드 요약(맥락)]
        {parent_feed_summary or "(none)"}

        [원문 댓글]
        \"\"\"
        {content.strip()}
        \"\"\"

        {_COMMENT_GUIDE}

        {_COMMENT_SCHEMA_HINT}

        위 스키마에 정확히 맞춘 JSON 만 출력하라.
        """
    ).strip()

    return [
        {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
        {"role": "user", "content": user_payload},
    ]


# ---------------------------------------------------------------------------
# 4. (선택) 사용자 의도 → Cypher 매핑 프롬프트
# ---------------------------------------------------------------------------

USER_INTENT_TO_CYPHER_SYSTEM_PROMPT: Final[str] = dedent(
    """
    너는 사용자의 자연어 추천 요청을, 미리 등록된 Cypher 템플릿 중 하나를 선택하고
  파라미터만 채우는 "Recommendation Template Planner" 다.
  raw Cypher 를 직접 작성하지 마라.

    [등록된 template_id]
    - hybrid_recommend: 영화 하이브리드 추천 (기본)
    - feed_about_movie: 특정 영화 관련 피드
    - similar_movie_by_theme: 테마 유사 영화
    - recent_feeds_positive: 긍정 피드 최신순
    - user_preference_summary: 사용자 선호 요약

    [출력 규칙]
    - 출력은 단일 JSON:
      {"template_id": "...", "params": {...}, "reasoning": "..."}
    - params 의 키는 템플릿이 요구하는 이름만 사용.
    - hybrid_recommend 기본 params 예:
      user_id, query_embedding (float[]), query_keywords, query_themes,
      query_moods, top_k, vec_top_k, w_vec, w_kw, w_theme, w_mood, w_user
    - 모르는 값은 빈 리스트/기본 가중치로 채운다.
    """
).strip()


def build_user_intent_messages(
    *,
    user_id: str,
    user_query: str,
    top_k: int = 20,
) -> list[dict[str, str]]:
    """사용자 자연어 추천 요청 → Cypher 변환 messages."""

    user_payload = dedent(
        f"""
        [요청]
        - user_id : {user_id}
        - top_k   : {top_k}
        - query   : "{user_query.strip()}"

        위 요청에 맞는 template_id 와 params 를 JSON 으로 반환하라.
        영화 추천이면 hybrid_recommend 를 우선 선택하라.
        """
    ).strip()

    return [
        {"role": "system", "content": USER_INTENT_TO_CYPHER_SYSTEM_PROMPT},
        {"role": "user", "content": user_payload},
    ]


__all__ = [
    "ONTOLOGY_SYSTEM_PROMPT",
    "USER_INTENT_TO_CYPHER_SYSTEM_PROMPT",
    "build_movie_plot_messages",
    "build_feed_messages",
    "build_comment_messages",
    "build_user_intent_messages",
]
