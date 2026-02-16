'use client';

import { useState, useRef, useEffect } from 'react';

interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; }

const QUICK_PROMPTS = [
  "What data do you have?",
  "How does search work?",
  "API access info",
  "Pricing and plans",
  "Data export formats",
  "Coverage by state",
];

export function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg || isLoading) return;
    
    setMessages(prev => [...prev, { id: `u-${Date.now()}`, role: 'user', content: msg }]);
    setInput('');
    setIsLoading(true);
    
    setTimeout(() => {
      setMessages(prev => [...prev, { id: `a-${Date.now()}`, role: 'assistant', content: getResponse(msg) }]);
      setIsLoading(false);
    }, 500);
  };

  if (!isOpen) return (
    <button onClick={() => setIsOpen(true)} className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-blue-600 text-white shadow-lg z-50 hover:bg-blue-700 flex items-center justify-center">
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
    </button>
  );

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-white rounded-2xl shadow-2xl flex flex-col z-50 border">
      <div className="p-4 bg-blue-600 text-white rounded-t-2xl flex justify-between items-center">
        <div>
          <h3 className="font-semibold">DataGod Support</h3>
          <p className="text-sm opacity-90">Public records assistance</p>
        </div>
        <button onClick={() => setIsOpen(false)} className="hover:bg-blue-700 p-1 rounded">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>
      
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        {messages.length === 0 && (
          <div className="text-center py-4">
            <p className="text-gray-600 mb-4">How can I help with public records?</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {QUICK_PROMPTS.map((p, i) => (
                <button key={i} onClick={() => handleSend(p)} className="px-3 py-1 text-sm bg-white border rounded-full hover:border-blue-400 hover:bg-blue-50">{p}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map(m => (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] px-4 py-2 rounded-2xl ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border shadow-sm'}`}>
              {m.content}
            </div>
          </div>
        ))}
        {isLoading && <div className="flex justify-start"><div className="bg-white border px-4 py-2 rounded-2xl shadow-sm">Typing...</div></div>}
      </div>
      
      <div className="p-4 border-t bg-white rounded-b-2xl">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask about data..." className="flex-1 px-4 py-2 border rounded-full focus:outline-none focus:border-blue-400" />
          <button type="submit" disabled={isLoading || !input.trim()} className="w-10 h-10 rounded-full bg-blue-600 text-white disabled:opacity-50 flex items-center justify-center">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
          </button>
        </form>
      </div>
    </div>
  );
}

function getResponse(q: string): string {
  const question = q.toLowerCase();
  if (question.includes('data') && (question.includes('what') || question.includes('have'))) return "DataGod aggregates public records from 10,000+ US jurisdictions:\n• Court records & case filings\n• Property records & deeds\n• Business registrations\n• Government filings\n• Arrest & criminal records\n• Marriage/divorce records";
  if (question.includes('search')) return "Our search supports:\n• Full-text search across all records\n• Advanced filters (date, jurisdiction, type)\n• Fuzzy name matching\n• Boolean operators\n• Saved searches with alerts\n• Bulk search via API";
  if (question.includes('api')) return "API access includes:\n• RESTful endpoints\n• Bulk search & export\n• Real-time webhooks\n• Rate limits: 1000 req/min (Pro), 10000/min (Enterprise)\n• Python & Node.js SDKs\n• Sandbox environment";
  if (question.includes('price') || question.includes('pricing') || question.includes('plan')) return "Plans:\n• Free: 50 searches/month, basic filters\n• Pro ($99/mo): Unlimited searches, API, exports\n• Enterprise: Custom pricing, bulk data, SLA\n\nAll plans include real-time updates.";
  if (question.includes('export') || question.includes('format')) return "Export formats:\n• CSV (all plans)\n• JSON (Pro+)\n• Excel (Pro+)\n• PDF reports (Enterprise)\n• Bulk API export\n• Scheduled exports";
  if (question.includes('coverage') || question.includes('state')) return "Coverage:\n• All 50 states\n• 10,000+ jurisdictions\n• Federal courts\n• Updated daily\n• Historical data back to 1990s\n• Coverage map at /jurisdictions";
  return "DataGod provides comprehensive US public records data. I can help with: data coverage, search features, API access, pricing, or export options. What would you like to know?";
}

export default AIChatWidget;
