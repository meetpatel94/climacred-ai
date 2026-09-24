import React, { useState, useEffect, useMemo } from 'react';
import {
  Zap,
  Droplets,
  Trash2,
  TrendingDown,
  ArrowRight,
  Check,
  RotateCcw,
  Loader2,
  Sliders,
  AlertTriangle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { EmptyState } from '../components/common/EmptyState';
import { AIInsightCard } from '../components/common/AIInsightCard';
import {
  getGreenSolutions,
  getClimateFingerprint,
  getEnergyAnalytics,
  getWaterAnalytics,
  getWasteAnalytics,
  getEmissionsAnalytics,
  runScenarioSimulationWithScale,
} from '../services/api';
import { EMPTY_STATES } from '../services/defaults';
import { GreenSolution, PageId } from '../types';

interface ScenarioSimulatorPageProps {
  onNavigate: (page: PageId) => void;
  initialSelectedSolutionIds?: string[];
}

export const ScenarioSimulatorPage: React.FC<ScenarioSimulatorPageProps> = ({
  onNavigate,
  initialSelectedSolutionIds = [],
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>(initialSelectedSolutionIds);
  const [adoptionScalePercent, setAdoptionScalePercent] = useState<number>(100);
  const [solutions, setSolutions] = useState<GreenSolution[]>([]);
  const [backendResult, setBackendResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [baseScore, setBaseScore] = useState<number | null>(null);
  // Real current footprint, used as the "before" side of the comparison chart
  const [currentFootprint, setCurrentFootprint] = useState<{
    energyKwhYear: number | null;
    waterLitresMonth: number | null;
    wasteKgMonth: number | null;
    emissionsTonnesYear: number | null;
  }>({ energyKwhYear: null, waterLitresMonth: null, wasteKgMonth: null, emissionsTonnesYear: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [catalogue, fingerprint, energy, water, waste, emissions] = await Promise.all([
        getGreenSolutions(),
        getClimateFingerprint(),
        getEnergyAnalytics(),
        getWaterAnalytics(),
        getWasteAnalytics(),
        getEmissionsAnalytics(),
      ]);
      if (cancelled) return;
      setSolutions(catalogue);
      setBaseScore(fingerprint?.overallScore ?? null);
      setCurrentFootprint({
        energyKwhYear: energy?.available ? energy?.annual_electricity_kwh ?? null : null,
        waterLitresMonth: water?.available ? water?.monthly_water_litres ?? null : null,
        wasteKgMonth: waste?.available ? waste?.total_waste_kg_per_month ?? null : null,
        emissionsTonnesYear: emissions?.available ? emissions?.annual_total_tonnes_co2e ?? null : null,
      });
    })();
    return () => { cancelled = true; };
  }, []);

  // Simulation always comes from the backend model - no local estimate is invented.
  useEffect(() => {
    let cancelled = false;
    async function simulate() {
      if (selectedIds.length === 0) {
        setBackendResult(null);
        setError(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const result = await runScenarioSimulationWithScale(selectedIds, adoptionScalePercent);
        if (!cancelled) setBackendResult(result);
      } catch (e: any) {
        if (!cancelled) {
          setBackendResult(null);
          setError(e.message || 'Simulation service unavailable.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    const timer = setTimeout(simulate, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [selectedIds, adoptionScalePercent]);

  const toggleSolution = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAll = () => setSelectedIds(solutions.map((s) => s.id));
  const clearAll = () => setSelectedIds([]);

  // Backend response only - nothing is substituted when the model is unavailable.
  const simulation = useMemo(() => {
    if (!backendResult) return null;
    return {
      investment: backendResult.totalInvestmentInr ?? backendResult.investment?.min_inr ?? 0,
      annualSavings: backendResult.totalAnnualSavingsInr ?? backendResult.annual_savings_inr ?? 0,
      monthlySavings: backendResult.monthly_savings_inr ?? Math.round((backendResult.totalAnnualSavingsInr || 0) / 12),
      paybackYears: backendResult.payback_period_years ?? backendResult.estimatedPaybackYears ?? null,
      co2ReductionTonnes:
        backendResult.emission_change?.co2ReductionTonnes ??
        backendResult.emission_change?.reduction_tonnes_co2_per_year ??
        null,
      energyReductionPct:
        backendResult.energy_change?.energyReductionPercent ??
        backendResult.energy_change?.reduction_percent ??
        null,
      waterReductionPct:
        backendResult.water_change?.waterReductionPercent ??
        backendResult.water_change?.reduction_percent ??
        null,
      wasteReductionPct:
        backendResult.waste_change?.wasteReductionPercent ??
        backendResult.waste_change?.reduction_percent ??
        null,
      co2ReductionPct:
        backendResult.emission_change?.co2ReductionPercent ??
        backendResult.emission_change?.reduction_percent ??
        null,
      projectedClimateScore: backendResult.projected_climate_score ?? backendResult.projectedClimateScore ?? null,
      selectedCount: backendResult.selected_count ?? selectedIds.length,
      assumptions: backendResult.assumptions || [],
    };
  }, [backendResult, selectedIds.length]);

  // Comparison chart: real recorded footprint vs the backend's projected reduction.
  const comparisonData = [
    {
      metric: 'Energy (kWh/yr)',
      current: currentFootprint.energyKwhYear,
      reductionPct: simulation?.energyReductionPct ?? null,
    },
    {
      metric: 'Water (L/mo)',
      current: currentFootprint.waterLitresMonth,
      reductionPct: simulation?.waterReductionPct ?? null,
    },
    {
      metric: 'Waste (kg/mo)',
      current: currentFootprint.wasteKgMonth,
      reductionPct: simulation?.wasteReductionPct ?? null,
    },
    {
      metric: 'CO₂e (MT/yr)',
      current: currentFootprint.emissionsTonnesYear,
      reductionPct: simulation?.co2ReductionPct ?? null,
    },
  ]
    .filter((row) => row.current !== null && row.current !== undefined && row.reductionPct !== null)
    .map((row) => ({
      metric: row.metric,
      Current: Math.round(Number(row.current)),
      Simulated: Math.max(0, Math.round(Number(row.current) * (1 - Number(row.reductionPct) / 100))),
    }));

  return (
    <div className="space-y-8 max-w-6xl pb-16">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <Sliders className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Scenario & Green Investment Simulator
            </h2>
          </div>
          <p className="text-xs text-slate-600">
            Combine green interventions and adjust implementation scale to simulate capital requirements, utility
            savings, payback timeline and footprint reduction. All figures are produced by the backend model.
          </p>
          {error && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1 mt-2 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" /> {error}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={selectAll}
            disabled={solutions.length === 0}
            className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 disabled:opacity-50"
          >
            Select All
          </button>
          <button
            onClick={clearAll}
            className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Prominent Headline */}
      <div className="text-center max-w-2xl mx-auto space-y-1">
        <h3 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          What happens if you transform your business?
        </h3>
        <p className="text-xs sm:text-sm text-slate-600">
          Select interventions below to simulate how operational retrofits impact your bottom line and ESG score.
        </p>
      </div>

      {solutions.length === 0 ? (
        <EmptyState
          icon={Sliders}
          title="Intervention catalog unavailable"
          message="The simulator needs the backend solution catalog. Check the API connection and try again."
        />
      ) : (
        <>
          {/* Multi-Selection Chips / Grid */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Select Interventions for Scenario ({selectedIds.length} Active){' '}
                {loading && <Loader2 className="w-3 h-3 inline animate-spin ml-1" />}
              </h4>
              <span className="text-xs font-semibold text-emerald-700">Click cards to toggle inclusion</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {solutions.map((sol) => {
                const isSelected = selectedIds.includes(sol.id);

                return (
                  <div
                    key={sol.id}
                    onClick={() => toggleSolution(sol.id)}
                    className={`p-3.5 rounded-xl border text-xs cursor-pointer transition-all flex items-start gap-3 select-none ${
                      isSelected
                        ? 'bg-emerald-50/70 border-emerald-500 shadow-2xs text-slate-900 ring-1 ring-emerald-500'
                        : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 transition-colors ${
                        isSelected ? 'bg-emerald-600 text-white' : 'border border-slate-300 bg-white'
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600">
                          {sol.category}
                        </span>
                        <span className="text-[10px] font-bold text-emerald-800">
                          {sol.estimatedPaybackPeriodYears ?? '—'}y Payback
                        </span>
                      </div>
                      <p className="font-bold text-slate-900 truncate">{sol.title}</p>
                      <div className="flex items-center justify-between text-[11px] text-slate-600 mt-1">
                        <span>{sol.investmentRange.split('–')[0]}</span>
                        <span className="font-semibold text-emerald-800">
                          +₹{(sol.potentialAnnualSavingsInr / 100000).toFixed(1)}L/yr
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Scale Slider */}
            <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="space-y-0.5">
                <label className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                  <span>Implementation Scale Slider</span>
                  <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    {adoptionScalePercent}%
                  </span>
                </label>
                <p className="text-[11px] text-slate-600">
                  Simulate a phased pilot vs full facility retrofit deployment.
                </p>
              </div>

              <div className="w-full sm:w-64 flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-600">25%</span>
                <input
                  type="range"
                  min={25}
                  max={100}
                  step={5}
                  value={adoptionScalePercent}
                  onChange={(e) => setAdoptionScalePercent(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <span className="text-xs font-semibold text-slate-600">100%</span>
              </div>
            </div>

            {(simulation?.assumptions?.length ?? 0) > 0 && (
              <details className="pt-3 border-t border-slate-100">
                <summary className="text-xs font-semibold text-slate-700 cursor-pointer">
                  View backend assumptions & methodology
                </summary>
                <ul className="text-[11px] text-slate-600 list-disc pl-4 mt-2 space-y-1">
                  {(simulation?.assumptions || []).map((a: string, i: number) => <li key={i}>{a}</li>)}
                </ul>
              </details>
            )}
          </div>

          {!simulation ? (
            <EmptyState
              icon={Sliders}
              title={selectedIds.length === 0 ? 'Select interventions to simulate' : 'Simulation unavailable'}
              message={
                selectedIds.length === 0
                  ? 'Pick one or more interventions above. The backend model will calculate capital outlay, savings, payback and footprint reduction for your business.'
                  : error || EMPTY_STATES.scenarioNoData
              }
            />
          ) : (
            <>
              {/* Simulated Outcomes Dashboard (Financial + Environmental) */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    Est. Total Capital Outlay
                  </span>
                  <div className="flex items-baseline space-x-1.5">
                    <span className="text-2xl sm:text-3xl font-black text-slate-900">
                      ₹{(simulation.investment / 100000).toFixed(2)}
                    </span>
                    <span className="text-xs font-semibold text-slate-600">Lakh</span>
                  </div>
                  <p className="text-[11px] text-slate-600 pt-1 border-t border-slate-100">
                    One-time equipment CAPEX estimate
                  </p>
                </div>

                <div className="bg-emerald-50/70 border border-emerald-200/90 rounded-2xl p-5 shadow-xs space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
                    Annual Utility Cost Savings
                  </span>
                  <div className="flex items-baseline space-x-1.5">
                    <span className="text-2xl sm:text-3xl font-black text-emerald-700">
                      ₹{(simulation.annualSavings / 100000).toFixed(2)}
                    </span>
                    <span className="text-xs font-semibold text-emerald-800">Lakh / yr</span>
                  </div>
                  <p className="text-[11px] text-emerald-800 pt-1 border-t border-emerald-200/60 font-medium">
                    ≈ ₹{simulation.monthlySavings.toLocaleString()} modelled savings every month
                  </p>
                </div>

                <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    Estimated Payback Period
                  </span>
                  <div className="flex items-baseline space-x-1.5">
                    <span className="text-2xl sm:text-3xl font-black text-slate-900">
                      {simulation.paybackYears !== null ? simulation.paybackYears : '—'}
                    </span>
                    <span className="text-xs font-semibold text-slate-600">Years</span>
                  </div>
                  <p className="text-[11px] text-slate-600 pt-1 border-t border-slate-100">
                    Based on your recorded utility baseline
                  </p>
                </div>

                <div className="bg-slate-900 text-white border border-slate-800 rounded-2xl p-5 shadow-md space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                    Projected Climate Score
                  </span>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-2xl sm:text-3xl font-black text-white">
                      {simulation.projectedClimateScore !== null ? simulation.projectedClimateScore : '—'}
                    </span>
                    <span className="text-xs font-semibold text-emerald-300">/ 100</span>
                    {simulation.projectedClimateScore !== null && baseScore !== null && (
                      <span className="text-[11px] text-emerald-400 font-bold ml-auto">
                        {simulation.projectedClimateScore - baseScore >= 0 ? '+' : ''}
                        {simulation.projectedClimateScore - baseScore} pts vs current
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
                    Modelled score after implementing the selected interventions
                  </p>
                </div>
              </div>

              {/* Comparison Chart & Resource Reductions */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                <div className="lg:col-span-7 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-extrabold text-slate-900">
                        Recorded Footprint vs Modelled Green State
                      </h4>
                      <p className="text-xs text-slate-600">
                        "Current" uses your stored assessment values; "Simulated" applies the backend reduction
                        percentages. Only dimensions with recorded data are shown.
                      </p>
                    </div>
                  </div>

                  {comparisonData.length === 0 ? (
                    <EmptyState
                      icon={Sliders}
                      title="No recorded baseline to compare"
                      message="Complete your Climate Assessment so the simulator can compare against your real footprint."
                    />
                  ) : (
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={comparisonData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                          <XAxis dataKey="metric" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                          <YAxis tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                          />
                          <Bar dataKey="Current" fill="#94a3b8" radius={[4, 4, 0, 0]} name="Recorded" />
                          <Bar dataKey="Simulated" fill="#10b981" radius={[4, 4, 0, 0]} name="Modelled green state" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>

                {/* Environmental Footprint Cuts Overview */}
                <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
                  <div className="space-y-4">
                    <h4 className="text-sm font-extrabold text-slate-900">Modelled Resource Reductions</h4>

                    <div className="space-y-3">
                      {[
                        { label: 'Grid Electricity Reduction', value: simulation.energyReductionPct, icon: Zap, color: 'text-amber-500', bar: 'bg-amber-500', text: 'text-amber-700' },
                        { label: 'Freshwater Extraction Reduction', value: simulation.waterReductionPct, icon: Droplets, color: 'text-cyan-500', bar: 'bg-cyan-500', text: 'text-cyan-700' },
                        { label: 'Scrap Landfill Diversion Rate', value: simulation.wasteReductionPct, icon: Trash2, color: 'text-emerald-500', bar: 'bg-emerald-500', text: 'text-emerald-700' },
                      ].map((row) => {
                        const Icon = row.icon;
                        const percent = row.value !== null && row.value !== undefined ? Number(row.value) : 0;
                        return (
                          <div key={row.label} className="space-y-1">
                            <div className="flex justify-between text-xs font-semibold">
                              <span className="flex items-center gap-1.5 text-slate-700">
                                <Icon className={`w-3.5 h-3.5 ${row.color}`} />
                                {row.label}
                              </span>
                              <span className={`font-bold ${row.text}`}>
                                {row.value !== null && row.value !== undefined ? `${percent}%` : '—'}
                              </span>
                            </div>
                            <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className={`h-full ${row.bar} rounded-full transition-all duration-500`}
                                style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}

                      <div className="space-y-1">
                        <div className="flex justify-between text-xs font-semibold">
                          <span className="flex items-center gap-1.5 text-slate-700">
                            <TrendingDown className="w-3.5 h-3.5 text-slate-700" />
                            Greenhouse Gas Abatement
                          </span>
                          <span className="font-bold text-slate-900">
                            {simulation.co2ReductionTonnes !== null ? `${simulation.co2ReductionTonnes} MT / yr` : '—'}
                            {simulation.co2ReductionPct !== null ? ` (${simulation.co2ReductionPct}%)` : ''}
                          </span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                          <div
                            className="h-full bg-slate-800 rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(100, Math.max(0, Number(simulation.co2ReductionPct || 0)))}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => onNavigate('transformation')}
                    className="w-full mt-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md flex items-center justify-center gap-2 transition-all hover:scale-[1.01]"
                  >
                    <span>Convert Scenario into Transformation Plan</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Scenario summary - calculated figures only */}
              <AIInsightCard
                title="Scenario Summary (Backend Model)"
                insight={`₹${(simulation.investment / 100000).toFixed(1)}L modelled investment yields ₹${(simulation.annualSavings / 100000).toFixed(1)}L in yearly savings${
                  simulation.paybackYears !== null ? ` with a ${simulation.paybackYears}-year payback` : ''
                }. Estimates come from the backend simulator, are capped to avoid double counting, and are not guarantees.`}
                actionText="Review Phased Implementation Timeline"
                onActionClick={() => onNavigate('transformation')}
              />
            </>
          )}
        </>
      )}
    </div>
  );
};
