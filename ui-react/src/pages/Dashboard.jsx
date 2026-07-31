import { useEffect, useState } from 'react';
import { Shield, FileText, Brain, AlertTriangle } from 'lucide-react';
import api from '../lib/api';

function ScoreCard({ title, score, status, color, icon: Icon, children }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5" style={{ color }} />
          <h3 className="font-semibold text-gray-800">{title}</h3>
        </div>
        <span className="text-xs px-2 py-1 rounded-full text-white" style={{ background: color }}>{status}</span>
      </div>
      <div className="text-4xl font-bold mb-2" style={{ color }}>{score}<span className="text-lg">%</span></div>
      {children}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/dashboard').then(r => setData(r.data)).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-12">Loading...</div>;
  if (!data) return <div className="text-center py-12 text-red-600">Failed to load</div>;

  const sys = data.system_capability;
  const docs = data.user_documents;
  const rag = data.rag_quality;

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl p-6">
        <h1 className="text-2xl font-bold mb-1">🛡️ Security Posture</h1>
        <div className="flex items-baseline gap-2">
          <span className="text-5xl font-bold">{data.overall_score}</span>
          <span className="text-xl">/ 100</span>
          <span className="ml-4 text-lg">{data.status}</span>
        </div>
        <p className="mt-2 text-sm opacity-90">💡 {data.recommendation}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ScoreCard title="System Capability" score={sys.overall_score} status={sys.status} color={sys.color} icon={Shield}>
          <div className="space-y-2 text-sm">
            {Object.entries(sys.breakdown).map(([k, v]) => (
              <div key={k}>
                <div className="flex justify-between"><span>{k}</span><span className="font-semibold">{v}%</span></div>
                <div className="h-1.5 bg-gray-200 rounded"><div className="h-full rounded" style={{ width: `${v}%`, background: sys.color }} /></div>
              </div>
            ))}
          </div>
        </ScoreCard>

        <ScoreCard title="Your Documents" score={docs.overall_score} status={docs.status} color={docs.color} icon={FileText}>
          <div className="text-sm space-y-1">
            <div>📄 Scanned: <strong>{docs.stats.documents_scanned}</strong></div>
            <div>✅ Safe: <strong className="text-green-600">{docs.stats.documents_safe}</strong></div>
            <div>🛑 Blocked: <strong className="text-red-600">{docs.stats.documents_blocked}</strong></div>
            <div>📚 Chunks: <strong>{docs.stats.total_chunks}</strong></div>
          </div>
        </ScoreCard>

        <ScoreCard title="RAG Quality" score={rag.overall_score || 0} status={rag.status} color={rag.color} icon={Brain}>
          {rag.metrics && Object.keys(rag.metrics).length > 0 ? (
            <div className="text-sm space-y-1">
              <div>🎯 Precision: <strong>{(rag.metrics['precision@k'] * 100).toFixed(0)}%</strong></div>
              <div>🥇 MRR: <strong>{rag.metrics.mrr?.toFixed(2)}</strong></div>
              <div>📊 NDCG: <strong>{rag.metrics['ndcg@k']?.toFixed(2)}</strong></div>
            </div>
          ) : <div className="text-sm text-gray-500">No documents to evaluate</div>}
        </ScoreCard>
      </div>

      {data.unsafe_documents?.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h3 className="font-semibold text-red-800 flex items-center gap-2"><AlertTriangle className="w-5 h-5" /> Blocked Documents</h3>
          <ul className="mt-2 text-sm text-red-700 list-disc list-inside">
            {data.unsafe_documents.map((d, i) => <li key={i}>{d}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}
