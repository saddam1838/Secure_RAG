import { useState, useEffect } from 'react';
import api from '../lib/api';

export default function AttackSim() {
  const [tab, setTab] = useState('query');
  const [types, setTypes] = useState([]);
  const [type, setType] = useState('');
  const [custom, setCustom] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get(`/attacks/${tab}/types`).then(r => { setTypes(r.data); setType(r.data[0]); });
  }, [tab]);

  const run = async () => {
    setLoading(true);
    try {
      const { data } = await api.post(`/attacks/${tab}/run`, { type, custom });
      setResults(data);
    } finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <div className="flex gap-2 mb-4">
          <button onClick={() => setTab('query')} className={`px-4 py-2 rounded ${tab === 'query' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>💬 Query Attacks</button>
          <button onClick={() => setTab('document')} className={`px-4 py-2 rounded ${tab === 'document' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>📄 Document Attacks</button>
        </div>
        <select value={type} onChange={e => setType(e.target.value)} className="w-full p-3 border rounded-lg mb-3">
          {types.map(t => <option key={t}>{t}</option>)}
        </select>
        {type === 'Custom' && <textarea value={custom} onChange={e => setCustom(e.target.value)} placeholder="Enter custom payload..." className="w-full p-3 border rounded-lg mb-3" rows={3} />}
        <button onClick={run} disabled={loading} className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
          {loading ? 'Running...' : '🚀 Run Attack'}
        </button>
      </div>

      {results && (
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h3 className="font-bold mb-3">Results {results.detection_rate !== undefined && <span className="text-sm font-normal text-gray-600">• Detection: {results.detection_rate}% ({results.blocked}/{results.total})</span>}</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {results.results.map((r, i) => (
              <div key={i} className={`p-3 rounded border ${r.blocked ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <div className="flex justify-between">
                  <span className="font-mono text-sm truncate">{(r.query || r.filename || '').slice(0, 80)}</span>
                  <span className="text-xs font-bold">{r.blocked ? '✅ BLOCKED' : '❌ PASSED'}</span>
                </div>
                {r.reason && <div className="text-xs text-gray-600 mt-1">{r.reason} (Score: {r.ml_score})</div>}
                {r.layer && <div className="text-xs text-gray-600 mt-1">Layer: {r.layer} | Severity: {r.severity} | {r.details}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
