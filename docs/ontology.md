# 온톨로지 매핑 정책

> LLM/SLM 으로 비정형 텍스트 3종(영화 줄거리 / 피드 / 댓글)을
> 동일한 표상 체계로 끌어올리기 위한 **온톨로지 매핑 정책**.

---

## 1. 정제 대상과 목표

| 대상 | 입력 | 정제 목표 | 출력 스키마 |
|------|------|-----------|--------------|
| 영화 줄거리 | `movie.plot` (단문) | 의미 보존 요약 + 테마/무드/키워드 | `MoviePlotOntology` |
| 피드 본문   | `feed.content` (비정형) | 카테고리 + 감정 + 키워드 + 참조 영화 | `FeedOntology` |
| 댓글 본문   | `comment.content` (비정형, 짧음) | 의도 + 감정 + 키워드 | `CommentOntology` |

> Ingest 시 `persona_id` 는 온톨로지 스키마가 아닌 **적재 메타** 로 전달되며,
> Neo4j 에서 `(:Persona)` 와 `WRITTEN_BY` 관계를 형성한다.
> 추천은 `(user_id, persona_id)` 기준으로 Persona 선호를 사용한다.
> 상세: [persona_recommendation.md](persona_recommendation.md)

> 세 결과는 모두 `OntologyResult` 를 상속해 동일한 메타(`source_id`, `language`, `schema_version`)를 가진다.

---

## 2. semantic ⇄ keyword 균형 전략

```mermaid
flowchart LR
    Raw["원문(비정형)"] --> Sem["Semantic 추출\n- summary\n- themes\n- moods\n- sentiment\n- intents"]
    Raw --> Key["Keyword 추출\n- entity (인물/장소/사물)\n- concept (정규화 표제어)\n- trope (snake_case)"]

    Sem --> Anchor["공통 Anchor 노드\n(:Theme/:Mood/:Category/:Emotion)"]
    Key --> Anchor2["(:Keyword {normalized,kind})"]

    Anchor --> KG[("Neo4j Knowledge Graph")]
    Anchor2 --> KG
```

- **Semantic anchor** 는 폐쇄형(Enum) 으로 강제해 휘발성/엔트로피를 낮춘다.
  - Sentiment 5단계, EmotionTag, FeedCategory, CommentIntent
- **Keyword anchor** 는 개방형(자유 어휘) 이되 `normalized` 로 동의어를 통합한다.
  - `kind` 로 종류를 분류해 검색/추천에서 가중치 차등 적용.

---

## 3. 프롬프트 모듈 구성

`src/ontology/prompts.py`

```mermaid
classDiagram
    class ONTOLOGY_SYSTEM_PROMPT {
        <<constant>>
        +출력 원칙
        +정규화 규칙
        +semantic/keyword 균형 규칙
    }

    class build_movie_plot_messages {
        +movie_id
        +title
        +producing_year
        +country
        +genres
        +plot
    }
    class build_feed_messages {
        +feed_id
        +user_id
        +persona_id
        +related_movie_id
        +known_movie_ids
        +content
    }
    class build_comment_messages {
        +comment_id
        +feed_id
        +user_id
        +persona_id
        +mentioned_user_ids
        +parent_feed_summary
        +content
    }
    class build_user_intent_messages {
        +user_id
        +persona_id
        +user_query
        +top_k
    }

    ONTOLOGY_SYSTEM_PROMPT <.. build_movie_plot_messages : reuses
    ONTOLOGY_SYSTEM_PROMPT <.. build_feed_messages       : reuses
    ONTOLOGY_SYSTEM_PROMPT <.. build_comment_messages    : reuses
```

> 핵심: **system role 은 모든 호출에서 동일한 상수**.
> 이는 vLLM PagedAttention prefix cache hit rate 를 끌어올리는 핵심 설계 결정이다.

---

## 4. 검증 흐름

```mermaid
sequenceDiagram
    participant App as Extractor
    participant V as vLLM (JSON mode)
    participant Py as Pydantic Validator
    participant Fix as Lenient Fallback

    App->>V: messages (system + user)
    V-->>App: JSON text
    App->>Py: model_validate(raw)
    alt 검증 성공
        Py-->>App: Ontology 객체
    else 검증 실패
        App->>Fix: 알려진 필드만 추려 재검증
        alt 재검증 성공
            Fix-->>App: Ontology 객체
        else 재검증 실패
            Fix-->>App: 원본 예외 재발생 + 원문 로깅
        end
    end
```

---

## 5. 운영 시 유의사항

- **schema_version** 은 1.0 으로 고정. 스키마 변경 시 bump 후 마이그레이션 스크립트 실행.
- **LLM 호출 격리**: extractor 는 단일 LLM 호출만 한다 (cost / latency 예측성 확보).
- **PII / Toxicity**: `toxicity_score` 가 임계값(예: 0.7)을 넘는 피드/댓글은
  추천 그래프에서 가중치 0으로 처리하거나 별도 큐로 보낸다.
- **Spoiler**: `contains_spoiler == true` 인 피드는 기본 추천에서 dim/exclude.
