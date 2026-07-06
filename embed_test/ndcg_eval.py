"""Build movie-search test queries and evaluate nDCG@K with precomputed embeddings."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from multilabel_metrics_eval import (
    ONTOLOGY_CSV,
    RESULT_DIR,
    embedding_matrix,
    load_ontology_df,
    load_result_csv,
)

ARCHIVE_DIR = Path(__file__).resolve().parent
NDCG_DIR = RESULT_DIR / "ndcg"
DEFAULT_MODEL = "qwen3_0_6b"
DEFAULT_RESULT_CSV = RESULT_DIR / f"result-{DEFAULT_MODEL}.csv"

WEIGHTS = {"genre": 0.35, "theme": 0.40, "mood": 0.25}
GRADE_BOUNDS = {"3": 10, "2": 30, "1": 100}
QUERIES_PER_GENRE = 11
MIN_CANDIDATES = 100
NDCG_KS = (5, 10, 20, 50)
RANDOM_SEED = 42


def primary_label(values: list[str]) -> str:
    cleaned = sorted(str(v).strip() for v in values if str(v).strip())
    return cleaned[0] if cleaned else "Unknown"


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def composite_similarity(
    query_row: pd.Series,
    candidate_row: pd.Series,
    *,
    weights: dict[str, float] = WEIGHTS,
) -> float:
    if not set(query_row["genres"]) & set(candidate_row["genres"]):
        return 0.0
    return (
        weights["genre"] * jaccard(query_row["genres"], candidate_row["genres"])
        + weights["theme"] * jaccard(query_row["themes"], candidate_row["themes"])
        + weights["mood"] * jaccard(query_row["moods"], candidate_row["moods"])
    )


def assign_grades(ranked_movie_ids: list[str]) -> dict[str, int]:
    grades: dict[str, int] = {}
    for rank, movie_id in enumerate(ranked_movie_ids, start=1):
        if rank <= GRADE_BOUNDS["3"]:
            grades[movie_id] = 3
        elif rank <= GRADE_BOUNDS["2"]:
            grades[movie_id] = 2
        elif rank <= GRADE_BOUNDS["1"]:
            grades[movie_id] = 1
    return grades


def build_test_queries(
    ontology_df: pd.DataFrame,
    *,
    queries_per_genre: int = QUERIES_PER_GENRE,
    min_candidates: int = MIN_CANDIDATES,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    rng = np.random.default_rng(random_seed)
    frame = ontology_df.copy()
    frame["primary_genre"] = frame["genres"].apply(primary_label)
    id_to_idx = {movie_id: idx for idx, movie_id in enumerate(frame["movie_id"])}

    queries: list[dict[str, Any]] = []
    skipped = 0

    for genre, group in frame.groupby("primary_genre", sort=True):
        if len(group) <= 1:
            skipped += 1
            continue

        sample_n = min(queries_per_genre, len(group))
        sampled = group.sample(n=sample_n, random_state=int(rng.integers(0, 1_000_000)))

        for _, query_row in sampled.iterrows():
            query_id = query_row["movie_id"]
            q_idx = id_to_idx[query_id]
            scores: list[tuple[str, float]] = []

            for idx, candidate_row in frame.iterrows():
                if idx == q_idx:
                    continue
                score = composite_similarity(query_row, candidate_row)
                if score > 0:
                    scores.append((candidate_row["movie_id"], score))

            if len(scores) < min_candidates:
                skipped += 1
                continue

            scores.sort(key=lambda item: item[1], reverse=True)
            top_ids = [movie_id for movie_id, _ in scores[:min_candidates]]
            relevant = assign_grades(top_ids)

            queries.append(
                {
                    "query_id": query_id,
                    "title": query_row["title"],
                    "year": int(query_row["year"]) if pd.notna(query_row["year"]) else None,
                    "primary_genre": genre,
                    "genres": query_row["genres"],
                    "n_relevant": len(relevant),
                    "relevant": relevant,
                }
            )

    return {
        "version": 1,
        "source": ONTOLOGY_CSV.name,
        "task": "movie_similarity_search",
        "description": (
            "Query = 영화 1편. relevance = 동일 genre 공유 후 "
            "genre/theme/mood Jaccard composite 유사도 상위 100편을 3/2/1 등급으로 부여."
        ),
        "grade_definition": {
            "3": f"similarity rank 1-{GRADE_BOUNDS['3']}",
            "2": f"similarity rank {GRADE_BOUNDS['3'] + 1}-{GRADE_BOUNDS['2']}",
            "1": f"similarity rank {GRADE_BOUNDS['2'] + 1}-{GRADE_BOUNDS['1']}",
            "0": "그 외",
        },
        "weights": WEIGHTS,
        "query_count": len(queries),
        "skipped_low_relevant": skipped,
        "queries": queries,
    }


def save_test_queries(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_test_queries(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dcg_at_k(relevances: list[int], k: int) -> float:
    return sum((2**rel - 1) / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))


def ndcg_at_k(relevances: list[int], k: int) -> float:
    if not relevances:
        return 0.0
    ideal = sorted(relevances, reverse=True)
    denom = dcg_at_k(ideal, k)
    if denom == 0:
        return 0.0
    return dcg_at_k(relevances, k) / denom


def rank_by_cosine(query_vec: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    scores = corpus @ query_vec
    return np.argsort(-scores)


def evaluate_ndcg(
    result_df: pd.DataFrame,
    test_payload: dict[str, Any],
    *,
    ks: tuple[int, ...] = NDCG_KS,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, float]]:
    X = embedding_matrix(result_df)
    movie_ids = result_df["movie_id"].tolist()
    id_to_pos = {movie_id: pos for pos, movie_id in enumerate(movie_ids)}

    per_query_rows: list[dict[str, Any]] = []

    for query in test_payload["queries"]:
        query_id = query["query_id"]
        if query_id not in id_to_pos:
            continue

        q_pos = id_to_pos[query_id]
        query_vec = X[q_pos]
        ranked_idx = rank_by_cosine(query_vec, X)
        ranked_idx = ranked_idx[ranked_idx != q_pos]

        relevant: dict[str, int] = query["relevant"]
        ranked_rels = [relevant.get(movie_ids[idx], 0) for idx in ranked_idx]

        row: dict[str, Any] = {
            "query_id": query_id,
            "title": query.get("title"),
            "primary_genre": query.get("primary_genre"),
            "n_relevant": query.get("n_relevant"),
        }
        for k in ks:
            row[f"ndcg@{k}"] = ndcg_at_k(ranked_rels, k)
        per_query_rows.append(row)

    per_query_df = pd.DataFrame(per_query_rows)
    summary_rows = []
    summary_map: dict[int, float] = {}
    for k in ks:
        col = f"ndcg@{k}"
        summary_map[k] = float(per_query_df[col].mean()) if len(per_query_df) else 0.0
        summary_rows.append(
            {
                "K": k,
                "ndcg": summary_map[k],
                "std": float(per_query_df[col].std()) if len(per_query_df) else 0.0,
                "n_queries": len(per_query_df),
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    return summary_df, per_query_df, summary_map


def plot_ndcg_chart(summary_df: pd.DataFrame, output_path: Path, *, model_name: str) -> None:
    plt.rcParams["font.family"] = "AppleGothic" if Path("/System/Library/Fonts").exists() else "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(8, 5))
    x = summary_df["K"].astype(str)
    y = summary_df["ndcg"]
    err = summary_df["std"]
    bars = ax.bar(x, y, color="#4C72B0", alpha=0.85, yerr=err, capsize=4)
    ax.set_xlabel("K")
    ax.set_ylabel("nDCG@K")
    ax.set_title(f"Movie Search nDCG@K ({model_name})")
    ax.set_ylim(0, max(0.3, float(y.max()) * 1.25))
    ax.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, y, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def write_report(
    output_path: Path,
    *,
    model_name: str,
    test_payload: dict[str, Any],
    summary_df: pd.DataFrame,
    per_query_df: pd.DataFrame,
    result_csv: Path,
) -> None:
    genre_ndcg = (
        per_query_df.groupby("primary_genre")["ndcg@10"]
        .agg(["count", "mean"])
        .rename(columns={"count": "n", "mean": "ndcg@10"})
        .sort_values("ndcg@10", ascending=False)
    )

    lines = [
        "# Movie Search nDCG@K 리포트",
        "",
        f"- **모델**: `{model_name}`",
        f"- **임베딩**: `{result_csv.name}`",
        f"- **테스트 쿼리**: {test_payload['query_count']}개 (`{test_payload['source']}` 기반)",
        f"- **과제**: query 영화 임베딩 → corpus cosine 검색",
        f"- **정답(relevance)**: genre 공유 + theme/mood Jaccard composite 상위 100편 (grade 3/2/1)",
        "",
        "## nDCG@K 요약",
        "",
        "| K | nDCG@K | std |",
        "|---|--------|-----|",
    ]
    for _, row in summary_df.iterrows():
        lines.append(f"| {int(row['K'])} | {row['ndcg']:.4f} | {row['std']:.4f} |")

    lines.extend(
        [
            "",
            "## 장르별 nDCG@10",
            "",
            "| primary_genre | n | nDCG@10 |",
            "|---------------|---|---------|",
        ]
    )
    for genre, row in genre_ndcg.iterrows():
        lines.append(f"| {genre} | {int(row['n'])} | {row['ndcg@10']:.4f} |")

    lines.extend(
        [
            "",
            "## 산출물",
            "",
            "| 파일 | 설명 |",
            "|------|------|",
            "| `test_queries.json` | 테스트 쿼리 + relevance grade |",
            "| `ndcg_summary.csv` | K별 평균 nDCG |",
            "| `ndcg_per_query.csv` | 쿼리별 nDCG |",
            "| `ndcg_chart.png` | nDCG@K 막대 차트 |",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(
    *,
    build: bool,
    model_name: str = DEFAULT_MODEL,
    result_csv: Path | None = None,
    ontology_csv: Path = ONTOLOGY_CSV,
    output_dir: Path = NDCG_DIR,
) -> None:
    result_csv = result_csv or RESULT_DIR / f"result-{model_name}.csv"
    if not result_csv.exists():
        raise FileNotFoundError(f"임베딩 CSV가 없습니다: {result_csv}")

    output_dir.mkdir(parents=True, exist_ok=True)
    test_queries_path = output_dir / "test_queries.json"

    ontology_df = load_ontology_df(ontology_csv)
    if build or not test_queries_path.exists():
        print(f"Building test queries from {ontology_csv.name} ...")
        test_payload = build_test_queries(ontology_df)
        save_test_queries(test_payload, test_queries_path)
        print(f"Saved {test_payload['query_count']} queries -> {test_queries_path}")
    else:
        print(f"Loading existing test queries: {test_queries_path}")
        test_payload = load_test_queries(test_queries_path)

    print(f"Loading embeddings: {result_csv.name}")
    result_df = load_result_csv(result_csv)
    summary_df, per_query_df, _ = evaluate_ndcg(result_df, test_payload)

    summary_path = output_dir / "ndcg_summary.csv"
    per_query_path = output_dir / "ndcg_per_query.csv"
    chart_path = output_dir / "ndcg_chart.png"
    report_path = output_dir / "ndcg_report.md"

    summary_df.to_csv(summary_path, index=False)
    per_query_df.to_csv(per_query_path, index=False)
    plot_ndcg_chart(summary_df, chart_path, model_name=model_name)
    write_report(
        report_path,
        model_name=model_name,
        test_payload=test_payload,
        summary_df=summary_df,
        per_query_df=per_query_df,
        result_csv=result_csv,
    )

    print("\n=== nDCG@K ===")
    print(summary_df.to_string(index=False))
    print(f"\nSaved: {summary_path}")
    print(f"Saved: {per_query_path}")
    print(f"Saved: {chart_path}")
    print(f"Saved: {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build test queries and evaluate movie search nDCG@K.")
    parser.add_argument("--build", action="store_true", help="Rebuild test_queries.json from ontology CSV.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model suffix in result-{model}.csv")
    parser.add_argument(
        "--result-csv",
        type=Path,
        default=None,
        help="Override embedding CSV path.",
    )
    parser.add_argument(
        "--ontology-csv",
        type=Path,
        default=ONTOLOGY_CSV,
        help="Ontology CSV path for test query construction.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=NDCG_DIR,
        help="Directory for ndcg outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(
        build=args.build,
        model_name=args.model,
        result_csv=args.result_csv,
        ontology_csv=args.ontology_csv,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
