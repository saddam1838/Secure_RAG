import numpy as np
import pytrec_eval
from typing import List, Dict
from config import settings


class EvaluationService:
    @staticmethod
    def compute_retrieval_metrics(
        queries: List[str],
        retrieved_docs: List[List[str]],  # Now expects List of chunk_ids
        relevant_docs: List[List[str]],  # List of relevant chunk_ids
        k: int = None,
    ) -> Dict[str, float]:
        if k is None:
            k = getattr(settings, "RETRIEVAL_K", 10)

        qrel = {}
        run = {}

        for i, q in enumerate(queries):
            qid = f"q{i}"

            # Ensure all doc IDs are strings for pytrec_eval compatibility
            qrel[qid] = {str(doc_id): 1 for doc_id in relevant_docs[i]}

            # Assign decreasing scores based on rank (1.0 for 1st, 0.5 for 2nd, etc.)
            run[qid] = {
                str(doc_id): 1.0 / (rank + 1)
                for rank, doc_id in enumerate(retrieved_docs[i][:k])
            }

        # Use valid pytrec_eval measure names with explicit cutoffs
        measures = {"map", "ndcg_cut_10", "recall_10"}
        evaluator = pytrec_eval.RelevanceEvaluator(qrel, measures)
        results = evaluator.evaluate(run)

        # Use .get() with default 0.0 to prevent KeyError if a measure is missing
        avg_recall = np.mean([r.get("recall_10", 0.0) for r in results.values()])
        avg_map = np.mean([r.get("map", 0.0) for r in results.values()])
        avg_ndcg = np.mean([r.get("ndcg_cut_10", 0.0) for r in results.values()])

        return {
            "recall@10": float(avg_recall),
            "map": float(avg_map),
            "ndcg@10": float(avg_ndcg),
        }
