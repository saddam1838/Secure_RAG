import { useState } from 'react';
import { HelpCircle, BarChart3 } from 'lucide-react';
import api from '../lib/api';

export default function Evaluate() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const { data } = await api.post('/evaluate');
      setResults(data);
    } finally { 
      setLoading(false); 
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-xl font-bold mb-2 flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-blue-600" /> RAG Quality Evaluation
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          This tool automatically tests your system by asking random questions based on your uploaded documents, then grades how well the AI finds and ranks the right answers.
        </p>
        <button 
          onClick={run} 
          disabled={loading} 
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
        >
          {loading ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              Evaluating... (This may take a minute)
            </>
          ) : (
            '🚀 Run Evaluation'
          )}
        </button>
      </div>

      {results && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          {results.error ? (
            <div className="text-center text-gray-500 py-8 bg-gray-50 rounded-lg border border-dashed border-gray-300">
              <p className="text-lg font-semibold text-red-600 mb-2">⚠️ Evaluation Skipped</p>
              <p>{results.error}</p>
            </div>
          ) : (
            <>
              {/* Simple Explanation Box for Non-Technical Users */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-5 mb-6">
                <h3 className="font-semibold text-blue-800 flex items-center gap-2 mb-3">
                  <HelpCircle className="w-5 h-5" /> What do these scores mean?
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-900">
                  <div className="flex gap-3">
                    <span className="text-xl">🎯</span>
                    <div>
                      <strong>Precision@K:</strong> Out of the top results shown to the user, what percentage were actually useful? (Higher is better)
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <span className="text-xl">🥇</span>
                    <div>
                      <strong>MRR (Mean Reciprocal Rank):</strong> How quickly did the system find the <em>first</em> correct answer? (1.0 means it was the very first result)
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <span className="text-xl">📊</span>
                    <div>
                      <strong>NDCG:</strong> A grade for how well the system ranked <em>all</em> results from most relevant to least relevant. (Max score is 1.0)
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <span className="text-xl">⭐</span>
                    <div>
                      <strong>Overall Score:</strong> A combined grade of the system's total accuracy, calculated from the metrics above.
                    </div>
                  </div>
                </div>
              </div>

              {/* Metrics Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 p-5 rounded-xl border border-blue-100 text-center">
                  <div className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">Overall Score</div>
                  <div className="text-3xl font-bold text-blue-700">
                    {((results.average_metrics['precision@k'] * 0.3 + results.average_metrics.mrr * 0.3 + results.average_metrics['ndcg@k'] * 0.3 + results.average_metrics.avg_relevance / 3 * 0.1) * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="bg-green-50 p-5 rounded-xl border border-green-100 text-center">
                  <div className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-1">Precision@K</div>
                  <div className="text-3xl font-bold text-green-700">{(results.average_metrics['precision@k'] * 100).toFixed(0)}%</div>
                </div>
                <div className="bg-purple-50 p-5 rounded-xl border border-purple-100 text-center">
                  <div className="text-xs font-semibold text-purple-700 uppercase tracking-wide mb-1">MRR</div>
                  <div className="text-3xl font-bold text-purple-700">{results.average_metrics.mrr.toFixed(2)}</div>
                </div>
                <div className="bg-orange-50 p-5 rounded-xl border border-orange-100 text-center">
                  <div className="text-xs font-semibold text-orange-700 uppercase tracking-wide mb-1">NDCG</div>
                  <div className="text-3xl font-bold text-orange-700">{results.average_metrics['ndcg@k'].toFixed(2)}</div>
                </div>
              </div>

              {/* Footer Stats */}
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600 flex flex-col md:flex-row md:items-center justify-between gap-2 border border-gray-200">
                <span>
                  Evaluated <strong className="text-gray-900">{results.queries_evaluated}</strong> test queries against <strong className="text-gray-900">{results.chunks_per_query}</strong> chunks per query.
                </span>
                <span className="text-xs bg-gray-200 text-gray-700 px-3 py-1.5 rounded-full font-medium self-start md:self-auto">
                  Total LLM grading calls: {results.total_llm_calls}
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
