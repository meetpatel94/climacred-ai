// TypeScript Types & Interfaces for ClimaCred AI (Phase 1 Frontend, Phase 2 Ready)

export type PageId =
  | 'landing'
  | 'dashboard'
  | 'profile'
  | 'assessment'
  | 'fingerprint'
  | 'energy'
  | 'water'
  | 'waste'
  | 'emissions'
  | 'mobility'
  | 'solutions'
  | 'simulator'
  | 'transformation'
  | 'verification'
  | 'report'
  | 'settings';

export type ImpactSeverity = 'Low' | 'Moderate' | 'High' | 'Very High';

// Numeric/text fields are nullable: a field that the user has not provided yet
// must stay empty (null) instead of being filled with a fabricated default.
export interface BusinessProfile {
  name: string | null;
  industry: string | null;
  businessType: string | null;
  location: string | null;
  employees: number | null;
  workingDaysPerMonth: number | null;
  productionVolume: string | null;
  operatingHoursPerDay: number | null;
  businessSize: 'Micro' | 'Small' | 'Medium' | 'Mid-Market' | null;
  facilityAreaSqFt: number | null;
  contactEmail: string | null;
  phone: string | null;
}

// Every field is optional/nullable: null means "not provided yet", which is what
// the UI renders as an empty state. Real zeros entered by the user stay 0.
export interface ClimateAssessmentData {
  energy: {
    monthlyElectricityKwh: number | null;
    monthlyElectricityBillInr: number | null;
    dieselGeneratorHoursPerMonth: number | null;
    generatorFuelLitresPerMonth: number | null;
    existingSolarCapacityKw: number | null;
    energyEfficientEquipmentPercent: number | null;
  };
  water: {
    monthlyWaterLitres: number | null;
    waterSource: 'Municipal' | 'Groundwater / Borewell' | 'Water Tanker' | 'Mixed' | '';
    waterRecyclingAvailable: boolean | null;
    rainwaterHarvesting: boolean | null;
    leakageFrequency: 'Never' | 'Rarely' | 'Monthly' | 'Frequent' | '';
    wastewaterTreatment: 'None' | 'Primary / Settling' | 'Full ETP / STP' | '';
  };
  waste: {
    organicWasteKgPerMonth: number | null;
    plasticWasteKgPerMonth: number | null;
    paperWasteKgPerMonth: number | null;
    industrialWasteKgPerMonth: number | null;
    textileMaterialWasteKgPerMonth: number | null;
    currentRecyclingPercent: number | null;
    wasteSegregationPracticed: boolean | null;
  };
  emissions: {
    primaryFuel: 'Electricity Grid' | 'Diesel' | 'Natural Gas / PNG' | 'Coal / Biomass' | '';
    monthlyDieselLitres: number | null;
    monthlyPetrolLitres: number | null;
    monthlyNaturalGasKg: number | null;
    mainEmissionSources: string[];
    airPollutionControlSystem: 'None' | 'Basic Scrubber' | 'Bag Filter / ESP' | 'Advanced Multi-Stage' | '';
  };
  mobility: {
    deliveryVehiclesCount: number | null;
    vehicleFuelType: 'Diesel' | 'Petrol' | 'CNG' | 'Electric' | 'Mixed Fleet' | '';
    monthlyFleetFuelLitres: number | null;
    employeeCommuteMode: 'Public Transport' | 'Two-Wheelers' | 'Company Bus' | 'Mixed' | '';
    evAdoptedPercent: number | null;
  };
  greenPractices: {
    ledLighting: boolean | null;
    solarPanels: boolean | null;
    rainwaterHarvesting: boolean | null;
    waterRecycling: boolean | null;
    wasteSegregation: boolean | null;
    energyEfficientMachinery: boolean | null;
    evAdoption: boolean | null;
    sustainableMaterials: boolean | null;
  };
}

export interface DimensionFingerprint {
  dimension: 'Energy' | 'Water' | 'Waste' | 'Emissions' | 'Mobility' | 'Operations';
  score: number; // 0 to 100
  impactLevel: ImpactSeverity;
  currentStatus: string;
  primaryCause: string;
  improvementOpportunity: string;
  potentialReduction: string;
}

export interface ClimateFingerprint {
  overallScore: number; // 0 to 100 (Climate Readiness)
  scoreLabel: string;
  dimensions: DimensionFingerprint[];
  topImprovementDimensions: string[];
  summaryNote: string;
  benchmarkPercentile: number;
}

export interface GreenSolution {
  id: string;
  title: string;
  category: 'Energy' | 'Water' | 'Waste' | 'Mobility' | 'Materials' | 'Operations';
  problemAddressed: string;
  shortDesc: string;
  investmentRange: string;
  investmentMinInr: number;
  investmentMaxInr: number;
  potentialAnnualSavingsInr: number;
  potentialEnvironmentalImpact: string;
  /** null when the catalog entry has no payback figure (never a made-up default) */
  estimatedPaybackPeriodYears: number | null;
  implementationDifficulty: 'Low' | 'Medium' | 'High' | null;
  co2ReductionTonnesPerYear: number;
  resourceReductionValue: string;
  featured?: boolean;
}

export interface ScenarioResult {
  selectedSolutionIds: string[];
  totalInvestmentInr: number;
  totalAnnualSavingsInr: number;
  energyReductionKwh: number;
  energyReductionPercent: number;
  waterReductionLitres: number;
  waterReductionPercent: number;
  wasteReductionKg: number;
  wasteReductionPercent: number;
  co2ReductionTonnes: number;
  co2ReductionPercent: number;
  estimatedPaybackYears: number;
  projectedClimateScore: number;
}

export interface TransformationPhaseItem {
  id: string;
  action: string;
  phase: 'Phase 1' | 'Phase 2' | 'Phase 3' | 'Phase 4';
  phaseName: string;
  priority: 'High' | 'Medium' | 'Low';
  estimatedCost: string;
  expectedBenefit: string;
  timeframe: string;
  status: 'Pending' | 'In Progress' | 'Completed';
  category: string;
}

export interface ImpactVerificationMetric {
  id: string;
  name: string;
  category: string;
  unit: string;
  beforeValue: number;
  afterValue: number;
  differenceValue: number;
  differencePercent: number;
  unitLabel: string;
  impactVerdict: string;
}

export interface UserPreferences {
  currency: 'INR' | 'USD' | 'EUR';
  measurementUnit: 'Metric' | 'Imperial';
  emailAlerts: boolean;
  benchmarkSharing: boolean;
  theme: 'light' | 'system';
}

// --- Gemini AI layer ---
export type AISource = 'gemini';

/** Connection states reported by GET /api/ai/status (plus the UI-only 'checking'). */
export type GeminiConnectionStatus = 'connected' | 'not_configured' | 'unreachable' | 'error';

export interface AIErrorInfo {
  code: string;
  message: string;
  http_status?: number;
}

/** GET /api/ai/status - real connection check (no API key is ever included). */
export interface AIStatusResponse {
  provider: 'Google Gemini' | string;
  configured: boolean;
  authenticated: boolean;
  model: string | null;
  status: GeminiConnectionStatus;
  message: string;
  checked_at: string;
  cached?: boolean;
  api_version?: string;
  model_source?: 'configured' | 'auto';
  configured_model?: string | null;
  error_code?: string;
  http_status?: number | null;
  available_models?: string[];
  latency_ms?: number;
}

export interface AINumberAudit {
  verified: boolean;
  unsupported_values: string[];
}

export interface AIDashboardInsightDetails {
  data_used: string[];
  reasoning_summary: string;
  historical_comparison: string;
  why_it_matters?: string;
  main_risks: string[];
  recommended_actions: string[];
  related_recommendations: string[];
  expected_impact_detail: string;
  confidence_note: string;
  assumptions: string[];
  number_audit: AINumberAudit;
}

export interface AIDashboardInsight {
  summary: string;
  recent_changes: string[];
  key_risk: string;
  focus_now: string;
  priority_action: string;
  forecast: string;
  expected_impact: string;
  confidence: string;
  details: AIDashboardInsightDetails;
}

export interface AIDashboardCalculatedValues {
  business_name: string | null;
  climate_score: number | null;
  score_label: string | null;
  top_improvement_dimensions: string[] | null;
  energy_kwh_month: number | null;
  energy_cost_inr_month: number | null;
  water_litres_month: number | null;
  waste_kg_month: number | null;
  emissions_tonnes_month: number | null;
  mobility_fuel_litres_month: number | null;
  data_quality_level: string | null;
  data_quality_completeness_percent: number | null;
  top_recommendation: { solution_id: string | null; title: string | null; priority: string | null };
  data_sources: string;
}

export interface AIDashboardHistory {
  available: boolean;
  fingerprint_snapshots: number | null;
  impact_records: number | null;
  scenario_runs: number | null;
  note: string;
}

export interface AIDashboardInsightsResponse {
  /** ok | no_data | not_configured | unreachable | error */
  status: 'ok' | 'no_data' | GeminiConnectionStatus;
  source: AISource | null;
  ai_available: boolean;
  /** false when the user has not stored any business climate data yet. */
  has_data: boolean;
  notice: string | null;
  /** Safe explanation when no insight could be generated. */
  message?: string | null;
  error?: AIErrorInfo | null;
  model: string | null;
  cached: boolean;
  generated_at: string;
  data_signature: string;
  disclaimer: string;
  calculated: AIDashboardCalculatedValues;
  history: AIDashboardHistory;
  /** Only present when Gemini generated it (never a template or fabricated insight). */
  insight: AIDashboardInsight | null;
}

// --- Gemini chat assistant ---
export interface AIChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  /** present on assistant messages */
  model?: string | null;
  notice?: string | null;
  pending?: boolean;
  error?: string | null;
}

/** POST /api/ai/chat -> {answer, provider, model, conversation_id, ...} */
export interface AIChatResponse {
  status: 'ok' | GeminiConnectionStatus;
  answer: string | null;
  provider: 'gemini';
  model: string | null;
  conversation_id: string;
  has_data: boolean;
  notice?: string | null;
  message?: string | null;
  error?: AIErrorInfo | null;
  number_audit?: AINumberAudit;
  generated_at: string;
  suggestions: string[];
  disclaimer: string;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message?: string;
}
