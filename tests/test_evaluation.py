import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.compute_human_metrics import evaluate_human_metrics
from evaluation.run_expansion_experiment import run_experiment


def test_runner_preserves_existing_labels_and_includes_display_column(tmp_path):
    first = run_experiment(out_dir=tmp_path)
    assert first["total_violations"] == 0
    assert first["preserved_labels"] == 0

    sheet_path = tmp_path / "annotation_sheet.csv"
    res_path = tmp_path / "expansion_results.csv"
    sum_path = tmp_path / "expansion_summary.csv"

    df_ann = pd.read_csv(sheet_path, dtype=str, keep_default_na=False)
    df_res = pd.read_csv(res_path)
    df_sum = pd.read_csv(sum_path)

    assert "display" in df_ann.columns
    assert "display" in df_res.columns
    assert "query_type" in df_sum.columns

    # Isi label simulasi dan pastikan tidak hilang saat runner dijalankan ulang
    expected_labels = {}
    for idx in range(len(df_ann)):
        lbl = str(idx % 3)
        df_ann.loc[idx, "relevance_label"] = lbl
        expected_labels[(df_ann.loc[idx, "query"], df_ann.loc[idx, "product_id"])] = lbl
    df_ann.to_csv(sheet_path, index=False)

    second = run_experiment(out_dir=tmp_path)
    assert second["preserved_labels"] == len(df_ann)

    df_ann_after = pd.read_csv(sheet_path, dtype=str, keep_default_na=False)
    for _, row in df_ann_after.iterrows():
        assert row["relevance_label"] == expected_labels[(row["query"], row["product_id"])]


def test_human_metrics_equal_denominator_and_separate_impossible():
    df_res = pd.DataFrame([
        # q1: kedua mode menemukan p1 (label 2)
        {"query": "q1", "mode": "no_expansion", "rank": 1, "product_id": "p1"},
        {"query": "q1", "mode": "with_expansion", "rank": 1, "product_id": "p1"},
        # q2: hanya with_expansion yang menemukan p2 (label 2); no_expansion kosong
        {"query": "q2", "mode": "with_expansion", "rank": 1, "product_id": "p2"},
    ])
    df_summary = pd.DataFrame([
        {"query": "q1", "query_type": "feasible", "mode": "no_expansion", "returned_count": 1, "total_candidates": 1},
        {"query": "q1", "query_type": "feasible", "mode": "with_expansion", "returned_count": 1, "total_candidates": 1},
        {"query": "q2", "query_type": "feasible", "mode": "no_expansion", "returned_count": 0, "total_candidates": 0},
        {"query": "q2", "query_type": "feasible", "mode": "with_expansion", "returned_count": 1, "total_candidates": 1},
        {"query": "imp1", "query_type": "impossible", "mode": "no_expansion", "returned_count": 0, "total_candidates": 0},
        {"query": "imp1", "query_type": "impossible", "mode": "with_expansion", "returned_count": 0, "total_candidates": 0},
    ])
    df_ann = pd.DataFrame([
        {"query": "q1", "product_id": "p1", "relevance_label": "2"},
        {"query": "q2", "product_id": "p2", "relevance_label": "2"},
    ])

    report = evaluate_human_metrics(df_res, df_ann, df_summary=df_summary, k=5)
    summary = report["summary_df"]

    # Kedua mode wajib dievaluasi pada penyebut yang sama (2 query layak)
    assert summary.loc["no_expansion", "Evaluated_Queries"] == 2
    assert summary.loc["with_expansion", "Evaluated_Queries"] == 2
    assert summary.loc["no_expansion", "Query_Coverage"] == 0.5
    assert summary.loc["with_expansion", "Query_Coverage"] == 1.0
    assert summary.loc["no_expansion", "Precision@5 (rel>=1)"] == 0.1
    assert summary.loc["with_expansion", "Precision@5 (rel>=1)"] == 0.2
    assert summary.loc["no_expansion", "nDCG@5"] == 0.5
    assert summary.loc["with_expansion", "nDCG@5"] == 1.0

    assert report["impossible_rejection"]["no_expansion"] == {"rejected": 1, "total": 1, "rejection_rate": 1.0}
    assert report["impossible_rejection"]["with_expansion"] == {"rejected": 1, "total": 1, "rejection_rate": 1.0}


def test_partial_annotation_reports_coverage_and_does_not_impute_zero():
    df_res = pd.DataFrame([
        {"query": "Query A", "mode": "no_expansion", "rank": 1, "product_id": "a1"},
        {"query": "Query A", "mode": "with_expansion", "rank": 1, "product_id": "a1"},
        {"query": "Query B", "mode": "no_expansion", "rank": 1, "product_id": "b1"},
        {"query": "Query B", "mode": "with_expansion", "rank": 1, "product_id": "b2"},
    ])
    df_summary = pd.DataFrame([
        {"query": "Query A", "query_type": "feasible", "mode": "no_expansion", "returned_count": 1, "total_candidates": 1},
        {"query": "Query A", "query_type": "feasible", "mode": "with_expansion", "returned_count": 1, "total_candidates": 1},
        {"query": "Query B", "query_type": "feasible", "mode": "no_expansion", "returned_count": 1, "total_candidates": 1},
        {"query": "Query B", "query_type": "feasible", "mode": "with_expansion", "returned_count": 1, "total_candidates": 1},
    ])
    # Query A selesai dinilai (2), Query B baru setengah dinilai (b1=2, b2 kosong)
    df_ann = pd.DataFrame([
        {"query": "Query A", "product_id": "a1", "relevance_label": "2"},
        {"query": "Query B", "product_id": "b1", "relevance_label": "2"},
        {"query": "Query B", "product_id": "b2", "relevance_label": ""},
    ])

    report = evaluate_human_metrics(df_res, df_ann, df_summary=df_summary, k=5)
    assert report["labeled_rows"] == 2
    assert report["total_annotation_rows"] == 3
    assert report["coverage_ratio"] == round(2 / 3, 4)
    assert report["complete_queries"] == ["Query A"]
    assert report["incomplete_queries"] == ["Query B"]
    # Hanya Query A yang masuk rata-rata, b2 yang kosong tidak dianggap 0
    assert report["summary_df"].loc["with_expansion", "Evaluated_Queries"] == 1
    assert report["summary_df"].loc["with_expansion", "nDCG@5"] == 1.0
