"""
Menghitung Precision@5 (ambang relevan: label >= 1) dan nDCG@5
setelah kolom `relevance_label` pada evaluation/annotation_sheet.csv diisi oleh penilai manusia
(0 = tidak relevan, 1 = sebagian sesuai, 2 = sangat sesuai).
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluator import SystemEvaluator


def main():
    eval_dir = Path(__file__).resolve().parent
    results_path = eval_dir / "expansion_results.csv"
    sheet_path = eval_dir / "annotation_sheet.csv"

    if not results_path.exists() or not sheet_path.exists():
        print("[!] Jalankan evaluation/run_expansion_experiment.py terlebih dahulu.")
        sys.exit(1)

    df_res = pd.read_csv(results_path)
    df_ann = pd.read_csv(sheet_path)

    labeled = df_ann[df_ann["relevance_label"].notna() & (df_ann["relevance_label"].astype(str).str.strip() != "")]
    if labeled.empty:
        print("[!] Kolom relevance_label di evaluation/annotation_sheet.csv masih kosong. Belum ada label manusia untuk dihitung.")
        sys.exit(0)

    labeled = labeled.copy()
    labeled["relevance_label"] = labeled["relevance_label"].astype(int)

    label_map = {
        (row["query"], str(row["product_id"])): int(row["relevance_label"])
        for _, row in labeled.iterrows()
    }
    pool_by_query = {}
    for (q, _), lbl in label_map.items():
        pool_by_query.setdefault(q, []).append(lbl)

    rows = []
    for (query, mode), grp in df_res.groupby(["query", "mode"]):
        grp_sorted = grp.sort_values("rank").head(5)
        rels = [label_map.get((query, str(pid)), 0) for pid in grp_sorted["product_id"]]
        ideal_pool = pool_by_query.get(query, rels)
        rows.append({
            "query": query,
            "mode": mode,
            "Precision@5 (rel>=1)": SystemEvaluator.precision_at_k(rels, k=5, threshold=1),
            "Precision@5 (rel==2)": SystemEvaluator.precision_at_k(rels, k=5, threshold=2),
            "nDCG@5": SystemEvaluator.ndcg_at_k(rels, k=5, ideal_relevances=ideal_pool),
        })

    df_metrics = pd.DataFrame(rows)
    print(df_metrics.groupby("mode")[["Precision@5 (rel>=1)", "Precision@5 (rel==2)", "nDCG@5"]].mean().round(4))


if __name__ == "__main__":
    main()
