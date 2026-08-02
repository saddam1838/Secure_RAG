"""
Dynamic LLM-as-a-Judge RAG Evaluator
Automatically generates queries from the user's actual uploaded documents.
"""

import random
import hashlib
import time
import torch
import numpy as np
from typing import List, Dict, Tuple
from models.model_manager import ModelManager


class LLMJudgeEvaluator:
    def __init__(self):
        self.mm = ModelManager()
        self._generator = None
        self._cache = {
            "key": None,
            "data": None,
            "timestamp": 0,
            "ttl": 1800,
        }  # 30 min cache

    def _get_generator(self):
        if self._generator is None:
            self._generator = self.mm.get_generator()
        return self._generator

    def _cache_key(self, chunk_ids: List[str]) -> str:
        return hashlib.md5(str(sorted(chunk_ids)).encode()).hexdigest()

    def _get_cached(self, key: str) -> Dict:
        if (
            self._cache["key"] == key
            and time.time() - self._cache["timestamp"] < self._cache["ttl"]
        ):
            return self._cache["data"]
        return None

    def _set_cache(self, key: str, data: Dict):
        self._cache["key"] = key
        self._cache["data"] = data
        self._cache["timestamp"] = time.time()

    def judge_chunk_relevance(self, query: str, chunk_text: str) -> Tuple[int, str]:
        generator = self._get_generator()
        tokenizer = generator["tokenizer"]
        model = generator["model"]
        device = generator["device"]

        chunk_text = chunk_text[:500]
        prompt = f"""Rate how relevant this document chunk is to the query.

Query: {query}

Document chunk: {chunk_text}

Rate relevance (0=not relevant, 1=partially relevant, 2=relevant, 3=highly relevant):"""

        try:
            inputs = tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=400
            ).to(device)
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=15,
                    temperature=0.1,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            response = (
                tokenizer.decode(outputs[0], skip_special_tokens=True).strip().lower()
            )

            score = 0
            for digit in ["3", "2", "1", "0"]:
                if digit in response:
                    score = int(digit)
                    break
            return score, response[:50]
        except Exception as e:
            return 0, "Evaluation failed"

    def run_dynamic_evaluation(
        self, rag_service, num_queries=3, k=3, progress_callback=None
    ) -> Dict:
        """
        Dynamically evaluates RAG by sampling random chunks from the user's corpus.
        Uses the multi-user isolated local FAISS/memory.
        """
        username = getattr(rag_service, 'current_user', None)
        if not username:
            return {"has_documents": False, "error": "No user context provided."}
            
        # Get user-specific isolated corpus
        corpus = rag_service.user_corpuses.get(username, [])
        metadata = rag_service.user_metadatas.get(username, [])
        
        # If local is empty, try loading from cloud
        if not corpus and rag_service.use_cloud:
            rag_service.load_user_data(username)
            corpus = rag_service.user_corpuses.get(username, [])
            metadata = rag_service.user_metadatas.get(username, [])

        if not corpus or len(corpus) < num_queries:
            return {
                "has_documents": False,
                "error": "Not enough documents to evaluate. Please upload more content.",
            }

        # Cache key based on current chunk IDs
        chunk_ids = [m.get("chunk_id") for m in metadata]
        cache_key = self._cache_key(chunk_ids)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Sample random chunks from the USER'S actual documents
        indices = random.sample(range(len(corpus)), num_queries)
        all_results = []
        all_metrics = []
        for idx, i in enumerate(indices):
            if progress_callback:
                progress_callback(
                    (idx + 1) / num_queries,
                    f"Evaluating dynamic query {idx + 1}/{num_queries}...",
                )
            target_chunk = corpus[i]
            target_metadata = metadata[i]
            target_chunk_id = target_metadata.get("chunk_id", f"chunk_{i}")
            
            # Create a dynamic query from the chunk itself
            words = target_chunk.split()
            if len(words) > 15:
                query = "Explain the context of: " + " ".join(words[:10]) + "..."
            else:
                query = "Explain: " + target_chunk
                
            # Retrieve
            retrieved = rag_service.retrieve(query, k=k)
            
            # Evaluate with LLM
            judgments = []
            for rank, r in enumerate(retrieved):
                score, reasoning = self.judge_chunk_relevance(query, r.get("text", ""))
                # If it's the exact original chunk, guarantee it's marked as highly relevant
                is_exact_match = r.get("chunk_id") == target_chunk_id
                final_score = 3 if is_exact_match else score
                judgments.append(
                    {
                        "rank": rank + 1,
                        "chunk_id": r.get("chunk_id"),
                        "source": r.get("source", "unknown"),
                        "relevance_score": final_score,
                        "reasoning": reasoning if not is_exact_match else "Exact original chunk matched",
                        "is_relevant": final_score >= 2,
                    }
                )
            metrics = self._compute_metrics(judgments)
            all_results.append(
                {
                    "query": query,
                    "target_source": target_metadata.get("source", "unknown"),
                    "judgments": judgments,
                    "metrics": metrics,
                }
            )
            all_metrics.append(metrics)

        # Aggregate
        if all_metrics:
            avg_metrics = {
                "precision@k": round(np.mean([m["precision@k"] for m in all_metrics]), 3),
                "mrr": round(np.mean([m["mrr"] for m in all_metrics]), 3),
                "ndcg@k": round(np.mean([m["ndcg@k"] for m in all_metrics]), 3),
                "avg_relevance": round(np.mean([m["avg_relevance"] for m in all_metrics]), 2),
            }
        else:
            avg_metrics = {"precision@k": 0, "mrr": 0, "ndcg@k": 0, "avg_relevance": 0}

        final_result = {
            "has_documents": True,
            "queries_evaluated": num_queries,
            "chunks_per_query": k,
            "total_llm_calls": num_queries * k,
            "average_metrics": avg_metrics,
            "per_query_results": all_results,
        }
        self._set_cache(cache_key, final_result)
        return final_result


    def _compute_metrics(self, judgments: List[Dict]) -> Dict:
        if not judgments:
            return {
                "precision@k": 0,
                "mrr": 0,
                "ndcg@k": 0,
                "avg_relevance": 0,
                "relevant_chunks": 0,
                "total_chunks": 0,
            }

        k = len(judgments)
        relevant_flags = [1 if j["is_relevant"] else 0 for j in judgments]
        relevance_scores = [j["relevance_score"] for j in judgments]

        precision_at_k = sum(relevant_flags) / k if k > 0 else 0

        mrr = 0
        for i, flag in enumerate(relevant_flags):
            if flag == 1:
                mrr = 1 / (i + 1)
                break

        dcg = sum(score / np.log2(i + 2) for i, score in enumerate(relevance_scores))
        ideal_scores = sorted(relevance_scores, reverse=True)
        idcg = sum(score / np.log2(i + 2) for i, score in enumerate(ideal_scores))
        ndcg = dcg / idcg if idcg > 0 else 0

        avg_relevance = (
            sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        )

        return {
            "precision@k": round(precision_at_k, 3),
            "mrr": round(mrr, 3),
            "ndcg@k": round(ndcg, 3),
            "avg_relevance": round(avg_relevance, 2),
            "relevant_chunks": sum(relevant_flags),
            "total_chunks": k,
        }
