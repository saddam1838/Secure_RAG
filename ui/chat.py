import gradio as gr
from services.rag_service import RAGService
from services.security_service import SecurityGuard
from services.audit_service import AuditService
from guardrails import Guardrail
from config import settings

rag = RAGService()
guard = SecurityGuard()
audit = AuditService()
guardrail = Guardrail()

# Global to track current user
CURRENT_CHAT_USER = {"username": "admin"}


def set_chat_user(username):
    """Called when user logs in or changes."""
    if username and username != "":
        CURRENT_CHAT_USER["username"] = username
        print(f"🔐 Chat user set to: {username}")
    else:
        CURRENT_CHAT_USER["username"] = "admin"


def chat_fn(message, history):
    """Main chat function with multi-tenant isolation."""
    if not message or not message.strip():
        return "Please enter a message."

    # Get username from global state
    username = CURRENT_CHAT_USER["username"]
    print(f"💬 Chat request from user: {username}")

    # Sanitize input
    message = guard.sanitize_input(message)

    # Layer 1: Regex scan
    query_issues = guard.scan_query(message)
    if query_issues:
        audit.log(username, "query_blocked", {
            "query": message[:100],
            "method": "regex",
            "issues": [i["name"] for i in query_issues],
        })
        return "🛑 **Query blocked.** Matched security policy."

    # Layer 2 + 3: ML classifier + LLM evaluation
    ml_score = guard.detect_prompt_injection(message)
    eval_result = guard.should_block_query_advanced(message, ml_score)
    if eval_result["blocked"]:
        audit.log(username, "query_blocked", {
            "query": message[:100],
            "method": eval_result["method"],
            "reason": eval_result["reason"],
            "ml_score": round(ml_score, 3),
        })
        return "🛑 **Query blocked.**"

    # CRITICAL: Retrieve documents ONLY for this specific user
    context = rag.retrieve(message, k=settings.TOP_K_DENSE, username=username)
    
    print(f"🔍 Found {len(context)} documents for user {username}")

    if not context:
        audit.log(username, "no_context_found", {"query": message[:100]})
        return f"No relevant documents found in your knowledge base. Please upload documents to get started.\n\n(Current user: {username})"

    # Generate response
    response = rag.generate(message, context)

    # Output guardrail
    guarded = guardrail.sanitize_output(response)
    final_response = guarded["cleaned"]

    audit.log(username, "query_answered", {
        "query": message[:100],
        "chunks_used": len(context),
        "sources": [c.get("source", "unknown") for c in context[:3]],
    })

    return final_response


def chat_interface(user_state):
    """Create the chat interface tab."""
    with gr.Tab("💬 Chat"):
        gr.Markdown("### 💬 Secure RAG Chat")
        gr.Markdown(
            "Ask questions about your uploaded documents. Responses are grounded in your "
            "knowledge base with full source citations. All queries are scanned for security threats."
        )

        # Simple ChatInterface - uses global CURRENT_CHAT_USER state
        chatbot = gr.ChatInterface(
            fn=chat_fn,
            examples=[
                "Summarize the main points from my documents",
                "What are the key findings?",
                "Explain the methodology used",
            ],
        )

        # CRITICAL: Sync user_state changes to the chat module
        def sync_user(username):
            set_chat_user(username)
        
        user_state.change(
            fn=sync_user,
            inputs=[user_state],
            outputs=[]
        )

    return chatbot
