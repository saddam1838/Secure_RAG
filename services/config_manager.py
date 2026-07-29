"""
Security Configuration Manager
Handles loading, saving, and validating security configuration.
"""

import json
import os
import re
from typing import Dict, List, Tuple


class ConfigManager:
    """Manages security configuration with validation and persistence."""

    def __init__(self):
        self.rules_file = "security_rules.json"
        self.config_file = ".env"

    def load_security_rules(self) -> Dict:
        """Load security rules from JSON file."""
        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load security rules: {e}")
            return {}

    def save_security_rules(self, rules: Dict) -> Tuple[bool, str]:
        """Save security rules to JSON file."""
        try:
            # Validate all regex patterns before saving
            for rule_type in ["document_rules", "query_rules"]:
                for rule in rules.get(rule_type, []):
                    pattern = rule.get("pattern", "")
                    if pattern:
                        try:
                            re.compile(pattern)
                        except re.error as e:
                            return (
                                False,
                                f"Invalid regex in {rule.get('id', 'unknown')}: {str(e)}",
                            )

            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2, ensure_ascii=False)
            return True, "Security rules saved successfully"
        except Exception as e:
            return False, f"Failed to save rules: {str(e)}"

    def test_rule_against_text(self, pattern: str, text: str) -> Dict:
        """Test a regex pattern against sample text."""
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            matches = compiled.findall(text)
            return {
                "valid": True,
                "matches": len(matches),
                "matched_text": matches[:5],  # First 5 matches
                "error": None,
            }
        except re.error as e:
            return {"valid": False, "matches": 0, "matched_text": [], "error": str(e)}

    def get_current_thresholds(self) -> Dict:
        """Get current security thresholds from environment/config."""
        try:
            from config import settings

            return {
                "ml_threshold": getattr(settings, "ML_THRESHOLD", 0.85),
                "max_query_length": getattr(settings, "MAX_QUERY_LENGTH", 2000),
                "max_document_size_mb": getattr(settings, "MAX_DOCUMENT_SIZE_MB", 10),
                "chunk_size": getattr(settings, "CHUNK_SIZE", 500),
                "chunk_overlap": getattr(settings, "CHUNK_OVERLAP", 50),
                "top_k_dense": getattr(settings, "TOP_K_DENSE", 20),
                "top_k_bm25": getattr(settings, "TOP_K_BM25", 20),
                "rate_limit_requests": getattr(settings, "RATE_LIMIT_REQUESTS", 10),
                "rate_limit_period": getattr(settings, "RATE_LIMIT_PERIOD", 60),
            }
        except Exception as e:
            print(f"⚠️ Failed to load thresholds: {e}")
            return {}

    def update_threshold(self, key: str, value) -> Tuple[bool, str]:
        """Update a single threshold with validation."""
        validations = {
            "ml_threshold": (0.0, 1.0, float),
            "max_query_length": (100, 10000, int),
            "max_document_size_mb": (1, 100, int),
            "chunk_size": (100, 2000, int),
            "chunk_overlap": (0, 500, int),
            "top_k_dense": (1, 100, int),
            "top_k_bm25": (1, 100, int),
            "rate_limit_requests": (1, 1000, int),
            "rate_limit_period": (1, 3600, int),
        }

        if key not in validations:
            return False, f"Unknown threshold: {key}"

        min_val, max_val, cast_type = validations[key]

        try:
            typed_value = cast_type(value)
            if typed_value < min_val or typed_value > max_val:
                return False, f"{key} must be between {min_val} and {max_val}"

            # Update in-memory config
            from config import settings

            setattr(settings, key.upper(), typed_value)

            # Persist to .env file
            self._persist_to_env(key.upper(), typed_value)

            return True, f"{key} updated to {typed_value}"
        except (ValueError, TypeError) as e:
            return False, f"Invalid value for {key}: {str(e)}"

    def _persist_to_env(self, key: str, value):
        """Persist a setting to .env file."""
        try:
            env_path = ".env"
            lines = []
            key_found = False

            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    key_found = True
                    break

            if not key_found:
                lines.append(f"{key}={value}\n")

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"⚠️ Failed to persist to .env: {e}")

    def get_compliance_details(self) -> Dict:
        """Get expanded compliance framework details with evidence."""
        # OWASP Top 10 for LLMs - with detailed explanations and evidence
        owasp = {
            "LLM01: Prompt Injection": {
                "status": "✅ Mitigated",
                "description": "Attackers manipulate LLMs through crafted inputs to bypass safety controls.",
                "implementation": "Three-layer defense: (1) Regex pattern matching for known attacks, (2) DeBERTa ML classifier for semantic detection, (3) LLM-as-a-Judge for ambiguous cases.",
                "evidence": "Attack Simulator tests 50+ prompt injection variants. Current detection rate shown in Security Dashboard.",
                "code_refs": [
                    "services/security_service.py: should_block_query_advanced()",
                    "security_rules.json: qry_001",
                ],
            },
            "LLM02: Insecure Output Handling": {
                "status": "✅ Mitigated",
                "description": "LLM outputs may contain harmful content that gets executed downstream.",
                "implementation": "Output filter redacts harmful patterns (violence, hate speech, PII). All responses are sanitized before display.",
                "evidence": "filter_output() method applies regex-based redaction to all generated responses.",
                "code_refs": ["services/security_service.py: filter_output()"],
            },
            "LLM03: Training Data Poisoning": {
                "status": "⚠️ Partially Mitigated",
                "description": "Adversaries inject malicious content into training/knowledge data.",
                "implementation": "Document scanner checks for: embedded system prompts, base64 obfuscation, zero-width steganography, null bytes, chunk-level ML detection.",
                "evidence": "Document Attack Test runs 25+ malicious payloads through scanner. Detection rate shown in Security Dashboard.",
                "code_refs": [
                    "services/security_service.py: scan_document(), scan_chunks()",
                    "document_attacks.json",
                ],
            },
            "LLM04: Model Denial of Service": {
                "status": "⚠️ Partially Mitigated",
                "description": "Attackers overwhelm the model with excessive requests or oversized inputs.",
                "implementation": "Rate limiting (10 req/60s), query length truncation (2000 chars), document size limits (10MB), token truncation in generation.",
                "evidence": "SlowAPI middleware enforces rate limits. Configurable via Security Config tab.",
                "code_refs": [
                    "api/routes.py: @limiter.limit",
                    "config.py: MAX_QUERY_LENGTH",
                ],
            },
            "LLM05: Supply Chain Vulnerabilities": {
                "status": "❌ Not Mitigated",
                "description": "Compromised dependencies or model weights can introduce backdoors.",
                "implementation": "Future work: dependency scanning (safety, pip-audit), SBOM generation, model weight verification.",
                "evidence": "Currently using verified HuggingFace models only. No automated supply chain checks.",
                "code_refs": [],
            },
            "LLM06: Sensitive Information Disclosure": {
                "status": "✅ Mitigated",
                "description": "LLMs may leak PII, credentials, or confidential data.",
                "implementation": "Credential harvesting detection in queries, output redaction, audit logging of all queries/responses, RAG grounding prevents hallucinated secrets.",
                "evidence": "qry_003 regex catches credential requests. Audit logs stored in Supabase.",
                "code_refs": [
                    "security_rules.json: qry_003",
                    "services/audit_service.py",
                ],
            },
            "LLM07: Insecure Plugin Design": {
                "status": "N/A",
                "description": "Plugins may expose dangerous functionality without proper controls.",
                "implementation": "No plugin architecture in current scope. System uses only verified internal services.",
                "evidence": "Architecture review confirms no external plugin execution.",
                "code_refs": [],
            },
            "LLM08: Excessive Agency": {
                "status": "N/A",
                "description": "LLMs may take unintended actions with excessive permissions.",
                "implementation": "No tool execution or external API calls. System is read-only (retrieval + generation only).",
                "evidence": "No function calling, no tool use, no external integrations.",
                "code_refs": [],
            },
            "LLM09: Overreliance": {
                "status": "✅ Mitigated",
                "description": "Users may blindly trust LLM outputs without verification.",
                "implementation": "RAG grounding ensures answers come from retrieved documents. Source citations provided for every response. Evaluation metrics verify retrieval quality.",
                "evidence": "Every response includes source references. Evaluate tab shows retrieval quality metrics.",
                "code_refs": [
                    "services/rag_service.py: generate()",
                    "services/llm_evaluator.py",
                ],
            },
            "LLM10: Model Theft": {
                "status": "❌ Not Mitigated",
                "description": "Adversaries may extract model weights or replicate model behavior.",
                "implementation": "Future work: model watermarking, API access controls, query monitoring for extraction attempts.",
                "evidence": "Currently using local models only (no API exposure). Basic auth protects endpoints.",
                "code_refs": [],
            },
        }

        # MITRE ATLAS
        mitre = {
            "AML.T0001: Prompt Injection": {
                "status": "✅ Mitigated",
                "description": "Direct manipulation of LLM behavior through crafted inputs.",
                "evidence": "3-layer detection: regex + ML + LLM judge.",
            },
            "AML.T0002: Data Poisoning": {
                "status": "⚠️ Partially",
                "description": "Injecting malicious data into training/knowledge base.",
                "evidence": "Document scanner with 25+ attack patterns.",
            },
            "AML.T0003: Model Evasion": {
                "status": "❌ Not",
                "description": "Adversarial examples that bypass model detection.",
                "evidence": "Future work: adversarial training.",
            },
            "AML.T0004: Model Theft": {
                "status": "❌ Not",
                "description": "Extracting model weights or replicating behavior.",
                "evidence": "Future work: watermarking.",
            },
            "AML.T0005: Exfiltration": {
                "status": "⚠️ Partially",
                "description": "Extracting training data or sensitive information.",
                "evidence": "Query filtering + output redaction.",
            },
            "AML.T0006: Reconnaissance": {
                "status": "✅ Mitigated",
                "description": "Probing system to discover vulnerabilities.",
                "evidence": "Rate limiting + audit logging + attack detection.",
            },
        }

        # NIST AI RMF
        nist = {
            "Govern": {
                "status": "✅ Implemented",
                "description": "Establish policies, roles, and accountability.",
                "evidence": "RBAC (admin/user roles), audit logging, security policies in security_rules.json.",
            },
            "Map": {
                "status": "✅ Implemented",
                "description": "Identify and document AI risks and data flows.",
                "evidence": "OWASP/MITRE/NIST mappings, threat modeling in document scanner.",
            },
            "Measure": {
                "status": "✅ Implemented",
                "description": "Assess and track AI risks quantitatively.",
                "evidence": "Dynamic evaluation: RAG quality (LLM-as-a-Judge), attack resistance, document security metrics.",
            },
            "Manage": {
                "status": "✅ Implemented",
                "description": "Prioritize and respond to AI risks.",
                "evidence": "Real-time blocking, audit trail, configurable thresholds, incident response via security dashboard.",
            },
        }

        return {"owasp": owasp, "mitre": mitre, "nist": nist}
