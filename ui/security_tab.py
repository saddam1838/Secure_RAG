import gradio as gr
import json
import os
import re


def load_security_rules():
    try:
        with open("security_rules.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_current_thresholds():
    try:
        from config import settings

        return {
            "ml_threshold": getattr(settings, "ML_PROMPT_INJECTION_THRESHOLD", 0.85),
            "max_query_length": getattr(settings, "MAX_QUERY_LENGTH", 2000),
            "max_document_size_mb": getattr(settings, "MAX_DOC_SIZE_MB", 10),
            "chunk_size": getattr(settings, "CHUNK_SIZE", 500),
            "chunk_overlap": getattr(settings, "CHUNK_OVERLAP", 50),
            "top_k_dense": getattr(settings, "TOP_K_DENSE", 20),
            "top_k_bm25": getattr(settings, "TOP_K_BM25", 20),
            "rate_limit_requests": getattr(settings, "RATE_LIMIT_REQUESTS", 10),
            "rate_limit_period": getattr(settings, "RATE_LIMIT_PERIOD", 60),
        }
    except Exception:
        return {}


def test_rule_pattern(pattern, test_text):
    if not pattern or not test_text:
        return "⚠️ Please provide both a pattern and test text."
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        matches = compiled.findall(test_text)
        if not matches:
            return "✅ **No matches found.** The pattern does not match the test text."
        matches_html = "<br>".join(
            [f"• <code>{str(m)[:100]}</code>" for m in matches[:5]]
        )
        return f"🎯 **{len(matches)} match(es) found:**<br>{matches_html}"
    except re.error as e:
        return f"❌ **Invalid regex pattern:** {str(e)}"


def update_threshold(key, value):
    if not key or not value:
        return "⚠️ Please select a setting and enter a value."

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
        return f"❌ Unknown setting: {key}"

    min_val, max_val, cast_type = validations[key]

    try:
        typed_value = cast_type(value)
        if typed_value < min_val or typed_value > max_val:
            return f"❌ {key} must be between {min_val} and {max_val}"

        from config import settings

        attr_name = key.upper()
        if hasattr(settings, attr_name):
            setattr(settings, attr_name, typed_value)
        elif hasattr(settings, key):
            setattr(settings, key, typed_value)

        # Persist to .env
        try:
            env_path = ".env"
            lines = []
            key_found = False
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{attr_name}="):
                    lines[i] = f"{attr_name}={typed_value}\n"
                    key_found = True
                    break
            if not key_found:
                lines.append(f"{attr_name}={typed_value}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass

        return f"✅ {key} updated to {typed_value}. Restart app for full effect."
    except (ValueError, TypeError):
        return f"❌ Invalid value for {key}. Expected {cast_type.__name__}."


def get_rules_html():
    rules = load_security_rules()
    html = ""

    # Document Rules
    html += "<h4 style='margin:12px 0 8px 0;color:#0369a1;'>📄 Document Rules</h4>"
    html += "<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
    html += "<thead><tr style='background:#f3f4f6;'>"
    html += "<th style='padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;'>ID</th>"
    html += "<th style='padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;'>Name</th>"
    html += "<th style='padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;'>Pattern</th>"
    html += "<th style='padding:8px;text-align:center;border-bottom:2px solid #e5e7eb;'>Severity</th>"
    html += "</tr></thead><tbody>"

    for rule in rules.get("document_rules", []):
        sev = rule.get("severity", "low")
        color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#10b981"}.get(
            sev, "#6b7280"
        )
        pattern = rule.get("pattern", "")
        display_pattern = pattern[:80] + ("..." if len(pattern) > 80 else "")
        html += f"<tr>"
        html += f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;font-family:monospace;'>{rule.get('id', '')}</td>"
        html += f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{rule.get('name', '')}</td>"
        html += f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;font-family:monospace;font-size:11px;'>{display_pattern}</td>"
        html += f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;text-align:center;'><span style='background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:11px;'>{sev.upper()}</span></td>"
        html += "</tr>"
    html += "</tbody></table>"

    # Query Rules
    html += "<h4 style='margin:16px 0 8px 0;color:#0369a1;'>💬 Query Rules</h4>"
    html += "<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
    html += "<thead><tr style='background:#f3f4f6;'>"
    html += "<th style='padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;'>ID</th>"
    html += "<th style='padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;'>Name</th>"
    html += "<th style='padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;'>Pattern</th>"
    html += "<th style='padding:8px;text-align:center;border-bottom:2px solid #e5e7eb;'>Severity</th>"
    html += "</tr></thead><tbody>"

    for rule in rules.get("query_rules", []):
        sev = rule.get("severity", "low")
        color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#10b981"}.get(
            sev, "#6b7280"
        )
        pattern = rule.get("pattern", "")
        display_pattern = pattern[:80] + ("..." if len(pattern) > 80 else "")
        html += f"<tr>"
        html += f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;font-family:monospace;'>{rule.get('id', '')}</td>"
        html += f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{rule.get('name', '')}</td>"
        html += f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;font-family:monospace;font-size:11px;'>{display_pattern}</td>"
        html += f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;text-align:center;'><span style='background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:11px;'>{sev.upper()}</span></td>"
        html += "</tr>"
    html += "</tbody></table>"

    # Benign Patterns
    html += "<h4 style='margin:16px 0 8px 0;color:#0369a1;'>✨ Benign Patterns (Auto-Allow)</h4>"
    html += "<div style='background:#f0fdf4;padding:12px;border-radius:6px;font-family:monospace;font-size:12px;'>"
    for pattern in rules.get("benign_patterns", []):
        html += f"<code>{pattern}</code><br>"
    html += "</div>"

    return html


def get_thresholds_html():
    thresholds = get_current_thresholds()
    html = "<div style='background:#f9fafb;padding:16px;border-radius:8px;'>"
    for key, value in thresholds.items():
        html += f"<div style='margin-bottom:12px;display:flex;align-items:center;gap:12px;'>"
        html += f"<label style='flex:1;font-weight:600;font-size:13px;'>{key.replace('_', ' ').title()}</label>"
        html += f"<code style='background:#e5e7eb;padding:4px 8px;border-radius:4px;font-size:12px;'>{value}</code>"
        html += "</div>"
    html += "</div>"
    return html


def get_compliance_html():
    owasp = {
        "LLM01: Prompt Injection": {
            "status": "✅ Mitigated",
            "description": "Attackers manipulate LLMs through crafted inputs to bypass safety controls.",
            "implementation": "3-layer defense: Regex matching, DeBERTa ML classifier, and LLM-as-a-Judge.",
            "evidence": "Attack Simulator tests 50+ prompt injection variants. Detection rate shown in Security Dashboard.",
            "code_refs": [
                "services/security_service.py: should_block_query_advanced()",
                "security_rules.json: qry_001",
            ],
        },
        "LLM02: Insecure Output Handling": {
            "status": "✅ Mitigated",
            "description": "LLM outputs may contain harmful content executed downstream.",
            "implementation": "Output filter redacts harmful patterns (violence, hate speech, PII).",
            "evidence": "filter_output() applies regex-based redaction to all generated responses.",
            "code_refs": ["services/security_service.py: filter_output()"],
        },
        "LLM03: Training Data Poisoning": {
            "status": "⚠️ Partially Mitigated",
            "description": "Adversaries inject malicious content into knowledge data.",
            "implementation": "Document scanner checks for embedded prompts, base64 obfuscation, steganography, and null bytes.",
            "evidence": "Document Attack Test runs 25+ malicious payloads through the scanner.",
            "code_refs": [
                "services/security_service.py: scan_document(), scan_chunks()",
                "document_attacks.json",
            ],
        },
        "LLM04: Model Denial of Service": {
            "status": "⚠️ Partially Mitigated",
            "description": "Attackers overwhelm the model with excessive requests or oversized inputs.",
            "implementation": "Configurable rate limiting, query/document size limits, and token truncation.",
            "evidence": "SlowAPI middleware enforces rate limits. Thresholds configurable via this panel.",
            "code_refs": [
                "api/routes.py: @limiter.limit",
                "config.py: MAX_QUERY_LENGTH",
            ],
        },
        "LLM05: Supply Chain Vulnerabilities": {
            "status": "❌ Not Mitigated",
            "description": "Compromised dependencies or model weights introduce backdoors.",
            "implementation": "Future work: dependency scanning, SBOM generation, and model weight verification.",
            "evidence": "Currently using verified HuggingFace models only.",
            "code_refs": [],
        },
        "LLM06: Sensitive Information Disclosure": {
            "status": "✅ Mitigated",
            "description": "LLMs may leak PII, credentials, or confidential data.",
            "implementation": "Credential harvesting detection, output redaction, audit logging, and RAG grounding.",
            "evidence": "qry_003 regex catches credential requests. Audit logs stored in Supabase.",
            "code_refs": ["security_rules.json: qry_003", "services/audit_service.py"],
        },
        "LLM07: Insecure Plugin Design": {
            "status": "N/A",
            "description": "Plugins may expose dangerous functionality without proper controls.",
            "implementation": "No plugin architecture. System uses only verified internal services.",
            "evidence": "Architecture review confirms no external plugin execution.",
            "code_refs": [],
        },
        "LLM08: Excessive Agency": {
            "status": "N/A",
            "description": "LLMs may take unintended actions with excessive permissions.",
            "implementation": "No tool execution or external API calls. System is read-only (retrieval + generation).",
            "evidence": "No function calling, no tool use, no external integrations.",
            "code_refs": [],
        },
        "LLM09: Overreliance": {
            "status": "✅ Mitigated",
            "description": "Users may blindly trust LLM outputs without verification.",
            "implementation": "RAG grounding ensures answers cite retrieved documents. Evaluation metrics verify quality.",
            "evidence": "Every response includes source references. Evaluate tab shows LLM-as-a-Judge metrics.",
            "code_refs": [
                "services/rag_service.py: generate()",
                "services/llm_evaluator.py",
            ],
        },
        "LLM10: Model Theft": {
            "status": "❌ Not Mitigated",
            "description": "Adversaries may extract model weights or replicate model behavior.",
            "implementation": "Future work: model watermarking, API access controls, and query monitoring.",
            "evidence": "Currently using local models only. Basic auth protects endpoints.",
            "code_refs": [],
        },
    }

    mitre = {
        "AML.T0001: Prompt Injection": {
            "status": "✅ Mitigated",
            "description": "Direct manipulation of LLM behavior through crafted inputs.",
            "evidence": "3-layer detection: regex + ML + LLM judge.",
        },
        "AML.T0002: Data Poisoning": {
            "status": "⚠️ Partially Mitigated",
            "description": "Injecting malicious data into training or knowledge base.",
            "evidence": "Document scanner with 25+ attack patterns.",
        },
        "AML.T0003: Model Evasion": {
            "status": "❌ Not Mitigated",
            "description": "Adversarial examples that bypass model detection.",
            "evidence": "Future work: adversarial training.",
        },
        "AML.T0004: Model Theft": {
            "status": "❌ Not Mitigated",
            "description": "Extracting model weights or replicating behavior.",
            "evidence": "Future work: watermarking.",
        },
        "AML.T0005: Exfiltration": {
            "status": "⚠️ Partially Mitigated",
            "description": "Extracting training data or sensitive information.",
            "evidence": "Query filtering + output redaction.",
        },
        "AML.T0006: Reconnaissance": {
            "status": "✅ Mitigated",
            "description": "Probing system to discover vulnerabilities.",
            "evidence": "Rate limiting + audit logging + attack detection.",
        },
    }

    nist = {
        "Govern": {
            "status": "✅ Implemented",
            "description": "Establish policies, roles, and accountability.",
            "evidence": "RBAC (admin/user roles), audit logging, and security policies.",
        },
        "Map": {
            "status": "✅ Implemented",
            "description": "Identify and document AI risks and data flows.",
            "evidence": "OWASP/MITRE/NIST mappings and threat modeling in document scanner.",
        },
        "Measure": {
            "status": "✅ Implemented",
            "description": "Assess and track AI risks quantitatively.",
            "evidence": "Dynamic evaluation of RAG quality, attack resistance, and document security metrics.",
        },
        "Manage": {
            "status": "✅ Implemented",
            "description": "Prioritize and respond to AI risks.",
            "evidence": "Real-time blocking, audit trails, and configurable thresholds.",
        },
    }

    html = ""

    # OWASP
    html += (
        "<h3 style='margin:16px 0 12px 0;color:#111827;'>🔷 OWASP Top 10 for LLMs</h3>"
    )
    for risk, info in owasp.items():
        status = info["status"]
        if "✅" in status:
            status_color = "#10b981"
        elif "⚠️" in status:
            status_color = "#f59e0b"
        elif "❌" in status:
            status_color = "#ef4444"
        else:
            status_color = "#6b7280"

        html += f"<div style='background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:12px;'>"
        html += f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
        html += f"<strong style='color:#111827;'>{risk}</strong>"
        html += f"<span style='background:{status_color};color:white;padding:4px 10px;border-radius:12px;font-size:12px;'>{status}</span>"
        html += "</div>"
        html += f"<p style='margin:6px 0;color:#374151;font-size:13px;'><strong>Risk:</strong> {info['description']}</p>"
        html += f"<p style='margin:6px 0;color:#374151;font-size:13px;'><strong>Implementation:</strong> {info['implementation']}</p>"
        html += f"<p style='margin:6px 0;color:#0369a1;font-size:13px;'><strong>📊 Evidence:</strong> {info['evidence']}</p>"
        if info.get("code_refs"):
            refs = ", ".join(
                [
                    f"<code style='font-size:11px;background:#f3f4f6;padding:2px 6px;border-radius:3px;'>{ref}</code>"
                    for ref in info["code_refs"]
                ]
            )
            html += f"<p style='margin:6px 0;color:#6b7280;font-size:12px;'><strong>Code References:</strong> {refs}</p>"
        html += "</div>"

    # MITRE
    html += "<h3 style='margin:20px 0 12px 0;color:#111827;'>🎯 MITRE ATLAS</h3>"
    for technique, info in mitre.items():
        status = info["status"]
        if "✅" in status:
            status_color = "#10b981"
        elif "⚠️" in status:
            status_color = "#f59e0b"
        else:
            status_color = "#ef4444"

        html += f"<div style='background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin-bottom:8px;'>"
        html += f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        html += f"<div><strong>{technique}</strong><br><span style='color:#6b7280;font-size:12px;'>{info['description']}</span></div>"
        html += f"<span style='background:{status_color};color:white;padding:4px 10px;border-radius:12px;font-size:12px;'>{status}</span>"
        html += "</div>"
        html += f"<p style='margin:6px 0 0 0;color:#0369a1;font-size:12px;'><strong>Evidence:</strong> {info['evidence']}</p>"
        html += "</div>"

    # NIST
    html += "<h3 style='margin:20px 0 12px 0;color:#111827;'>📘 NIST AI RMF</h3>"
    for function, info in nist.items():
        html += f"<div style='background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin-bottom:8px;'>"
        html += f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        html += f"<div><strong>{function}</strong><br><span style='color:#6b7280;font-size:12px;'>{info['description']}</span></div>"
        html += f"<span style='background:#10b981;color:white;padding:4px 10px;border-radius:12px;font-size:12px;'>{info['status']}</span>"
        html += "</div>"
        html += f"<p style='margin:6px 0 0 0;color:#0369a1;font-size:12px;'><strong>Evidence:</strong> {info['evidence']}</p>"
        html += "</div>"

    return html


def security_tab():
    with gr.Tab("Security Config"):
        gr.Markdown("### ⚙️ Security Administration")
        gr.Markdown(
            "Manage rules, adjust thresholds, test patterns, and review compliance frameworks."
        )

        # ===== SECTION 1: Active Security Rules =====
        with gr.Accordion("📋 Active Security Rules", open=True):
            gr.Markdown("View regex patterns used for document and query scanning.")
            rules_html = gr.HTML(value=get_rules_html())

        # ===== SECTION 2: Rule Testing Playground =====
        with gr.Accordion("🧪 Rule Testing Playground", open=False):
            gr.Markdown(
                "Test regex patterns against sample text before adding them to active rules."
            )
            with gr.Row():
                with gr.Column():
                    test_pattern = gr.Textbox(
                        label="Regex Pattern",
                        placeholder="e.g., (?i)(ignore previous|system prompt)",
                        lines=2,
                    )
                    test_text = gr.Textbox(
                        label="Sample Text to Test",
                        placeholder="Paste text to test against the pattern...",
                        lines=4,
                    )
                    test_btn = gr.Button("🔍 Test Pattern", variant="secondary")
                with gr.Column():
                    test_result = gr.HTML(label="Test Result")
            test_btn.click(test_rule_pattern, [test_pattern, test_text], test_result)

        # ===== SECTION 3: Guardrail Configuration =====
        with gr.Accordion("🔧 Guardrail Configuration", open=False):
            gr.Markdown("""
            **Current Security Thresholds**
            
            These values control the sensitivity and limits of your security system.
            """)
            thresholds_html = gr.HTML(value=get_thresholds_html())

            gr.Markdown("---")
            gr.Markdown("**Update a Threshold:**")
            with gr.Row():
                threshold_key = gr.Dropdown(
                    choices=[
                        "ml_threshold",
                        "max_query_length",
                        "max_document_size_mb",
                        "chunk_size",
                        "chunk_overlap",
                        "top_k_dense",
                        "top_k_bm25",
                        "rate_limit_requests",
                        "rate_limit_period",
                    ],
                    label="Setting",
                    value="ml_threshold",
                )
                threshold_value = gr.Textbox(
                    label="New Value", placeholder="e.g., 0.85"
                )
                update_btn = gr.Button("💾 Update", variant="primary")
            update_result = gr.Markdown()
            update_btn.click(
                update_threshold, [threshold_key, threshold_value], update_result
            )

        # ===== SECTION 4: Compliance Framework Details =====
        with gr.Accordion("📊 Compliance Framework Mapping", open=False):
            gr.Markdown(
                "Detailed mapping to industry standards with implementation evidence and code references."
            )
            compliance_html = gr.HTML(value=get_compliance_html())
