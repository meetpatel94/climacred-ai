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

export interface BusinessProfile {
  name: string;
  industry: string;
  businessType: string;
  location: string;
  employees: number;
  workingDaysPerMonth: number;
  productionVolume: string;
  operatingHoursPerDay: number;
  businessSize: 'Micro' | 'Small' | 'Medium' | 'Mid-Market';
  facilityAreaSqFt: number;
  contactEmail: string;
  phone: string;
}

export interface ClimateAssessmentData {
  energy: {
    monthlyElectricityKwh: number;
    monthlyElectricityBillInr: number;
    dieselGeneratorHoursPerMonth: number;
    generatorFuelLitresPerMonth: number;
    existingSolarCapacityKw: number;
    energyEfficientEquipmentPercent: number;
  };
  water: {
    monthlyWaterLitres: number;
    waterSource: 'Municipal' | 'Groundwater / Borewell' | 'Water Tanker' | 'Mixed';
    waterRecyclingAvailable: boolean;
    rainwaterHarvesting: boolean;
    leakageFrequency: 'Never' | 'Rarely' | 'Monthly' | 'Frequent';
    wastewaterTreatment: 'None' | 'Primary / Settling' | 'Full ETP / STP';
  };
  waste: {
    organicWasteKgPerMonth: number;
    plasticWasteKgPerMonth: number;
    paperWasteKgPerMonth: number;
    industrialWasteKgPerMonth: number;
    textileMaterialWasteKgPerMonth: number;
    currentRecyclingPercent: number;
    wasteSegregationPracticed: boolean;
  };
  emissions: {
    primaryFuel: 'Electricity Grid' | 'Diesel' | 'Natural Gas / PNG' | 'Coal / Biomass';
    monthlyDieselLitres: number;
    monthlyPetrolLitres: number;
    monthlyNaturalGasKg: number;
    mainEmissionSources: string[];
    airPollutionControlSystem: 'None' | 'Basic Scrubber' | 'Bag Filter / ESP' | 'Advanced Multi-Stage';
  };
  mobility: {
    deliveryVehiclesCount: number;
    vehicleFuelType: 'Diesel' | 'Petrol' | 'CNG' | 'Electric' | 'Mixed Fleet';
    monthlyFleetFuelLitres: number;
    employeeCommuteMode: 'Public Transport' | 'Two-Wheelers' | 'Company Bus' | 'Mixed';
    evAdoptedPercent: number;
  };
  greenPractices: {
    ledLighting: boolean;
    solarPanels: boolean;
    rainwaterHarvesting: boolean;
    waterRecycling: boolean;
    wasteSegregation: boolean;
    energyEfficientMachinery: boolean;
    evAdoption: boolean;
    sustainableMaterials: boolean;
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
  estimatedPaybackPeriodYears: number;
  implementationDifficulty: 'Low' | 'Medium' | 'High';
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

// --- Gemini AI intelligence layer (Phase 3) ---
export type AISource = 'gemini' | 'calculated';

export interface AINumberAudit {
  verified: boolean;
  unsupported_values: string[];
}

export interface AIDashboardInsightDetails {
  data_used: string[];
  reasoning_summary: string;
  historical_comparison: string;
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
  status: 'ok' | 'unavailable' | 'error' | string;
  source: AISource;
  ai_available: boolean;
  notice: string | null;
  reason?: string | null;
  model: string;
  cached: boolean;
  generated_at: string;
  data_signature: string;
  disclaimer: string;
  calculated: AIDashboardCalculatedValues;
  history: AIDashboardHistory;
  insight: AIDashboardInsight;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message?: string;
}
