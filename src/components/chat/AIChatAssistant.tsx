import React, { useEffect, useRef, useState } from 'react';
import {
  Sparkles,
  Send,
  X,
  Trash2,
  MessageSquare,
  AlertTriangle,
  Loader2,
  Database,
  ShieldAlert,
} from 'lucide-react';
import { AIChatMessage } from '../../types';
import { askAIAssistant, getAIChatSuggestions } from '../../services/api';

/**
 * ClimaCred AI Assistant - floating chat button (bottom-right) + chat panel.
 *
 * The browser only sends the question and the current session's turns; the
 * FastAPI backend collects the user's stored ClimaCred data automatically and
 * asks Gemini. The Gemini API key never reaches this component.
 */
const FALLBACK_SUGGESTIONS = [
  "What's my biggest climate risk?",
  'What changed recently?',
  'What should I do next?',
  'Explain my climate score.',
];

const SESSION_KEY = 'climacred_ai_chat_session';

const newId = () => Math.random().toString(36).slice(2, 10);

const readSession = (): AIChatMessage[] => {
  try {
    const raw = window.sessionStorage.getItem(SESSION_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const writeSession = (messages: AIChatMessage[]) => {
  try {
    // Keep the browser session's conversation so follow-ups keep working while
    // the user navigates between pages. Nothing is stored server-side.
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(messages.slice(-30)));
  } catch {
    // sessionStorage unavailable - the conversation simply stays in memory
  }
};

const timeLabel = (iso: string): string => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
};

export const AIChatAssistant: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<AIChatMessage[]>(() => readSession());
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_SUGGESTIONS);
  const [hasData, setHasData] = useState<boolean | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  // Suggested questions come from the backend and adapt to whether real data exists.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const res = await getAIChatSuggestions();
      if (cancelled) return;
      setHasData(res.has_data);
      if (res.suggestions?.length) setSuggestions(res.suggestions);
    })();
    return () => { cancelled = true; };
  }, [open]);

  useEffect(() => {
    writeSession(messages);
  }, [messages]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    inputRef.current?.focus();
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const el = scrollRef.current;
    if (!el) return;
    // Guarded for environments without Element.scrollTo (older browsers / test DOMs)
    if (typeof el.scrollTo === 'function') {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    } else {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, open, loading]);

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || loading) return;

    const userMessage: AIChatMessage = {
      id: newId(),
      role: 'user',
      content: question,
      createdAt: new Date().toISOString(),
    };
    const pendingId = newId();
    const history = messages
      .filter((m) => !m.error)
      .map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: pendingId, role: 'assistant', content: '', createdAt: new Date().toISOString(), pending: true },
    ]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const res = await askAIAssistant(question, history);
      setHasData(res.has_data);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? {
                ...m,
                pending: false,
                content: res.reply,
                source: res.source,
                ai_available: res.ai_available,
                notice: res.notice ?? null,
              }
            : m
        )
      );
    } catch (err: any) {
      // Clean user-facing error; the technical detail stays in the console.
      console.warn('AI chat request failed', err);
      const message = 'AI assistant is temporarily unavailable. Your calculated data on the dashboard is unaffected.';
      setError(message);
      setMessages((prev) =>
        prev.map((m) => (m.id === pendingId ? { ...m, pending: false, error: message, content: '' } : m))
      );
    } finally {
      setLoading(false);
    }
  };

  const clearConversation = () => {
    setMessages([]);
    setError(null);
    writeSession([]);
  };

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    void send(input);
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void send(input);
    }
  };

  return (
    <>
      {/* Floating action button - bottom right, visible on every page */}
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        data-testid="ai-chat-fab"
        aria-label={open ? 'Close ClimaCred AI Assistant' : 'Open ClimaCred AI Assistant'}
        aria-expanded={open}
        className="fixed bottom-5 right-5 z-[60] inline-flex items-center gap-2 rounded-full bg-gradient-to-br from-emerald-600 via-teal-600 to-emerald-700 px-4 py-3 text-white shadow-lg shadow-emerald-600/30 transition-transform hover:scale-[1.03] focus:outline-hidden focus-visible:ring-2 focus-visible:ring-emerald-400"
      >
        {open ? <X className="w-4 h-4" /> : <MessageSquare className="w-4 h-4" />}
        <span className="hidden sm:inline text-xs font-bold">
          {open ? 'Close' : 'ClimaCred AI'}
        </span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[65] flex items-end justify-end p-0 sm:p-5"
          role="dialog"
          aria-modal="true"
          aria-label="ClimaCred AI Assistant"
        >
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs" onClick={() => setOpen(false)} />

          <section className="relative w-full sm:max-w-md h-[85vh] sm:h-[70vh] bg-white border border-slate-200 rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden mb-16 sm:mb-20">
            {/* Header */}
            <header className="px-4 py-3 border-b border-slate-200/80 bg-gradient-to-r from-emerald-50 via-teal-50 to-slate-50 flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-700 text-white flex items-center justify-center shrink-0">
                  <Sparkles className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <h3 className="text-sm font-extrabold text-slate-900 tracking-tight truncate">
                    ClimaCred AI Assistant
                  </h3>
                  <p className="text-[11px] text-slate-600 truncate">Ask me about your climate data</p>
                </div>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  onClick={clearConversation}
                  title="Start a new conversation"
                  aria-label="Start a new conversation"
                  data-testid="ai-chat-clear"
                  className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-white/70"
                  disabled={loading || messages.length === 0}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  title="Close assistant"
                  aria-label="Close assistant"
                  className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-white/70"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </header>

            {/* Conversation */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-slate-50/60">
              {messages.length === 0 && (
                <div className="space-y-3">
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {hasData === false
                      ? "I don't have your business climate data yet. Complete your Climate Assessment and I'll analyze it for you."
                      : 'Ask me anything about your stored ClimaCred data - risks, trends, scores, costs or next steps.'}
                  </p>
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600">
                      Suggested questions
                    </span>
                    <div className="flex flex-col gap-1.5">
                      {suggestions.map((question) => (
                        <button
                          key={question}
                          type="button"
                          onClick={() => void send(question)}
                          className="text-left text-[11px] font-medium text-emerald-900 bg-white border border-emerald-200/80 rounded-xl px-3 py-2 hover:bg-emerald-50 transition-colors"
                        >
                          {question}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {messages.map((message) => {
                const isUser = message.role === 'user';
                return (
                  <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed border ${
                        isUser
                          ? 'bg-emerald-600 text-white border-emerald-600 rounded-br-sm'
                          : 'bg-white text-slate-800 border-slate-200 rounded-bl-sm'
                      }`}
                    >
                      {message.pending ? (
                        <span className="flex items-center gap-2 text-slate-600">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Analyzing your stored data…
                        </span>
                      ) : message.error ? (
                        <span className="flex items-start gap-1.5 text-rose-700">
                          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                          <span>{message.error}</span>
                        </span>
                      ) : (
                        <>
                          <p className="whitespace-pre-wrap">{message.content}</p>
                          {!isUser && (
                            <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center gap-1.5 flex-wrap">
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-500">
                                {message.source === 'gemini' ? (
                                  <>
                                    <Sparkles className="w-3 h-3 text-emerald-600" /> AI interpretation
                                  </>
                                ) : (
                                  <>
                                    <Database className="w-3 h-3 text-slate-500" /> Calculated values
                                  </>
                                )}
                              </span>
                              {message.notice && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-700">
                                  <ShieldAlert className="w-3 h-3" /> {message.notice}
                                </span>
                              )}
                              <span className="text-[10px] text-slate-400 ml-auto">{timeLabel(message.createdAt)}</span>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Composer */}
            <div className="border-t border-slate-200/80 bg-white px-3 py-2.5 space-y-1.5">
              {error && (
                <p className="text-[10px] text-rose-700 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> {error}
                </p>
              )}
              <form onSubmit={onSubmit} className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={onKeyDown}
                  rows={1}
                  data-testid="ai-chat-input"
                  placeholder="Ask about your climate data…"
                  aria-label="Message the ClimaCred AI Assistant"
                  className="flex-1 resize-none max-h-28 px-3 py-2 rounded-xl border border-slate-300 bg-white text-xs text-slate-900 focus:border-emerald-600 focus:outline-hidden"
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  data-testid="ai-chat-send"
                  className="p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  aria-label="Send message"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </form>
              <p className="text-[10px] text-slate-500">
                Answers use your stored ClimaCred data. Estimates are not guarantees.
              </p>
            </div>
          </section>
        </div>
      )}
    </>
  );
};
