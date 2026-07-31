import { useState } from 'react';
import api from '../lib/api';

export default function Evaluate() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const { data } = await api.post('/evaluate');
      setResults(data);
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-xl font-bold mb-2">📊 RAG Quality Evaluation</h2>
        <p className="text-sm text-gray-600 mb-4">LLM-as-a-Judge evaluation of retrieval quality.</p>
        <button onClick={run} disabled={loading} className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
          {loading ? 'Evaluating...' : '🚀 Run Evaluation'}
        </button>
      </div>

      {results && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          {results.error ? (
            <div className="text-center text-gray-500 py-8">{results.error}</div>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-blue-50 p-4 rounded text-center">
                  <div className="text-xs text-blue-700">Overall</div>
                  <div className="text-2xl font-bold text-blue-700">
                    {((results.average_metrics['precision@k'] * 0.3 + results.average_metrics.mrr * 0.3 + results.average_metrics['ndcg@k'] * 0.3 + results.average_metrics.avg_relevance / 3 * 0.1) * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="bg-green-50 p-4 rounded text-center">
                  <div className="text-xs text-green-700">Precision@K</div>
                  <div className="text-2xl font-bold text-green-700">{(results.average_metrics['precision@k'] * 100).toFixed(0)}%</div>
                </div>
                <div className="bg-purple-50 p-4 rounded text-center">
                  <div className="text-xs text-purple-700">MRR</div>
                  <div className="text-2xl font-bold text-purple-700">{results.average_metrics.mrr.toFixed(2)}</div>
                </div>
                <div className="bg-orange-50 p-4 rounded text-center">
                  <div className="text-xs text-orange-700">NDCG</div>
                  <div className="text-2xl font-bold text-orange-700">{results.average_metrics['ndcg@k'].toFixed(2)}</div>
                </div>
              </div>
              <div className="text-sm text-gray-600">
                Evaluated {results.queries_evaluated} queries × {results.chunks_per_query} chunks = {results.total_llm_calls} LLM calls
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
