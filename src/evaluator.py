import pandas as pd

class SystemEvaluator:
    @staticmethod
    def evaluate_query(results_df: pd.DataFrame, full_df: pd.DataFrame, relevance_condition, k: int = 5) -> dict:
        """
        relevance_condition: fungsi lambda untuk menentukan ground truth laptop yang relevan di dataset.
        """
        top_k = results_df.head(k)
        relevant_in_top_k = top_k[top_k.apply(relevance_condition, axis=1)]
        total_relevant_in_dataset = full_df[full_df.apply(relevance_condition, axis=1)]

        precision_at_k = len(relevant_in_top_k) / k
        total_rel_count = len(total_relevant_in_dataset)
        recall_at_k = len(relevant_in_top_k) / total_rel_count if total_rel_count > 0 else 0.0

        return {
            f"Precision@{k}": round(precision_at_k, 4),
            f"Recall@{k}": round(recall_at_k, 4),
            "Relevant_Found": len(relevant_in_top_k),
            "Total_Relevant_In_DB": total_rel_count
        }