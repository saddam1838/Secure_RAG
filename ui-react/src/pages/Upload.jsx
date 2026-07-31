import { useState } from 'react';
import { Upload as UploadIcon, ShieldCheck, ShieldAlert } from 'lucide-react';
import api from '../lib/api';
import toast from 'react-hot-toast';

export default function Upload() {
  const [file, setFile] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [indexing, setIndexing] = useState(false);

  const scan = async () => {
    if (!file) return;
    setScanning(true); setScanResult(null);
    const fd = new FormData(); fd.append('file', file);
    try {
      const { data } = await api.post('/documents/scan', fd);
      setScanResult(data);
      toast[data.is_safe ? 'success' : 'error'](data.message);
    } catch (err) { toast.error(err.response?.data?.detail || 'Scan failed'); }
    finally { setScanning(false); }
  };

  const index = async () => {
    if (!file) return;
    setIndexing(true);
    const fd = new FormData(); fd.append('file', file);
    try {
      const { data } = await api.post('/documents/upload-and-index', fd);
      toast.success(data.message || 'Indexed successfully!');
      setFile(null); setScanResult(null);
    } catch (err) { toast.error(err.response?.data?.detail || 'Index failed'); }
    finally { setIndexing(false); }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2"><UploadIcon className="w-6 h-6" /> Secure Upload</h2>
        <p className="text-sm text-gray-600 mb-4">Files are scanned for prompt injections, hidden payloads, and PII before indexing.</p>
        <input type="file" onChange={e => setFile(e.target.files[0])} accept=".txt,.pdf,.docx,.html,.md" className="w-full p-3 border-2 border-dashed rounded-lg" />
        <button onClick={scan} disabled={!file || scanning} className="mt-4 w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
          {scanning ? 'Scanning...' : '🔍 Scan for Threats'}
        </button>
      </div>

      {scanResult && (
        <div className={`rounded-xl border p-6 ${scanResult.is_safe ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-center gap-3 mb-3">
            {scanResult.is_safe ? <ShieldCheck className="w-8 h-8 text-green-600" /> : <ShieldAlert className="w-8 h-8 text-red-600" />}
            <div>
              <h3 className="font-bold text-lg">{scanResult.message}</h3>
              <p className="text-sm">{scanResult.filename} • {scanResult.size_mb} MB</p>
            </div>
          </div>
          {scanResult.issues?.length > 0 && (
            <div className="mt-3 space-y-1">
              {scanResult.issues.map((i, idx) => (
                <div key={idx} className="text-sm bg-white/60 p-2 rounded">⚠️ {i.name} ({i.severity})</div>
              ))}
            </div>
          )}
          {scanResult.is_safe && (
            <button onClick={index} disabled={indexing} className="mt-4 w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50">
              {indexing ? 'Indexing...' : '✅ Index Secure Document'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
