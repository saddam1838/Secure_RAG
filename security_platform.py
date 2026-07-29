import json
from services.security_service import SecurityGuard
from services.rag_service import RAGService
from guardrails import Guardrail


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def get_owasp_status():
    data = load_json("owasp_mappings.json")
    return [
        {"Risk": k, "Status": v["status"], "Implementation": v["implementation"]}
        for k, v in data.items()
    ]


def get_mitre_mapping():
    data = load_json("mitre_mappings.json")
    return [{"Technique": k, "Status": v} for k, v in data.items()]


def get_nist_mapping():
    data = load_json("nist_mappings.json")
    return [{"Function": k, "Status": v} for k, v in data.items()]


def run_attack_simulation(attack_type, query, security_guard, rag_pipeline, guardrail):
    issues = security_guard.scan_query(query)
    ml_score = security_guard.detect_prompt_injection(query)
    blocked = bool(issues) or ml_score > security_guard.get_ml_threshold()

    # Fixed: Prevents IndexError if blocked by ML score but no regex issues were found
    if issues:
        reason = issues[0]["name"]
    elif blocked:
        reason = "ML score exceeded threshold"
    else:
        reason = "None"

    return {
        "attack_type": attack_type,
        "query": query,
        "blocked": blocked,
        "reason": reason,
        "ml_score": ml_score,
    }


def run_all_attacks():
    security = SecurityGuard()
    rag = RAGService()
    guardrail = Guardrail()
    with open("attacks.json", "r", encoding="utf-8") as f:
        attacks = json.load(f)
    results = []
    for attack_type, queries in attacks.items():
        for q in queries:
            results.append(
                run_attack_simulation(attack_type, q, security, rag, guardrail)
            )
    return results
