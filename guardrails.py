import re
from typing import Dict, Any
from datetime import datetime

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
}

try:
    from transformers import pipeline

    _toxicity_pipeline = pipeline(
        "text-classification", model="unitary/toxic-bert", top_k=None
    )

    def get_toxicity_score(text: str) -> float:
        for res in _toxicity_pipeline(text)[0]:
            if res["label"] == "toxic":
                return res["score"]
        return 0.0
except Exception:

    def get_toxicity_score(text: str) -> float:
        return 0.0


class Guardrail:
    """Output guardrails: PII redaction, toxicity filtering, system override detection."""

    @staticmethod
    def sanitize_output(text: str) -> Dict[str, Any]:
        violations = []
        cleaned = text

        # 1. PII Detection & Redaction
        for label, pattern in PII_PATTERNS.items():
            matches = re.findall(pattern, cleaned)
            if matches:
                violations.append(
                    {
                        "type": f"pii_{label}",
                        "count": len(matches),
                        "examples": matches[:2],
                    }
                )
                cleaned = re.sub(pattern, f"[REDACTED_{label.upper()}]", cleaned)

        # 2. Toxicity Score
        toxicity = get_toxicity_score(text)
        if toxicity > 0.8:
            violations.append(
                {"type": "toxicity", "score": round(toxicity, 3), "threshold": 0.8}
            )

        # 3. System override attempts (only if the entire output is an override)
        dangerous = [
            r"^system prompt",
            r"^ignore previous",
            r"^admin password",
            r"^sudo",
        ]
        for pat in dangerous:
            if re.search(pat, cleaned.strip(), re.IGNORECASE):
                violations.append({"type": "system_override", "pattern": pat})
                cleaned = "[Content blocked due to policy violation]"
                break

        return {
            "original": text,
            "cleaned": cleaned,
            "is_safe": len(violations) == 0,
            "violations": violations,
            "toxicity_score": round(toxicity, 3),
            "pii_redacted": any(v["type"].startswith("pii_") for v in violations),
        }

    @staticmethod
    def build_guardrail_report(prompt: str, response: str) -> Dict:
        out = Guardrail.sanitize_output(response)
        return {
            "timestamp": datetime.now().isoformat(),
            "input_length": len(prompt),
            "output_length": len(response),
            "output_safe": out["is_safe"],
            "toxicity_score": out["toxicity_score"],
            "pii_redacted": out["pii_redacted"],
            "violations": out["violations"],
            "final_output": out["cleaned"],
        }
