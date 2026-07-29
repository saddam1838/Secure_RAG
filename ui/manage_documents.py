import gradio as gr
import os
from services.cloud_storage import cloud_storage
from services.rag_service import RAGService
from ui.dashboard import get_security_score_html

rag = RAGService()


def get_user_documents(username):
    """Fetch documents for the dropdown with robust error handling."""
    if not username:
        return []

    if cloud_storage.is_cloud_enabled:
        try:
            result = (
                cloud_storage.supabase.table("documents")
                .select("id, filename, size_mb, created_at")
                .eq("uploaded_by", username)
                .order("created_at", desc=True)
                .execute()
            )
            docs = result.data
        except Exception as e:
            print(f"⚠️ Supabase connection dropped while fetching documents: {e}")
            print(
                "💡 Tip: If using the free tier, your Supabase project may have gone to sleep. Try waking it up in the Supabase dashboard."
            )
            docs = []
    else:
        # Local fallback
        seen = set()
        docs = []
        for m in rag.metadata:
            fname = m.get("source", "unknown")
            if fname not in seen:
                seen.add(fname)
                docs.append(
                    {
                        "id": "local",
                        "filename": fname,
                        "size_mb": 0,
                        "created_at": "Local",
                    }
                )

    choices = []
    for d in docs:
        clean_name = os.path.basename(d["filename"])
        size = d.get("size_mb", 0)
        choices.append((f"{clean_name} ({size} MB)", d["id"]))
    return choices


def delete_selected_document(doc_id, username):
    """Handle the deletion logic and refresh Dashboard + Dropdown."""
    if not doc_id or doc_id == "":
        return (
            "⚠️ Please select a document first.",
            gr.update(),
            get_security_score_html(),
        )

    filename = "unknown"
    if cloud_storage.is_cloud_enabled:
        try:
            res = (
                cloud_storage.supabase.table("documents")
                .select("filename")
                .eq("id", doc_id)
                .execute()
            )
            if res.data:
                filename = os.path.basename(res.data[0]["filename"])
            success, msg = cloud_storage.delete_document(doc_id, username)
        except Exception as e:
            print(f"⚠️ Supabase error during deletion: {e}")
            return (
                f"❌ Database connection error: {e}",
                gr.update(),
                get_security_score_html(),
            )
    else:
        filename = doc_id
        success, msg = True, "Deleted locally"
        rag.remove_document_from_memory(filename)

    # Generate the new dashboard score regardless of success/failure to keep UI in sync
    new_dashboard_html = get_security_score_html()

    if success:
        new_choices = get_user_documents(username)
        return (
            f"✅ Successfully deleted: {filename}",
            gr.update(choices=new_choices, value=None),
            new_dashboard_html,
        )
    else:
        return f"❌ {msg}", gr.update(), new_dashboard_html


def manage_documents_tab(user_state, dashboard_html):
    with gr.Tab("Manage Documents"):
        gr.Markdown("### 🗂️ Indexed Documents")
        gr.Markdown(
            "Select a document to delete. You can only remove documents you uploaded."
        )

        with gr.Row():
            with gr.Column(scale=2):
                doc_dropdown = gr.Dropdown(
                    label="Select Document to Delete", choices=[], interactive=True
                )
            with gr.Column(scale=1):
                delete_btn = gr.Button("🗑️ Delete Selected", variant="stop")
                refresh_btn = gr.Button("🔄 Refresh List", variant="secondary")

        status_box = gr.Textbox(label="Status", interactive=False)

        def refresh_list(username):
            return gr.update(choices=get_user_documents(username))

        # FIX: Added dashboard_html to the outputs of the delete button!
        delete_btn.click(
            delete_selected_document,
            inputs=[doc_dropdown, user_state],
            outputs=[
                status_box,
                doc_dropdown,
                dashboard_html,
            ],
        )

        refresh_btn.click(refresh_list, inputs=[user_state], outputs=[doc_dropdown])
        user_state.change(refresh_list, inputs=[user_state], outputs=[doc_dropdown])

    return doc_dropdown
