import { useEffect, useState } from 'react';
import api from '../lib/api';
import toast from 'react-hot-toast';

export default function SecurityConfig() {
  const [thresholds, setThresholds] = useState({});
  const [rules, setRules] = useState({});
  const [compliance, setCompliance] = useState(null);
  const [testPattern, setTestPattern] = useState('');
  const [testText, setTestText] = useState('');
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    api.get('/security/thresholds').then(r => setThresholds(r.data));
    api.get('/security/rules').then(r => setRules(r.data));
    api.get('/compliance').then(r => setCompliance(r.data));
  }, []);

  const update = async (key, value) => {
    try {
      const { data } = await api.put('/security/thresholds', { key, value });
      toast[data.success ? 'success' : 'error'](data.message);
      if (data.success) setThresholds(t => ({ ...t, [key]: value }));
    } catch { toast.error('Update failed'); }
    window.location.reload();
  };

  const testRegex = async () => {
    try {
      const { data } = await api.post('/security/test-pattern', { pattern: testPattern, text: testText });
      setTestResult(data);
    } catch { setTestResult({ valid: false, error: 'Failed to test' }); }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-xl font-bold mb-4">⚙️ Security Thresholds</h2>
        <div className="space-y-3">
          {Object.entries(thresholds).map(([k, v]) => (
            <div key={k} className="flex items-center gap-3">
              <label className="flex-1 text-sm font-medium">{k.replace(/_/g, ' ')}</label>
              <input type="text" defaultValue={v} onBlur={e => update(k, e.target.value)} className="w-32 px-3 py-1.5 border rounded text-sm" />
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-xl font-bold mb-4">🧪 Rule Testing Playground</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input value={testPattern} onChange={e => setTestPattern(e.target.value)} placeholder="Regex pattern (e.g., (?i)ignore previous)" className="p-3 border rounded" />
          <textarea value={testText} onChange={e => setTestText(e.target.value)} placeholder="Sample text to test..." className="p-3 border rounded" rows={3} />
        </div>
        <button onClick={testRegex} className="mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">🔍 Test Pattern</button>
        {testResult && (
          <div className={`mt-3 p-3 rounded ${testResult.valid ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
            {testResult.valid ? `${testResult.message} ${testResult.matched_text.length > 0 ? 'Matches: ' + testResult.matched_text.join(', ') : ''}` : `Invalid: ${testResult.error}`}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-xl font-bold mb-4">📋 Active Rules ({rules.document_rules?.length || 0} doc, {rules.query_rules?.length || 0} query)</h2>
        <details className="mb-3">
          <summary className="cursor-pointer font-semibold text-blue-700">Document Rules</summary>
          <div className="mt-2 space-y-1 max-h-60 overflow-y-auto">
            {rules.document_rules?.map(r => (
              <div key={r.id} className="text-xs p-2 bg-gray-50 rounded flex justify-between">
                <span><strong>{r.id}</strong> {r.name}</span>
                <span className={`px-2 rounded text-white ${r.severity === 'high' ? 'bg-red-500' : r.severity === 'medium' ? 'bg-yellow-500' : 'bg-green-500'}`}>{r.severity}</span>
              </div>
            ))}
          </div>
        </details>
      </div>

      {compliance && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-xl font-bold mb-4">📊 Compliance Frameworks</h2>
          {['owasp', 'mitre', 'nist'].map(fw => (
            <details key={fw} className="mb-3">
              <summary className="cursor-pointer font-semibold uppercase text-blue-700">{fw}</summary>
              <div className="mt-2 space-y-2">
                {Object.entries(compliance[fw]).map(([k, v]) => (
                  <div key={k} className="text-sm p-2 bg-gray-50 rounded">
                    <div className="flex justify-between"><strong>{k}</strong><span>{v.status}</span></div>
                    {v.description && <div className="text-xs text-gray-600 mt-1">{v.description}</div>}
                  </div>
                ))}
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
