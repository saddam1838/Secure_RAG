import gradio as gr
from services.llm_evaluator import LLMJudgeEvaluator
from services.rag_service import RAGService
from config import settings

rag = RAGService()
evaluator = LLMJudgeEvaluator()


def run_dynamic_evaluation(progress=gr.Progress()):
    """Run dynamic, corpus-based LLM evaluation."""

    if len(rag.corpus) == 0:
        return (
            {},
            """
<div style="background:#fff7ed;border-left:4px solid #f59e0b;padding:20px;border-radius:8px;">
    <h3 style="margin:0 0 8px 0;color:#92400e;">⚠️ No Documents to Evaluate</h3>
    <p style="margin:0;color:#78350f;">
        Upload documents via the <strong>Secure Upload</strong> tab first. The evaluation dynamically generates queries from your actual content.
    </p>
</div>
""",
        )

    def progress_callback(fraction, description):
        progress(fraction, desc=description)

    progress(0.05, desc="Sampling chunks from your documents...")

    # Dynamically evaluate based on the user's actual uploaded corpus
    results = evaluator.run_dynamic_evaluation(
        rag_service=rag, num_queries=3, k=3, progress_callback=progress_callback
    )

    if not results.get("has_documents"):
        return (
            {},
            f"""
<div style="background:#fff7ed;border-left:4px solid #f59e0b;padding:20px;border-radius:8px;">
    <h3 style="margin:0 0 8px 0;color:#92400e;">⚠️ Insufficient Content</h3>
    <p style="margin:0;color:#78350f;">{results.get("error", "Please upload more documents.")}</p>
</div>
""",
        )

    progress(0.9, desc="Generating report...")

    avg = results["average_metrics"]
    overall = (
        avg["precision@k"] * 0.3
        + avg["mrr"] * 0.3
        + avg["ndcg@k"] * 0.3
        + (avg["avg_relevance"] / 3) * 0.1
    ) * 100

    if overall >= 75:
        status, color = "✅ Excellent", "#10b981"
    elif overall >= 55:
        status, color = "⚠️ Good", "#f59e0b"
    elif overall >= 35:
        status, color = "⚠️ Fair", "#f97316"
    else:
        status, color = "❌ Needs Improvement", "#ef4444"

    # Build per-query detail table
    query_rows = ""
    for r in results["per_query_results"]:
        q = r["query"]
        m = r["metrics"]
        target = r["target_source"].split("/")[-1][:30]

        judgments = r["judgments"]
        relevant_details = []
        for j in judgments:
            if j["is_relevant"]:
                src = j["source"].split("/")[-1][:25]
                marker = "🎯 " if "Exact original" in j["reasoning"] else "✓ "
                relevant_details.append(f"{marker}[{j['rank']}] {src}")

        relevant_str = "<br>".join(relevant_details[:3]) if relevant_details else "—"

        query_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-size:12px;"><em>"{q}"</em><br><span style="color:#6b7280;">Target: {target}</span></td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:center;"><strong>{m["precision@k"]:.0%}</strong></td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:center;"><strong>{m["mrr"]:.2f}</strong></td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:center;"><strong>{m["ndcg@k"]:.2f}</strong></td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-size:11px;">{relevant_str}</td>
        </tr>
        """

    recommendations = []
    if avg["precision@k"] < 0.5:
        recommendations.append(
            "🎯 <strong>Low precision</strong>: Many irrelevant chunks are being retrieved."
        )
    if avg["mrr"] < 0.5:
        recommendations.append(
            "📊 <strong>Low MRR</strong>: The best answer isn't appearing first."
        )
    if avg["ndcg@k"] < 0.6:
        recommendations.append(
            "📈 <strong>Low NDCG</strong>: Relevant chunks are ranked too low."
        )
    if not recommendations:
        recommendations.append(
            "✨ Your retrieval is performing excellently on your specific documents!"
        )

    rec_html = "\n".join([f"<li>{r}</li>" for r in recommendations])

    html = f"""
<div style="background:#ffffff;border-radius:12px;padding:24px;border:1px solid #e5e7eb;">

<div style="background:#f0f9ff;border-left:4px solid #0ea5e9;padding:12px 16px;border-radius:6px;margin-bottom:16px;">
    <strong style="color:#0369a1;">🤖 Evaluation Method:</strong> 
    <span style="color:#0c4a6e;">The system sampled 3 chunks from <strong>your uploaded documents</strong>, formed queries, and used the LLM to verify if the RAG pipeline accurately retrieved the original content.</span>
</div>

<h2 style="margin:0 0 16px 0;color:#111827;">📊 Evaluation Results</h2>

<div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
    <div style="font-size:48px;font-weight:800;color:{color};">{overall:.0f}%</div>
    <div>
        <span style="background:{color};color:white;padding:4px 12px;border-radius:16px;font-weight:600;font-size:14px;">{status}</span>
        <p style="margin:8px 0 0 0;color:#6b7280;font-size:13px;">Based on {results["total_llm_calls"]} LLM judgments across your corpus</p>
    </div>
</div>

<h3 style="margin:0 0 12px 0;color:#111827;font-size:16px;">📈 Average Metrics</h3>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:20px;">
<thead><tr style="background:#f3f4f6;">
    <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;">Metric</th>
    <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;">Score</th>
    <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;">What It Means</th>
</tr></thead>
<tbody>
    <tr>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;font-weight:600;">🎯 Precision@3</td>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;text-align:center;"><strong>{avg["precision@k"]:.0%}</strong></td>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;">Of the 3 chunks retrieved, {avg["precision@k"]:.0%} were actually relevant to the query.</td>
    </tr>
    <tr>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;font-weight:600;">🥇 MRR</td>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;text-align:center;"><strong>{avg["mrr"]:.2f}</strong></td>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;">The first relevant chunk appears {"at the top" if avg["mrr"] >= 0.8 else "near the top" if avg["mrr"] >= 0.5 else "too far down"} on average.</td>
    </tr>
    <tr>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;font-weight:600;">📊 NDCG@3</td>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;text-align:center;"><strong>{avg["ndcg@k"]:.2f}</strong></td>
        <td style="padding:10px;border-bottom:1px solid #e5e7eb;">Most relevant chunks are {"ranked first" if avg["ndcg@k"] >= 0.8 else "ranked well" if avg["ndcg@k"] >= 0.6 else "scattered in rankings"}.</td>
    </tr>
</tbody>
</table>

<h3 style="margin:0 0 12px 0;color:#111827;font-size:16px;">🔍 Per-Query Breakdown</h3>
<div style="overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px;">
<thead><tr style="background:#f3f4f6;">
    <th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;">Dynamic Query & Target Source</th>
    <th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb;">Precision</th>
    <th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb;">MRR</th>
    <th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb;">NDCG</th>
    <th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb;">Relevant Chunks Found</th>
</tr></thead>
<tbody>{query_rows}</tbody>
</table>
</div>

<div style="background:#f0f9ff;border-left:4px solid #0ea5e9;padding:16px 20px;border-radius:6px;">
    <h3 style="margin:0 0 12px 0;color:#0369a1;font-size:16px;">💡 Recommendations</h3>
    <ul style="margin:0;padding-left:20px;color:#0c4a6e;font-size:14px;line-height:1.8;">
        {rec_html}
    </ul>
</div>

</div>
"""

    progress(1.0, desc="Complete!")
    return results, html


def evaluate_tab():
    with gr.Tab("Evaluate"):
        gr.Markdown("### 📊 RAG Evaluation (LLM-as-a-Judge)")
        gr.Markdown("""
        This evaluation **adapts to your specific documents**. It samples content from your uploaded files, forms queries, and uses the LLM to verify if the RAG pipeline accurately retrieves the original context.
        """)

        eval_btn = gr.Button("🚀 Run Evaluation", variant="primary")

        with gr.Accordion("📋 Raw LLM Judgments", open=False):
            raw_output = gr.JSON(label="Raw Results")

        explanation_output = gr.HTML(label="Results")

        eval_btn.click(run_dynamic_evaluation, None, [raw_output, explanation_output])
