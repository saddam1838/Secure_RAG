import gradio as gr
import os
from services.rag_service import RAGService
from document_scanner import read_file_content, scan_document
from services.audit_service import AuditService

rag = RAGService()
audit = AuditService()

last_scan_result = {"content": None, "filename": None, "is_safe": False, "size_mb": 0.0}


def scan_file_for_security(file):
    if file is None:
        return "⚠️ No file selected.", gr.update(interactive=False, value="Index Secure Document")

    try:
        clean_filename = os.path.basename(file.name)
        file_size_mb = os.path.getsize(file.name) / (1024 * 1024)

        content = read_file_content(file.name)
        if not content:
            return "⚠️ Could not extract text from file.", gr.update(interactive=False, value="Index Secure Document")

        report = scan_document(content, file.name)
        last_scan_result["content"] = content
        last_scan_result["filename"] = clean_filename
        last_scan_result["is_safe"] = report["is_safe"]
        last_scan_result["size_mb"] = round(file_size_mb, 2)

        audit.log("user", "document_scan", {
            "filename": clean_filename,
            "size_mb": last_scan_result["size_mb"],
            "is_safe": report["is_safe"],
            "issues_count": len(report["issues"]),
            "issues": [i["name"] for i in report["issues"][:3]],
        })

        if report["is_safe"]:
            return (
                f"✅ **SECURE**: No threats detected in `{clean_filename}`.\n\nSize: {last_scan_result['size_mb']} MB | Ready for indexing.",
                gr.update(interactive=True, value="✅ Index Secure Document"),
            )
        else:
            issues_str = "\n".join([f"- **{issue['name']}** (Severity: `{issue['severity']}`)" for issue in report["issues"]])
            return (
                f"🛑 **BLOCKED**: Document contains security threats.\n\n**Issues Found:**\n{issues_str}\n\n*This document cannot be indexed until threats are removed.*",
                gr.update(interactive=False, value="🚫 Indexing Disabled (Unsafe)"),
            )
    except Exception as e:
        return f"❌ Error reading file: {str(e)}", gr.update(interactive=False, value="Index Secure Document")


def index_approved_document(username):
    """Index document with strict username validation."""
    # 🔥 CRITICAL: Validate username - NEVER allow empty/None
    if not username or username == "" or username is None:
        error_msg = "❌ **ERROR:** You are not logged in. Please log out and log back in to upload documents."
        print(f"❌ BLOCKED: Upload attempted with invalid username: '{username}'")
        return error_msg, gr.update(), gr.update()

    if not last_scan_result["is_safe"] or not last_scan_result["content"]:
        return "❌ Cannot index: Document has not passed security scan.", gr.update(), gr.update()

    try:
        metadata = {
            "source": last_scan_result["filename"],
            "size_mb": last_scan_result["size_mb"],
        }

        print(f"📤 INDEXING: filename='{last_scan_result['filename']}', uploaded_by='{username}'")
        
        # 🔥 CRITICAL: Pass username to RAG service
        rag.add_document(last_scan_result["content"], metadata, uploaded_by=username)

        audit.log(username, "document_indexed", {"filename": last_scan_result["filename"]})

        filename = last_scan_result["filename"]

        # Clear scan result
        last_scan_result["content"] = None
        last_scan_result["filename"] = None
        last_scan_result["is_safe"] = False
        last_scan_result["size_mb"] = 0.0

        print(f"✅ Document indexed by '{username}': {filename}")

        # Refresh dashboard and document list
        from ui.dashboard import get_security_score_html
        from ui.manage_documents import get_user_documents

        new_dashboard = get_security_score_html(username)
        new_choices = get_user_documents(username)

        return (
            f"✅ Successfully indexed: {filename} (as user: {username})",
            new_dashboard,
            gr.update(choices=new_choices),
        )
    except Exception as e:
        print(f"❌ Indexing failed: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Indexing failed: {str(e)}", gr.update(), gr.update()


def upload_tab(user_state, dashboard_html, doc_dropdown):
    with gr.Tab("Secure Upload"):
        gr.Markdown("### 🔒 Zero-Trust Document Ingestion")
        gr.Markdown(
            "All documents are scanned for prompt injections, hidden payloads, base64 obfuscation, and PII before indexing. Only verified-clean documents enter the vector database."
        )

        # 🔥 Show current user for debugging
        user_display = gr.Markdown("")

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Step 1: Upload & Scan")
                file_input = gr.File(
                    label="Choose file",
                    file_types=[".txt", ".pdf", ".docx", ".html", ".md"],
                )
                scan_btn = gr.Button("🔍 Scan Document for Threats", variant="secondary")
                scan_output = gr.Markdown(label="Scan Status")

            with gr.Column():
                gr.Markdown("#### Step 2: Index")
                index_btn = gr.Button("Index Secure Document", variant="primary", interactive=False)
                index_output = gr.Textbox(label="Indexing Status", interactive=False)

        scan_btn.click(scan_file_for_security, [file_input], [scan_output, index_btn])

        # 🔥 CRITICAL: Pass user_state to index function
        index_btn.click(
            index_approved_document,
            inputs=[user_state],
            outputs=[index_output, dashboard_html, doc_dropdown],
        )

        # 🔥 Update user display when user_state changes
        def update_user_display(username):
            if username and username != "":
                return f"**👤 Logged in as:** `{username}`"
            return "**⚠️ Not logged in**"

        user_state.change(update_user_display, inputs=[user_state], outputs=[user_display])
