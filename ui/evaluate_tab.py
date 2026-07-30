import gradio as gr
from services.rag_service import RAGService

rag = RAGService()


def run_evaluation(username):
    """Run LLM-as-a-Judge evaluation with safe empty-state handling."""
    # 1. Check if the global corpus is empty
    if not rag.corpus or len(rag.metadata) == 0:
        return """
        <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:20px;text-align:center;">
            <div style="font-size:40px;margin-bottom:10px;">📭</div>
            <h3 style="margin:0 0 8px 0;color:#0369a1;">No Documents Found</h3>
            <p style="margin:0;color:#0c4a6e;">Please upload documents in the <strong>Secure Upload</strong> tab to run RAG quality evaluations.</p>
        </div>
        """
    
    # 2. Check if the CURRENT user has any documents
    user_docs = [m for m in rag.metadata if m.get("uploaded_by") == username]
    if not user_docs:
        return f"""
        <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:20px;text-align:center;">
            <div style="font-size:40px;margin-bottom:10px;">📭</div>
            <h3 style="margin:0 0 8px 0;color:#0369a1;">No Documents for '{username}'</h3>
            <p style="margin:0;color:#0c4a6e;">You haven't uploaded any documents yet. Please go to the <strong>Secure Upload</strong> tab to add documents to your knowledge base.</p>
        </div>
        """

    # 3. Run the actual evaluation
    try:
        from services.llm_evaluator import LLMJudgeEvaluator
        print(f"🔄 Running RAG evaluation for user: {username}...")
        
        evaluator = LLMJudgeEvaluator()
        results = evaluator.run_dynamic_evaluation(rag, num_queries=3, k=3)
        
        if not results.get("has_documents"):
            return """
            <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:20px;text-align:center;">
                <h3 style="margin:0 0 8px 0;color:#92400e;">⚠️ Insufficient Data</h3>
                <p style="margin:0;color:#78350f;">Not enough valid chunks to run a meaningful evaluation.</p>
            </div>
            """

        avg = results["average_metrics"]
        overall = (
            avg.get("precision@k", 0) * 0.3 + 
            avg.get("mrr", 0) * 0.3 + 
            avg.get("ndcg@k", 0) * 0.3 + 
            (avg.get("avg_relevance", 0) / 3) * 0.1
        ) * 100

        html = f"""
        <div style="background:#ffffff;border-radius:12px;padding:24px;border:1px solid #e5e7eb;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <h3 style="margin:0 0 16px 0;color:#111827;">📊 RAG Quality Evaluation Results</h3>
            
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:16px;margin-bottom:20px;">
                <div style="background:#f0f9ff;padding:16px;border-radius:8px;text-align:center;">
                    <div style="font-size:12px;color:#0369a1;font-weight:600;">Overall Score</div>
                    <div style="font-size:28px;font-weight:800;color:#0ea5e9;">{overall:.1f}%</div>
                </div>
                <div style="background:#f0fdf4;padding:16px;border-radius:8px;text-align:center;">
                    <div style="font-size:12px;color:#047857;font-weight:600;">Precision@K</div>
                    <div style="font-size:28px;font-weight:800;color:#10b981;">{avg.get("precision@k", 0):.1%}</div>
                </div>
                <div style="background:#faf5ff;padding:16px;border-radius:8px;text-align:center;">
                    <div style="font-size:12px;color:#6b21a8;font-weight:600;">MRR</div>
                    <div style="font-size:28px;font-weight:800;color:#a855f7;">{avg.get("mrr", 0):.2f}</div>
                </div>
                <div style="background:#fff7ed;padding:16px;border-radius:8px;text-align:center;">
                    <div style="font-size:12px;color:#9a3412;font-weight:600;">NDCG@K</div>
                    <div style="font-size:28px;font-weight:800;color:#f97316;">{avg.get("ndcg@k", 0):.2f}</div>
                </div>
            </div>
            
            <div style="background:#f9fafb;padding:16px;border-radius:8px;">
                <h4 style="margin:0 0 8px 0;color:#374151;">Detailed Metrics</h4>
                <ul style="margin:0;padding-left:20px;color:#4b5563;line-height:1.8;">
                    <li><strong>Average Relevance:</strong> {avg.get("avg_relevance", 0):.1f} / 3.0</li>
                    <li><strong>Queries Evaluated:</strong> {results.get("num_queries", 0)}</li>
                    <li><strong>Chunks in Knowledge Base:</strong> {len(user_docs)}</li
                </ul>
            </div>
        </div>
        """
        return html
        
    except Exception as e:
        print(f"⚠️ Evaluation failed: {e}")
        return f"""
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:20px;">
            <h3 style="margin:0 0 8px 0;color:#991b1b;">❌ Evaluation Failed</h3>
            <p style="margin:0;color:#7f1d1d;">{str(e)}</p>
        </div>
        """


def evaluate_tab(user_state):
    with gr.Tab("📊 Evaluate RAG"):
        gr.Markdown("### 📊 Dynamic RAG Quality Evaluation")
        gr.Markdown(
            "Run LLM-as-a-Judge evaluations to measure retrieval precision, MRR, and NDCG. "
            "This ensures your RAG pipeline is returning high-fidelity, relevant results."
        )
        
        eval_btn = gr.Button("🚀 Run Evaluation", variant="primary")
        
        # Default state shows the empty message
        eval_output = gr.HTML(
            value="""
            <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:20px;text-align:center;">
                <div style="font-size:40px;margin-bottom:10px;">📭</div>
                <h3 style="margin:0 0 8px 0;color:#0369a1;">No Documents Found</h3>
                <p style="margin:0;color:#0c4a6e;">Please upload documents in the <strong>Secure Upload</strong> tab to run RAG quality evaluations.</p>
            </div>
            """
        )
        
        # Run evaluation when button is clicked
        eval_btn.click(
            fn=run_evaluation,
            inputs=[user_state],
            outputs=[eval_output]
        )
        
        # Also auto-refresh evaluation tab when user logs in/changes
        user_state.change(
            fn=run_evaluation,
            inputs=[user_state],
            outputs=[eval_output]
        )
        
    return eval_output
