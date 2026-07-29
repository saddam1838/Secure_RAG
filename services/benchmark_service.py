import json
from collections import defaultdict
from services.security_service import SecurityGuard

ATTACKS_FILE = "attacks.json"

def run_all_attacks():
    guard = SecurityGuard()
    with open(ATTACKS_FILE, "r", encoding="utf-8") as f:
        attacks = json.load(f)
    
    results = []
    for attack_type, queries in attacks.items():
        for q in queries:
            score = guard.detect_prompt_injection(q)
            blocked = guard.should_block_query(q, score)
            results.append({
                "attack_type": attack_type,
                "query": q,
                "blocked": blocked,
                "ml_score": round(score, 4)
            })
    return results

def run_benchmark():
    results = run_all_attacks()
    total = len(results)
    blocked = sum(1 for r in results if r["blocked"])
    detection_rate = (blocked / total) * 100 if total else 0
    
    by_type = {}
    for r in results:
        at = r["attack_type"]
        if at not in by_type:
            by_type[at] = {"total": 0, "blocked": 0}
        by_type[at]["total"] += 1
        if r["blocked"]:
            by_type[at]["blocked"] += 1
            
    return {
        "total_attacks": total,
        "blocked": blocked,
        "detection_rate": round(detection_rate, 2),
        "by_type": by_type,
    }

class BenchmarkService:
    @staticmethod
    def get_attack_stats():
        results = run_all_attacks()
        stats = defaultdict(int)
        for r in results:
            stats[r["attack_type"]] += 1
        return dict(stats)

    @staticmethod
    def run_benchmark():
        return run_benchmark()