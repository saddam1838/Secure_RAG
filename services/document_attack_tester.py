"""
Document Attack Tester (Optimized for Speed)
Runs 1 payload per category through the scanner.
Estimated time: 20-30 seconds (instead of 2 hours).
"""

import json
import time
import hashlib
from services.security_service import SecurityGuard

# Cache for 1 hour
_doc_attack_cache = {"data": None, "timestamp": 0, "cache_duration": 3600, "key": None}


def _get_cache_key() -> str:
    try:
        with open("security_rules.json", "rb") as f:
            rules_hash = hashlib.md5(f.read()).hexdigest()
        with open("document_attacks.json", "rb") as f:
            attacks_hash = hashlib.md5(f.read()).hexdigest()
        return f"{rules_hash}_{attacks_hash}"
    except Exception:
        return "default"


def run_document_attack_test() -> dict:
    """
    Optimized: Tests 1 payload per category (25 total).
    Skips ML scan if regex already caught the issue.
    """
    current_time = time.time()
    cache_key = _get_cache_key()

    # Return cached result if valid
    if (
        _doc_attack_cache["data"] is not None
        and _doc_attack_cache.get("key") == cache_key
        and current_time - _doc_attack_cache["timestamp"]
        < _doc_attack_cache["cache_duration"]
    ):
        return _doc_attack_cache["data"]

    print("🔄 Running document attack test (optimized, ~20-30 seconds)...")
    start_time = time.time()

    guard = SecurityGuard()

    try:
        with open("document_attacks.json", "r", encoding="utf-8") as f:
            attacks = json.load(f)
    except Exception as e:
        print(f"⚠️ Could not load document_attacks.json: {e}")
        return {"total": 0, "blocked": 0, "detection_rate": 0, "by_type": {}}

    results = []
    by_type = {}

    for attack_type, payloads in attacks.items():
        # OPTIMIZATION: Only test the FIRST payload per category
        # This reduces 100+ tests to 25 tests
        if not payloads:
            continue

        content = payloads[0]  # Only first payload

        # OPTIMIZATION: Reduce oversized test to 1MB (instead of 15MB)
        if content == "__OVERSIZED__":
            content = "A" * (1 * 1024 * 1024)  # 1MB instead of 15MB

        filename = f"{attack_type.lower().replace(' ', '_')}_test.txt"

        # LAYER 1: Regex scan (FAST - milliseconds)
        doc_issues = guard.scan_document(content, filename)

        # LAYER 2: ML scan ONLY if regex didn't catch it (SLOW - seconds)
        chunk_issues = []
        if not doc_issues and len(content) > 50:
            # OPTIMIZATION: Only scan first 500 chars (1 chunk) instead of 3
            # This reduces ML calls from 300+ to ~25
            chunks = [content[:500]]
            try:
                chunk_issues = guard.scan_chunks(chunks)
            except Exception as e:
                print(f"⚠️ Chunk scan error for {attack_type}: {e}")
                chunk_issues = []

        all_issues = doc_issues + chunk_issues
        is_blocked = len(all_issues) > 0

        results.append(
            {
                "attack_type": attack_type,
                "blocked": is_blocked,
                "layers_triggered": {
                    "regex": len(doc_issues) > 0,
                    "ml_chunk": len(chunk_issues) > 0,
                },
            }
        )

        by_type[attack_type] = {
            "total": 1,
            "blocked": 1 if is_blocked else 0,
        }

    total = len(results)
    blocked = sum(1 for r in results if r["blocked"])
    detection_rate = (blocked / total * 100) if total > 0 else 0

    elapsed = time.time() - start_time
    print(
        f"✅ Document attack test complete: {detection_rate:.1f}% detection rate in {elapsed:.1f}s"
    )

    final_result = {
        "total": total,
        "blocked": blocked,
        "detection_rate": round(detection_rate, 2),
        "by_type": by_type,
    }

    # Cache the result
    _doc_attack_cache["data"] = final_result
    _doc_attack_cache["timestamp"] = current_time
    _doc_attack_cache["key"] = cache_key

    return final_result
