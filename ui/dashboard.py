import gradio as gr
import json
from services.security_scorer import SecurityScorer


def get_security_score_html(username="admin"):
    """Generate security score HTML for a specific user."""
    if not username or username == "":
        username = "admin"
    
    print(f"📊 Generating dashboard for user: '{username}'")
    
    score_data = SecurityScorer.calculate_posture_score(username)
    system_score = score_data["system_capability"]
    user_score = score_data["user_documents"]
    rag_score = score_data["rag_quality"]
    color = score_data["color"]
    stats = score_data["stats"]

    # System breakdown rows
    system_rows = ""
    for metric, value in system_score["breakdown"].items():
        bar_color = "#10b981" if value >= 90 else "#f59e0b" if value >= 75 else "#f97316" if value >= 50 else "#ef4444"
        system_rows += f'<tr><td style="padding:4px 0;font-size:11px;">{metric}</td><td style="padding:4px 0;"><div style="background:#e5e7eb;border-radius:4px;overflow:hidden;width:100%;"><div style="background:{bar_color};width:{value}%;height:10px;"></div></div></td><td style="padding:4px 0 4px 6px;text-align:right;font-size:11px;">{value:.0f}%</td></tr>'

    # RAG metrics
    rag_metrics = rag_score.get("metrics", {})
    if rag_metrics and rag_score.get("has_documents"):
        rag_details = f"""
        <div style="font-size:11px;color:#374151;line-height:1.7;margin-top:8px;">
            🎯 Precision: <strong>{rag_metrics.get("precision@k", 0):.0%}</strong><br>
            🥇 MRR: <strong>{rag_metrics.get("mrr", 0):.2f}</strong><br>
            📊 NDCG: <strong>{rag_metrics.get("ndcg@k", 0):.2f}</strong><br>
            ⭐ Avg Relevance: <strong>{rag_metrics.get("avg_relevance", 0)}/3</strong>
        </div>"""
    else:
        rag_details = '<div style="font-size:11px;color:#6b7280;margin-top:8px;">No documents to evaluate</div>'

    # Query Attack detection rate
    query_attacks_tested = stats.get("attacks_tested", 0)
    query_attacks_blocked = stats.get("attacks_blocked", 0)
    query_detection_rate = round((query_attacks_blocked / query_attacks_tested * 100) if query_attacks_tested > 0 else 0, 1)
    query_color = "#10b981" if query_detection_rate >= 90 else "#f59e0b" if query_detection_rate >= 75 else "#ef4444"

    # Document Scanner detection rate
    doc_attacks_tested = stats.get("doc_attacks_tested", 0)
    doc_attacks_blocked = stats.get("doc_attacks_blocked", 0)
    doc_detection_rate = system_score["breakdown"].get("Document Scanner", 0)
    doc_color = "#10b981" if doc_detection_rate >= 90 else "#f59e0b" if doc_detection_rate >= 75 else "#ef4444"

    # Attack rows
    attack_rows = ""
    for attack_type, data in score_data.get("attack_by_type", {}).items():
        total = data.get("total", 0)
        blocked = data.get("blocked", 0)
        pct = (blocked / total * 100) if total > 0 else 0
        bar_color = "#10b981" if pct >= 90 else "#f59e0b" if pct >= 75 else "#ef4444"
        attack_rows += f'<tr><td style="padding:8px;">{attack_type}</td><td style="padding:8px;text-align:center;">{total}</td><td style="padding:8px;text-align:center;">{blocked}</td><td style="padding:8px;"><div style="background:#e5e7eb;border-radius:4px;overflow:hidden;width:120px;"><div style="background:{bar_color};width:{pct}%;height:14px;"></div></div></td><td style="padding:8px;text-align:center;">{pct:.0f}%</td></tr>'
    if not attack_rows:
        attack_rows = '<tr><td colspan="5" style="text-align:center;color:#6b7280;padding:12px;">No attacks tested yet.</td></tr>'

    unsafe_docs = score_data.get("unsafe_documents", [])
    unsafe_html = ("<ul style='margin:0;padding-left:20px;'>" + "".join([f"<li>🛑 {doc}</li>" for doc in unsafe_docs]) + "</ul>") if unsafe_docs else "<p style='color:#10b981;margin:0;'>✅ No blocked documents.</p>"

    html = f"""
    <div style="background:#ffffff;border-radius:12px;padding:24px;border:1px solid #e5e7eb;font-family:-apple-system,sans-serif;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
            <h2 style="margin:0;color:#111827;">🛡️ Enterprise Security Overview</h2>
            <span style="background:{color};color:white;padding:6px 14px;border-radius:20px;font-weight:600;">{score_data["status"]}</span>
        </div>
        
        <div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:10px 14px;border-radius:6px;margin-bottom:16px;">
            <strong style="color:#92400e;">👤 Viewing as:</strong> <span style="color:#78350f;font-weight:600;">{username}</span>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:24px;">
            <div style="background:linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);padding:16px;border-radius:12px;border:2px solid #0ea5e9;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                    <div style="font-size:28px;">{system_score["emoji"]}</div>
                    <div>
                        <div style="font-size:12px;color:#0369a1;font-weight:600;">System Capability</div>
                        <div style="font-size:28px;font-weight:800;color:{system_score["color"]};line-height:1;">{system_score["overall_score"]}<span style="font-size:16px;">%</span></div>
                    </div>
                </div>
                <div style="font-size:11px;color:#0c4a6e;margin-bottom:8px;">{system_score["status"]}</div>
                <table style="width:100%;border-collapse:collapse;">{system_rows}</table>
            </div>

            <div style="background:linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);padding:16px;border-radius:12px;border:2px solid #10b981;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                    <div style="font-size:28px;">{user_score["emoji"]}</div>
                    <div>
                        <div style="font-size:12px;color:#047857;font-weight:600;">Your Documents</div>
                        <div style="font-size:28px;font-weight:800;color:{user_score["color"]};line-height:1;">{user_score["overall_score"]}<span style="font-size:16px;">%</span></div>
                    </div>
                </div>
                <div style="font-size:11px;color:#065f46;margin-bottom:10px;">{user_score["status"]}</div>
                <div style="font-size:11px;color:#374151;line-height:1.8;">
                    📄 Scanned: <strong>{user_score["stats"]["documents_scanned"]}</strong><br>
                    ✅ Safe: <strong style="color:#10b981;">{user_score["stats"]["documents_safe"]}</strong><br>
                    🛑 Blocked: <strong style="color:#ef4444;">{user_score["stats"]["documents_blocked"]}</strong><br>
                    📚 Chunks: <strong>{user_score["stats"]["total_chunks"]:,}</strong>
                </div>
            </div>

            <div style="background:linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);padding:16px;border-radius:12px;border:2px solid #a855f7;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                    <div style="font-size:28px;">{rag_score.get("emoji", "⚪")}</div>
                    <div>
                        <div style="font-size:12px;color:#6b21a8;font-weight:600;">RAG Quality</div>
                        <div style="font-size:28px;font-weight:800;color:{rag_score.get("color", "#6b7280")};line-height:1;">{rag_score.get("overall_score", 0)}<span style="font-size:16px;">%</span></div>
                    </div>
                </div>
                <div style="font-size:11px;color:#581c87;margin-bottom:8px;">{rag_score.get("status", "N/A")}</div>
                {rag_details}
            </div>
        </div>

        <div style="background:#f0f9ff;border-left:4px solid #0ea5e9;padding:12px 16px;border-radius:6px;margin-bottom:20px;">
            <strong style="color:#0369a1;">💡 Recommendation:</strong> <span style="color:#0c4a6e;">{score_data["recommendation"]}</span>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
            <div style="background:#f9fafb;padding:16px;border-radius:8px;">
                <div style="font-size:12px;color:#6b7280;margin-bottom:8px;">📊 System Statistics</div>
                <div style="font-size:13px;color:#374151;line-height:1.8;">
                    <div style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #e5e7eb;">
                        <div style="font-size:11px;color:#0369a1;font-weight:600;margin-bottom:4px;">💬 Query Attacks (Chat Input)</div>
                        • Attacks tested: <strong>{query_attacks_tested}</strong><br>
                        • Attacks blocked: <strong style="color:#10b981;">{query_attacks_blocked}</strong><br>
                        • Detection rate: <strong style="color:{query_color};">{query_detection_rate}%</strong>
                    </div>
                    <div>
                        <div style="font-size:11px;color:#047857;font-weight:600;margin-bottom:4px;">📄 Document Scanner (Upload Pipeline)</div>
                        • Payloads tested: <strong>{doc_attacks_tested}</strong><br>
                        • Payloads blocked: <strong style="color:#10b981;">{doc_attacks_blocked}</strong><br>
                        • Detection rate: <strong style="color:{doc_color};">{doc_detection_rate:.0f}%</strong>
                    </div>
                </div>
            </div>
            <div style="background:#f9fafb;padding:16px;border-radius:8px;">
                <div style="font-size:12px;color:#6b7280;margin-bottom:4px;">🛑 Blocked Documents</div>
                {unsafe_html}
            </div>
        </div>

        <div style="margin-top:20px;">
            <h3 style="margin:0 0 12px 0;color:#111827;font-size:16px;">🎯 Attack Resistance by Type</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead><tr style="background:#f3f4f6;"><th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;">Attack Type</th><th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb;">Total</th><th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb;">Blocked</th><th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;">Success Rate</th><th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb;">%</th></tr></thead>
                <tbody>{attack_rows}</tbody>
            </table>
        </div>
    </div>"""
    return html


def get_compliance_html():
    try:
        with open("owasp_mappings.json", "r", encoding="utf-8") as f:
            owasp = json.load(f)
        with open("mitre_mappings.json", "r", encoding="utf-8") as f:
            mitre = json.load(f)
        with open("nist_mappings.json", "r", encoding="utf-8") as f:
            nist = json.load(f)
    except Exception as e:
        return f"<p>Error loading compliance data: {e}</p>"

    owasp_rows = "".join([f"<tr><td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{k}</td><td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{v['status']}</td><td style='padding:8px;border-bottom:1px solid #e5e7eb;font-size:12px;'>{v['implementation']}</td></tr>" for k, v in owasp.items()])
    mitre_rows = "".join([f"<tr><td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{k}</td><td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{v}</td></tr>" for k, v in mitre.items()])
    nist_rows = "".join([f"<tr><td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{k}</td><td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{v}</td></tr>" for k, v in nist.items()])

    return f"""<div style="display:grid;grid-template-columns:1fr;gap:16px;">
        <div style="background:#ffffff;border-radius:12px;padding:20px;border:1px solid #e5e7eb;"><h3 style="margin:0 0 12px 0;color:#111827;">🔷 OWASP Top 10 for LLMs</h3><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f3f4f6;"><th style="padding:8px;text-align:left;">Risk</th><th style="padding:8px;text-align:left;">Status</th><th style="padding:8px;text-align:left;">Implementation</th></tr></thead><tbody>{owasp_rows}</tbody></table></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
            <div style="background:#ffffff;border-radius:12px;padding:20px;border:1px solid #e5e7eb;"><h3 style="margin:0 0 12px 0;color:#111827;">🎯 MITRE ATLAS</h3><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f3f4f6;"><th style="padding:8px;text-align:left;">Technique</th><th style="padding:8px;text-align:left;">Status</th></tr></thead><tbody>{mitre_rows}</tbody></table></div>
            <div style="background:#ffffff;border-radius:12px;padding:20px;border:1px solid #e5e7eb;"><h3 style="margin:0 0 12px 0;color:#111827;">📘 NIST AI RMF</h3><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f3f4f6;"><th style="padding:8px;text-align:left;">Function</th><th style="padding:8px;text-align:left;">Status</th></tr></thead><tbody>{nist_rows}</tbody></table></div>
        </div>
    </div>"""


def dashboard_tab(user_state):
    with gr.Tab("Security Dashboard"):
        gr.Markdown("### 🏢 Enterprise RAG Security Evaluation")
        
        # 🔥 CRITICAL FIX: Start with empty placeholder, force refresh on user_state change
        score_html = gr.HTML(value="<p style='text-align:center;padding:20px;'>Loading dashboard...</p>")
        
        refresh_btn = gr.Button("🔄 Recalculate Security Score", variant="primary")
        
        # 🔥 CRITICAL: Force refresh when user logs in/changes
        def refresh_for_user(username):
            print(f"🔄 Dashboard refresh triggered for user: '{username}'")
            return get_security_score_html(username if username else "admin")
        
        refresh_btn.click(
            fn=refresh_for_user,
            inputs=[user_state],
            outputs=score_html,
        )
        
        user_state.change(
            fn=refresh_for_user,
            inputs=[user_state],
            outputs=score_html,
        )
        
        gr.Markdown("---")
        gr.Markdown("### 📋 Compliance Framework Mappings")
        gr.HTML(value=get_compliance_html())
    
    return score_html
