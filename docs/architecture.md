# 시스템 아키텍처

> Knowledge-graph 기반 영화/피드 추천 + LLM Chat 서비스의 전체 아키텍처.
> 모든 다이어그램은 Mermaid 로 작성한다.

---

## 1. High-Level Component View

```mermaid
flowchart LR
    subgraph Client["Client"]
        WebApp["Web / Mobile App"]
    end

    subgraph API["FastAPI Gateway"]
        ChatAPI["/chat (LangGraph)"]
        FeedAPI["/feed/recommend"]
        IngestAPI["/ingest"]
    end

    subgraph LLM["LLM Layer (vLLM)"]
        VLLM["vLLM Server\n(KV-cache + PagedAttention\n+ Prefix Caching)"]
        Embed["Embedding Model\n(BGE-M3 등)"]
    end

    subgraph Graph["Knowledge Layer"]
        Neo4j[("Neo4j 5.x\n(Graph + Vector + Fulltext)")]
    end

    subgraph State["State Layer"]
        Postgres[("PostgreSQL\n- chat_session (persona_id)\n- chat_message (persona_id)\n- bandit_state (context_key)\n- LangGraph checkpoint")]
    end

    subgraph ETL["Ontology ETL"]
        Movie["Movie Plot\nExtractor"]
        FeedX["Feed Extractor"]
        CmtX["Comment Extractor"]
        Loader["Neo4j Loader"]
    end

    WebApp -->|REST/WebSocket| ChatAPI
    WebApp --> FeedAPI
    WebApp --> IngestAPI

    ChatAPI --> VLLM
    ChatAPI --> Neo4j
    ChatAPI --> Postgres

    FeedAPI --> Neo4j
    FeedAPI --> Embed

    IngestAPI --> Movie
    IngestAPI --> FeedX
    IngestAPI --> CmtX
    Movie --> VLLM
    FeedX --> VLLM
    CmtX --> VLLM
    Movie --> Embed
    FeedX --> Embed
    CmtX --> Embed
    Movie --> Loader
    FeedX --> Loader
    CmtX --> Loader
    Loader --> Neo4j
```

---

## 2. 온톨로지 ETL 파이프라인 (비정형 → 지식그래프)

```mermaid
flowchart TB
    subgraph Source["Raw Source"]
        S1["영화 메타 + 줄거리(plot)"]
        S2["피드 본문(content)"]
        S3["댓글 본문(content)"]
    end

    subgraph Prompt["Ontology Mapping Prompt"]
        P1["build_movie_plot_messages"]
        P2["build_feed_messages"]
        P3["build_comment_messages"]
    end

    subgraph Model["LLM (vLLM)"]
        L1["Ontology Mapper\n(JSON guided decoding)"]
    end

    subgraph Schema["Pydantic 스키마 검증"]
        V1["MoviePlotOntology"]
        V2["FeedOntology"]
        V3["CommentOntology"]
    end

    subgraph Embed["Embedding"]
        E1["plot_summary → vec"]
        E2["feed.summary → vec"]
        E3["comment.summary → vec"]
    end

    subgraph Load["Neo4j Upsert"]
        U1["MERGE (:Movie)+Rels"]
        U2["MERGE (:Feed)+Rels"]
        U3["MERGE (:Comment)+Rels"]
    end

    S1 --> P1 --> L1
    S2 --> P2 --> L1
    S3 --> P3 --> L1

    L1 --> V1 --> E1 --> U1
    L1 --> V2 --> E2 --> U2
    L1 --> V3 --> E3 --> U3

    U1 --> Neo4j[("Neo4j")]
    U2 --> Neo4j
    U3 --> Neo4j
```

---

## 3. 사용자 Chat 흐름 (LangGraph)

`src/chat/graph.py` 의 StateGraph 노드 시퀀스는 다음과 같다.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as FastAPI /chat
    participant LG as LangGraph (StateGraph)
    participant PG as PostgreSQL (chat_message + checkpoint)
    participant VL as vLLM (prefix-cache)
    participant NEO as Neo4j
    participant EMB as Embedding

    U->>API: query "감성적인 한국 영화 추천해줘"<br/>+ persona_id (선택)
    API->>PG: open_session(user_id, persona_id) + append(user message)
    API->>LG: invoke(state{user_id, persona_id, session_id, query})

    LG->>EMB: embed_query
    LG->>LG: plan_intent (IntentResolver: vocab + NN)
    LG->>LG: select_weights (context_key = user_id:persona_id)
    LG->>NEO: retrieve_movies (Persona-scoped hybrid_recommend)
    NEO-->>LG: top-K movies

    LG->>VL: generate_reply (vLLM JSON mode)
    VL-->>LG: assistant text

    LG->>PG: persist_history(ontology_ref={arm_id,movie_ids,themes})
    LG-->>API: final state (reply, arm_id, retrieved)
    API-->>U: ChatResponse
```

체크포인트는 `langgraph-checkpoint-postgres` 의 `PostgresSaver` 가 담당하며,
세션별 thread_id = `session_id` 규약을 따른다.

---

## 4. vLLM KV-Cache 재사용 전략

```mermaid
flowchart LR
    subgraph Prefix["고정 Prefix (호출 간 동일)"]
        SP["System Prompt\n(ONTOLOGY_SYSTEM_PROMPT)"]
        UP["Persona Prefix\n(user_id + persona_id 기반 안정 prefix)"]
    end

    subgraph Variable["가변 Suffix"]
        Q["Per-call Query\n(영화메타/피드/댓글/대화)"]
    end

    SP -- block 0~N --> KV["KV Cache\n(PagedAttention blocks)"]
    UP -- block N+1 --> KV
    Q  -- 가변 영역 --> KV

    KV -- 동일 prefix 재사용 --> Reuse["같은 user/system 의 다음 호출\n→ block reuse → TTFT 감소"]
```

> **운영 가이드**
> - vLLM 실행 시 `--enable-prefix-caching --enable-chunked-prefill` 옵션 필수.
> - 시스템 프롬프트(`ONTOLOGY_SYSTEM_PROMPT`) 는 **불변 상수**로 유지.
> - 사용자별 가변 정보(피드/영화 메타)는 user role 메시지의 **뒤쪽**에 배치.
> - `user_id` 를 OpenAI 호환 `user` 필드로 전달해 서버 사이드 로깅/라우팅을 잡는다.

---

## 5. 추천 알고리즘 (Hybrid: Semantic × Keyword × Graph × Persona)

> Persona 는 추천의 **최소 단위**이다. `(user_id, persona_id)` 로 선호·Bandit·세션이 스코프된다.
> 상세: [persona_recommendation.md](persona_recommendation.md)

```mermaid
flowchart TB
    Q["사용자 질의 / 컨텍스트\n(user_id + persona_id)"]
    Q --> E["Query Embedding\n(BGE-M3)"]
    Q --> KW["Keyword/Theme/Mood 추출\n(IntentResolver)"]

    E --> V["Vector Search\n(movie_plot_vec)"]
    KW --> KS["Keyword Match\n(:MENTIONS via Keyword)"]
    KW --> TM["Theme/Mood Match"]

    subgraph PersonaPref["Persona 선호도\n(persona_id 존재 시)"]
        P1["(:Persona)-[:PREFERS]"]
        P2["(:Persona)-[:INTERACTED]"]
    end

    subgraph UserFallback["Fallback\n(persona_id 없음)"]
        U1["(:User)-[:PREFERS]"]
        U2["(:User)-[:INTERACTED]"]
    end

    V --> S["가중합 스코어\nBandit arm 가중치 적용\n(w_vec, w_kw, w_theme, w_mood, w_user)"]
    KS --> S
    TM --> S
    PersonaPref --> S
    UserFallback --> S

    S --> R["Top-K\n(Movie / Feed / Comment)"]
```

### 5-1. 도메인별 Persona 파생

| 도메인 | 엔드포인트 | Persona 역할 |
|--------|-----------|--------------|
| Chat | `/chat` | LangGraph `select_weights` + `retrieve_movies` + 세션 이력 |
| Movie | `/recommend` | Bandit arm + hybrid Cypher `$persona_id` |
| Feed | `/ingest/feed` + 랭킹 | `WRITTEN_BY` Persona, Persona-scoped `INTERACTED` |
| Comment | `/ingest/comment` + 랭킹 | Persona affinity + intent/sentiment 부스트 |
| Feedback | `/feedback` | `context_key = user_id:persona_id` posterior 갱신 |
