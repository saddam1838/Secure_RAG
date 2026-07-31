import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User } from 'lucide-react';
import api from '../lib/api';

export default function Chat() {
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Hello! Ask me anything about your uploaded documents.' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: 'user', content: input };
    setMessages(m => [...m, userMsg]);
    setInput(''); setLoading(true);
    try {
      const { data } = await api.post('/chat', { message: input });
      setMessages(m => [...m, { role: data.blocked ? 'system' : 'assistant', content: data.reply }]);
    } catch (err) {
      setMessages(m => [...m, { role: 'system', content: 'Error: ' + (err.response?.data?.detail || err.message) }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border flex flex-col h-[calc(100vh-180px)]">
      <div className="p-4 border-b"><h2 className="text-xl font-bold">💬 Secure RAG Chat</h2></div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role !== 'user' && <Bot className={`w-8 h-8 flex-shrink-0 ${m.role === 'system' ? 'text-red-500' : 'text-blue-600'}`} />}
            <div className={`max-w-[80%] p-3 rounded-2xl ${
              m.role === 'user' ? 'bg-blue-600 text-white' :
              m.role === 'system' ? 'bg-red-50 text-red-800 border border-red-200' :
              'bg-gray-100 text-gray-800'
            }`}>
              <div className="whitespace-pre-wrap text-sm">{m.content}</div>
            </div>
            {m.role === 'user' && <User className="w-8 h-8 flex-shrink-0 text-blue-600" />}
          </div>
        ))}
        {loading && <div className="flex gap-3"><Bot className="w-8 h-8 text-blue-600" /><div className="bg-gray-100 p-3 rounded-2xl text-sm">Thinking...</div></div>}
        <div ref={endRef} />
      </div>
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Ask about your documents..." className="flex-1 px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          <button onClick={send} disabled={loading} className="bg-blue-600 text-white px-6 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
