import { useEffect, useState } from 'react';
import { Lock, Shield, Edit3 } from 'lucide-react';
import api from '../lib/api';
import toast from 'react-hot-toast';

export default function SecurityConfig() {
  const [thresholds, setThresholds] = useState({});
  const [rules, setRules] = useState({});
  const [compliance, setCompliance] = useState(null);
  const [testPattern, setTestPattern] = useState('');
  const [testText, setTestText] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [userRole, setUserRole] = useState('user');
  const [editingKey, setEditingKey] = useState(null);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    api.get('/security/thresholds').then(r => setThresholds(r.data));
    api.get('/security/rules').then(r => setRules(r.data));
    api.get('/compliance').then(r => setCompliance(r.data));
    
    const role = localStorage.getItem('role') || 'user';
    setUserRole(role);
  }, []);

  const isAdmin = userRole === 'admin';

  const testRegex = async () => {
    if (!testPattern || !testText) {
      toast.error('Please provide both pattern and text');
      return;
    }
    try {
      const { data } = await api.post('/security/test-pattern', { pattern: testPattern, text: testText });
      setTestResult(data);
    } catch { setTestResult({ valid: false, error: 'Failed to test' }); }
  };

  const startEdit = (key, currentValue) => {
    setEditingKey(key);
    setEditValue(currentValue);
  };

  const saveEdit = async (key) => {
    try {
      const { data } = await api.put('/security/thresholds', { key, value: editValue });
      if (data.success) {
        toast.success(data.message);
        setThresholds(t => ({ ...t, [key]: editValue }));
        setEditingKey(null);
      } else {
        toast.error(data.message);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed');
    }
  };

  const cancelEdit = () => {
    setEditingKey(null);
    setEditValue('');
  };

  const thresholdEntries = Object.entries(thresholds).filter(
    ([k]) => !['editable', 'message'].includes(k)
  );

  return (
    <div className="space-y-6">
      {/* Thresholds Section */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            ⚙️ Security Thresholds
            {!isAdmin && <Lock className="w-5 h-5 text-gray-400" />}
          </h2>
          {isAdmin ? (
            <span className="flex items-center gap-1 text-xs bg-green-50 text-green-700 px-3 py-1.5 rounded-full border border-green-200">
              <Edit3 className="w-3 h-3" /> Admin Mode
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full border border-gray-200">
              <Shield className="w-3 h-3" /> View Only
            </span>
          )}
        </div>

        <div className="space-y-3">
          {thresholdEntries.map(([k, v]) => (
            <div key={k} className="flex items-center gap-3">
              <label className="flex-1 text-sm font-medium text-gray-700">
                {k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </label>
              <div className="flex items-center gap-2">
                {isAdmin && editingKey === k ? (
                  <>
                    <input
                      type="text"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      className="w-32 px-3 py-1.5 border rounded text-sm focus:ring-2 focus:ring-blue-500"
                      autoFocus
                    />
                    <button
                      onClick={() => saveEdit(k)}
                      className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="px-3 py-1.5 bg-gray-400 text-white text-sm rounded hover:bg-gray-500"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <input
                      type="text"
                      value={v}
                      readOnly
                      disabled={!isAdmin}
                      className={`w-32 px-3 py-1.5 border rounded text-sm ${
                        isAdmin ? 'bg-white cursor-pointer hover:bg-blue-50' : 'bg-gray-50 text-gray-500 cursor-not-allowed'
                      }`}
                      onClick={() => isAdmin && startEdit(k, v)}
                    />
                    {isAdmin && (
                      <button
                        onClick={() => startEdit(k, v)}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                        title="Edit threshold"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                    )}
                    {!isAdmin && <Lock className="w-3 h-3 text-gray-400" />}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Rule Testing Playground */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-xl font-bold mb-4">🧪 Rule Testing Playground</h2>
        <p className="text-sm text-gray-600 mb-4">Test regex patterns against sample text to verify security rules.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Regex Pattern</label>
            <input
              value={testPattern}
              onChange={e => setTestPattern(e.target.value)}
              placeholder="e.g., (?i)ignore previous"
              className="w-full p-3 border rounded"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Sample Text</label>
            <textarea
              value={testText}
              onChange={e => setTestText(e.target.value)}
              placeholder="Paste text to test..."
              className="w-full p-3 border rounded"
              rows={3}
            />
          </div>
        </div>
        <button onClick={testRegex} className="mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          🔍 Test Pattern
        </button>
        {testResult && (
          <div className={`mt-3 p-3 rounded ${testResult.valid ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
            {testResult.valid
              ? `${testResult.message} ${testResult.matched_text?.length > 0 ? 'Matches: ' + testResult.matched_text.join(', ') : ''}`
              : `Invalid: ${testResult.error}`}
          </div>
        )}
      </div>

      {/* Active Rules */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-xl font-bold mb-4">
          📋 Active Rules ({rules.document_rules?.length || 0} doc, {rules.query_rules?.length || 0} query)
        </h2>
        <details className="mb-3">
          <summary className="cursor-pointer font-semibold text-blue-700">Document Rules</summary>
          <div className="mt-2 space-y-1 max-h-60 overflow-y-auto">
            {rules.document_rules?.map(r => (
              <div key={r.id} className="text-xs p-2 bg-gray-50 rounded flex justify-between items-center">
                <span><strong>{r.id}</strong> {r.name}</span>
                <span className={`px-2 py-0.5 rounded text-white text-[10px] ${
                  r.severity === 'high' ? 'bg-red-500' : r.severity === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                }`}>{r.severity}</span>
              </div>
            ))}
          </div>
        </details>
        <details>
          <summary className="cursor-pointer font-semibold text-blue-700">Query Rules</summary>
          <div className="mt-2 space-y-1 max-h-60 overflow-y-auto">
            {rules.query_rules?.map(r => (
              <div key={r.id} className="text-xs p-2 bg-gray-50 rounded flex justify-between items-center">
                <span><strong>{r.id}</strong> {r.name}</span>
                <span className={`px-2 py-0.5 rounded text-white text-[10px] ${
                  r.severity === 'high' ? 'bg-red-500' : 'bg-yellow-500'
                }`}>{r.severity}</span>
              </div>
            ))}
          </div>
        </details>
      </div>

      {/* Compliance Frameworks */}
      {compliance && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-xl font-bold mb-4">📊 Compliance Frameworks</h2>
          {['owasp', 'mitre', 'nist'].map(fw => (
            <details key={fw} className="mb-3">
              <summary className="cursor-pointer font-semibold uppercase text-blue-700">{fw}</summary>
              <div className="mt-2 space-y-2">
                {Object.entries(compliance[fw]).map(([k, v]) => (
                  <div key={k} className="text-sm p-2 bg-gray-50 rounded">
                    <div className="flex justify-between">
                      <strong>{k}</strong>
                      <span>{v.status}</span>
                    </div>
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
