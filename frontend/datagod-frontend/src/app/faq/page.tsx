'use client';

import { useState } from 'react';
import Link from 'next/link';

interface FAQ { question: string; answer: string; }
interface Category { name: string; icon: string; items: FAQ[]; }

const FAQ_DATA: Category[] = [
  {
    name: "Getting Started",
    icon: "🚀",
    items: [
      { question: "What is DataGod?", answer: "DataGod is a comprehensive platform for searching and analyzing public records from 10,000+ US jurisdictions. We aggregate court records, property records, business registrations, and more into a single searchable database." },
      { question: "What data sources do you cover?", answer: "We cover: court records (civil, criminal, bankruptcy), property records & deeds, business registrations & filings, arrest records, marriage/divorce records, liens & judgments, UCC filings, and more." },
      { question: "How current is the data?", answer: "Most jurisdictions update daily. Some smaller jurisdictions update weekly. You can see the last update date for each source in search results. We also offer real-time alerts for new records." },
      { question: "Is this data legal to access?", answer: "Yes. All data in DataGod comes from public records that are legally accessible. We comply with all applicable laws including FCRA for consumer reporting." },
    ]
  },
  {
    name: "Search & Filters",
    icon: "🔍",
    items: [
      { question: "How does search work?", answer: "Enter a name, business, address, or case number. Our engine supports full-text search, fuzzy matching for name variations, Boolean operators (AND, OR, NOT), and advanced filters for date, jurisdiction, and record type." },
      { question: "Can I search multiple people at once?", answer: "Yes! Pro and Enterprise plans support bulk search. Upload a CSV of names or use our API for batch queries. Results are returned in a downloadable report." },
      { question: "How do I narrow my results?", answer: "Use filters: jurisdiction (state, county, court), date range, record type, case status, and more. You can also save filter combinations as presets for quick access." },
      { question: "What is fuzzy name matching?", answer: "Fuzzy matching finds records even with spelling variations, typos, or name changes. 'John Smith' will also find 'Jon Smith', 'John Smyth', etc. You can adjust sensitivity in search settings." },
    ]
  },
  {
    name: "Data Coverage",
    icon: "🗺️",
    items: [
      { question: "Which states do you cover?", answer: "All 50 US states plus DC, Puerto Rico, and US territories. Coverage depth varies by jurisdiction - major metros have the most complete records. See our coverage map at /jurisdictions." },
      { question: "How far back does historical data go?", answer: "Varies by jurisdiction. Most have data from 2000+. Major courts often go back to the 1990s. Some property records extend to the 1970s. We're continuously adding historical data." },
      { question: "Do you have federal court records?", answer: "Yes. We cover all federal district courts, circuit courts of appeal, bankruptcy courts, and US Tax Court through PACER integration." },
      { question: "What about international records?", answer: "Currently US-only. International coverage is on our roadmap for 2027. For now, we recommend specialized international databases for non-US records." },
    ]
  },
  {
    name: "API & Integration",
    icon: "⚙️",
    items: [
      { question: "How do I access the API?", answer: "API access is included in Pro and Enterprise plans. Get your API key from Settings > API Keys. Full documentation at /api-docs with OpenAPI spec, code examples, and SDKs." },
      { question: "What are the rate limits?", answer: "Free: 50 requests/day. Pro: 1,000 requests/minute. Enterprise: 10,000+ requests/minute (custom). Rate limit headers are included in all API responses." },
      { question: "Can I get real-time alerts?", answer: "Yes! Set up webhooks to receive notifications when new records match your saved searches. Great for monitoring litigation, property changes, or business filings." },
      { question: "Do you have SDKs?", answer: "Official SDKs for Python, Node.js, and Ruby. Community SDKs for Go, Java, and C#. All available on GitHub with examples." },
    ]
  },
  {
    name: "Export & Reports",
    icon: "📊",
    items: [
      { question: "What export formats are available?", answer: "CSV (all plans), JSON (Pro+), Excel with formatting (Pro+), PDF reports (Enterprise). Bulk exports via API can handle millions of records." },
      { question: "Can I schedule automatic exports?", answer: "Enterprise plans include scheduled exports. Set up daily, weekly, or monthly exports of saved searches delivered via email, SFTP, or cloud storage." },
      { question: "Are there limits on exports?", answer: "Free: 100 records/export. Pro: 10,000 records/export. Enterprise: Unlimited. Large exports are processed async and you're notified when ready." },
      { question: "Can I white-label reports?", answer: "Enterprise plans support white-label PDF reports with your logo and branding. Contact sales for customization options." },
    ]
  },
  {
    name: "Pricing & Billing",
    icon: "💳",
    items: [
      { question: "What plans are available?", answer: "Free: 50 searches/month, basic features. Pro ($99/mo): Unlimited searches, API, exports. Enterprise: Custom pricing for high-volume, SLA, dedicated support." },
      { question: "Is there a free trial?", answer: "Yes! Pro plans include a 14-day free trial with full access. No credit card required to start. Enterprise trials are available upon request." },
      { question: "Can I change plans anytime?", answer: "Yes. Upgrade instantly, downgrade at end of billing cycle. No long-term contracts required for Free or Pro plans." },
      { question: "Do you offer volume discounts?", answer: "Enterprise plans include volume pricing. Discounts start at 10K+ searches/month. Contact sales for a custom quote." },
    ]
  },
];

export default function FAQPage() {
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const filtered = FAQ_DATA.map(cat => ({
    ...cat,
    items: cat.items.filter(i => 
      i.question.toLowerCase().includes(search.toLowerCase()) ||
      i.answer.toLowerCase().includes(search.toLowerCase())
    )
  })).filter(c => c.items.length > 0);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-blue-600 text-white py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl font-bold mb-4">Help Center</h1>
          <p className="text-xl opacity-90 mb-8">24 answers about public records data</p>
          <input
            type="text"
            placeholder="Search questions..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full max-w-md px-6 py-3 rounded-full text-gray-900"
          />
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4">
        {filtered.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No results for "{search}"</p>
            <button onClick={() => setSearch('')} className="mt-4 text-blue-600 hover:underline">Clear</button>
          </div>
        ) : (
          filtered.map((cat, ci) => (
            <div key={cat.name} className="mb-10">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <span>{cat.icon}</span>{cat.name}
              </h2>
              <div className="space-y-3">
                {cat.items.map((faq, fi) => {
                  const key = `${ci}-${fi}`;
                  return (
                    <div key={key} className="bg-white rounded-lg shadow-sm border overflow-hidden">
                      <button onClick={() => setOpen(p => ({...p, [key]: !p[key]}))} className="w-full p-4 text-left flex justify-between items-center hover:bg-gray-50">
                        <span className="font-medium">{faq.question}</span>
                        <span className={`transform transition-transform ${open[key] ? 'rotate-180' : ''}`}>▼</span>
                      </button>
                      {open[key] && <div className="px-4 pb-4 text-gray-600 whitespace-pre-line">{faq.answer}</div>}
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}

        <div className="mt-12 bg-blue-600 rounded-2xl p-8 text-center text-white">
          <h3 className="text-2xl font-bold mb-2">Still have questions?</h3>
          <p className="opacity-90 mb-6">Our team is ready to help</p>
          <Link href="mailto:support@datagod.io" className="inline-block px-6 py-3 bg-white text-blue-600 rounded-full font-semibold hover:bg-gray-100">
            Contact Support
          </Link>
        </div>
      </div>
    </div>
  );
}
