// Centralized API Client for ClimaCred AI (Phase 2 - Full Stack)
// Connects Phase 1 frontend to FastAPI backend with fallback handling, validation, and error transparency.

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

let cachedProfile: BusinessProfile | null = null;
let cachedAssessment: ClimateAssessmentData | null = null;

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
      const message =
        typeof detail === 'object' && detail?.detail
          ? typeof detail.detail === 'string'
            ? detail.detail
            : JSON.stringify(detail.detail)
          : detail || `Request failed with ${res.status}`;
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
    estimatedPaybackPeriodYears: s.estimatedPaybackPeriodYears ?? s.estimated_payback_years ?? 3,
    implementationDifficulty: s.implementationDifficulty || s.implementation_difficulty || 'Medium',
    co2ReductionTonnesPerYear: s.co2ReductionTonnesPerYear ?? s.co2_reduction_tonnes_per_year ?? 0,
    resourceReductionValue: s.resourceReductionValue || s.resource_reduction_value || '',
    featured: s.featured || false,
  }));
}

// ---------------------------------------------------------------------------
// Profile API
// ---------------------------------------------------------------------------
export async function getBusinessProfile(): Promise<BusinessProfile | null> {
  try {
    const raw = await apiFetch<any>('/api/profile');
    const normalized = normalizeProfile(raw);
    cachedProfile = normalized;
    return normalized ? { ...normalized } : null;
  } catch (err) {
    console.warn('getBusinessProfile failed', err);
    // Never fabricate a business profile: return null (or the last known real one).
    return cachedProfile ? { ...cachedProfile } : null;
  }
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
    const normalized = normalizeProfile(raw);
    cachedProfile = normalized;
    return normalized ? { ...normalized } : null;
  } catch (err: any) {
    console.error('saveBusinessProfile failed', err);
    throw new Error(err.message || 'Failed to update business profile');
  }
}

export async function resetBusinessProfile(): Promise<BusinessProfile | null> {
  try {
    const raw = await apiFetch<any>('/api/profile/reset', { method: 'POST' });
    const normalized = normalizeProfile(raw);
    cachedProfile = normalized;
    return normalized ? { ...normalized } : null;
  } catch (err: any) {
    throw new Error(err.message || 'Failed to reset profile');
  }
}

// ---------------------------------------------------------------------------
// Assessment API
// ---------------------------------------------------------------------------
export async function getClimateAssessment(): Promise<ClimateAssessmentData | null> {
  try {
    const raw = await apiFetch<any>('/api/assessment');
    if (!raw || typeof raw !== 'object') return null;
    cachedAssessment = JSON.parse(JSON.stringify(raw));
    return JSON.parse(JSON.stringify(raw));
  } catch (err) {
    console.warn('getClimateAssessment failed', err);
    // No stored assessment -> null (the UI shows an empty state, never demo values).
    return cachedAssessment ? JSON.parse(JSON.stringify(cachedAssessment)) : null;
  }
}

export async function saveClimateAssessment(data: ClimateAssessmentData): Promise<{ success: boolean; fingerprint: ClimateFingerprint | null }> {
  try {
    // POST assessment (full)
    await apiFetch<any>('/api/assessment', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    cachedAssessment = JSON.parse(JSON.stringify(data));
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
    cachedAssessment = JSON.parse(JSON.stringify(raw));
    return JSON.parse(JSON.stringify(raw));
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
    console.warn('Energy analytics fallback');
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
    console.warn('getClimateReport fallback');
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
// Gemini AI dashboard intelligence + chat (Phase 3)
// The Gemini API key lives only in the backend environment; the browser never
// sees it. The backend returns a calculated answer when Gemini is unavailable.
// ---------------------------------------------------------------------------
export const AI_INSIGHT_TIMEOUT_MS = 30000;
export const AI_CHAT_TIMEOUT_MS = 30000;

export async function getAIDashboardInsights(refresh = false): Promise<AIDashboardInsightsResponse> {
  const query = refresh ? '?refresh=true' : '';
  return await apiFetch<AIDashboardInsightsResponse>(`/api/ai/dashboard-insights${query}`, {
    timeoutMs: AI_INSIGHT_TIMEOUT_MS,
  });
}

/**
 * Ask the ClimaCred AI Assistant a question about the user's own stored data.
 * The backend collects the context automatically; the browser only sends the
 * question plus the current session's turns (so follow-ups resolve correctly).
 */
export async function askAIAssistant(
  message: string,
  history: { role: 'user' | 'assistant'; content: string }[] = []
): Promise<AIChatResponse> {
  return await apiFetch<AIChatResponse>('/api/ai/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
    timeoutMs: AI_CHAT_TIMEOUT_MS,
  });
}

/** Suggested starter questions (data-aware, generated by the backend). */
export async function getAIChatSuggestions(): Promise<{ has_data: boolean; suggestions: string[] }> {
  try {
    return await apiFetch<{ has_data: boolean; suggestions: string[] }>('/api/ai/chat/suggestions');
  } catch {
    return { has_data: false, suggestions: [] };
  }
}

/** Is the Gemini layer configured on the backend? (no key is ever returned) */
export async function getAIStatus(): Promise<{ gemini_configured: boolean; model: string } | null> {
  try {
    return await apiFetch<{ gemini_configured: boolean; model: string }>('/api/ai/status');
  } catch {
    return null;
  }
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
