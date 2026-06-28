# 기술 스택 요약 (장표)

> 근거: [architecture.md](architecture.md), [README.md](../README.md), [api.md](api.md), [neo4j_schema.md](neo4j_schema.md), [ontology.md](ontology.md), [persona_recommendation.md](persona_recommendation.md) 및 기타 `docs/` 문서.

---

## 1. ML / LLM

- **Qwen (생성 모델)**
  - 운영: `Qwen3-8B-GGUF:Q4_K_M` (vLLM `:8000`) — 로컬 T4 16GB 기준
  - 역할: 영화·피드·댓글 → 온톨로지 JSON 추출, Chat Agent(tool calling), structured reply 생성
  - Chat Cypher 생성: `GraphCypherQAChain` 전용 LLM (`enable_thinking=False`)
  - 이유: 한국어 도메인 지시 따르기·JSON guided decoding에 적합, 온톨로지 시스템 프롬프트를 **불변 prefix**로 두어 vLLM prefix-cache 재사용 ([architecture.md](architecture.md) §4)
- **vLLM**
  - PagedAttention·Prefix Caching·Chunked Prefill로 KV-cache 메모리 절감·TTFT 단축
  - OpenAI 호환 API로 `VLLMChatClient` / LangChain `ChatOpenAI` 단일 추상화
- **Qwen3-Embedding-0.6B (임베딩)**
  - `:8001` 별도 서빙, 1024차원 — `plot_summary`·`feed/comment summary`·질의 벡터화
  - 이유: semantic 검색(하이브리드 score의 `w_vec`)과 다국어 문장 표현에 사용
- **LangGraph**
  - `StateGraph`: `embed_query` → `agent` ⇄ `neo4j_tools` → `persist_history`
  - Chat Agent 가 필요 시 `query_neo4j_graph` tool 로 Neo4j read-only 조회
  - structured reply 는 `build_structured_reply` (`ontology/prompts/reply.py`)
  - 이유: 채팅 단계를 명시적 상태 기계로 분리, `(user_id, persona_id)` + `session_id` 체크포인트
- **Pydantic + 프롬프트 (`ontology/`)**
  - `MoviePlotOntology` / `FeedOntology` / `CommentOntology` 검증, 환각·스키마 이탈 방지
  - 이유: 비정형 → 지식그래프 적재 전 **단일 표상 체계** 보장 ([ontology.md](ontology.md))

---

## 2. API / 애플리케이션

- **FastAPI** (`root_path=/chat-api`)
  - `/chat/stream`, `/chat/list`, `/chat/history/{session_id}`
  - `/recommend/movie`, `/recommend/feed`
  - `/ingest/*`, `/feedback`, `/healthz`
  - 이유: LangGraph·Neo4j·Outbox를 얇은 HTTP 게이트웨이로 노출 ([api.md](api.md))
- **LangChain (연동)**
  - `GraphCypherQAChain`, `ChatOpenAI`, CyVer Cypher 검증 — Chat Neo4j tool 파이프라인

---

## 3. 지식·추천 (GraphRAG)

- **Neo4j 5.x**
  - 그래프 + 벡터 인덱스 + 풀텍스트 — `Movie`·`Feed`·`User`·`Persona`·`Theme`/`Mood`/`Keyword` 등
  - 이유: semantic × keyword × graph **하이브리드 추천** + **Persona-scoped** 선호·상호작용을 한 저장소에서 Cypher로 표현
- **Cypher Template Registry** (Recommend API 전용)
  - 등록 템플릿 2종: `hybrid_recommend`, `hybrid_feed_recommend`
  - `TemplateExecutor` 가 파라미터 검증 후 실행, 실패 시 `hybrid_recommend` fallback
  - 이유: injection·쿼리 폭주 방지, 운영 가능한 고정 쿼리 세트 ([cypher_templates.md](cypher_templates.md))
- **GraphCypherQAChain** (Chat 전용)
  - LLM 이 read-only Cypher 생성 → CyVer 검증 → Neo4j 실행
  - write 키워드(`CREATE`, `MERGE`, `DELETE` 등) 차단
- **Thompson Bandit (`RecommendPolicy`)**
  - 6 arms: `baseline`, `vec_heavy`, `kw_heavy`, `user_heavy`, `balanced`, `theme_mood`
  - `w_vec, w_kw, w_theme, w_mood, w_user` arm 샘플링, `/feedback`으로 α/β 갱신
  - `context_key = user_id:persona_id` — Persona 별 posterior 분리
  - 이유: **Persona** 맥락별 하이브리드 가중치를 온라인 학습 ([bandit_weights.md](bandit_weights.md))
- **IntentResolver** (Recommend API)
  - 룰 기반 token 매칭 + (선택) embedding nearest-neighbor — LLM query analyzer 대체
  - 질의 → `(keywords, themes, moods)` 정규화 토큰 추출
- **Auto Vocabulary (`VocabPipeline`)**
  - 추출 어휘 → 표준 `Theme`/`Mood` 또는 `CandidateTerm` → 야간 승격
  - 이유: LLM 개방 어휘를 그래프 앵커(Enum)와 점진적으로 정렬 ([auto_vocab.md](auto_vocab.md))

---

## 4. 상태·영속화

- **PostgreSQL**
  - `chat_session` / `chat_message` — **persona_id** 기준 세션·대화 이력 격리
  - `langgraph-checkpoint-postgres` (`PostgresSaver`) — LangGraph 체크포인트
  - `ingest_outbox` / `ingest_dlq` — 온톨로지 ETL **트랜잭션 아웃박스** 큐
  - `eval_score`, Bandit posterior (`bandit_state`) — 평가·정책 write-through
  - 이유: 그래프(Neo4j)와 **세션·큐·학습 상태** 분리, API는 enqueue만 하고 worker가 비동기 적재
- **Versioned Embedding**
  - `plot_embedding_v1`, `v2`… + active/shadow dual-write → Recall@K 후 승격
  - feed/comment `summary_embedding_vN` 도 동일 패턴
  - 이유: 임베딩 모델 교체 시 무중단·오프라인 검증 후 전환 ([versioned_embedding.md](versioned_embedding.md))

---

## 5. ETL·운영·품질

- **Outbox Ingest Worker**
  - `FOR UPDATE SKIP LOCKED` 폴링, `prompt_version` 불일치 시 재 enqueue, 3회 실패 DLQ
  - aggregate: movie/feed/comment + like/delete/judge + user/persona + reembed
  - 이유: ingest API 응답 지연·LLM 장시간 작업을 백그라운드로 격리 ([outbox_ingest.md](outbox_ingest.md))
- **Ontology ETL 파이프라인**
  - 비정형 → 프롬프트 → vLLM JSON → Pydantic → 임베딩 → Neo4j MERGE ([architecture.md](architecture.md) §2)
- **LLM Judge & Drift**
  - Goldenset 샘플·vLLM 채점·KL/cos_sim 알람
  - 이유: 온톨로지 품질·키워드 분포 드리프트 조기 감지 ([llm_judge.md](llm_judge.md))

---

## 6. 한 줄 아키텍처

```
Client → FastAPI → LangGraph (Chat) / TemplateExecutor (Recommend) → (vLLM + Embedding + Neo4j + Postgres)
              └→ Outbox Worker → Extractor/Loader → Neo4j
```

**핵심 설계 의도**: 비정형을 **온톨로지·지식그래프**로 올린 뒤, 벡터·키워드·그래프·Persona 선호를 가중합하고, LLM은 구조화 추출·Chat Agent·추천 **근거 설명**에 쓴다.
