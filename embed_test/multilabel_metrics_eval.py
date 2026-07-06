"""Label-wise / multi-label aware embedding evaluation for result_check2 data."""

from __future__ import annotations

import ast
import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    coverage_error,
    f1_score,
    hamming_loss,
    jaccard_score,
    label_ranking_average_precision_score,
    label_ranking_loss,
    precision_score,
    recall_score,
)
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MultiLabelBinarizer

warnings.filterwarnings("ignore")

NOTEBOOK_DIR = Path(__file__).resolve().parent
ORIGIN_DIR = NOTEBOOK_DIR / "origin_data"
RESULT_DIR = NOTEBOOK_DIR / "result_data_3"
ONTOLOGY_CSV = ORIGIN_DIR / "movie_all_fixed.csv"

RESULT_LABEL_COLUMNS = ("genres", "moods", "themes", "keywords")
ONTOLOGY_LABEL_COLUMNS = ("genres", "themes", "moods", "keywords")

LABEL_TYPES: dict[str, str] = {
    "genre": "genres",
    "theme": "themes",
    "mood": "moods",
}

KNN_K = 107
MIN_LABEL_SUPPORT = 10
MIN_SEPARATION_SUPPORT = 20
SILHOUETTE_SAMPLE = 2000


def parse_label_list(value: Any) -> list[str]:
    """Parse label field from result_data_3 CSV or fixed ontology CSV."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]

    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple)):
            return [str(v).strip() for v in parsed if str(v).strip()]
        text = str(parsed).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1]
    return [part.strip() for part in text.split(",") if part.strip()]


def load_ontology_df(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in ONTOLOGY_LABEL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(parse_label_list)
    return df


def load_result_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in RESULT_LABEL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(parse_label_list)
    return df


def build_model_frame(result_df: pd.DataFrame, ontology: pd.DataFrame | None = None) -> pd.DataFrame:
    frame = result_df.copy()
    if ontology is None or "title" in frame.columns:
        return frame
    return frame.merge(
        ontology[["movie_id", "title"]].drop_duplicates("movie_id"),
        on="movie_id",
        how="left",
    )


def embedding_matrix(df: pd.DataFrame) -> np.ndarray:
    emb_cols = sorted(
        [c for c in df.columns if c.startswith("embedding_")],
        key=lambda c: int(c.split("_")[1]),
    )
    x = df[emb_cols].to_numpy(dtype=float)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return x / norms


def label_sets(series: pd.Series) -> list[set[str]]:
    out: list[set[str]] = []
    for values in series:
        if values is None or (isinstance(values, float) and np.isnan(values)):
            out.append(set())
        else:
            out.append({str(v).strip() for v in values if str(v).strip()})
    return out


def knn_predict(Y: np.ndarray, neighbor_idx: np.ndarray, threshold: float = 0.35) -> np.ndarray:
    """Majority-vote multi-label prediction from kNN neighbor label sets."""
    neighbor_labels = Y[neighbor_idx]
    freq = neighbor_labels.mean(axis=1)
    return (freq >= threshold).astype(int)


def multilabel_retrieval_metrics(Y_true: np.ndarray, Y_pred: np.ndarray) -> dict[str, float]:
    return {
        "subset_accuracy": float(np.mean(np.all(Y_true == Y_pred, axis=1))),
        "hamming_loss": float(hamming_loss(Y_true, Y_pred)),
        "micro_precision": float(precision_score(Y_true, Y_pred, average="micro", zero_division=0)),
        "micro_recall": float(recall_score(Y_true, Y_pred, average="micro", zero_division=0)),
        "micro_f1": float(f1_score(Y_true, Y_pred, average="micro", zero_division=0)),
        "macro_f1": float(f1_score(Y_true, Y_pred, average="macro", zero_division=0)),
        "samples_f1": float(f1_score(Y_true, Y_pred, average="samples", zero_division=0)),
        "micro_jaccard": float(jaccard_score(Y_true, Y_pred, average="micro", zero_division=0)),
        "macro_jaccard": float(jaccard_score(Y_true, Y_pred, average="macro", zero_division=0)),
        "samples_jaccard": float(jaccard_score(Y_true, Y_pred, average="samples", zero_division=0)),
        "lrap": float(label_ranking_average_precision_score(Y_true, Y_pred)),
        "coverage": float(coverage_error(Y_true, Y_pred)),
        "ranking_loss": float(label_ranking_loss(Y_true, Y_pred)),
    }


def label_wise_knn_metrics(
    Y_true: np.ndarray,
    neighbor_idx: np.ndarray,
    label_names: list[str],
    *,
    min_support: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    n_labels = Y_true.shape[1]
    for j in range(n_labels):
        support = int(Y_true[:, j].sum())
        if support < min_support:
            continue
        y_true = Y_true[:, j]
        neighbor_hits = Y_true[neighbor_idx, j].mean(axis=1)
        y_pred = (neighbor_hits >= 0.5).astype(int)
        rows.append(
            {
                "label": label_names[j],
                "support": support,
                "prevalence": support / len(Y_true),
                "precision": float(precision_score(y_true, y_pred, zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, zero_division=0)),
                "f1": float(f1_score(y_true, y_pred, zero_division=0)),
                "avg_neighbor_hit_rate": float(neighbor_hits[y_true == 1].mean()),
            }
        )
    return pd.DataFrame(rows)


def mean_average_precision_at_k(
    Y_true: np.ndarray,
    neighbor_idx: np.ndarray,
    label_names: list[str],
    *,
    min_support: int,
) -> tuple[float, pd.DataFrame]:
    neighbor_labels = Y_true[neighbor_idx]
    per_label_ap: list[dict[str, Any]] = []
    aps: list[float] = []
    weights: list[int] = []

    for j, label in enumerate(label_names):
        positives = Y_true[:, j] == 1
        support = int(positives.sum())
        if support < min_support:
            continue
        scores = neighbor_labels[:, :, j].mean(axis=1)
        ap = float(average_precision_score(positives, scores))
        aps.append(ap)
        weights.append(support)
        per_label_ap.append({"label": label, "support": support, "map_label": ap})

    macro_map = float(np.mean(aps)) if aps else float("nan")
    weighted_map = float(np.average(aps, weights=weights)) if aps else float("nan")
    return macro_map, pd.DataFrame(per_label_ap).assign(weighted_map=weighted_map)


def label_wise_separation(
    X: np.ndarray,
    Y_true: np.ndarray,
    label_names: list[str],
    *,
    min_support: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for j, label in enumerate(label_names):
        mask = Y_true[:, j] == 1
        support = int(mask.sum())
        if support < min_support:
            continue

        pos = X[mask]
        neg = X[~mask]
        pos_centroid = pos.mean(axis=0)
        pos_centroid /= max(np.linalg.norm(pos_centroid), 1e-12)

        intra = float(np.mean(pos @ pos_centroid))
        inter = float(np.mean(neg @ pos_centroid)) if len(neg) else float("nan")
        margin = intra - inter

        pos_pair_idx = np.random.default_rng(42).choice(
            len(pos),
            size=min(500, len(pos)),
            replace=len(pos) < 500,
        )
        sampled = pos[pos_pair_idx]
        pairwise = sampled @ sampled.T
        np.fill_diagonal(pairwise, np.nan)
        intra_pairwise = float(np.nanmean(pairwise))

        rows.append(
            {
                "label": label,
                "support": support,
                "intra_centroid_cosine": intra,
                "inter_centroid_cosine": inter,
                "separation_margin": margin,
                "intra_pairwise_cosine": intra_pairwise,
            }
        )
    return pd.DataFrame(rows)


def knn_label_jaccard(Y_true: np.ndarray, neighbor_idx: np.ndarray) -> float:
    """Example-wise Jaccard between true label set and kNN label union."""
    neighbor_union = (Y_true[neighbor_idx].max(axis=1) > 0).astype(int)
    return float(jaccard_score(Y_true, neighbor_union, average="samples", zero_division=0))


def label_wise_binary_silhouette(
    X: np.ndarray,
    Y_true: np.ndarray,
    label_names: list[str],
    *,
    min_support: int,
    sample_size: int,
) -> float | None:
    """Macro-average silhouette per label (binary has-label vs no-label)."""
    from sklearn.metrics import silhouette_score

    scores: list[float] = []
    weights: list[int] = []
    n = len(X)
    sample_n = min(sample_size, n)
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(n, size=sample_n, replace=False) if sample_n < n else np.arange(n)

    for j, _label in enumerate(label_names):
        y = Y_true[:, j]
        support = int(y.sum())
        neg = int((1 - y).sum())
        if support < min_support or neg < min_support:
            continue
        x_sub = X[sample_idx]
        y_sub = y[sample_idx]
        if len(np.unique(y_sub)) < 2:
            continue
        sil = float(
            silhouette_score(
                x_sub,
                y_sub,
                metric="cosine",
                sample_size=min(1000, len(sample_idx)),
                random_state=42,
            )
        )
        scores.append(sil)
        weights.append(support)

    if not scores:
        return None
    return float(np.average(scores, weights=weights))


def evaluate_model(model_name: str, frame: pd.DataFrame, X: np.ndarray, threshold: float) -> dict[str, Any]:
    nn = NearestNeighbors(n_neighbors=KNN_K + 1, metric="cosine", algorithm="brute")
    nn.fit(X)
    _, all_neighbors = nn.kneighbors(X)
    neighbor_idx = all_neighbors[:, 1:]

    summary_rows: list[dict[str, Any]] = []
    labelwise_tables: dict[str, pd.DataFrame] = {}
    map_tables: dict[str, pd.DataFrame] = {}
    separation_tables: dict[str, pd.DataFrame] = {}

    for label_name, src_col in LABEL_TYPES.items():
        sets = label_sets(frame[src_col])
        mlb = MultiLabelBinarizer(sparse_output=False)
        Y = mlb.fit_transform([sorted(s) for s in sets])
        label_names = list(mlb.classes_)
        Y_pred = knn_predict(Y, neighbor_idx, threshold)

        metrics = multilabel_retrieval_metrics(Y, Y_pred)
        lw = label_wise_knn_metrics(Y, neighbor_idx, label_names, min_support=MIN_LABEL_SUPPORT)
        macro_map, map_df = mean_average_precision_at_k(
            Y, neighbor_idx, label_names, min_support=MIN_LABEL_SUPPORT
        )
        sep = label_wise_separation(X, Y, label_names, min_support=MIN_SEPARATION_SUPPORT)
        knn_jaccard = knn_label_jaccard(Y, neighbor_idx)
        label_sil = label_wise_binary_silhouette(
            X,
            Y,
            label_names,
            min_support=MIN_SEPARATION_SUPPORT,
            sample_size=SILHOUETTE_SAMPLE,
        )

        summary_rows.append(
            {
                "model": model_name,
                "label_type": label_name,
                "n_samples": len(frame),
                "n_labels": len(label_names),
                "avg_labels_per_movie": float(np.mean([len(s) for s in sets])),
                "knn_k": KNN_K,
                "macro_map": macro_map,
                "macro_label_f1": float(lw["f1"].mean()) if len(lw) else None,
                "macro_separation_margin": float(sep["separation_margin"].mean()) if len(sep) else None,
                "knn_label_jaccard_samples": knn_jaccard,
                "label_wise_silhouette_macro": label_sil,
                **metrics,
            }
        )
        labelwise_tables[label_name] = lw.sort_values("f1", ascending=False)
        map_tables[label_name] = map_df.sort_values("map_label", ascending=False)
        separation_tables[label_name] = sep.sort_values("separation_margin", ascending=False)

    return {
        "summary": pd.DataFrame(summary_rows),
        "labelwise": labelwise_tables,
        "map": map_tables,
        "separation": separation_tables,
    }


def main() -> None:
    ontology = load_ontology_df(ONTOLOGY_CSV)
    all_summaries: list[pd.DataFrame] = []
    full_report: dict[str, Any] = {"models": {}}

    for path in sorted(RESULT_DIR.glob("result-*.csv")):
        model_name = path.stem.replace("result-", "")
        frame = build_model_frame(load_result_csv(path), ontology)
        X = embedding_matrix(frame)
        result = evaluate_model(model_name, frame, X)
        all_summaries.append(result["summary"])
        full_report["models"][model_name] = {
            "summary": result["summary"].to_dict(orient="records"),
            "labelwise_top5": {
                k: v.head(5).to_dict(orient="records") for k, v in result["labelwise"].items()
            },
            "labelwise_bottom5": {
                k: v.tail(5).sort_values("f1").to_dict(orient="records")
                for k, v in result["labelwise"].items()
            },
            "separation_top5": {
                k: v.head(5).to_dict(orient="records") for k, v in result["separation"].items()
            },
            "separation_bottom5": {
                k: v.tail(5).sort_values("separation_margin").to_dict(orient="records")
                for k, v in result["separation"].items()
            },
        }
        print(f"\n{'=' * 80}\nMODEL: {model_name}\n{'=' * 80}")
        print(result["summary"].to_string(index=False))

    combined = pd.concat(all_summaries, ignore_index=True)
    out_csv = NOTEBOOK_DIR / "multilabel_metrics_summary.csv"
    combined.to_csv(out_csv, index=False)
    out_json = NOTEBOOK_DIR / "multilabel_metrics_report.json"
    out_json.write_text(json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_csv}")
    print(f"Saved: {out_json}")


if __name__ == "__main__":
    main()
