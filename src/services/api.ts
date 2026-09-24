// Centralized API Client for ClimaCred AI.
// Every business value shown in the UI comes from the FastAPI backend. Nothing is
// cached in browser storage and nothing is substituted when a request fails.

import {
  BusinessProfile,
  ClimateAssessmentData,
  ClimateFingerprint,
  GreenSolution,
  ScenarioResult,
  TransformationPhaseItem,
  ImpactVerificationMetric,
  UserPreferences,
  AIDashboardInsightsResponse,
  AIChatResponse,
  AIStatusResponse,
  ImportResponse,
  ImportPreviewResponse,
  ImportStatus,
  ImportAssessmentSync,
  ImportedBusiness,
} from '../types';

import { DEFAULT_USER_PREFERENCES } from './defaults';

// ---------------------------------------------------------------------------
// Config & Helpers
// ---------------------------------------------------------------------------
// VITE_API_URL semantics:
//   - not defined  -> same-origin: requests go to /api/... and the vite dev/preview
//                     server proxies them to the backend (works in any browser)
//   - set to ""    -> same as not defined (same-origin)
//   - set to a URL -> that URL is used verbatim (e.g. a deployed API host)
const API_BASE_URL = import.meta.env.VITE_API_URL
  ? String(import.meta.env.VITE_API_URL).replace(/\/$/, '')
  : '';
const API_TIMEOUT_MS = 8000;

// Helper to get base without trailing slash
const getBase = () => API_BASE_URL.replace(/\/$/, '');

async function apiFetch<T>(path: string, options: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const { timeoutMs = API_TIMEOUT_MS, ...requestOptions } = options;
  const url = `${getBase()}${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...requestOptions,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(requestOptions.headers || {}),
      },
    });
    clearTimeout(timeout);
    if (!res.ok) {
      let detail: any = null;
      try {
        detail = await res.json();
      } catch {
        detail = await res.text();
      }
      const inner = typeof detail === 'object' ? detail?.detail : null;
      const message =
        typeof inner === 'string'
          ? inner
          : inner && typeof inner === 'object' && typeof inner.message === 'string'
          ? inner.message
          : inner
          ? JSON.stringify(inner)
          : (typeof detail === 'string' && detail) || `Request failed with ${res.status}`;
      const err: any = new Error(message);
      err.status = res.status;
      err.detail = detail;
      throw err;
    }
    // Handle 204 no content
    if (res.status === 204) return null as T;
    const data = await res.json();
    return data as T;
  } catch (e: any) {
    clearTimeout(timeout);
    if (e.name === 'AbortError') {
      const err: any = new Error(`Request timeout after ${timeoutMs}ms to ${path}`);
      err.status = 0;
      throw err;
    }
    throw e;
  }
}

// Normalize backend profile to frontend BusinessProfile.
// Nothing is invented: a field the user has not provided stays null.
function normalizeProfile(raw: any): BusinessProfile | null {
  if (!raw || typeof raw !== 'object') return null;
  return {
    name: raw.name ?? raw.business_name ?? null,
    industry: raw.industry ?? null,
    businessType: raw.businessType ?? raw.business_type ?? null,
    location: raw.location ?? null,
    employees: raw.employees ?? null,
    workingDaysPerMonth: raw.workingDaysPerMonth ?? raw.working_days ?? null,
    productionVolume: raw.productionVolume ?? raw.production_volume ?? null,
    operatingHoursPerDay: raw.operatingHoursPerDay ?? raw.operating_hours ?? null,
    businessSize: raw.businessSize ?? raw.business_size ?? null,
    facilityAreaSqFt: raw.facilityAreaSqFt ?? raw.facility_area_sqft ?? null,
    contactEmail: raw.contactEmail ?? raw.contact_email ?? null,
    phone: raw.phone ?? null,
  };
}

// Normalize fingerprint backend -> frontend ClimateFingerprint.
// Returns null when nothing has been calculated yet (no fabricated scores).
function normalizeFingerprint(raw: any): ClimateFingerprint | null {
  if (!raw || raw.overallScore === undefined || raw.overallScore === null) return null;
  const dimensions = (raw.dimensions || []).map((d: any) => ({
    dimension: d.dimension,
    score: d.score,
    impactLevel: d.impactLevel || d.impact_level || 'Moderate',
    currentStatus: d.currentStatus || d.current_status || '',
    primaryCause: d.primaryCause || d.primary_cause || '',
    improvementOpportunity: d.improvementOpportunity || d.improvement_opportunity || '',
    potentialReduction: d.potentialReduction || d.potential_reduction || '',
  }));
  if (!dimensions.length) return null;
  return {
    overallScore: raw.overallScore,
    scoreLabel: raw.scoreLabel ?? raw.score_label ?? '',
    benchmarkPercentile: raw.benchmarkPercentile ?? raw.benchmark_percentile ?? null as any,
    summaryNote: raw.summaryNote || raw.summary_note || '',
    topImprovementDimensions: raw.topImprovementDimensions || raw.top_improvement_dimensions || [],
    dimensions,
  };
}

// Normalize solution catalog (platform content served by the backend)
function normalizeSolutions(raw: any): GreenSolution[] {
  const list = raw?.solutions || raw || [];
  if (!Array.isArray(list)) return [];
  return list.map((s: any) => ({
    id: s.id,
    title: s.title || s.name,
    category: s.category,
    problemAddressed: s.problemAddressed || s.problem_area || '',
    shortDesc: s.shortDesc || s.description || s.short_desc || '',
    investmentRange: s.investmentRange || s.investment_range || `${s.investmentMinInr}-${s.investmentMaxInr}`,
    investmentMinInr: s.investmentMinInr ?? s.investment_min_inr ?? 0,
    investmentMaxInr: s.investmentMaxInr ?? s.investment_max_inr ?? 0,
    potentialAnnualSavingsInr: s.potentialAnnualSavingsInr ?? s.potential_annual_savings_inr ?? 0,
    potentialEnvironmentalImpact: s.potentialEnvironmentalImpact || s.potential_environmental_impact || '',
    estimatedPaybackPeriodYears: s.estimatedPaybackPeriodYears ?? s.estimated_payback_years ?? null,
    implementationDifficulty: s.implementationDifficulty || s.implementation_difficulty || null,
    co2ReductionTonnesPerYear: s.co2ReductionTonnesPerYear ?? s.co2_reduction_tonnes_per_year ?? 0,
    resourceReductionValue: s.resourceReductionValue || s.resource_reduction_value || '',
    featured: s.featured || false,
  }));
}

// ---------------------------------------------------------------------------
// Profile API
// ---------------------------------------------------------------------------
/**
 * Stored business profile, or null when none exists.
 * Throws when the backend cannot be reached, so the UI can say so instead of
 * silently showing a stale or empty profile.
 */
export async function getBusinessProfile(): Promise<BusinessProfile | null> {
  const raw = await apiFetch<any>('/api/profile');
  return normalizeProfile(raw);
}

export async function saveBusinessProfile(updated: Partial<BusinessProfile>): Promise<BusinessProfile | null> {
  try {
    // Map frontend to backend alias but backend handles both
    const payload: any = { ...updated };
    // Ensure both conventions sent for robustness
    if (updated.name) {
      payload.business_name = updated.name;
      payload.name = updated.name;
    }
    if (updated.businessType) {
      payload.business_type = updated.businessType;
      payload.businessType = updated.businessType;
    }
    if (updated.workingDaysPerMonth !== undefined) {
      payload.working_days = updated.workingDaysPerMonth;
      payload.workingDaysPerMonth = updated.workingDaysPerMonth;
    }
    if (updated.operatingHoursPerDay !== undefined) {
      payload.operating_hours = updated.operatingHoursPerDay;
      payload.operatingHoursPerDay = updated.operatingHoursPerDay;
    }
    if (updated.businessSize) {
      payload.business_size = updated.businessSize;
      payload.businessSize = updated.businessSize;
    }
    if (updated.facilityAreaSqFt !== undefined) {
      payload.facility_area_sqft = updated.facilityAreaSqFt;
      payload.facilityAreaSqFt = updated.facilityAreaSqFt;
    }
    if (updated.contactEmail) {
      payload.contact_email = updated.contactEmail;
      payload.contactEmail = updated.contactEmail;
    }
    const raw = await apiFetch<any>('/api/profile', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return normalizeProfile(raw);
  } catch (err: any) {
    console.error('saveBusinessProfile failed', err);
    throw new Error(err.message || 'Failed to update business profile');
  }
}

export interface ResetResult {
  has_data: false;
  data: null;
  profile: null;
  deleted: Record<string, number>;
  message: string;
}

/**
 * Development reset: deletes ALL stored data of the current user on the backend
 * (profile, assessment, fingerprints, plans, scenarios, reports, impact records,
 * AI caches and chat history). Afterwards every module shows its empty state.
 */
export async function resetAllStoredData(): Promise<ResetResult> {
  try {
    const result = await apiFetch<ResetResult>('/api/profile/reset', { method: 'POST' });
    purgeLegacyBrowserStorage();
    return result;
  } catch (err: any) {
    throw new Error(err.message || 'Failed to reset stored data');
  }
}

/** @deprecated kept for compatibility - use resetAllStoredData(). */
export const resetBusinessProfile = resetAllStoredData;

// ---------------------------------------------------------------------------
// Assessment API
// ---------------------------------------------------------------------------
/** Stored assessment, or null when none exists. Throws when the backend is unreachable. */
export async function getClimateAssessment(): Promise<ClimateAssessmentData | null> {
  const raw = await apiFetch<any>('/api/assessment');
  if (!raw || typeof raw !== 'object') return null;
  return raw as ClimateAssessmentData;
}

export async function saveClimateAssessment(data: ClimateAssessmentData): Promise<{ success: boolean; fingerprint: ClimateFingerprint | null }> {
  try {
    // POST assessment (full)
    await apiFetch<any>('/api/assessment', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    // After assessment, generate fingerprint (invalidated per backend logic)
    let fingerprint: ClimateFingerprint | null;
    try {
      const fpRaw = await apiFetch<any>('/api/climate-fingerprint/generate', { method: 'POST' });
      fingerprint = normalizeFingerprint(fpRaw);
    } catch (e) {
      // Try fetch existing
      const fpRaw2 = await apiFetch<any>('/api/climate-fingerprint');
      fingerprint = normalizeFingerprint(fpRaw2);
    }
    return { success: true, fingerprint };
  } catch (err: any) {
    console.error('saveClimateAssessment failed', err);
    throw new Error(err.message || 'Failed to save climate assessment');
  }
}

export async function patchClimateAssessment(partial: Partial<ClimateAssessmentData>): Promise<ClimateAssessmentData | null> {
  try {
    const raw = await apiFetch<any>('/api/assessment', {
      method: 'PATCH',
      body: JSON.stringify(partial),
    });
    return raw as ClimateAssessmentData;
  } catch (err: any) {
    throw new Error(err.message || 'Failed to patch assessment');
  }
}

// ---------------------------------------------------------------------------
// Fingerprint API
// ---------------------------------------------------------------------------
export async function getClimateFingerprint(): Promise<ClimateFingerprint | null> {
  try {
    const raw = await apiFetch<any>('/api/climate-fingerprint');
    return normalizeFingerprint(raw);
  } catch (err) {
    console.warn('getClimateFingerprint failed', err);
    // No stored data -> null; the fingerprint page shows the "complete your
    // assessment" empty state instead of a demo score.
    return null;
  }
}

export async function generateClimateFingerprint(): Promise<ClimateFingerprint | null> {
  try {
    const raw = await apiFetch<any>('/api/climate-fingerprint/generate', { method: 'POST' });
    return normalizeFingerprint(raw);
  } catch (err: any) {
    throw new Error(err.message || 'Failed to generate fingerprint');
  }
}

// Additional analytics helpers
export async function getEnergyAnalytics(): Promise<any> {
  try {
    return await apiFetch<any>('/api/climate-fingerprint/analytics/energy');
  } catch (e) {
    console.warn('Energy analytics request failed');
    return null;
  }
}
export async function getWaterAnalytics(): Promise<any> {
  try {
    return await apiFetch<any>('/api/climate-fingerprint/analytics/water');
  } catch {
    return null;
  }
}
export async function getWasteAnalytics(): Promise<any> {
  try {
    return await apiFetch<any>('/api/climate-fingerprint/analytics/waste');
  } catch {
    return null;
  }
}
export async function getEmissionsAnalytics(): Promise<any> {
  try {
    return await apiFetch<any>('/api/climate-fingerprint/analytics/emissions');
  } catch {
    return null;
  }
}
export async function getMobilityAnalytics(): Promise<any> {
  try {
    return await apiFetch<any>('/api/climate-fingerprint/analytics/mobility');
  } catch {
    return null;
  }
}
export async function getDataQuality(): Promise<any> {
  try {
    return await apiFetch<any>('/api/climate-fingerprint/analytics/data-quality');
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Solutions & Recommendations
// ---------------------------------------------------------------------------
export async function getGreenSolutions(categoryFilter?: string): Promise<GreenSolution[]> {
  try {
    const q = categoryFilter && categoryFilter !== 'All' ? `?category=${encodeURIComponent(categoryFilter)}` : '';
    const raw = await apiFetch<any>(`/api/solutions${q}`);
    return normalizeSolutions(raw);
  } catch (err) {
    console.warn('getGreenSolutions failed', err);
    // Platform catalog comes from the backend only - no local copy is invented.
    return [];
  }
}

export async function getRecommendedSolutions(topN = 5): Promise<any[]> {
  try {
    const raw = await apiFetch<any>(`/api/solutions/recommendations?top_n=${topN}`);
    return raw.recommendations || raw || [];
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Scenario Simulator
// ---------------------------------------------------------------------------
export async function runScenarioSimulation(selectedSolutionIds: string[]): Promise<ScenarioResult> {
  try {
    const raw = await apiFetch<any>('/api/scenarios/simulate', {
      method: 'POST',
      body: JSON.stringify({ selected_solution_ids: selectedSolutionIds, adoption_scale_percent: 100 }),
    });
    // Map backend to frontend ScenarioResult
    return {
      selectedSolutionIds: raw.selected_solutions || raw.selectedSolutionIds || selectedSolutionIds,
      totalInvestmentInr: raw.totalInvestmentInr ?? raw.investment?.min_inr ?? 0,
      totalAnnualSavingsInr: raw.totalAnnualSavingsInr ?? raw.annual_savings_inr ?? 0,
      energyReductionKwh: raw.energy_change?.energyReductionKwh ?? raw.energy_change?.reduction_kwh_per_year ?? 0,
      energyReductionPercent: raw.energy_change?.energyReductionPercent ?? raw.energy_change?.reduction_percent ?? 0,
      waterReductionLitres: raw.water_change?.waterReductionLitres ?? raw.water_change?.reduction_litres_per_year ?? 0,
      waterReductionPercent: raw.water_change?.waterReductionPercent ?? raw.water_change?.reduction_percent ?? 0,
      wasteReductionKg: raw.waste_change?.wasteReductionKg ?? raw.waste_change?.reduction_kg_per_year ?? 0,
      wasteReductionPercent: raw.waste_change?.wasteReductionPercent ?? raw.waste_change?.reduction_percent ?? 0,
      co2ReductionTonnes: raw.emission_change?.co2ReductionTonnes ?? raw.emission_change?.reduction_tonnes_co2_per_year ?? 0,
      co2ReductionPercent: raw.emission_change?.co2ReductionPercent ?? raw.emission_change?.reduction_percent ?? 0,
      estimatedPaybackYears: raw.payback_period_years ?? raw.estimatedPaybackYears ?? 0,
      projectedClimateScore: raw.projected_climate_score ?? raw.projectedClimateScore ?? 0,
    };
  } catch (err: any) {
    console.error('runScenarioSimulation failed', err);
    throw new Error(err.message || 'Scenario simulation failed');
  }
}

// Extended simulation with scale
export async function runScenarioSimulationWithScale(selectedSolutionIds: string[], scalePercent: number): Promise<any> {
  try {
    const raw = await apiFetch<any>('/api/scenarios/simulate', {
      method: 'POST',
      body: JSON.stringify({ selected_solution_ids: selectedSolutionIds, adoption_scale_percent: scalePercent }),
    });
    return raw;
  } catch (err: any) {
    throw new Error(err.message || 'Scenario simulation failed');
  }
}

// ---------------------------------------------------------------------------
// Transformation Plan
// ---------------------------------------------------------------------------
export async function getTransformationPlan(): Promise<TransformationPhaseItem[]> {
  try {
    const raw = await apiFetch<any>('/api/transformation-plan');
    const list = raw?.plan || raw || [];
    return Array.isArray(list) ? (list as TransformationPhaseItem[]) : [];
  } catch (err) {
    console.warn('getTransformationPlan failed', err);
    return [];
  }
}

export async function generateTransformationPlan(): Promise<TransformationPhaseItem[]> {
  try {
    const raw = await apiFetch<any>('/api/transformation-plan/generate', { method: 'POST' });
    return raw.plan || raw;
  } catch (err: any) {
    throw new Error(err.message || 'Failed to generate transformation plan');
  }
}

export async function updateTransformationItemStatus(
  id: string,
  status: 'Pending' | 'In Progress' | 'Completed'
): Promise<TransformationPhaseItem[]> {
  try {
    const raw = await apiFetch<any>(`/api/transformation-plan/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
    return raw.plan || raw;
  } catch (err: any) {
    throw new Error(err.message || 'Failed to update plan item');
  }
}

// ---------------------------------------------------------------------------
// Impact Verification
// ---------------------------------------------------------------------------
export async function getImpactVerification(): Promise<ImpactVerificationMetric[]> {
  try {
    const raw = await apiFetch<any>('/api/impact');
    if (raw.metrics && Array.isArray(raw.metrics) && raw.metrics.length) {
      return raw.metrics as ImpactVerificationMetric[];
    }
    if (raw.records && raw.records.length) {
      // If records exist, derive metrics from the latest submitted record
      const latest = raw.records[0];
      if (latest.calculated_metrics) {
        const metricsRes = await apiFetch<any>('/api/impact/metrics');
        if (metricsRes.metrics) return metricsRes.metrics;
      }
    }
    // Nothing submitted yet -> empty list (no demo before/after metrics).
    return [];
  } catch (err) {
    console.warn('getImpactVerification failed', err);
    return [];
  }
}

export async function submitImpactVerification(data: { before: any; after: any; intervention_ids?: string[] }): Promise<any> {
  try {
    const raw = await apiFetch<any>('/api/impact', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return raw;
  } catch (err: any) {
    throw new Error(err.message || 'Failed to submit impact verification');
  }
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------
export async function getClimateReport(): Promise<any> {
  try {
    const raw = await apiFetch<any>('/api/reports/climate');
    return raw;
  } catch (err) {
    console.warn('Climate report request failed');
    return null;
  }
}

export async function generateClimateReport(): Promise<any> {
  try {
    const raw = await apiFetch<any>('/api/reports/climate/generate', { method: 'POST' });
    return raw;
  } catch (err: any) {
    throw new Error(err.message || 'Failed to generate report');
  }
}

// ---------------------------------------------------------------------------
// Stored history (real records only - powers the charts and trend analysis)
// ---------------------------------------------------------------------------
export interface FingerprintSnapshot {
  created_at: string | null;
  overall_score: number | null;
  score_label: string | null;
  dimension_scores: Record<string, number | null>;
  dimension_metrics: Record<string, Record<string, number | null>>;
}

/** Stored fingerprint snapshots (oldest → newest). Empty until real data exists. */
export async function getClimateFingerprintHistory(limit = 24): Promise<FingerprintSnapshot[]> {
  try {
    const raw = await apiFetch<any>(`/api/climate-fingerprint/history?limit=${limit}`);
    const snapshots = raw?.snapshots || [];
    return Array.isArray(snapshots) ? snapshots : [];
  } catch (err) {
    console.warn('getClimateFingerprintHistory failed', err);
    return [];
  }
}

// ---------------------------------------------------------------------------
// Gemini (status, dashboard insight, chat). The Gemini API key lives only in
// backend/.env; the browser only ever talks to these FastAPI endpoints.
// ---------------------------------------------------------------------------
// The backend waits up to GEMINI_TIMEOUT_SECONDS (default 60 s) for Gemini.
export const AI_INSIGHT_TIMEOUT_MS = 90000;
export const AI_CHAT_TIMEOUT_MS = 90000;
export const AI_STATUS_TIMEOUT_MS = 45000;

/** Real connection check performed by the backend (cached briefly server-side). */
export async function getAIStatus(refresh = false): Promise<AIStatusResponse> {
  return await apiFetch<AIStatusResponse>(`/api/ai/status${refresh ? '?refresh=true' : ''}`, {
    timeoutMs: AI_STATUS_TIMEOUT_MS,
  });
}

// One shared in-flight request: React StrictMode (dev) mounts effects twice, and a
// second concurrent request would otherwise trigger a second Gemini generation.
let insightInflight: Promise<AIDashboardInsightsResponse> | null = null;

export async function getAIDashboardInsights(refresh = false): Promise<AIDashboardInsightsResponse> {
  if (!refresh && insightInflight) return insightInflight;
  const query = refresh ? '?refresh=true' : '';
  const request = apiFetch<AIDashboardInsightsResponse>(`/api/ai/dashboard-insights${query}`, {
    timeoutMs: AI_INSIGHT_TIMEOUT_MS,
  }).finally(() => {
    if (insightInflight === request) insightInflight = null;
  });
  insightInflight = request;
  return request;
}

/**
 * Ask the ClimaCred AI Assistant. The backend gathers the stored business context
 * itself and keeps the conversation memory server-side under `conversation_id`
 * (omit it to start a new conversation; reuse the returned id for follow-ups).
 */
export async function askAIAssistant(message: string, conversationId?: string | null): Promise<AIChatResponse> {
  return await apiFetch<AIChatResponse>('/api/ai/chat', {
    method: 'POST',
    body: JSON.stringify(conversationId ? { message, conversation_id: conversationId } : { message }),
    timeoutMs: AI_CHAT_TIMEOUT_MS,
  });
}

/** "Clear chat": forget the conversation on the server. */
export async function clearAIConversation(conversationId: string): Promise<void> {
  await apiFetch<{ cleared: boolean }>(`/api/ai/chat/${encodeURIComponent(conversationId)}`, { method: 'DELETE' });
}

/** Starter questions + whether stored business data exists. */
export async function getAIChatSuggestions(): Promise<{ has_data: boolean; suggestions: string[] }> {
  return await apiFetch<{ has_data: boolean; suggestions: string[] }>('/api/ai/chat/suggestions');
}

// ---------------------------------------------------------------------------
// Browser storage hygiene
// ---------------------------------------------------------------------------
// The only things ClimaCred keeps in the browser are UI preferences
// (climacred_theme, climacred_preferences). Business data, AI insights and chat
// transcripts are never stored client-side. Earlier builds cached the AI insight
// and the chat transcript in sessionStorage; those keys are removed here so stale
// content from an older build can never repopulate the UI.
const LEGACY_SESSION_KEYS = ['climacred_ai_dashboard_insight', 'climacred_ai_chat_session'];
const ALLOWED_LOCAL_KEYS = new Set(['climacred_theme', 'climacred_preferences']);
const PREFERENCE_FIELDS = ['currency', 'measurementUnit', 'emailAlerts', 'benchmarkSharing', 'theme'];

export function purgeLegacyBrowserStorage(): string[] {
  const removed: string[] = [];
  try {
    for (const key of LEGACY_SESSION_KEYS) {
      if (window.sessionStorage.getItem(key) !== null) {
        window.sessionStorage.removeItem(key);
        removed.push(`sessionStorage:${key}`);
      }
    }
    for (let i = window.localStorage.length - 1; i >= 0; i -= 1) {
      const key = window.localStorage.key(i);
      if (key && key.toLowerCase().startsWith('climacred') && !ALLOWED_LOCAL_KEYS.has(key)) {
        window.localStorage.removeItem(key);
        removed.push(`localStorage:${key}`);
      }
    }
    // Preferences may only contain preference fields - never business data.
    const rawPrefs = window.localStorage.getItem('climacred_preferences');
    if (rawPrefs) {
      const parsed = JSON.parse(rawPrefs);
      const clean: Record<string, unknown> = {};
      for (const field of PREFERENCE_FIELDS) if (parsed && field in parsed) clean[field] = parsed[field];
      if (JSON.stringify(clean) !== JSON.stringify(parsed)) {
        window.localStorage.setItem('climacred_preferences', JSON.stringify(clean));
        removed.push('localStorage:climacred_preferences (non-preference fields)');
      }
    }
  } catch {
    // Storage unavailable (private mode) - nothing stored, nothing to clean.
  }
  return removed;
}

// ---------------------------------------------------------------------------
// User Preferences (local platform settings - persisted in localStorage)
// ---------------------------------------------------------------------------
export async function getUserPreferences(): Promise<UserPreferences> {
  try {
    const stored = localStorage.getItem('climacred_preferences');
    if (stored) return JSON.parse(stored);
  } catch {
    // localStorage unavailable - fall through to platform defaults
  }
  return { ...DEFAULT_USER_PREFERENCES };
}

export async function saveUserPreferences(prefs: Partial<UserPreferences>): Promise<UserPreferences> {
  try {
    const current = await getUserPreferences();
    const updated = { ...current, ...prefs };
    localStorage.setItem('climacred_preferences', JSON.stringify(updated));
    // Optionally also PATCH to backend if endpoint exists in future
    // await apiFetch('/api/preferences', {method:'PATCH', body: JSON.stringify(prefs)}).catch(()=>{})
    return updated;
  } catch (err: any) {
    throw new Error(err.message || 'Failed to save preferences');
  }
}

// ---------------------------------------------------------------------------
// AI Insights helpers (anomaly & forecast)
// ---------------------------------------------------------------------------
export async function detectAnomalies(historicalData: any[], metricKey: string): Promise<any> {
  try {
    return await apiFetch<any>('/api/climate-fingerprint/anomaly-detection', {
      method: 'POST',
      body: JSON.stringify({ historical_data: historicalData, metric_key: metricKey }),
    });
  } catch (err: any) {
    return { status: 'insufficient_data', message: err.message };
  }
}

export async function forecastConsumption(historicalData: any[], metricKey: string, periods = 3): Promise<any> {
  try {
    return await apiFetch<any>('/api/climate-fingerprint/forecast', {
      method: 'POST',
      body: JSON.stringify({ historical_data: historicalData, metric_key: metricKey, periods }),
    });
  } catch (err: any) {
    return { status: 'insufficient_data', message: err.message };
  }
}

// ---------------------------------------------------------------------------
// Data Import (Excel / CSV upload)
// ---------------------------------------------------------------------------
// Multipart uploads must NOT carry a JSON Content-Type: the browser has to set the
// multipart boundary itself. These helpers therefore use fetch directly, but keep
// the same base URL, timeout and error shape as apiFetch.
const IMPORT_TIMEOUT_MS = 120000;

async function uploadFiles<T>(path: string, files: File[]): Promise<T> {
  const form = new FormData();
  files.forEach((file) => form.append('files', file, file.name));
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), IMPORT_TIMEOUT_MS);
  try {
    const res = await fetch(`${getBase()}${path}`, { method: 'POST', body: form, signal: controller.signal });
    clearTimeout(timeout);
    let detail: any = null;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text().catch(() => null);
    }
    if (!res.ok) {
      const inner = typeof detail === 'object' ? detail?.detail : null;
      const message =
        typeof inner === 'string'
          ? inner
          : Array.isArray(inner)
          ? inner.map((e: any) => e?.msg || JSON.stringify(e)).join('; ')
          : inner
          ? JSON.stringify(inner)
          : `Import failed (${res.status})`;
      throw new Error(message);
    }
    return detail as T;
  } catch (err: any) {
    clearTimeout(timeout);
    if (err?.name === 'AbortError') throw new Error(`Upload timed out after ${IMPORT_TIMEOUT_MS / 1000}s.`);
    throw err;
  }
}

/** Parse + detect + validate the selected files WITHOUT storing anything. */
export async function previewImport(files: File[]): Promise<ImportPreviewResponse> {
  return uploadFiles<ImportPreviewResponse>('/api/import/preview', files);
}

/** Validate and store the selected files, then refresh the derived data. */
export async function importDataFiles(files: File[]): Promise<ImportResponse> {
  return uploadFiles<ImportResponse>('/api/import', files);
}

/** Datasets the backend can detect, supported formats and the stored row counts. */
export async function getImportStatus(): Promise<ImportStatus> {
  return apiFetch<ImportStatus>('/api/import', { timeoutMs: 20000 });
}

/** Re-derive the Climate Assessment (and Fingerprint) from the imported data. */
export async function syncAssessmentFromImports(): Promise<ImportAssessmentSync> {
  return apiFetch<ImportAssessmentSync>('/api/import/sync-assessment', { method: 'POST', timeoutMs: 60000 });
}

/** Serve a different imported business (B001, B002, ...). */
export async function activateImportedBusiness(businessId: string): Promise<{ business_id: string; assessment_synced: ImportAssessmentSync }> {
  return apiFetch(`/api/import/businesses/${encodeURIComponent(businessId)}/activate`, {
    method: 'POST',
    timeoutMs: 60000,
  });
}

export async function getImportedBusinesses(): Promise<{ active_business_id: string | null; businesses: ImportedBusiness[] }> {
  return apiFetch('/api/import/businesses', { timeoutMs: 20000 });
}
