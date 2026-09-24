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
} from '../types';

import {
  INITIAL_BUSINESS_PROFILE,
  INITIAL_ASSESSMENT_DATA,
  INITIAL_CLIMATE_FINGERPRINT,
  GREEN_SOLUTIONS_LIBRARY,
  INITIAL_TRANSFORMATION_PLAN,
  INITIAL_IMPACT_VERIFICATION,
  INITIAL_PREFERENCES,
} from './mockData';

// ---------------------------------------------------------------------------
// Config & Helpers
// ---------------------------------------------------------------------------
// VITE_API_URL semantics:
//   - not defined        -> dev default http://localhost:8000
//   - set to "" (empty)  -> same-origin: requests go to /api/... and are proxied
//                           by the vite dev/preview server to the backend
//   - set to a URL       -> that URL is used verbatim
const API_BASE_URL = import.meta.env.VITE_API_URL !== undefined
  ? import.meta.env.VITE_API_URL
  : 'http://localhost:8000';
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

// Normalize backend profile to frontend BusinessProfile
function normalizeProfile(raw: any): BusinessProfile {
  if (!raw) return { ...INITIAL_BUSINESS_PROFILE };
  return {
    name: raw.name || raw.business_name || INITIAL_BUSINESS_PROFILE.name,
    industry: raw.industry || INITIAL_BUSINESS_PROFILE.industry,
    businessType: raw.businessType || raw.business_type || INITIAL_BUSINESS_PROFILE.businessType,
    location: raw.location || INITIAL_BUSINESS_PROFILE.location,
    employees: typeof raw.employees === 'number' ? raw.employees : INITIAL_BUSINESS_PROFILE.employees,
    workingDaysPerMonth: raw.workingDaysPerMonth ?? raw.working_days ?? INITIAL_BUSINESS_PROFILE.workingDaysPerMonth,
    productionVolume: raw.productionVolume || raw.production_volume || INITIAL_BUSINESS_PROFILE.productionVolume,
    operatingHoursPerDay: raw.operatingHoursPerDay ?? raw.operating_hours ?? INITIAL_BUSINESS_PROFILE.operatingHoursPerDay,
    businessSize: raw.businessSize || raw.business_size || INITIAL_BUSINESS_PROFILE.businessSize,
    facilityAreaSqFt: raw.facilityAreaSqFt ?? raw.facility_area_sqft ?? INITIAL_BUSINESS_PROFILE.facilityAreaSqFt,
    contactEmail: raw.contactEmail || raw.contact_email || INITIAL_BUSINESS_PROFILE.contactEmail,
    phone: raw.phone || INITIAL_BUSINESS_PROFILE.phone,
  };
}

// Normalize fingerprint backend -> frontend ClimateFingerprint
function normalizeFingerprint(raw: any): ClimateFingerprint {
  if (!raw) return JSON.parse(JSON.stringify(INITIAL_CLIMATE_FINGERPRINT));
  const overallScore = raw.overallScore ?? raw.overall_score ?? raw.overallScore ?? 58;
  const scoreLabel = raw.scoreLabel ?? raw.score_label ?? 'Transition Stage';
  const dimensions = (raw.dimensions || []).map((d: any) => ({
    dimension: d.dimension,
    score: d.score,
    impactLevel: d.impactLevel || d.impact_level || 'Moderate',
    currentStatus: d.currentStatus || d.current_status || '',
    primaryCause: d.primaryCause || d.primary_cause || '',
    improvementOpportunity: d.improvementOpportunity || d.improvement_opportunity || '',
    potentialReduction: d.potentialReduction || d.potential_reduction || '',
  }));
  // Fallback to mock dimensions if empty
  const finalDims = dimensions.length ? dimensions : INITIAL_CLIMATE_FINGERPRINT.dimensions;
  return {
    overallScore,
    scoreLabel,
    benchmarkPercentile: raw.benchmarkPercentile ?? raw.benchmark_percentile ?? 46,
    summaryNote: raw.summaryNote || raw.summary_note || INITIAL_CLIMATE_FINGERPRINT.summaryNote,
    topImprovementDimensions: raw.topImprovementDimensions || raw.top_improvement_dimensions || INITIAL_CLIMATE_FINGERPRINT.topImprovementDimensions,
    dimensions: finalDims,
  };
}

// Normalize solution catalog
function normalizeSolutions(raw: any): GreenSolution[] {
  const list = raw?.solutions || raw || [];
  if (!Array.isArray(list) || list.length === 0) return [...GREEN_SOLUTIONS_LIBRARY];
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
export async function getBusinessProfile(): Promise<BusinessProfile> {
  try {
    const raw = await apiFetch<any>('/api/profile');
    const normalized = normalizeProfile(raw);
    cachedProfile = normalized;
    return { ...normalized };
  } catch (err) {
    console.warn('getBusinessProfile backend failed, using mock fallback', err);
    // If backend unavailable in dev, fallback to mock but indicate error via console
    // For production, throw to let UI show error
    if (cachedProfile) return { ...cachedProfile };
    // Try mock
    return { ...INITIAL_BUSINESS_PROFILE };
  }
}

export async function saveBusinessProfile(updated: Partial<BusinessProfile>): Promise<BusinessProfile> {
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
    return { ...normalized };
  } catch (err: any) {
    console.error('saveBusinessProfile failed', err);
    throw new Error(err.message || 'Failed to update business profile');
  }
}

export async function resetBusinessProfile(): Promise<BusinessProfile> {
  try {
    const raw = await apiFetch<any>('/api/profile/reset', { method: 'POST' });
    const normalized = normalizeProfile(raw);
    cachedProfile = normalized;
    return { ...normalized };
  } catch (err: any) {
    throw new Error(err.message || 'Failed to reset profile');
  }
}

// ---------------------------------------------------------------------------
// Assessment API
// ---------------------------------------------------------------------------
export async function getClimateAssessment(): Promise<ClimateAssessmentData> {
  try {
    const raw = await apiFetch<any>('/api/assessment');
    // Backend returns same shape as frontend
    // Ensure deep copy
    cachedAssessment = JSON.parse(JSON.stringify(raw));
    return JSON.parse(JSON.stringify(raw));
  } catch (err) {
    console.warn('getClimateAssessment fallback to mock', err);
    if (cachedAssessment) return JSON.parse(JSON.stringify(cachedAssessment));
    return JSON.parse(JSON.stringify(INITIAL_ASSESSMENT_DATA));
  }
}

export async function saveClimateAssessment(data: ClimateAssessmentData): Promise<{ success: boolean; fingerprint: ClimateFingerprint }> {
  try {
    // POST assessment (full)
    await apiFetch<any>('/api/assessment', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    cachedAssessment = JSON.parse(JSON.stringify(data));
    // After assessment, generate fingerprint (invalidated per backend logic)
    let fingerprint: ClimateFingerprint;
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

export async function patchClimateAssessment(partial: Partial<ClimateAssessmentData>): Promise<ClimateAssessmentData> {
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
export async function getClimateFingerprint(): Promise<ClimateFingerprint> {
  try {
    const raw = await apiFetch<any>('/api/climate-fingerprint');
    return normalizeFingerprint(raw);
  } catch (err) {
    console.warn('getClimateFingerprint fallback to mock', err);
    return JSON.parse(JSON.stringify(INITIAL_CLIMATE_FINGERPRINT));
  }
}

export async function generateClimateFingerprint(): Promise<ClimateFingerprint> {
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
    console.warn('getGreenSolutions fallback to mock', err);
    if (!categoryFilter || categoryFilter === 'All') {
      return [...GREEN_SOLUTIONS_LIBRARY];
    }
    return GREEN_SOLUTIONS_LIBRARY.filter((s) => s.category.toLowerCase() === categoryFilter.toLowerCase());
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
      projectedClimateScore: raw.projected_climate_score ?? raw.projectedClimateScore ?? 58,
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
    const list = raw.plan || raw || [];
    if (Array.isArray(list) && list.length) return list as TransformationPhaseItem[];
    return [...INITIAL_TRANSFORMATION_PLAN];
  } catch (err) {
    console.warn('getTransformationPlan fallback', err);
    return [...INITIAL_TRANSFORMATION_PLAN];
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
      // If records exist, derive metrics from latest
      const latest = raw.records[0];
      if (latest.calculated_metrics) {
        // Convert to frontend shape already handled by backend fallback in /metrics
        const metricsRes = await apiFetch<any>('/api/impact/metrics');
        if (metricsRes.metrics) return metricsRes.metrics;
      }
    }
    return [...INITIAL_IMPACT_VERIFICATION];
  } catch (err) {
    console.warn('getImpactVerification fallback', err);
    return [...INITIAL_IMPACT_VERIFICATION];
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
// Gemini AI dashboard intelligence (Phase 3)
// The Gemini API key lives only in the backend environment; the browser never
// sees it. The backend returns a calculated insight when Gemini is unavailable.
// ---------------------------------------------------------------------------
export const AI_INSIGHT_TIMEOUT_MS = 30000;

export async function getAIDashboardInsights(refresh = false): Promise<AIDashboardInsightsResponse> {
  const query = refresh ? '?refresh=true' : '';
  return await apiFetch<AIDashboardInsightsResponse>(`/api/ai/dashboard-insights${query}`, {
    timeoutMs: AI_INSIGHT_TIMEOUT_MS,
  });
}

// ---------------------------------------------------------------------------
// User Preferences (still mock-backed unless backend implements)
// ---------------------------------------------------------------------------
export async function getUserPreferences(): Promise<UserPreferences> {
  // Try backend if exists, else mock
  try {
    const raw = await apiFetch<any>('/api/profile'); // no preferences endpoint yet
    // If backend has preferences endpoint in future, we'd call it
    // For now, return mock with localStorage persistence
    const stored = localStorage.getItem('climacred_preferences');
    if (stored) return JSON.parse(stored);
    return { ...INITIAL_PREFERENCES };
  } catch {
    return { ...INITIAL_PREFERENCES };
  }
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
