import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import api from '../lib/api';
import toast from 'react-hot-toast';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isRegister) {
        await api.post('/auth/register', { username, password });
        toast.success('Registered! Please login.');
        setIsRegister(false);
      } else {
        const { data } = await api.post('/auth/login', { username, password });
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', username);
        toast.success(`Welcome, ${username}!`);
        navigate('/dashboard');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-10 h-10 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold">SecureRAG</h1>
            <p className="text-sm text-gray-500">Enterprise AI Security Platform</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)}
            className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" required />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)}
            className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" required />
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
            {loading ? 'Please wait...' : (isRegister ? 'Register' : 'Login')}
          </button>
        </form>
        <button onClick={() => setIsRegister(!isRegister)} className="w-full mt-4 text-sm text-blue-600 hover:underline">
          {isRegister ? 'Already have an account? Login' : "Don't have an account? Register"}
        </button>
      </div>
    </div>
  );
}
