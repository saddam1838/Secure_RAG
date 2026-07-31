import { useEffect, useState } from 'react';
import { Trash2, RefreshCw } from 'lucide-react';
import api from '../lib/api';
import toast from 'react-hot-toast';

export default function ManageDocs() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.get('/documents').then(r => setDocs(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const del = async (id, name) => {
    if (!confirm(`Delete ${name}?`)) return;
    try {
      await api.delete(`/documents/${id}`);
      toast.success('Deleted'); load();
    } catch { toast.error('Delete failed'); }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border">
      <div className="p-4 border-b flex justify-between items-center">
        <h2 className="text-xl font-bold">📁 My Documents</h2>
        <button onClick={load} className="p-2 hover:bg-gray-100 rounded"><RefreshCw className="w-5 h-5" /></button>
      </div>
      {loading ? <div className="p-8 text-center">Loading...</div> : docs.length === 0 ? (
        <div className="p-8 text-center text-gray-500">No documents uploaded yet</div>
      ) : (
        <div className="divide-y">
          {docs.map(d => (
            <div key={d.id} className="p-4 flex justify-between items-center hover:bg-gray-50">
              <div>
                <div className="font-medium">{d.filename}</div>
                <div className="text-xs text-gray-500">{d.size_mb?.toFixed(2)} MB • {d.created_at?.split('T')[0]}</div>
              </div>
              <button onClick={() => del(d.id, d.filename)} className="p-2 text-red-600 hover:bg-red-50 rounded">
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
