import re
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import List, Dict
from config import settings

RULES_FILE = "security_rules.json"
with open(RULES_FILE, "r", encoding="utf-8") as f:
    SECURITY_RULES = json.load(f)

DOCUMENT_RULES = SECURITY_RULES.get("document_rules", [])
QUERY_RULES = SECURITY_RULES.get("query_rules", [])
MAX_DOC_SIZE_MB = SECURITY_RULES.get("max_document_size_mb", 10)
MAX_QUERY_LENGTH = SECURITY_RULES.get("max_query_length", 2000)
ML_THRESHOLD = SECURITY_RULES.get("ml_prompt_injection_threshold", 0.85)

_PI_DETECTOR = None


def _get_pi_detector():
    global _PI_DETECTOR
    if _PI_DETECTOR is None:
        from transformers import pipeline

        _PI_DETECTOR = pipeline(
            "text-classification", model="meta-llama/Prompt-Guard-86M", device=-1
        )
    return _PI_DETECTOR


os.makedirs(settings.LOG_DIR, exist_ok=True)
LOG_FILE = settings.LOG_DIR / "audit.log"
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
if not audit_logger.handlers:
    handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    audit_logger.addHandler(handler)


class SecurityGuard:
    @staticmethod
    def load_rules():
        return SECURITY_RULES

    @staticmethod
    def scan_document(content: str, filename: str) -> List[Dict]:
        issues = []
        size_mb = len(content.encode("utf-8")) / (1024 * 1024)
        if size_mb > MAX_DOC_SIZE_MB:
            issues.append(
                {
                    "rule_id": "doc_size",
                    "name": "Document Size Exceeded",
                    "severity": "high",
                    "description": f"Size {size_mb:.2f} MB exceeds limit of {MAX_DOC_SIZE_MB} MB",
                }
            )
        for rule in DOCUMENT_RULES:
            if rule["pattern"]:
                matches = re.findall(rule["pattern"], content)
                if matches:
                    issues.append(
                        {
                            "rule_id": rule["id"],
                            "name": rule["name"],
                            "severity": rule["severity"],
                            "description": rule["description"],
                            "matches": matches[:3],
                        }
                    )
        if "\x00" in content:
            issues.append(
                {
                    "rule_id": "doc_null",
                    "name": "Null Byte Detected",
                    "severity": "high",
                    "description": "File contains null bytes.",
                }
            )
        return issues

    @staticmethod
    def scan_chunks(chunks: List[str]) -> List[Dict]:
        issues = []
        detector = _get_pi_detector()
        for i, chunk in enumerate(chunks):
            try:
                result = detector(chunk)[0]
                if result["label"] == "INJECTION" and result["score"] > 0.8:
                    issues.append(
                        {
                            "chunk_index": i,
                            "score": result["score"],
                            "severity": "high",
                            "description": "Potential prompt injection detected in chunk.",
                        }
                    )
            except:
                continue
        return issues

    @staticmethod
    def scan_query(query: str) -> List[Dict]:
        issues = []
        for rule in QUERY_RULES:
            if rule["pattern"]:
                if re.search(rule["pattern"], query):
                    issues.append(
                        {
                            "rule_id": rule["id"],
                            "name": rule["name"],
                            "severity": rule["severity"],
                            "description": f"Query matched pattern: {rule['pattern']}",
                        }
                    )
        return issues

    @staticmethod
    def sanitize_input(text: str) -> str:
        if not isinstance(text, str):
            return ""
        if len(text) > MAX_QUERY_LENGTH:
            text = text[:MAX_QUERY_LENGTH] + "... [truncated]"
        return text

    @staticmethod
    def filter_output(text: str) -> str:
        harmful_patterns = [
            (r"\bkill\b.*\b(attack|violence|plan|method|instructions|guide)\b", "kill"),
            (
                r"\bterrorist\b.*\b(attack|plan|instructions|guide|method)\b",
                "terrorist",
            ),
            (r"\bhate\b.*\b(speech|crime|campaign|group|organization)\b", "hate"),
            (
                r"\bviolent\b.*\b(attack|act|plan|instructions|guide|method)\b",
                "violent",
            ),
        ]
        for pattern, word in harmful_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(rf"\b{word}\b", "[REDACTED]", text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def log_audit(user: str, action: str, details: dict):
        audit_logger.info(
            f"User: {user}, Action: {action}, Details: {json.dumps(details)}"
        )

    @staticmethod
    def check_permission(user_role: str, action: str) -> bool:
        from config import settings

        return action in settings.ROLES.get(user_role, [])

    @staticmethod
    def detect_prompt_injection(text: str) -> float:
        """
        Returns a score from 0.0 (safe) to 1.0 (injection) using Prompt-Guard.
        Only returns score if label is 'INJECTION', otherwise 0.0.
        """
        try:
            detector = _get_pi_detector()
            result = detector(text)[0]
            if result["label"] == "INJECTION":
                return result["score"]
            else:
                return 0.0
        except:
            return 0.0

    @staticmethod
    def get_ml_threshold() -> float:
        return ML_THRESHOLD

    @staticmethod
    def should_block_query(query: str, score: float) -> bool:
        """
        Determine if query should be blocked.
        - If query matches any regex rule, block (high confidence).
        - Else if score > threshold, block.
        """
        # First check regex rules
        for rule in QUERY_RULES:
            if rule["pattern"] and re.search(rule["pattern"], query, re.IGNORECASE):
                return True
        # Then check ML score
        return score > ML_THRESHOLD
