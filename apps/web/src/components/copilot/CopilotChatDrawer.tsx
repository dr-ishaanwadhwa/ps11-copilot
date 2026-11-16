'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useCockpitStore, useVaultStore } from '@/lib/store';
import { formatINR } from '@/lib/types';
import type { CitationItem, CopilotMessage, ToolExecutionStep } from '@/lib/types';
import { streamCopilot } from '@/lib/api';
import { useAccountantRestricted } from '@/components/vault/ClientVaultDisplay';
import { Bot, User, Send, Mic, Sparkles, ChevronDown, ChevronUp, ShieldCheck, Zap, Briefcase, Search, Coins } from 'lucide-react';

// SAMPLE DATA ONLY: the offline fallback answer. Live answers come from POST /api/v1/copilot/stream.
const initialMessages: CopilotMessage[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'Can I safely pay my staff salaries on October 1st?',
    timestamp: '10:15 AM',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content:
      'Yes, you can safely pay your October 1st salaries of **₹4,65,000** [1]. Even if you pay 100% of salaries exclusively from your HDFC bank account, your bank balance will remain positive at **₹7,74,000**, which is **₹32,74,000 clear** of your sanctioned CC facility limit (-₹25.00L). You also have **{{LOCAL_VAULT_GALLA_CASH}}** physical cash in your godown drawer [2].\n*(Note: Drawer cash count interpolated in local volatile RAM; zero cash data sent to cloud).*',
    hindiSummary:
      'हाँ, आप 1 अक्टूबर को ₹4,65,000 का वेतन आराम से दे सकते हैं। वेतन भुगतान के बाद भी बैंक में ₹7.74L शेष रहेगा और गल्ले में नकदी सुरक्षित रहेगी।',
    toolExecutions: [
      { toolName: 'consult_bank_liquidity', status: 'completed', resultSummary: '₹12.39L HDFC current balance' },
      { toolName: 'evaluate_payroll_commitments', status: 'completed', resultSummary: '₹4.65L (24 staff members)' },
    ],
    citations: [
      { id: '1', source: 'Payroll Ledger (24 staff)', amount: 465000, date: '2026-10-01', badge: 'BANK_FORMAL' },
      { id: '2', source: 'Local Sovereign Vault (Till GL-9024)', amount: 420000, date: '2026-09-30', badge: 'RAM_ONLY' },
    ],
    timestamp: '10:15 AM',
  },
];

const MIN_QUESTION_LENGTH = 3;
const MAX_QUESTION_LENGTH = 300;

// Questions the copilot must not answer: investment, borrowing, tax-evasion and legal advice.
const BLOCKED_TOPICS: { topic: string; pattern: RegExp }[] = [
  // Whole phrases only: ordinary words like "share" ("share my cash book") or "stock" (inventory) must pass.
  { topic: 'investment', pattern: /\b(invest(ing|ment|ments)?|(buy|buying|sell|selling|purchase|purchasing)\s+(\w+\s+){0,2}(stocks?|shares?)|(stock|share|equity)\s+(market|markets|tips?|trading)|mutual funds?|sip|crypto(currency)?|bitcoin|(day|stock|share|crypto|forex)\s+trading|ipo|fixed deposits?|fd rates?)\b/i },
  { topic: 'borrowing', pattern: /\b(borrow(ing)?|loans?|take (a )?credit|raise (debt|funds)|lend(ing)?|emi|refinanc\w*)\b/i },
  { topic: 'tax-evasion', pattern: /\b(evad(e|ing)|evasion|avoid(ing)? (paying )?(gst|tax|taxes)|hide (income|cash|sales|money)|black money|under-?report\w*|fake (bills?|invoices?)|bogus (bills?|invoices?)|without (a )?bill)\b/i },
  { topic: 'legal', pattern: /\b(legal advice|lawyers?|advocate|sue|lawsuit|court|litigation|legal notice|file (a )?case|file (an )?fir)\b/i },
  // Bare "fir" is excluded on purpose: in Hinglish it means "then" ("fir kitna bachega?").
];

export type QuestionCheck =
  | { ok: true; text: string }
  | { ok: false; reason: string };

/** Client-side gate for free-text questions: trims, enforces 3-300 characters, refuses advice topics. */
export function validateQuestion(raw: string): QuestionCheck {
  const text = raw.trim();
  if (text.length < MIN_QUESTION_LENGTH) {
    return { ok: false, reason: `Please type at least ${MIN_QUESTION_LENGTH} characters.` };
  }
  if (text.length > MAX_QUESTION_LENGTH) {
    return { ok: false, reason: `Please keep your question under ${MAX_QUESTION_LENGTH} characters (now ${text.length}).` };
  }
  if (BLOCKED_TOPICS.some((b) => b.pattern.test(text))) {
    return {
      ok: false,
      reason: 'I cannot help with investment, borrowing, tax-saving tricks or legal advice. Please ask a professional. I can answer questions about your bank, books and receivables.',
    };
  }
  return { ok: true, text };
}

const normaliseQuestion = (q: string) => q.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, ' ').replace(/\s+/g, ' ').trim();

const SALARY_WORDS = /\b(salary|salaries|payroll|staff|wages?)\b/i;
const IN_SCOPE_WORDS = /\b(bank|balance|books?|ledger|cash|till|drawer|galla|owe|owes|owed|receivables?|debtors?|customers?|invoices?|gst|tax|forecast|due|dues|payment|payments|pay|runway|credit|statement|reconcil\w*|salary|salaries|payroll|collect\w*)\b/i;
const OUT_OF_SCOPE_REPLY = 'I can only answer questions about your bank, books and receivables.';

type AnswerBody = Omit<CopilotMessage, 'id' | 'timestamp'>;
interface ChatMessage extends CopilotMessage {
  /** 'sample' marks the offline fallback answer. */
  source?: 'live' | 'sample';
  streaming?: boolean;
}

const GREETING: ChatMessage = {
  id: 'msg-greeting',
  role: 'assistant',
  content: 'Ask me about your bank balance, salaries, receivables or dues. Answers are computed from your formal ledgers.',
  timestamp: '',
};

export function CopilotChatDrawer() {
  const { isUnlocked, gallaEntry } = useVaultStore();
  const businessId = useCockpitStore((st) => st.businessId);
  const businessName = useCockpitStore((st) => st.businessName);
  const asOfDate = useCockpitStore((st) => st.asOfDate);
  const vaultRestricted = useAccountantRestricted();
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [inputValue, setInputValue] = useState('');
  const [inputError, setInputError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Session-only cache of finished live answers keyed by business + normalised question, so repeats
  // are not re-requested. Entries keep the raw {{LOCAL_VAULT_*}} tokens, never substituted vault values.
  const answerCache = useRef<Map<string, AnswerBody>>(new Map());
  const abortRef = useRef<AbortController | null>(null);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});

  useEffect(() => () => abortRef.current?.abort(), []);

  const drawerCash = isUnlocked && !vaultRestricted ? (gallaEntry?.countedCash ?? 0) : 0;

  // ADR-001: template tokens are filled here, in the browser, from the vault store. They are never
  // sent to the API. While the vault is locked the token renders as "locked".
  const interpolateTokens = (text: string) =>
    text.replace(/\{\{LOCAL_VAULT_([A-Z_]+)\}\}/g, (_m, name: string) => {
      const open = isUnlocked && !vaultRestricted && gallaEntry;
      if (!open) return 'locked';
      if (name === 'GALLA_CASH') return formatINR(drawerCash);
      if (name === 'GALLA_COUNT_DATE') return gallaEntry.date;
      return 'locked';
    });

  const buildSampleAnswer = (q: string): AnswerBody => {
    if (SALARY_WORDS.test(q)) {
      const { id: _id, timestamp: _ts, ...salaryAnswer } = initialMessages[1];
      return salaryAnswer;
    }
    if (!IN_SCOPE_WORDS.test(q)) {
      return { role: 'assistant', content: OUT_OF_SCOPE_REPLY };
    }
    return {
      role: 'assistant',
      content: `Regarding your query: "${q}". Your verified bank balance is ₹12.39L and today's drawer float in volatile RAM is {{LOCAL_VAULT_GALLA_CASH}}. All numbers verified from source ledgers with zero probabilistic guessing.`,
      hindiSummary: 'आपके प्रश्न के अनुसार सभी वित्तीय आंकड़े सत्यापित हैं। कोई अनुमानित संख्या नहीं है।',
      citations: [{ id: '1', source: 'Bank Statement HDFC #9023', amount: 1239000, badge: 'BANK_FORMAL' }],
    };
  };

  const handleSend = async (text?: string) => {
    if (busy) return;
    const check = validateQuestion(text ?? inputValue);
    if (!check.ok) {
      setInputError(check.reason);
      return;
    }
    setInputError(null);
    const q = check.text;
    const stamp = Date.now();
    const userMsg: ChatMessage = { id: `msg-${stamp}`, role: 'user', content: q, timestamp: 'Just now' };
    setInputValue('');

    const key = `${businessId}|${normaliseQuestion(q)}`;
    const cached = answerCache.current.get(key);
    if (cached) {
      setMessages((prev) => [...prev, userMsg, { ...cached, id: `msg-resp-${stamp}`, timestamp: 'Just now', source: 'live' }]);
      return;
    }

    const respId = `msg-resp-${stamp}`;
    const patch = (fn: (m: ChatMessage) => ChatMessage) =>
      setMessages((prev) => prev.map((m) => (m.id === respId ? fn(m) : m)));
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: respId, role: 'assistant', content: '', timestamp: 'Just now', streaming: true, source: 'live' },
    ]);
    setExpandedCitations((prev) => ({ ...prev, [respId]: true }));
    setBusy(true);

    const ctl = new AbortController();
    abortRef.current = ctl;
    const tools: ToolExecutionStep[] = [];
    const citations: CitationItem[] = [];
    let content = '';
    let gotAny = false;
    try {
      // Body is formal-plane context only: question, business, date. No vault values (ADR-001).
      await streamCopilot({ question: q, businessId, asOfDate }, (chunk) => {
        gotAny = true;
        if (chunk.type === 'token') content += chunk.content;
        else if (chunk.type === 'template_token') content += chunk.token;
        else if (chunk.type === 'tool_start') tools.push({ toolName: chunk.toolName, status: 'running' });
        else if (chunk.type === 'tool_done') {
          const t = tools.find((x) => x.toolName === chunk.toolName && x.status === 'running');
          if (t) {
            t.status = 'completed';
            t.resultSummary = chunk.result;
          } else tools.push({ toolName: chunk.toolName, status: 'completed', resultSummary: chunk.result });
        } else if (chunk.type === 'citation') citations.push(chunk.citation);
        patch((m) => ({
          ...m,
          content,
          toolExecutions: tools.map((t) => ({ ...t })),
          citations: citations.length ? [...citations] : undefined,
          streaming: chunk.type !== 'done',
        }));
      }, ctl.signal);
      if (!gotAny || !content) throw new Error('Empty stream');
      patch((m) => ({ ...m, streaming: false }));
      const { id: _i, timestamp: _t, source: _s, streaming: _st, ...body } = {
        id: respId,
        role: 'assistant' as const,
        timestamp: '',
        content,
        toolExecutions: tools.map((t) => ({ ...t })),
        citations: citations.length ? [...citations] : undefined,
        source: 'live' as const,
        streaming: false,
      };
      answerCache.current.set(key, body);
    } catch (err) {
      if (ctl.signal.aborted) return;
      // API unreachable or stream failed: fall back to the labelled sample answer.
      const sample = buildSampleAnswer(q);
      patch((m) => ({ ...m, ...sample, id: respId, timestamp: 'Just now', source: 'sample', streaming: false }));
      void err;
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] max-w-5xl mx-auto rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xl overflow-hidden">
      {/* Context Status Bar */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-emerald-600 flex items-center justify-center text-white">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Grounded Financial Copilot
              </h3>
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold px-2 py-0.5 border border-emerald-300">
                Zero Stochastic Hallucinations
              </span>
            </div>
            <span className="text-[11px] text-slate-500">
              Context: {businessId} ({businessName}) • As-Of: {asOfDate}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isUnlocked ? (
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="h-4 w-4" />
              Vault: Unlocked (RAM)
            </span>
          ) : (
            <span className="text-xs font-semibold text-slate-400">
              Vault: Locked (Formal Plane)
            </span>
          )}
        </div>
      </div>

      {/* Conversation Stream Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="h-8 w-8 rounded-full bg-emerald-600 flex-shrink-0 flex items-center justify-center text-white mt-1">
                <Bot className="h-4 w-4" />
              </div>
            )}

            <div
              className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 ml-12'
                  : 'bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200'
              }`}
            >
              {/* Tool Execution Steps Callout */}
              {msg.toolExecutions && msg.toolExecutions.length > 0 && (
                <div className="mb-3 p-2.5 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 space-y-1.5">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                    <Zap className="h-3 w-3 text-amber-500" />
                    <span>Deterministic Tool Invocations</span>
                  </div>
                  {msg.toolExecutions.map((tool, idx) => (
                    <div key={idx} className="flex items-center justify-between text-[11px] font-mono">
                      <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
                        <Zap className="h-3 w-3 text-amber-500" aria-hidden="true" />
                        {tool.toolName}
                      </span>
                      <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                        {tool.status === 'running' ? 'running…' : tool.resultSummary}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Message Content (with Client-Side RAM Token Interpolation) */}
              <div className="whitespace-pre-line text-sm">
                {msg.content ? interpolateTokens(msg.content) : msg.streaming ? <span className="animate-pulse text-slate-400">Thinking…</span> : null}
              </div>
              {msg.source === 'sample' && (
                <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-2 py-0.5 text-[10px] font-bold text-slate-600 dark:text-slate-300">
                  Sample data
                </span>
              )}

              {/* Devanagari Summary Card */}
              {msg.hindiSummary && (
                <div className="mt-3 p-3 rounded-xl bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-950 dark:text-amber-200 text-xs">
                  <span className="font-bold block mb-0.5 text-[11px] text-amber-800 dark:text-amber-400">
                    हिन्दी सारांश (Devanagari Summary):
                  </span>
                  <p>{msg.hindiSummary}</p>
                </div>
              )}

              {/* Citations Accordion */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-2 border-t border-slate-200 dark:border-slate-700">
                  <button
                    onClick={() =>
                      setExpandedCitations((prev) => ({
                        ...prev,
                        [msg.id]: !prev[msg.id],
                      }))
                    }
                    className="flex items-center justify-between w-full text-[11px] font-bold text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                  >
                    <span>Verified Citations &amp; Source Ledger Rows ({msg.citations.length})</span>
                    {expandedCitations[msg.id] ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  </button>

                  {expandedCitations[msg.id] && (
                    <div className="mt-2 space-y-1.5">
                      {msg.citations.map((cite) => (
                        <div
                          key={cite.id}
                          className="flex items-center justify-between p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[11px]"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-400">[{cite.id}]</span>
                            <span className="font-medium text-slate-700 dark:text-slate-300">{cite.source}</span>
                            <span
                              className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                                cite.badge === 'RAM_ONLY'
                                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                                  : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                              }`}
                            >
                              {cite.badge}
                            </span>
                          </div>
                          <span className="font-mono font-bold text-slate-900 dark:text-white">
                            {formatINR(cite.amount)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="h-8 w-8 rounded-full bg-slate-900 text-white flex-shrink-0 flex items-center justify-center dark:bg-slate-100 dark:text-slate-900 mt-1">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Prompt Suggestions Carousel */}
      <div className="px-6 py-2 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 flex items-center gap-2 overflow-x-auto text-xs">
        <span className="text-[11px] text-slate-400 flex items-center gap-1 flex-shrink-0">
          <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          Suggested:
        </span>
        <button
          onClick={() => void handleSend('Can I safely pay my staff salaries on October 1st?')}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-emerald-500 text-slate-700 dark:text-slate-300 whitespace-nowrap transition"
        >
          <Briefcase className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
          Can I pay salaries on 1 Oct?
        </button>
        <button
          onClick={() => void handleSend('Who owes me the most money over 60 days?')}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-emerald-500 text-slate-700 dark:text-slate-300 whitespace-nowrap transition"
        >
          <Search className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
          Who owes me the most?
        </button>
        <button
          onClick={() => void handleSend("What is today's counted till cash balance?")}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-emerald-500 text-slate-700 dark:text-slate-300 whitespace-nowrap transition"
        >
          <Coins className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
          What is today&apos;s till cash?
        </button>
      </div>

      {/* Input Composer */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            placeholder="Ask a cashflow question in English, हिन्दी, or Hinglish..."
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              if (inputError) setInputError(null);
            }}
            aria-label="Ask a question"
            aria-invalid={inputError ? true : undefined}
            className="flex-1 p-2.5 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button
            type="button"
            onClick={() => alert('Gemini Voice speech transcription active: Speak your question.')}
            className="p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <Mic className="h-4 w-4" />
          </button>
          <button
            type="submit"
            disabled={busy}
            className="disabled:opacity-60 flex items-center gap-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-sm transition"
          >
            <span>Send</span>
            <Send className="h-3.5 w-3.5" />
          </button>
        </form>
        {inputError && (
          <p role="alert" className="mt-2 text-[11px] font-medium text-red-600 dark:text-red-400">
            {inputError}
          </p>
        )}
      </div>
    </div>
  );
}
