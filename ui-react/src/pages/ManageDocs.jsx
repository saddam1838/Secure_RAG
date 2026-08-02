import { useState, useEffect } from 'react';
import { FileText, Trash2, Shield, ShieldAlert, RefreshCw } from 'lucide-react';
import api from '../lib/api';
import toast from 'react-hot-toast';

export default function ManageDocs() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/documents');
      setDocs(data);
    } catch (err) {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const remove = async (id, filename) => {
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
      await api.delete(`/documents/${id}`);
      toast.success('Document deleted');
      load();
    } catch (err) {
      toast.error('Delete failed');
    }
  };

  const safeDocs = docs.filter(d => d.is_safe);
  const blockedDocs = docs.filter(d => !d.is_safe);

  return (
    <div className="space-y-6">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <FileText className="w-6 h-6 text-blue-600" /> My Documents
        </h2>
        <button onClick={load} disabled={loading} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Safe Documents Section */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2 text-green-700">
          <Shield className="w-5 h-5" /> Safe Documents ({safeDocs.length})
        </h3>
        {safeDocs.length === 0 ? (
          <p className="text-gray-500 text-sm">No safe documents found. Upload documents to get started.</p>
        ) : (
          <div className="space-y-2">
            {safeDocs.map(d => (
              <div key={d.id} className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <FileText className="w-5 h-5 text-green-600 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{d.filename}</div>
                    <div className="text-xs text-gray-600">
                      {d.size_mb ? `${d.size_mb.toFixed(2)} MB` : 'Local'} • {new Date(d.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <button onClick={() => remove(d.id, d.filename)} className="p-2 text-red-600 hover:bg-red-50 rounded">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Blocked Documents Section */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2 text-red-700">
          <ShieldAlert className="w-5 h-5" /> Blocked Documents ({blockedDocs.length})
        </h3>
        {blockedDocs.length === 0 ? (
          <p className="text-gray-500 text-sm">No blocked documents. All your documents are safe!</p>
        ) : (
          <div className="space-y-2">
            {blockedDocs.map(d => (
              <div key={d.id} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <ShieldAlert className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{d.filename}</div>
                      <div className="text-xs text-gray-600 mb-2">
                        {d.size_mb ? `${d.size_mb.toFixed(2)} MB` : 'Local'} • {new Date(d.created_at).toLocaleDateString()}
                      </div>
                      {d.scan_issues && d.scan_issues.length > 0 && (
                        <div className="text-xs text-red-700 space-y-1">
                          {d.scan_issues.slice(0, 3).map((issue, idx) => (
                            <div key={idx}>⚠️ {issue.name || issue} ({issue.severity || 'unknown'})</div>
                          ))}
                          {d.scan_issues.length > 3 && (
                            <div className="text-gray-500">+{d.scan_issues.length - 3} more issues</div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <button onClick={() => remove(d.id, d.filename)} className="p-2 text-red-600 hover:bg-red-100 rounded flex-shrink-0">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
