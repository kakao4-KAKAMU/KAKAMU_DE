# LLM Judge & Drift Monitoring

Daily golden-set sampling, vLLM-based ontology quality scoring, PostgreSQL persistence, and drift alarms.

---

## Flow

```mermaid
flowchart LR
    GS[(goldenset_sample.jsonl)]
    JR[JudgeRunner]
    VLLM[VLLMChatClient]
    PG[(eval_score)]
    DD[DriftDetector]
    AL[Alarm / Slack]

    GS -->|daily sample| JR
    JR -->|chat_json + schema| VLLM
    VLLM -->|themes/sentiment 0-1| JR
    JR -->|insert_score| PG
    PG -->|keyword history| DD
    DD -->|KL, fail_rate, cos_sim| AL
```

---

## Components

| Module | Role |
|--------|------|
| `src/eval/judge_prompts.py` | System prompt + JSON schema (schema/themes/sentiment 0–1) |
| `src/eval/judge_runner.py` | Sample → judge → `eval_score` (`judge_one`, `run_daily`) |
| `src/eval/drift_detector.py` | KL on keywords, failure rate, mean cos_sim |
| `src/eval/alarm.py` | Threshold logging + optional Slack webhook |
| `src/persistence/eval_schema.sql` | `eval_score` table DDL |
| `scripts/build_goldenset.py` | 30-row dummy goldenset (`data/goldenset_sample.jsonl`) |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JUDGE_DAILY_SAMPLE_SIZE` | 100 | Max rows judged per run |
| `DRIFT_KL_THRESHOLD` | 0.15 | KL(P\|\|Q) alert threshold |
| `EVAL_SLACK_WEBHOOK_URL` | (empty) | Optional Slack incoming webhook |

vLLM 생성 모델: `VLLM_GEN__MODEL_NAME` (`.env.example` 참고)

---

## Usage

```bash
python -m scripts.build_goldenset
python -c "from src.eval.judge_runner import JudgeRunner; JudgeRunner().run_daily()"
```

Postgres schema: `python -m scripts.bootstrap_schema` (eval_score DDL 포함)

---

## Smoke (단건)

```python
from src.eval.judge_runner import JudgeRunner

runner = JudgeRunner()
scores = runner.judge_one(
    source_id="m-demo",
    source_type="movie",
    raw_text="가족과 성장을 다룬 드라마",
    ontology={"summary": "가족 드라마", "themes": ["성장"], "sentiment": "neutral"},
)
print(scores)
```

상세 smoke: [smoke_test.md](smoke_test.md) §5
