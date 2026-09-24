import React, { useEffect, useRef, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';
import { GeminiIndicatorState, useGeminiStatus } from '../../services/geminiStatus';

const LABELS: Record<GeminiIndicatorState, string> = {
  checking: 'Gemini Checking...',
  connected: 'Gemini Connected',
  not_connected: 'Gemini Not Connected',
  error: 'Gemini Error',
};

const STATUS_TEXT: Record<GeminiIndicatorState, string> = {
  checking: 'Checking...',
  connected: 'Connected',
  not_connected: 'Not Connected',
  error: 'Error',
};

const DOT_CLASS: Record<GeminiIndicatorState, string> = {
  checking: 'bg-amber-400 animate-pulse',
  connected: 'bg-emerald-500',
  not_connected: 'bg-slate-400',
  error: 'bg-rose-500',
};

const PILL_CLASS: Record<GeminiIndicatorState, string> = {
  checking: 'border-amber-200 dark:border-amber-500/40',
  connected: 'border-emerald-200 dark:border-emerald-500/40',
  not_connected: 'border-slate-200 dark:border-slate-600',
  error: 'border-rose-200 dark:border-rose-500/40',
};

const formatTime = (iso?: string | null): string => {
  if (!iso) return '—';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

/**
 * Navbar Gemini indicator. Driven only by GET /api/ai/status - the backend reports
 * "connected" solely after a verified model answered a real generateContent call.
 */
export const GeminiStatusIndicator: React.FC = () => {
  const { status, requestError, indicator, refresh } = useGeminiStatus();
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const message = requestError
    ? `The ClimaCred backend could not be reached (${requestError}).`
    : status?.status === 'connected'
    ? null
    : status?.message || null;

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        data-testid="gemini-status"
        data-state={indicator}
        aria-haspopup="dialog"
        aria-expanded={open}
        title={LABELS[indicator]}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border bg-white text-slate-700 hover:bg-slate-50 text-xs font-semibold transition-colors ${PILL_CLASS[indicator]}`}
      >
        <span className={`w-2 h-2 rounded-full shrink-0 ${DOT_CLASS[indicator]}`} aria-hidden="true" />
        <span className="hidden sm:inline whitespace-nowrap">{LABELS[indicator]}</span>
        <span className="sm:hidden">Gemini</span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Gemini connection status"
          data-testid="gemini-status-popover"
          className="absolute right-0 mt-2 w-72 z-50 bg-white border border-slate-200 rounded-2xl shadow-xl p-4 space-y-3"
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${DOT_CLASS[indicator]}`} aria-hidden="true" />
              Gemini
            </p>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="p-1 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              aria-label="Close Gemini status"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <dl className="text-xs space-y-1.5">
            <div className="flex justify-between gap-3">
              <dt className="text-slate-600">Status:</dt>
              <dd className="font-semibold text-slate-900">{STATUS_TEXT[indicator]}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-600">Model:</dt>
              <dd className="font-mono text-[11px] text-slate-900 truncate" title={status?.model || ''}>
                {status?.model || status?.configured_model || '—'}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-600">Last checked:</dt>
              <dd className="text-slate-900">{formatTime(status?.checked_at)}</dd>
            </div>
          </dl>

          {message && (
            <p
              className={`text-[11px] leading-relaxed p-2.5 rounded-xl border ${
                indicator === 'error' ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}
              data-testid="gemini-status-message"
            >
              {message}
            </p>
          )}

          {status?.available_models && status.available_models.length > 0 && (
            <p className="text-[10px] text-slate-600 leading-relaxed">
              Models available to this key: <span className="font-mono">{status.available_models.slice(0, 6).join(', ')}</span>
            </p>
          )}

          <button
            type="button"
            onClick={() => void refresh(true)}
            disabled={indicator === 'checking'}
            data-testid="gemini-status-recheck"
            className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${indicator === 'checking' ? 'animate-spin' : ''}`} />
            Re-check now
          </button>
        </div>
      )}
    </div>
  );
};
