import math
from typing import Dict, Iterable, List, Optional, Sequence
import pandas as pd


class SystemEvaluator:
    @staticmethod
    def precision_at_k(relevances: Sequence[int], k: int = 5, threshold: int = 1) -> float:
        """
        Precision@K berdasarkan label relevansi manusia (0=tidak relevan, 1=sebagian, 2=sangat).
        Item dianggap relevan jika label >= threshold (default: 1).
        """
        if k <= 0:
            return 0.0
        top_k = list(relevances)[:k]
        if not top_k:
            return 0.0
        rel_count = sum(1 for r in top_k if r >= threshold)
        return round(rel_count / k, 4)

    @staticmethod
    def ndcg_at_k(relevances: Sequence[int], k: int = 5, ideal_relevances: Optional[Sequence[int]] = None) -> float:
        """
        nDCG@K dengan gain = (2^rel - 1) / log2(rank + 1).
        Jika ideal_relevances tidak diberikan, ideal dihitung dari pool relevansi yang tersedia.
        """
        if k <= 0:
            return 0.0
        top_k = list(relevances)[:k]
        if not top_k:
            return 0.0

        def _dcg(rels: Sequence[int]) -> float:
            return sum(((2 ** r) - 1) / math.log2(idx + 2) for idx, r in enumerate(rels[:k]))

        dcg = _dcg(top_k)
        ideal_pool = sorted(ideal_relevances if ideal_relevances is not None else top_k, reverse=True)
        idcg = _dcg(ideal_pool)
        return round(dcg / idcg, 4) if idcg > 0 else 0.0

    @staticmethod
    def top_k_overlap(ids_a: Iterable[str], ids_b: Iterable[str], k: int = 5) -> Dict[str, float]:
        """Mengukur overlap kandidat top-K antara dua mode (bukan ukuran relevansi)."""
        set_a = set(list(ids_a)[:k])
        set_b = set(list(ids_b)[:k])
        inter = len(set_a & set_b)
        union = len(set_a | set_b)
        return {
            "overlap_count": inter,
            "overlap_ratio_at_k": round(inter / k, 4) if k > 0 else 0.0,
            "jaccard": round(inter / union, 4) if union > 0 else 1.0,
        }

    @staticmethod
    def evaluate_query(
        results_df: pd.DataFrame,
        full_df: pd.DataFrame,
        relevance_condition,
        k: int = 5,
        complete_ground_truth: bool = False,
    ) -> dict:
        """
        Evaluasi berbasis aturan objektif pada katalog.
        Recall@K hanya dilaporkan jika complete_ground_truth=True (seluruh item relevan di katalog diketahui).
        """
        top_k = results_df.head(k)
        relevant_in_top_k = top_k[top_k.apply(relevance_condition, axis=1)] if not top_k.empty else top_k
        precision_at_k = len(relevant_in_top_k) / k if k > 0 else 0.0

        out = {
            f"Precision@{k}": round(precision_at_k, 4),
            "Relevant_Found": int(len(relevant_in_top_k)),
        }

        if complete_ground_truth:
            total_relevant_in_dataset = full_df[full_df.apply(relevance_condition, axis=1)]
            total_rel_count = len(total_relevant_in_dataset)
            recall_at_k = len(relevant_in_top_k) / total_rel_count if total_rel_count > 0 else 0.0
            out[f"Recall@{k}"] = round(recall_at_k, 4)
            out["Total_Relevant_In_DB"] = int(total_rel_count)

        return out
