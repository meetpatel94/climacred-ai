// Shared frontend defaults & empty-state helpers.
//
// IMPORTANT: this file intentionally contains NO business data. Values are only
// ever displayed when they come from user input, user imports or the backend.
// Anything missing is rendered as an empty state ("No energy data yet", ...).

import { BusinessProfile, ClimateAssessmentData, UserPreferences } from '../types';

/** Platform defaults (currency/units/theme) - not business data. */
export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  currency: 'INR',
  measurementUnit: 'Metric',
  emailAlerts: true,
  benchmarkSharing: true,
  theme: 'light',
};

/** Empty state copy (kept in one place so every page says the same thing). */
export const EMPTY_STATES = {
  profile: 'No business profile yet. Add your business details to get started.',
  energy: 'No energy data yet',
  water: 'No water data yet',
  waste: 'No waste data yet',
  emissions: 'No emissions data yet',
  mobility: 'No mobility data yet',
  fingerprint: 'Complete your Climate Assessment to generate your Climate Fingerprint.',
  dashboard: 'No business climate data yet.',
  recommendations: 'No recommendations yet. Complete your Climate Assessment to unlock personalized interventions.',
  plan: 'No transformation plan yet. Complete your Climate Assessment to generate a personalized roadmap.',
  impact: 'No impact verification data yet. Submit before/after meter readings after an intervention.',
  report: 'No climate report yet. Add business data and complete the Climate Assessment to generate one.',
  history: 'Insufficient historical data for a reliable trend. Generate another Climate Fingerprint snapshot to build history.',
  solutions: 'No solutions match your filters.',
  scenarioNoData: 'No business climate data yet. Complete your Climate Assessment to simulate scenarios for your business.',
  aiNoData: 'No business climate data yet. Complete your Climate Assessment so the ClimaCred AI Assistant can analyze your actual data.',
};

/**
 * A blank assessment draft for the data-entry wizard.
 * Empty strings/null mean "not provided" - never a fabricated zero.
 */
export function emptyAssessmentDraft(): ClimateAssessmentData {
  return {
    energy: {
      monthlyElectricityKwh: null,
      monthlyElectricityBillInr: null,
      dieselGeneratorHoursPerMonth: null,
      generatorFuelLitresPerMonth: null,
      existingSolarCapacityKw: null,
      energyEfficientEquipmentPercent: null,
    },
    water: {
      monthlyWaterLitres: null,
      waterSource: '',
      waterRecyclingAvailable: null,
      rainwaterHarvesting: null,
      leakageFrequency: '',
      wastewaterTreatment: '',
    },
    waste: {
      organicWasteKgPerMonth: null,
      plasticWasteKgPerMonth: null,
      paperWasteKgPerMonth: null,
      industrialWasteKgPerMonth: null,
      textileMaterialWasteKgPerMonth: null,
      currentRecyclingPercent: null,
      wasteSegregationPracticed: null,
    },
    emissions: {
      primaryFuel: '',
      monthlyDieselLitres: null,
      monthlyPetrolLitres: null,
      monthlyNaturalGasKg: null,
      mainEmissionSources: [],
      airPollutionControlSystem: '',
    },
    mobility: {
      deliveryVehiclesCount: null,
      vehicleFuelType: '',
      monthlyFleetFuelLitres: null,
      employeeCommuteMode: '',
      evAdoptedPercent: null,
    },
    greenPractices: {
      ledLighting: null,
      solarPanels: null,
      rainwaterHarvesting: null,
      waterRecycling: null,
      wasteSegregation: null,
      energyEfficientMachinery: null,
      evAdoption: null,
      sustainableMaterials: null,
    },
  };
}

/** A blank business profile draft (empty strings, no invented values). */
export function emptyProfileDraft(): BusinessProfile {
  return {
    name: '',
    industry: '',
    businessType: '',
    location: '',
    employees: null as number | null,
    workingDaysPerMonth: null as number | null,
    productionVolume: '',
    operatingHoursPerDay: null as number | null,
    businessSize: null,
    facilityAreaSqFt: null as number | null,
    contactEmail: '',
    phone: '',
  };
}

const isFilled = (value: unknown): boolean => {
  if (value === null || value === undefined || value === '') return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'number') return value !== 0;
  if (typeof value === 'boolean') return value;
  return true;
};

/** True only when the stored assessment actually contains user-entered values. */
export function hasAssessmentData(assessment: ClimateAssessmentData | null | undefined): boolean {
  if (!assessment) return false;
  return Object.values(assessment).some((section) =>
    section && typeof section === 'object'
      ? Object.values(section as Record<string, unknown>).some(isFilled)
      : isFilled(section)
  );
}

/** True when the stored profile contains at least a business name. */
export function hasProfileData(profile: { name?: string | null } | null | undefined): boolean {
  return Boolean(profile && profile.name && profile.name.trim());
}

/** True when a calculated metric exists (i.e. the user recorded it). */
export function hasMetric(value: unknown): boolean {
  return value !== null && value !== undefined && !Number.isNaN(Number(value));
}

/** Format helpers that return null (→ empty state) instead of a fake number. */
export function formatNumber(value: unknown, fractionDigits = 0): string | null {
  if (!hasMetric(value)) return null;
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits });
}

export function formatInrCompact(value: unknown): string | null {
  if (!hasMetric(value)) return null;
  const amount = Number(value);
  if (Math.abs(amount) >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
  if (Math.abs(amount) >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
  if (Math.abs(amount) >= 1000) return `₹${(amount / 1000).toFixed(1)}k`;
  return `₹${amount.toFixed(0)}`;
}

/** Chart palette shared by the resource pages (no data values, only colours). */
export const CHART_COLORS = ['#10b981', '#059669', '#0d9488', '#14b8a6', '#34d399', '#0284c7', '#f59e0b', '#6366f1'];
