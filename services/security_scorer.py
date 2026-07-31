import json
import time
from config import settings
from services.cloud_storage import cloud_storage

_CACHE_DURATION = 86400  # 24 hours

_benchmark_cache = {"data": None, "timestamp": 0, "cache_duration": _CACHE_DURATION}
_rag_cache = {"data": None, "timestamp": 0, "cache_duration": _CACHE_DURATION}
_doc_security_cache = {"data": None, "timestamp": 0, "cache_duration": _CACHE_DURATION}


def _get_cached_benchmark():
    current_time = time.time()
    if _benchmark_cache["data"] is not None and (current_time - _benchmark_cache["timestamp"]) < _CACHE_DURATION:
        return _benchmark_cache["data"]
    try:
        from services.benchmark_service import run_benchmark
        print("🔄 Refreshing benchmark cache...")
        _benchmark_cache["data"] = run_benchmark()
        _benchmark_cache["timestamp"] = current_time
        return _benchmark_cache["data"]
    except Exception as e:
        print(f"⚠️ Benchmark failed: {e}")
        return {"total_attacks": 0, "blocked": 0, "by_type": {}}


def _get_cached_rag_quality():
    """System-wide RAG quality evaluation - no user filter."""
    current_time = time.time()
    if _rag_cache["data"] is not None and (current_time - _rag_cache["timestamp"]) < _CACHE_DURATION:
        return _rag_cache["data"]
    try:
        from services.rag_service import RAGService
        rag = RAGService()
        
        # Skip expensive evaluation if no documents
        if len(rag.corpus) == 0:
            result = {"has_documents": False, "overall_score": 0, "status": "No Documents", "color": "#6b7280", "emoji": "⚪", "metrics": {}}
            _rag_cache["data"] = result
            _rag_cache["timestamp"] = current_time
            return result

        from services.llm_evaluator import LLMJudgeEvaluator
        print("🔄 Refreshing RAG quality cache...")
        evaluator = LLMJudgeEvaluator()
        # 🔥 FIX: Don't pass username parameter - evaluator doesn't accept it
        results = evaluator.run_dynamic_evaluation(rag, num_queries=2, k=3)
        
        if not results.get("has_documents"):
            result = {"has_documents": False, "overall_score": 0, "status": "No Documents", "color": "#6b7280", "emoji": "⚪", "metrics": {}}
        else:
            avg = results["average_metrics"]
            overall = (avg.get("precision@k", 0) * 0.3 + avg.get("mrr", 0) * 0.3 + avg.get("ndcg@k", 0) * 0.3 + (avg.get("avg_relevance", 0) / 3) * 0.1) * 100
            status, color, emoji = ("Excellent", "#10b981", "🟢") if overall >= 75 else ("Good", "#f59e0b", "🟡") if overall >= 55 else ("Fair", "#f97316", "🟠") if overall >= 35 else ("Needs Improvement", "#ef4444", "🔴")
            result = {"has_documents": True, "overall_score": round(overall, 1), "status": status, "color": color, "emoji": emoji, "metrics": avg}
            
        _rag_cache["data"] = result
        _rag_cache["timestamp"] = current_time
        return result
    except Exception as e:
        print(f"⚠️ RAG quality evaluation failed: {e}")
        return {"has_documents": True, "overall_score": 0, "status": "Error", "color": "#6b7280", "emoji": "⚪", "metrics": {}}


def _get_cached_document_security():
    current_time = time.time()
    if _doc_security_cache["data"] is not None and (current_time - _doc_security_cache["timestamp"]) < _CACHE_DURATION:
        return _doc_security_cache["data"]
    try:
        from services.document_attack_tester import run_document_attack_test
        print("🔄 Refreshing document security cache...")
        _doc_security_cache["data"] = run_document_attack_test()
        _doc_security_cache["timestamp"] = current_time
        return _doc_security_cache["data"]
    except Exception as e:
        print(f"⚠️ Document security test failed: {e}")
        return {"total": 0, "blocked": 0, "detection_rate": 0, "by_type": {}}


class SecurityScorer:
    @staticmethod
    def calculate_system_capability_score() -> dict:
        benchmark = _get_cached_benchmark()
        attack_total = benchmark.get("total_attacks", 0)
        attack_blocked = benchmark.get("blocked", 0)
        query_attack_score = (attack_blocked / attack_total * 100) if attack_total > 0 else 0.0
        
        doc_attack_result = _get_cached_document_security()
        doc_attack_score = doc_attack_result.get("detection_rate", 0)
        doc_attack_total = doc_attack_result.get("total", 0)
        doc_attack_blocked = doc_attack_result.get("blocked", 0)

        try:
            with open("owasp_mappings.json", "r", encoding="utf-8") as f: owasp = json.load(f)
            with open("mitre_mappings.json", "r", encoding="utf-8") as f: mitre = json.load(f)
            with open("nist_mappings.json", "r", encoding="utf-8") as f: nist = json.load(f)
            compliance_score = (
                (sum(1 for v in owasp.values() if "✅" in v.get("status", "")) / len(owasp) * 100 if owasp else 0) +
                (sum(1 for v in mitre.values() if "✅" in v) / len(mitre) * 100 if mitre else 0) +
                (sum(1 for v in nist.values() if "✅" in v) / len(nist) * 100 if nist else 0)
            ) / 3
        except Exception:
            compliance_score = 0

        try:
            from services.security_service import SecurityGuard
            stats = SecurityGuard().adaptive_stats
            config_score = 100.0 - (20 if stats.get("ml_threshold", 0) < 0.7 else 0) - (10 if stats.get("max_query_length", 0) > 5000 else 0) - (10 if stats.get("max_document_size_mb", 0) > 20 else 0)
        except Exception:
            config_score = 100.0

        final_score = (query_attack_score * 0.35) + (doc_attack_score * 0.15) + (compliance_score * 0.30) + (config_score * 0.20)
        status, color, emoji = ("Excellent", "#10b981", "🟢") if final_score >= 90 else ("Good", "#f59e0b", "🟡") if final_score >= 75 else ("Fair", "#f97316", "🟠") if final_score >= 50 else ("Needs Improvement", "#ef4444", "🔴")

        return {
            "overall_score": round(final_score, 1), "status": status, "color": color, "emoji": emoji,
            "breakdown": {"Query Attack Resistance": round(query_attack_score, 1), "Document Scanner": round(doc_attack_score, 1), "Compliance Coverage": round(compliance_score, 1), "Security Configuration": round(config_score, 1)},
            "stats": {"attacks_tested": attack_total, "attacks_blocked": attack_blocked, "attack_by_type": benchmark.get("by_type", {}), "doc_attacks_tested": doc_attack_total, "doc_attacks_blocked": doc_attack_blocked},
        }

    @staticmethod
    def calculate_user_documents_score(username: str = "admin") -> dict:
        """User-specific - NOT cached, always fresh from Supabase."""
        total_scans = safe_scans = total_chunks = 0
        unsafe_documents = []

        if cloud_storage.is_cloud_enabled:
            try:
                all_docs = cloud_storage.supabase.table("documents").select("id, is_safe, filename, uploaded_by").eq("uploaded_by", username).execute().data
                total_scans = len(all_docs)
                safe_scans = sum(1 for d in all_docs if d.get("is_safe"))
                unsafe_documents = [d.get("filename") for d in all_docs if not d.get("is_safe")]
                
                from services.rag_service import RAGService
                rag = RAGService()
                user_filenames = [d.get("filename") for d in all_docs]
                total_chunks = sum(1 for m in rag.metadata if m.get("source") in user_filenames and m.get("uploaded_by") == username) if total_scans > 0 else 0
            except Exception as e:
                print(f"⚠️ Failed to fetch document stats: {e}")
        else:
            from services.rag_service import RAGService
            rag = RAGService()
            user_chunks = [m for m in rag.metadata if m.get("uploaded_by") == username]
            total_scans = len(set(m.get("source") for m in user_chunks))
            safe_scans = total_scans
            total_chunks = len(user_chunks)

        if total_scans == 0:
            return {"overall_score": 0.0, "status": "No Documents", "color": "#6b7280", "emoji": "⚪", "breakdown": {"Document Safety": 0.0, "Knowledge Coverage": 0.0}, "stats": {"documents_scanned": 0, "documents_safe": 0, "documents_blocked": 0, "total_chunks": 0}, "unsafe_documents": [], "recommendation": "Upload documents to start building your knowledge base."}
        
        doc_safety_score = safe_scans / total_scans * 100
        quality_score = min(100.0, (total_chunks / 50) * 10)
        final_score = (doc_safety_score * 0.70) + (quality_score * 0.30)
        status, color, emoji = ("Excellent", "#10b981", "🟢") if final_score >= 90 else ("Good", "#f59e0b", "🟡") if final_score >= 75 else ("Fair", "#f97316", "🟠") if final_score >= 50 else ("Needs Attention", "#ef4444", "🔴")
        recommendation = "Your documents are secure and well-indexed." if final_score >= 90 else "Review blocked documents." if doc_safety_score < 80 else "Upload more documents to improve coverage." if quality_score < 50 else "Your document collection is in good shape."

        return {
            "overall_score": round(final_score, 1), "status": status, "color": color, "emoji": emoji,
            "breakdown": {"Document Safety": round(doc_safety_score, 1), "Knowledge Coverage": round(quality_score, 1)},
            "stats": {"documents_scanned": total_scans, "documents_safe": safe_scans, "documents_blocked": total_scans - safe_scans, "total_chunks": total_chunks},
            "unsafe_documents": unsafe_documents[:5], "recommendation": recommendation,
        }

    @staticmethod
    def calculate_posture_score(username: str = "admin") -> dict:
        system_score = SecurityScorer.calculate_system_capability_score()
        user_score = SecurityScorer.calculate_user_documents_score(username)
        rag_score = _get_cached_rag_quality()

        user_rag_score = rag_score if user_score["stats"]["documents_scanned"] > 0 else {"has_documents": False, "overall_score": 0, "status": "No Documents", "color": "#6b7280", "emoji": "⚪", "metrics": {}}

        final_score = (system_score["overall_score"] * 0.40) + (user_score["overall_score"] * 0.30) + (user_rag_score.get("overall_score", 0) * 0.30) if user_score["stats"]["documents_scanned"] > 0 and user_rag_score.get("has_documents") else system_score["overall_score"]
        status, color = ("Excellent", "#10b981") if final_score >= 90 else ("Good", "#f59e0b") if final_score >= 75 else ("Fair", "#f97316") if final_score >= 50 else ("At Risk", "#ef4444")

        return {
            "overall_score": round(final_score, 1), "status": status, "color": color,
            "system_capability": system_score, "user_documents": user_score, "rag_quality": user_rag_score,
            "breakdown": {"System Capability": round(system_score["overall_score"], 1), "User Documents": round(user_score["overall_score"], 1), "RAG Quality": round(user_rag_score.get("overall_score", 0), 1)},
            "stats": {**system_score["stats"], **user_score["stats"]}, "attack_by_type": system_score["stats"].get("attack_by_type", {}),
            "unsafe_documents": user_score["unsafe_documents"], "recommendation": user_score["recommendation"],
        }
