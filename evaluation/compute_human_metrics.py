"""
Menghitung Precision@5 (ambang relevan: label >= 1) dan nDCG@5
setelah kolom `relevance_label` pada evaluation/annotation_sheet.csv diisi oleh penilai manusia
(0 = tidak relevan, 1 = sebagian sesuai, 2 = sangat sesuai).

Menjamin kedua mode dibandingkan pada penyebut query yang sama:
- Query layak tanpa hasil untuk suatu mode diberi skor 0.0 (tidak didrop).
- Query mustahil (tidak ada kandidat di kedua mode) dilaporkan terpisah.
- Baris yang belum berlabel tidak diam-diam dianggap 0; hanya query dengan seluruh
  kandidat top-K yang telah berlabel yang dihitung dalam perbandingan.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluator import SystemEvaluator


def _parse_label(raw: Any) -> int:
    text = str(raw).strip()
    try:
        num = float(text)
    except ValueError as exc:
        raise ValueError(f"Label relevansi tidak valid: {raw!r} (harus 0, 1, atau 2)") from exc
    if not num.is_integer() or int(num) not in (0, 1, 2):
        raise ValueError(f"Label relevansi di luar rentang 0..2: {raw!r}")
    return int(num)


def evaluate_human_metrics(
    df_res: pd.DataFrame,
    df_ann: pd.DataFrame,
    df_summary: Optional[pd.DataFrame] = None,
    k: int = 5,
) -> Dict[str, Any]:
    total_annotation_rows = len(df_ann)
    label_map: Dict[tuple, int] = {}

    if not df_ann.empty and "relevance_label" in df_ann.columns:
        for _, row in df_ann.iterrows():
            raw_lbl = row["relevance_label"]
            if pd.isna(raw_lbl) or str(raw_lbl).strip() == "":
                continue
            key = (str(row["query"]).strip(), str(row["product_id"]).strip())
            label_map[key] = _parse_label(raw_lbl)

    labeled_rows = len(label_map)
    coverage_ratio = round(labeled_rows / total_annotation_rows, 4) if total_annotation_rows > 0 else 0.0

    if df_summary is not None and not df_summary.empty:
        modes = list(dict.fromkeys(df_summary["mode"].astype(str).tolist()))
        if "query_type" in df_summary.columns:
            feasible_queries = list(
                dict.fromkeys(df_summary[df_summary["query_type"] == "feasible"]["query"].astype(str).tolist())
            )
            impossible_queries = list(
                dict.fromkeys(df_summary[df_summary["query_type"] == "impossible"]["query"].astype(str).tolist())
            )
        else:
            q_max_cands = df_summary.groupby("query", sort=False)["total_candidates"].max()
            feasible_queries = [str(q) for q, c in q_max_cands.items() if int(c) > 0]
            impossible_queries = [str(q) for q, c in q_max_cands.items() if int(c) == 0]
    else:
        modes = list(dict.fromkeys(df_res["mode"].astype(str).tolist())) if not df_res.empty else ["no_expansion", "with_expansion"]
        if not modes:
            modes = ["no_expansion", "with_expansion"]
        src_queries = df_ann["query"].tolist() if not df_ann.empty else (df_res["query"].tolist() if not df_res.empty else [])
        feasible_queries = list(dict.fromkeys(str(q) for q in src_queries))
        impossible_queries = []

    impossible_rejection: Dict[str, Dict[str, Any]] = {}
    if df_summary is not None and not df_summary.empty and impossible_queries:
        imp_df = df_summary[df_summary["query"].isin(impossible_queries)]
        for mode in modes:
            m_df = imp_df[imp_df["mode"] == mode]
            total_imp = len(impossible_queries)
            rejected = int((m_df["returned_count"] == 0).sum()) if not m_df.empty else 0
            impossible_rejection[mode] = {
                "rejected": rejected,
                "total": total_imp,
                "rejection_rate": round(rejected / total_imp, 4) if total_imp > 0 else 0.0,
            }

    complete_queries: List[str] = []
    incomplete_queries: List[str] = []
    for query in feasible_queries:
        q_res = df_res[df_res["query"].astype(str) == query] if not df_res.empty else pd.DataFrame()
        required_keys = set()
        for mode in modes:
            m_res = q_res[q_res["mode"].astype(str) == mode].sort_values("rank").head(k) if not q_res.empty else pd.DataFrame()
            for pid in m_res.get("product_id", []):
                required_keys.add((query, str(pid)))
        if required_keys and all(key in label_map for key in required_keys):
            complete_queries.append(query)
        else:
            incomplete_queries.append(query)

    pool_by_query: Dict[str, List[int]] = {}
    for (q, _), lbl in label_map.items():
        pool_by_query.setdefault(q, []).append(lbl)

    per_query_rows = []
    for query in complete_queries:
        q_res = df_res[df_res["query"].astype(str) == query]
        ideal_pool = pool_by_query.get(query, [])
        for mode in modes:
            grp_sorted = q_res[q_res["mode"].astype(str) == mode].sort_values("rank").head(k)
            if grp_sorted.empty:
                rels: List[int] = []
                has_result = 0
            else:
                rels = [label_map[(query, str(pid))] for pid in grp_sorted["product_id"]]
                has_result = 1
            per_query_rows.append({
                "query": query,
                "mode": mode,
                "Has_Result": has_result,
                f"Precision@{k} (rel>=1)": SystemEvaluator.precision_at_k(rels, k=k, threshold=1),
                f"Precision@{k} (rel==2)": SystemEvaluator.precision_at_k(rels, k=k, threshold=2),
                f"nDCG@{k}": SystemEvaluator.ndcg_at_k(rels, k=k, ideal_relevances=ideal_pool),
            })

    per_query_df = pd.DataFrame(per_query_rows)
    if not per_query_df.empty:
        summary_df = (
            per_query_df.groupby("mode", sort=False)
            .agg(
                Evaluated_Queries=("query", "count"),
                Query_Coverage=("Has_Result", "mean"),
                **{
                    f"Precision@{k} (rel>=1)": (f"Precision@{k} (rel>=1)", "mean"),
                    f"Precision@{k} (rel==2)": (f"Precision@{k} (rel==2)", "mean"),
                    f"nDCG@{k}": (f"nDCG@{k}", "mean"),
                },
            )
            .round(4)
        )
    else:
        summary_df = pd.DataFrame()

    return {
        "total_annotation_rows": total_annotation_rows,
        "labeled_rows": labeled_rows,
        "coverage_ratio": coverage_ratio,
        "feasible_queries_total": len(feasible_queries),
        "complete_queries": complete_queries,
        "incomplete_queries": incomplete_queries,
        "per_query_df": per_query_df,
        "summary_df": summary_df,
        "impossible_rejection": impossible_rejection,
    }


def main():
    eval_dir = Path(__file__).resolve().parent
    results_path = eval_dir / "expansion_results.csv"
    sheet_path = eval_dir / "annotation_sheet.csv"
    summary_path = eval_dir / "expansion_summary.csv"

    if not results_path.exists() or not sheet_path.exists():
        print("[!] Jalankan evaluation/run_expansion_experiment.py terlebih dahulu.")
        sys.exit(1)

    df_res = pd.read_csv(results_path)
    df_ann = pd.read_csv(sheet_path, dtype=str, keep_default_na=False)
    df_summary = pd.read_csv(summary_path) if summary_path.exists() else None

    report = evaluate_human_metrics(df_res, df_ann, df_summary=df_summary, k=5)

    print(
        f"[i] Cakupan anotasi: {report['labeled_rows']}/{report['total_annotation_rows']} baris "
        f"({report['coverage_ratio'] * 100:.1f}%), "
        f"{len(report['complete_queries'])}/{report['feasible_queries_total']} kueri layak selesai dinilai."
    )

    if report["impossible_rejection"]:
        print("\n--- Penolakan Kueri Mustahil (Dilaporkan Terpisah) ---")
        for mode, stats in report["impossible_rejection"].items():
            print(f"  {mode}: {stats['rejected']}/{stats['total']} ditolak ({stats['rejection_rate'] * 100:.1f}%)")

    if not report["complete_queries"]:
        print("\n[!] Belum ada kueri layak yang seluruh pasangan top-5-nya berlabel pada evaluation/annotation_sheet.csv.")
        sys.exit(0)

    if report["incomplete_queries"]:
        print(
            f"\n[!] Peringatan: {len(report['incomplete_queries'])} kueri layak belum berlabel lengkap dan tidak dihitung "
            "(label kosong tidak dianggap 0)."
        )

    print("\n--- Perbandingan Kualitas Peringkat (Penyebut Query Sama) ---")
    print(report["summary_df"])


if __name__ == "__main__":
    main()
