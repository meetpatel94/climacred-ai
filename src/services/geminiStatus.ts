// Shared Gemini connection status (single source: GET /api/ai/status).
//
// The navbar indicator and the chat assistant both read this store, so the
// backend is polled once, not per component. The backend performs the real check
// (verified model + live generateContent) and caches it briefly; this store never
// decides "connected" on its own.

import { useEffect, useState } from 'react';
import { AIStatusResponse } from '../types';
import { getAIStatus } from './api';

export interface GeminiStatusState {
  /** Last response of GET /api/ai/status (null until the first answer). */
  status: AIStatusResponse | null;
  /** True while a visible (non-background) check is running. */
  checking: boolean;
  /** Set when the ClimaCred backend itself could not be reached. */
  requestError: string | null;
}

export type GeminiIndicatorState = 'checking' | 'connected' | 'not_connected' | 'error';

const POLL_MS = 5 * 60 * 1000;

let state: GeminiStatusState = { status: null, checking: false, requestError: null };
const listeners = new Set<(next: GeminiStatusState) => void>();
let inflight: Promise<void> | null = null;
let pollTimer: number | null = null;

function emit(patch: Partial<GeminiStatusState>): void {
  state = { ...state, ...patch };
  listeners.forEach((listener) => listener(state));
}

/**
 * Ask the backend for the current status.
 * @param force  bypass the backend's short status cache (explicit "Re-check")
 * @param silent keep showing the previous state while checking (background polls)
 */
export function refreshGeminiStatus(force = false, silent = false): Promise<void> {
  if (inflight && !force) return inflight;
  if (!silent || !state.status) emit({ checking: true });
  const run: Promise<void> = getAIStatus(force)
    .then((status) => emit({ status, checking: false, requestError: null }))
    .catch((err: any) =>
      emit({
        status: null,
        checking: false,
        requestError: err?.message || 'The ClimaCred backend could not be reached.',
      })
    )
    .finally(() => {
      if (inflight === run) inflight = null;
    });
  inflight = run;
  return run;
}

/** Map the backend status to the four indicator states required by the UI. */
export function indicatorState(snapshot: GeminiStatusState): GeminiIndicatorState {
  if (snapshot.checking || (!snapshot.status && !snapshot.requestError)) return 'checking';
  if (!snapshot.status) return 'not_connected'; // backend unreachable -> Gemini cannot be reached either
  switch (snapshot.status.status) {
    case 'connected':
      return 'connected';
    case 'not_configured':
    case 'unreachable':
      return 'not_connected';
    default:
      return 'error';
  }
}

export function useGeminiStatus(): GeminiStatusState & {
  indicator: GeminiIndicatorState;
  refresh: (force?: boolean) => Promise<void>;
} {
  const [snapshot, setSnapshot] = useState<GeminiStatusState>(state);

  useEffect(() => {
    listeners.add(setSnapshot);
    setSnapshot(state);
    if (!state.status && !state.requestError && !inflight) void refreshGeminiStatus();
    if (pollTimer === null) {
      pollTimer = window.setInterval(() => void refreshGeminiStatus(false, true), POLL_MS);
    }
    return () => {
      listeners.delete(setSnapshot);
      if (listeners.size === 0 && pollTimer !== null) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    };
  }, []);

  return { ...snapshot, indicator: indicatorState(snapshot), refresh: (force = false) => refreshGeminiStatus(force) };
}
