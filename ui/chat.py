import gradio as gr
from services.rag_service import RAGService
from services.security_service import SecurityGuard
from config import settings

rag = RAGService()
security = SecurityGuard()


def chat_response(message, history):
    history.append({"role": "user", "content": message})
    yield history

    # Check if knowledge base is empty
    if len(rag.corpus) == 0:
        history.append(
            {
                "role": "assistant",
                "content": "📚 **No documents in knowledge base.**\n\nUpload documents via the **Secure Upload** tab to begin.",
            }
        )
        yield history
        return

    # Security check
    pi_score = security.detect_prompt_injection(message)
    eval_result = security.should_block_query_advanced(message, pi_score)

    if eval_result["blocked"]:
        # SECURITY: Do not expose which detection method blocked the query
        # This prevents attackers from learning how to bypass specific layers
        history.append(
            {
                "role": "assistant",
                "content": f"🛑 **Query blocked.** {eval_result['reason']}",
            }
        )
        yield history
        return

    # RAG pipeline
    safe_query = security.sanitize_input(message)
    chunks = rag.retrieve(safe_query, k=settings.TOP_K_DENSE)

    if not chunks:
        history.append(
            {
                "role": "assistant",
                "content": "No relevant information found in the uploaded documents. Try rephrasing your question or uploading additional documents.",
            }
        )
        yield history
        return

    chunks = rag.rerank(safe_query, chunks)
    full_response = ""
    history.append({"role": "assistant", "content": ""})

    for token in rag.generate_stream(safe_query, chunks):
        full_response += token
        history[-1]["content"] = full_response
        yield history


def chat_interface(user_state):
    with gr.Tab("Ask"):
        # Show knowledge base status
        kb_status = (
            f"📚 Knowledge Base: {len(rag.corpus):,} chunks loaded"
            if len(rag.corpus) > 0
            else "⚠️ Knowledge Base: Empty (upload documents first)"
        )
        gr.Markdown(kb_status)

        chatbot = gr.Chatbot(label="Conversation", height=400)
        msg = gr.Textbox(label="Your Question", placeholder="Ask anything...")
        clear = gr.Button("Clear Chat")

        msg.submit(chat_response, [msg, chatbot], chatbot)
        clear.click(lambda: [], None, chatbot)

        user_state.change(lambda: [], None, chatbot)
