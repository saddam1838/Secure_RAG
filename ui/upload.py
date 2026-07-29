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
        return "⚠️ No file selected.", gr.update(
            interactive=False, value="Index Secure Document"
        )

    try:
        clean_filename = os.path.basename(file.name)
        file_size_mb = os.path.getsize(file.name) / (1024 * 1024)

        content = read_file_content(file.name)
        if not content:
            return "⚠️ Could not extract text from file.", gr.update(
                interactive=False, value="Index Secure Document"
            )

        report = scan_document(content, file.name)
        last_scan_result["content"] = content
        last_scan_result["filename"] = clean_filename
        last_scan_result["is_safe"] = report["is_safe"]
        last_scan_result["size_mb"] = round(file_size_mb, 2)

        audit.log(
            "user",
            "document_scan",
            {
                "filename": clean_filename,
                "size_mb": last_scan_result["size_mb"],
                "is_safe": report["is_safe"],
                "issues_count": len(report["issues"]),
                "issues": [i["name"] for i in report["issues"][:3]],
            },
        )

        if report["is_safe"]:
            return (
                f"✅ **SECURE**: No threats detected in `{clean_filename}`.\n\nSize: {last_scan_result['size_mb']} MB | Ready for indexing.",
                gr.update(interactive=True, value="✅ Index Secure Document"),
            )
        else:
            issues_str = "\n".join(
                [
                    f"- **{issue['name']}** (Severity: `{issue['severity']}`)"
                    for issue in report["issues"]
                ]
            )
            return (
                f"🛑 **BLOCKED**: Document contains security threats.\n\n**Issues Found:**\n{issues_str}\n\n*This document cannot be indexed until threats are removed.*",
                gr.update(interactive=False, value="🚫 Indexing Disabled (Unsafe)"),
            )
    except Exception as e:
        return f"❌ Error reading file: {str(e)}", gr.update(
            interactive=False, value="Index Secure Document"
        )


def index_approved_document(username):
    if not last_scan_result["is_safe"] or not last_scan_result["content"]:
        return "❌ Cannot index: Document has not passed security scan."
    try:
        metadata = {
            "source": last_scan_result["filename"],
            "size_mb": last_scan_result["size_mb"],
        }
        rag.add_document(last_scan_result["content"], metadata, uploaded_by=username)
        audit.log(
            "user", "document_indexed", {"filename": last_scan_result["filename"]}
        )
        return f"✅ Successfully indexed: {last_scan_result['filename']}"
    except Exception as e:
        return f"❌ Indexing failed: {str(e)}"


# FIX: New function to refresh other tabs automatically
def refresh_after_upload(username):
    from ui.dashboard import get_security_score_html
    from ui.manage_documents import get_user_documents

    new_score_html = get_security_score_html()
    new_choices = get_user_documents(username)
    return new_score_html, gr.update(choices=new_choices)


def upload_tab(user_state, dashboard_html, doc_dropdown):
    with gr.Tab("Secure Upload"):
        gr.Markdown("### 🔒 Zero-Trust Document Ingestion")
        gr.Markdown(
            "All documents are scanned for prompt injections, hidden payloads, base64 obfuscation, and PII before indexing. Only verified-clean documents enter the vector database."
        )

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Step 1: Upload & Scan")
                file_input = gr.File(
                    label="Choose file",
                    file_types=[".txt", ".pdf", ".docx", ".html", ".md"],
                )
                scan_btn = gr.Button(
                    "🔍 Scan Document for Threats", variant="secondary"
                )
                scan_output = gr.Markdown(label="Scan Status")

            with gr.Column():
                gr.Markdown("#### Step 2: Index")
                index_btn = gr.Button(
                    "Index Secure Document", variant="primary", interactive=False
                )
                index_output = gr.Textbox(label="Indexing Status", interactive=False)

        scan_btn.click(scan_file_for_security, [file_input], [scan_output, index_btn])

        # FIX: Chain the events! First index, then refresh Dashboard and Manage Docs automatically.
        index_btn.click(
            index_approved_document, inputs=[user_state], outputs=[index_output]
        ).then(
            refresh_after_upload,
            inputs=[user_state],
            outputs=[dashboard_html, doc_dropdown],
        )
