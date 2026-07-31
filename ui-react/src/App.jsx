import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import { Shield, MessageSquare, Upload as UploadIcon, LayoutDashboard, FileText, Target, Settings, BarChart3, LogOut } from 'lucide-react';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import ManageDocs from './pages/ManageDocs';
import AttackSim from './pages/AttackSim';
import SecurityConfig from './pages/SecurityConfig';
import Evaluate from './pages/Evaluate';

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function Layout({ children }) {
  const navigate = useNavigate();
  const username = localStorage.getItem('username') || 'user';
  const logout = () => { localStorage.clear(); navigate('/login'); };
  const links = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/chat', icon: MessageSquare, label: 'Chat' },
    { to: '/upload', icon: UploadIcon, label: 'Upload' },
    { to: '/docs', icon: FileText, label: 'Documents' },
    { to: '/attacks', icon: Target, label: 'Attacks' },
    { to: '/security', icon: Settings, label: 'Security' },
    { to: '/evaluate', icon: BarChart3, label: 'Evaluate' },
  ];
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 font-bold text-lg">
            <Shield className="w-6 h-6 text-blue-600" /> SecureRAG
          </Link>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 hidden sm:block">👤 {username}</span>
            <button onClick={logout} className="flex items-center gap-1 text-sm text-red-600 hover:text-red-700">
              <LogOut className="w-4 h-4" /> Logout
            </button>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-2 pb-2 flex gap-1 overflow-x-auto">
          {links.map(l => (
            <Link key={l.to} to={l.to} className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md hover:bg-gray-100 whitespace-nowrap">
              <l.icon className="w-4 h-4" /> {l.label}
            </Link>
          ))}
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/*" element={<ProtectedRoute><Layout><Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/docs" element={<ManageDocs />} />
          <Route path="/attacks" element={<AttackSim />} />
          <Route path="/security" element={<SecurityConfig />} />
          <Route path="/evaluate" element={<Evaluate />} />
        </Routes></Layout></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}
