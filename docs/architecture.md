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

    subgraph API["FastAPI Gateway\nroot_path=/chat-api"]
        ChatAPI["/chat/* (LangGraph SSE)"]
        RecAPI["/recommend/movie · /recommend/feed"]
        IngestAPI["/ingest/*"]
        FbAPI["/feedback"]
    end

    subgraph LLM["LLM Layer (vLLM)"]
        VLLM["vLLM Server\n(KV-cache + PagedAttention\n+ Prefix Caching)"]
        Embed["Embedding Model\n(Qwen3-Embedding-0.6B)"]
    end

    subgraph Graph["Knowledge Layer"]
        Neo4j[("Neo4j 5.x\n(Graph + Vector + Fulltext)")]
    end

    subgraph State["State Layer"]
        Postgres[("PostgreSQL\n- chat_session (persona_id)\n- chat_message (persona_id)\n- bandit_state (context_key)\n- ingest_outbox\n- LangGraph checkpoint")]
    end

    subgraph ETL["Ontology ETL (Outbox Worker)"]
        Movie["Movie Plot\nExtractor"]
        FeedX["Feed Extractor"]
        CmtX["Comment Extractor"]
        Loader["Neo4j Loader"]
    end

    WebApp -->|REST/SSE| ChatAPI
    WebApp --> RecAPI
    WebApp --> IngestAPI
    WebApp --> FbAPI

    ChatAPI --> VLLM
    ChatAPI --> Neo4j
    ChatAPI --> Postgres

    RecAPI --> Neo4j
    RecAPI --> Embed
    RecAPI --> Postgres

    IngestAPI -->|enqueue| Postgres
    Postgres --> ETL
    ETL --> VLLM
    ETL --> Embed
    ETL --> Loader
    Loader --> Neo4j

    FbAPI --> Postgres
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

    subgraph Prompt["Ontology Mapping Prompt\n(src/ontology/prompts/)"]
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

Ingest API 는 `ingest_outbox` 에만 적재하고, 실제 ETL 은 [Outbox Worker](outbox_ingest.md) 가 비동기 수행한다.

---

## 3. 사용자 Chat 흐름 (LangGraph)

`src/chat/graph.py` 의 StateGraph 노드 시퀀스:

```
START → embed_query → agent
                         ├─ (tool_calls) → neo4j_tools → agent  (루프, max 15)
                         └─ (no tools)   → persist_history → END
```

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as POST /chat/stream
    participant LG as LangGraph (StateGraph)
    participant PG as PostgreSQL (chat_message + checkpoint)
    participant VL as vLLM (prefix-cache)
    participant NEO as Neo4j (GraphCypherQAChain)
    participant EMB as Embedding

    U->>API: query + persona_id (SSE)
    API->>PG: open_session + append(user message)
    API->>LG: astream(state, thread_id=session_id)

    LG->>EMB: embed_query
    LG->>VL: agent (tool-calling LLM)

    alt Neo4j 조회 필요
        LG->>NEO: query_neo4j_graph (CyVer 검증)
        NEO-->>LG: retrieved_movies / retrieved_feeds
        LG->>VL: agent (재호출, max 15)
    end

    LG->>VL: build_structured_reply (intent_scope별 JSON)
    LG->>PG: persist_history (ontology_ref)
    LG-->>API: partial state (SSE node events)
    API-->>U: event:done
```

- **agent** : `query_neo4j_graph` tool 이 필요할 때만 Neo4j 조회. 단순 인사는 tool 없이 종료.
- **neo4j_tools** : `Neo4jCypherService` (`GraphCypherQAChain` + CyVer) — read-only Cypher 생성·실행.
- **persist_history** : `build_structured_reply` 결과를 `chat_message` 에 저장.

체크포인트는 `langgraph-checkpoint-postgres` 의 `PostgresSaver` 가 담당하며,
세션별 thread_id = `session_id` 규약을 따른다.

> Chat 은 Bandit arm 을 직접 선택하지 않는다. 하이브리드 가중치 학습은 `/recommend/*` + `/feedback` 경로에서 수행한다.

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
    Q --> E["Query Embedding\n(Qwen3-Embedding)"]
    Q --> KW["Keyword/Theme/Mood 추출\n(IntentResolver)"]

    E --> V["Vector Search\n(plot_embedding / summary_embedding)"]
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

    B["Bandit arm\n(w_vec … w_user)"] --> S

    V --> S["가중합 스코어"]
    KS --> S
    TM --> S
    PersonaPref --> S
    UserFallback --> S

    S --> R["Top-K\n(Movie / Feed)"]
```

### 5-1. Cypher 실행 경로

| 경로 | Cypher 생성 | 템플릿 |
|------|-------------|--------|
| `/recommend/movie` | `TemplateExecutor` | `hybrid_recommend` |
| `/recommend/feed` | `TemplateExecutor` | `hybrid_feed_recommend` |
| Chat (`/chat/stream`) | `GraphCypherQAChain` | read-only, CyVer 검증 |

### 5-2. 도메인별 Persona 파생

| 도메인 | 엔드포인트 | Persona 역할 |
|--------|-----------|--------------|
| Chat | `/chat/stream` | 세션 이력·체크포인트 스코프. Neo4j 조회는 Agent tool |
| Movie | `/recommend/movie` | Bandit arm + hybrid Cypher `$persona_id` |
| Feed | `/recommend/feed` | Bandit arm + hybrid feed Cypher `$persona_id` |
| Ingest | `/ingest/feed`, `/ingest/comment` | `WRITTEN_BY` Persona, Persona-scoped `INTERACTED` |
| Feedback | `/feedback` | `context_key = user_id:persona_id` posterior 갱신 |
