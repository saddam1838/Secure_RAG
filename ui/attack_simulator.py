import gradio as gr
import json
from services.security_service import SecurityGuard
from services.rag_service import RAGService

security = SecurityGuard()
rag = RAGService()


# ============ SECTION 1: QUERY ATTACKS ============
def run_query_attack(attack_type, custom_query):
    if attack_type == "Custom" and custom_query:
        queries = [custom_query]
    else:
        with open("attacks.json", "r", encoding="utf-8") as f:
            attacks = json.load(f)
        queries = attacks.get(attack_type, [])

    results_md = "### 💬 Query Attack Results\n\n"
    results_md += "| Status | Attack Query | Detection Reason | ML Confidence |\n"
    results_md += "| :--- | :--- | :--- | :--- |\n"

    for q in queries:
        issues = security.scan_query(q)
        ml_score = security.detect_prompt_injection(q)
        blocked = bool(issues) or ml_score > security.get_ml_threshold()

        if issues:
            reason = issues[0]["name"]
        elif blocked:
            reason = "ML score exceeded threshold"
        else:
            reason = "Passed all checks"

        status = "❌ **Blocked**" if blocked else "✅ **Allowed**"
        score_pct = f"{ml_score * 100:.2f}%"
        safe_query = q.replace("|", "\\|").replace("\n", " ").strip()[:80]
        results_md += f"| {status} | {safe_query} | {reason} | `{score_pct}` |\n"

    return results_md


# ============ SECTION 2: DOCUMENT ATTACKS ============
def run_document_attack(attack_type, custom_content):
    """
    Tests the document scanner against malicious payloads using the
    production scanning pipeline.
    """
    if attack_type == "Custom" and custom_content:
        payloads = [(custom_content, "custom_test.txt")]
    elif attack_type == "Oversized Document":
        payloads = [("A" * (15 * 1024 * 1024), "oversized_test.txt")]
    else:
        with open("document_attacks.json", "r", encoding="utf-8") as f:
            attacks = json.load(f)
        payloads = [
            (content, f"{attack_type.lower().replace(' ', '_')}_test.txt")
            for content in attacks.get(attack_type, [])
        ]

    results_md = "### 📄 Document Scanner Test Results\n\n"
    results_md += "| Status | Attack Type | Detection Layer | Severity | Details |\n"
    results_md += "| :--- | :--- | :--- | :--- | :--- |\n"

    total = 0
    blocked = 0

    for content, filename in payloads:
        total += 1

        # LAYER 1: Real document scanner (regex rules)
        doc_issues = security.scan_document(content, filename)

        # LAYER 2: If passed regex, chunk it and run ML detector
        chunk_issues = []
        if not doc_issues and len(content) > 50:
            chunks = [
                content[i : i + 500] for i in range(0, min(len(content), 1500), 500)
            ]
            try:
                chunk_issues = security.scan_chunks(chunks)
            except Exception:
                chunk_issues = []

        all_issues = doc_issues + chunk_issues
        is_blocked = len(all_issues) > 0

        if is_blocked:
            blocked += 1
            severity_order = {"high": 0, "medium": 1, "low": 2}
            top_issue = min(
                all_issues,
                key=lambda x: severity_order.get(x.get("severity", "low"), 3),
            )
            layer = (
                "📋 Regex Scanner" if top_issue in doc_issues else "🤖 ML Chunk Scanner"
            )
            status = "❌ **Blocked**"
            severity = f"`{top_issue.get('severity', 'unknown').upper()}`"
            details = top_issue.get("name", "Unknown")[:60]
        else:
            status = "✅ **Passed**"
            layer = "—"
            severity = "—"
            details = "No threats detected"

        safe_type = attack_type.replace("|", "\\|")[:40]
        results_md += f"| {status} | {safe_type} | {layer} | {severity} | {details} |\n"

    detection_rate = (blocked / total * 100) if total > 0 else 0
    summary_color = (
        "#10b981"
        if detection_rate >= 90
        else "#f59e0b"
        if detection_rate >= 70
        else "#ef4444"
    )

    results_md += f"\n---\n\n"
    results_md += f"**📊 Document Attack Detection Rate:** "
    results_md += f"<span style='color:{summary_color};font-weight:bold;font-size:18px;'>{detection_rate:.0f}%</span> "
    results_md += f"({blocked}/{total} malicious documents blocked)\n\n"

    if detection_rate == 100:
        results_md += "✅ **Excellent.** The document scanner blocked all adversarial payloads. Malicious files would not be indexed.\n"
    elif detection_rate >= 80:
        results_md += "⚠️ **Good.** Most payloads were blocked, but some slipped through. Review the failures above.\n"
    else:
        results_md += "🛑 **Critical.** Many malicious documents would be indexed. Update security rules to improve detection.\n"

    return results_md


# ============ UI LAYOUT ============
def attack_simulator_tab():
    with gr.Tab("Attack Simulator"):
        gr.Markdown("""
        ### 🎯 Security Testing
        Test both **query-level** and **document-level** defenses.
        """)

        # ===== SECTION 1: Query Attacks =====
        gr.Markdown("---")
        gr.Markdown("### 💬 Query-Level Attacks")
        gr.Markdown("Test if the chat blocks malicious prompts.")

        with gr.Row():
            with gr.Column(scale=2):
                query_attack_type = gr.Dropdown(
                    choices=[
                        "Prompt Injection",
                        "Role Override",
                        "System Prompt Extraction",
                        "SQL Injection",
                        "Credential Harvesting",
                        "Hidden Prompt",
                        "Unicode Attack",
                        "Base64 Attack",
                        "Crescendo",
                        "Jailbreak Suffix",
                        "Indirect HTML",
                        "Tool Manipulation",
                        "Custom",
                    ],
                    label="Attack Type",
                    value="Prompt Injection",
                )
                custom_query = gr.Textbox(
                    label="Custom Query",
                    placeholder="Enter your own adversarial prompt...",
                    lines=2,
                )
            with gr.Column(scale=1):
                query_run_btn = gr.Button(
                    "🚀 Run Query Attack", variant="primary", size="lg"
                )

        query_output = gr.Markdown(label="Query Attack Results")
        query_run_btn.click(
            run_query_attack, [query_attack_type, custom_query], query_output
        )

        # ===== SECTION 2: Document Attacks =====
        gr.Markdown("---")
        gr.Markdown("### 📄 Document-Level Attacks")
        gr.Markdown("""
        Tests the document scanner against malicious payloads using the same
        scanning pipeline as real uploads.
        """)

        with gr.Row():
            with gr.Column(scale=2):
                doc_attack_type = gr.Dropdown(
                    choices=[
                        "Embedded System Prompt",
                        "Base64 Obfuscation",
                        "Zero-Width Steganography",
                        "HTML/Script Injection",
                        "Null Byte Injection",
                        "Indirect Prompt Injection",
                        "XML/Entity Injection",
                        "Markdown Injection",
                        "Oversized Document",
                        "Multi-Vector Attack",
                        "Custom",
                    ],
                    label="Document Attack Type",
                    value="Embedded System Prompt",
                )
                custom_doc_content = gr.Textbox(
                    label="Custom Document Content",
                    placeholder="Paste malicious document content here...",
                    lines=4,
                )
            with gr.Column(scale=1):
                doc_run_btn = gr.Button(
                    "🔍 Run Document Attack", variant="primary", size="lg"
                )

        doc_output = gr.Markdown(label="Document Attack Results")
        doc_run_btn.click(
            run_document_attack, [doc_attack_type, custom_doc_content], doc_output
        )
