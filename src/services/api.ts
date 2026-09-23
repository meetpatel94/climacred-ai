// Mock Service Layer for ClimaCred AI (Phase 1 Frontend)
// In Phase 2, each function will be swapped to fetch() / axios calls to FastAPI endpoints.

import {
  BusinessProfile,
  ClimateAssessmentData,
  ClimateFingerprint,
  GreenSolution,
  ScenarioResult,
  TransformationPhaseItem,
  ImpactVerificationMetric,
  UserPreferences,
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

// Simulated storage cache (in-memory for demo / tab session)
let cachedProfile: BusinessProfile = { ...INITIAL_BUSINESS_PROFILE };
let cachedAssessment: ClimateAssessmentData = JSON.parse(JSON.stringify(INITIAL_ASSESSMENT_DATA));
let cachedFingerprint: ClimateFingerprint = JSON.parse(JSON.stringify(INITIAL_CLIMATE_FINGERPRINT));
let cachedPlan: TransformationPhaseItem[] = [...INITIAL_TRANSFORMATION_PLAN];
let cachedPreferences: UserPreferences = { ...INITIAL_PREFERENCES };

const SIMULATED_LATENCY_MS = 250;

const delay = (ms = SIMULATED_LATENCY_MS) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Phase 2 target: GET /api/v1/profile
 */
export async function getBusinessProfile(): Promise<BusinessProfile> {
  await delay();
  return { ...cachedProfile };
}

/**
 * Phase 2 target: PATCH /api/v1/profile
 */
export async function saveBusinessProfile(updated: Partial<BusinessProfile>): Promise<BusinessProfile> {
  await delay(350);
  cachedProfile = { ...cachedProfile, ...updated };
  return { ...cachedProfile };
}

/**
 * Phase 2 target: GET /api/v1/assessment
 */
export async function getClimateAssessment(): Promise<ClimateAssessmentData> {
  await delay();
  return JSON.parse(JSON.stringify(cachedAssessment));
}

/**
 * Phase 2 target: POST /api/v1/assessment
 */
export async function saveClimateAssessment(data: ClimateAssessmentData): Promise<{ success: boolean; fingerprint: ClimateFingerprint }> {
  await delay(600); // Simulate AI calculation
  cachedAssessment = JSON.parse(JSON.stringify(data));

  // Dynamic illustrative fingerprint update based on inputs
  const hasSolar = data.energy.existingSolarCapacityKw > 0 || data.greenPractices.solarPanels;
  const hasWaterRecycling = data.water.waterRecyclingAvailable || data.greenPractices.waterRecycling;
  const highEfficiency = data.energy.energyEfficientEquipmentPercent > 50;

  let newScore = 58;
  if (hasSolar) newScore += 7;
  if (hasWaterRecycling) newScore += 8;
  if (highEfficiency) newScore += 6;
  if (data.greenPractices.wasteSegregation) newScore += 4;
  if (data.greenPractices.rainwaterHarvesting) newScore += 4;

  cachedFingerprint.overallScore = Math.min(newScore, 92);
  cachedFingerprint.scoreLabel = newScore > 75 ? 'Leadership Stage' : newScore > 65 ? 'Accelerated Stage' : 'Transition Stage';

  return { success: true, fingerprint: { ...cachedFingerprint } };
}

/**
 * Phase 2 target: GET /api/v1/climate-fingerprint
 */
export async function getClimateFingerprint(): Promise<ClimateFingerprint> {
  await delay();
  return JSON.parse(JSON.stringify(cachedFingerprint));
}

/**
 * Phase 2 target: GET /api/v1/solutions
 */
export async function getGreenSolutions(categoryFilter?: string): Promise<GreenSolution[]> {
  await delay();
  if (!categoryFilter || categoryFilter === 'All') {
    return [...GREEN_SOLUTIONS_LIBRARY];
  }
  return GREEN_SOLUTIONS_LIBRARY.filter((s) => s.category.toLowerCase() === categoryFilter.toLowerCase());
}

/**
 * Phase 2 target: POST /api/v1/scenario/simulate
 */
export async function runScenarioSimulation(selectedSolutionIds: string[]): Promise<ScenarioResult> {
  await delay(300);

  const selected = GREEN_SOLUTIONS_LIBRARY.filter((s) => selectedSolutionIds.includes(s.id));

  const totalInvestment = selected.reduce((acc, curr) => acc + curr.investmentMinInr, 0);
  const totalSavings = selected.reduce((acc, curr) => acc + curr.potentialAnnualSavingsInr, 0);
  const totalCo2 = selected.reduce((acc, curr) => acc + curr.co2ReductionTonnesPerYear, 0);

  // Dynamic percentage reductions
  const hasSolar = selectedSolutionIds.includes('sol-solar');
  const hasVfd = selectedSolutionIds.includes('sol-machinery-vfd');
  const hasRo = selectedSolutionIds.includes('sol-water-ro');
  const hasLeak = selectedSolutionIds.includes('sol-leak-sensors');
  const hasWaste = selectedSolutionIds.includes('sol-waste-recovery');

  const energyReductionKwh = (hasSolar ? 9000 : 0) + (hasVfd ? 3830 : 0);
  const energyReductionPercent = Math.min(Math.round((energyReductionKwh / 38500) * 100), 55);

  const waterReductionLitres = (hasRo ? 312000 : 0) + (hasLeak ? 35000 : 0);
  const waterReductionPercent = Math.min(Math.round((waterReductionLitres / 480000) * 100), 75);

  const wasteReductionKg = hasWaste ? 2375 : 0;
  const wasteReductionPercent = Math.min(Math.round((wasteReductionKg / 3600) * 100), 68);

  const paybackYears = totalSavings > 0 ? Number((totalInvestment / totalSavings).toFixed(1)) : 0;
  const projectedClimateScore = Math.min(58 + Math.round(selected.length * 5.2), 94);

  return {
    selectedSolutionIds,
    totalInvestmentInr: totalInvestment,
    totalAnnualSavingsInr: totalSavings,
    energyReductionKwh,
    energyReductionPercent,
    waterReductionLitres,
    waterReductionPercent,
    wasteReductionKg,
    wasteReductionPercent,
    co2ReductionTonnes: totalCo2,
    co2ReductionPercent: Math.min(Math.round((totalCo2 / 41.2) * 100), 70),
    estimatedPaybackYears: paybackYears,
    projectedClimateScore,
  };
}

/**
 * Phase 2 target: GET /api/v1/transformation-plan
 */
export async function getTransformationPlan(): Promise<TransformationPhaseItem[]> {
  await delay();
  return [...cachedPlan];
}

/**
 * Phase 2 target: PATCH /api/v1/transformation-plan/:id
 */
export async function updateTransformationItemStatus(
  id: string,
  status: 'Pending' | 'In Progress' | 'Completed'
): Promise<TransformationPhaseItem[]> {
  await delay(150);
  cachedPlan = cachedPlan.map((item) => (item.id === id ? { ...item, status } : item));
  return [...cachedPlan];
}

/**
 * Phase 2 target: GET /api/v1/impact/verification
 */
export async function getImpactVerification(): Promise<ImpactVerificationMetric[]> {
  await delay();
  return [...INITIAL_IMPACT_VERIFICATION];
}

/**
 * Phase 2 target: GET /api/v1/settings/preferences
 */
export async function getUserPreferences(): Promise<UserPreferences> {
  await delay();
  return { ...cachedPreferences };
}

/**
 * Phase 2 target: PATCH /api/v1/settings/preferences
 */
export async function saveUserPreferences(prefs: Partial<UserPreferences>): Promise<UserPreferences> {
  await delay(200);
  cachedPreferences = { ...cachedPreferences, ...prefs };
  return { ...cachedPreferences };
}
