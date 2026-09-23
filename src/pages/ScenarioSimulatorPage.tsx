import React, { useState, useEffect, useMemo } from 'react';
import {
  Sliders,
  Zap,
  Droplets,
  Trash2,
  TrendingDown,
  ArrowRight,
  RotateCcw,
  Check,
  Loader2,
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
import { GREEN_SOLUTIONS_LIBRARY } from '../services/mockData';
import { DemoTag } from '../components/common/StatusBadge';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { PageId } from '../types';
import { getGreenSolutions, runScenarioSimulationWithScale, getClimateFingerprint } from '../services/api';

interface ScenarioSimulatorPageProps {
  onNavigate: (page: PageId) => void;
  initialSelectedSolutionIds?: string[];
}

export const ScenarioSimulatorPage: React.FC<ScenarioSimulatorPageProps> = ({
  onNavigate,
  initialSelectedSolutionIds = ['sol-solar', 'sol-water-ro'],
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>(initialSelectedSolutionIds);
  const [adoptionScalePercent, setAdoptionScalePercent] = useState<number>(100);
  const [solutions, setSolutions] = useState(GREEN_SOLUTIONS_LIBRARY);
  const [backendResult, setBackendResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [baseScore, setBaseScore] = useState(58);

  useEffect(() => {
    getGreenSolutions().then(setSolutions).catch(()=> setSolutions(GREEN_SOLUTIONS_LIBRARY));
    getClimateFingerprint().then(fp => setBaseScore(fp.overallScore)).catch(()=> setBaseScore(58));
  }, []);

  // Debounced backend simulation
  useEffect(() => {
    let cancelled = false;
    async function simulate() {
      if (selectedIds.length === 0) {
        setBackendResult(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const result = await runScenarioSimulationWithScale(selectedIds, adoptionScalePercent);
        if (!cancelled) setBackendResult(result);
      } catch (e: any) {
        if (!cancelled) setError(e.message || 'Simulation failed');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    const t = setTimeout(simulate, 300);
    return () => { cancelled = true; clearTimeout(t); };
  }, [selectedIds, adoptionScalePercent]);

  const toggleSolution = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    setSelectedIds(solutions.map((s) => s.id));
  };

  const clearAll = () => {
    setSelectedIds([]);
  };

  // Fallback local calculation if backend not available
  const fallbackSimulation = useMemo(() => {
    const selected = solutions.filter((s) => selectedIds.includes(s.id));
    const scaleFactor = adoptionScalePercent / 100;
    const baseInvestment = selected.reduce((acc, curr) => acc + curr.investmentMinInr, 0);
    const scaledInvestment = Math.round(baseInvestment * scaleFactor);
    const baseSavings = selected.reduce((acc, curr) => acc + curr.potentialAnnualSavingsInr, 0);
    const scaledSavings = Math.round(baseSavings * scaleFactor);
    const baseCo2 = selected.reduce((acc, curr) => acc + curr.co2ReductionTonnesPerYear, 0);
    const scaledCo2 = Number((baseCo2 * scaleFactor).toFixed(1));
    const paybackYears = scaledSavings > 0 ? Number((scaledInvestment / scaledSavings).toFixed(1)) : 0;
    const hasSolar = selectedIds.includes('sol-solar');
    const hasVfd = selectedIds.includes('sol-machinery-vfd');
    const hasRo = selectedIds.includes('sol-water-ro');
    const hasLeak = selectedIds.includes('sol-leak-sensors');
    const hasWaste = selectedIds.includes('sol-waste-recovery');
    const energyReductionPct = Math.round(((hasSolar ? 28 : 0) + (hasVfd ? 12 : 0)) * scaleFactor);
    const waterReductionPct = Math.round(((hasRo ? 58 : 0) + (hasLeak ? 9 : 0)) * scaleFactor);
    const wasteReductionPct = Math.round((hasWaste ? 66 : 0) * scaleFactor);
    const co2ReductionPct = Math.min(Math.round(((scaledCo2 / 494.4) * 100)), 65);
    const projectedClimateScore = Math.min(baseScore + Math.round(selected.length * 4.2 * scaleFactor), 94);
    return {
      investment: scaledInvestment,
      annualSavings: scaledSavings,
      monthlySavings: Math.round(scaledSavings / 12),
      paybackYears,
      co2ReductionTonnes: scaledCo2,
      energyReductionPct,
      waterReductionPct,
      wasteReductionPct,
      co2ReductionPct,
      projectedClimateScore,
      selectedCount: selected.length,
    };
  }, [selectedIds, adoptionScalePercent, solutions, baseScore]);

  const simulation = backendResult ? {
    investment: backendResult.totalInvestmentInr ?? backendResult.investment?.min_inr ?? fallbackSimulation.investment,
    annualSavings: backendResult.totalAnnualSavingsInr ?? backendResult.annual_savings_inr ?? fallbackSimulation.annualSavings,
    monthlySavings: backendResult.monthly_savings_inr ?? Math.round((backendResult.totalAnnualSavingsInr||0)/12) ?? fallbackSimulation.monthlySavings,
    paybackYears: backendResult.payback_period_years ?? backendResult.estimatedPaybackYears ?? fallbackSimulation.paybackYears,
    co2ReductionTonnes: backendResult.emission_change?.co2ReductionTonnes ?? backendResult.emission_change?.reduction_tonnes_co2_per_year ?? fallbackSimulation.co2ReductionTonnes,
    energyReductionPct: backendResult.energy_change?.energyReductionPercent ?? backendResult.energy_change?.reduction_percent ?? fallbackSimulation.energyReductionPct,
    waterReductionPct: backendResult.water_change?.waterReductionPercent ?? backendResult.water_change?.reduction_percent ?? fallbackSimulation.waterReductionPct,
    wasteReductionPct: backendResult.waste_change?.wasteReductionPercent ?? backendResult.waste_change?.reduction_percent ?? fallbackSimulation.wasteReductionPct,
    co2ReductionPct: backendResult.emission_change?.co2ReductionPercent ?? backendResult.emission_change?.reduction_percent ?? fallbackSimulation.co2ReductionPct,
    projectedClimateScore: backendResult.projected_climate_score ?? backendResult.projectedClimateScore ?? fallbackSimulation.projectedClimateScore,
    selectedCount: backendResult.selected_count ?? fallbackSimulation.selectedCount,
    assumptions: backendResult.assumptions || [],
  } : fallbackSimulation;

  // Comparison chart data (Current vs Simulated Green State)
  const comparisonData = [
    {
      metric: 'Energy (k kWh/yr)',
      Current: 462,
      Simulated: Math.round(462 * (1 - (simulation.energyReductionPct||0) / 100)),
    },
    {
      metric: 'Water (k Litres/mo)',
      Current: 480,
      Simulated: Math.round(480 * (1 - (simulation.waterReductionPct||0) / 100)),
    },
    {
      metric: 'Waste (kg/mo)',
      Current: 3600,
      Simulated: Math.round(3600 * (1 - (simulation.wasteReductionPct||0) / 100)),
    },
    {
      metric: 'CO₂e (MT/yr)',
      Current: 494,
      Simulated: Math.max(Math.round(494 - (simulation.co2ReductionTonnes||0)), 150),
    },
  ];

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
            <DemoTag label={loading ? "Calculating..." : "Live Backend Model"} />
          </div>
          <p className="text-xs text-slate-600">
            Combine green interventions and adjust implementation scale to simulate capital requirements, operational utility savings, payback timeline, and footprint reduction. <span className="text-emerald-700 font-semibold">Backend avoids double counting (energy cap 55%, water 75%).</span>
          </p>
          {error && <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1 mt-2 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> {error} – showing local estimate.</p>}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={selectAll}
            className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700"
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

      {/* Multi-Selection Chips / Grid */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Select Interventions for Scenario ({simulation.selectedCount} Active) {loading && <Loader2 className="w-3 h-3 inline animate-spin ml-1" />}
          </h4>
          <span className="text-xs font-semibold text-emerald-700">
            Click cards to toggle inclusion
          </span>
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
                      {sol.estimatedPaybackPeriodYears}y Payback
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
              Simulate phased 50% pilot testing vs 100% full facility retrofit deployment.
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
        {simulation.assumptions?.length > 0 && (
          <details className="pt-3 border-t border-slate-100">
            <summary className="text-xs font-semibold text-slate-700 cursor-pointer">View backend assumptions & methodology</summary>
            <ul className="text-[11px] text-slate-600 list-disc pl-4 mt-2 space-y-1">
              {simulation.assumptions.map((a: string, i: number) => <li key={i}>{a}</li>)}
            </ul>
          </details>
        )}
      </div>

      {/* Simulated Outcomes Dashboard (Financial + Environmental) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Capital Investment */}
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

        {/* Annual Utility OPEX Savings */}
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
            ≈ ₹{simulation.monthlySavings.toLocaleString()} saved every month
          </p>
        </div>

        {/* Payback Period */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Estimated Payback Period
          </span>
          <div className="flex items-baseline space-x-1.5">
            <span className="text-2xl sm:text-3xl font-black text-slate-900">
              {simulation.paybackYears}
            </span>
            <span className="text-xs font-semibold text-slate-600">Years</span>
          </div>
          <p className="text-[11px] text-slate-600 pt-1 border-t border-slate-100">
            Based on current power & water rates
          </p>
        </div>

        {/* Projected Climate Readiness Score */}
        <div className="bg-slate-900 text-white border border-slate-800 rounded-2xl p-5 shadow-md space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
            Projected Climate Score
          </span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl sm:text-3xl font-black text-white">
              {simulation.projectedClimateScore}
            </span>
            <span className="text-xs font-semibold text-emerald-300">/ 100</span>
            <span className="text-[11px] text-emerald-400 font-bold ml-auto">
              +{simulation.projectedClimateScore - baseScore} pts
            </span>
          </div>
          <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
            Accelerated Leadership readiness tier
          </p>
        </div>
      </div>

      {/* Comparison Chart & Resource Reductions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Before vs Simulated Scenario Chart */}
        <div className="lg:col-span-7 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-extrabold text-slate-900">
                Current Operational Footprint vs Simulated Green State
              </h4>
              <p className="text-xs text-slate-600">
                Direct comparison of resource consumption across key dimensions.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="metric" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="Current" fill="#94a3b8" radius={[4, 4, 0, 0]} name="Current State" />
                <Bar dataKey="Simulated" fill="#10b981" radius={[4, 4, 0, 0]} name="Simulated Green State" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Environmental Footprint Cuts Overview */}
        <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
          <div className="space-y-4">
            <h4 className="text-sm font-extrabold text-slate-900">
              Quantified Resource Reductions
            </h4>

            <div className="space-y-3">
              {/* Energy */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-slate-700">
                    <Zap className="w-3.5 h-3.5 text-amber-500" />
                    Grid Electricity Reduction
                  </span>
                  <span className="font-bold text-amber-700">{simulation.energyReductionPct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full transition-all duration-500"
                    style={{ width: `${simulation.energyReductionPct}%` }}
                  />
                </div>
              </div>

              {/* Water */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-slate-700">
                    <Droplets className="w-3.5 h-3.5 text-cyan-500" />
                    Freshwater Extraction Reduction
                  </span>
                  <span className="font-bold text-cyan-700">{simulation.waterReductionPct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 rounded-full transition-all duration-500"
                    style={{ width: `${simulation.waterReductionPct}%` }}
                  />
                </div>
              </div>

              {/* Waste */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-slate-700">
                    <Trash2 className="w-3.5 h-3.5 text-emerald-500" />
                    Scrap Landfill Diversion Rate
                  </span>
                  <span className="font-bold text-emerald-700">{simulation.wasteReductionPct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                    style={{ width: `${simulation.wasteReductionPct}%` }}
                  />
                </div>
              </div>

              {/* Carbon */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-slate-700">
                    <TrendingDown className="w-3.5 h-3.5 text-slate-700" />
                    Greenhouse Gas Abatement
                  </span>
                  <span className="font-bold text-slate-900">
                    {simulation.co2ReductionTonnes} MT / yr ({simulation.co2ReductionPct}%)
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-slate-800 rounded-full transition-all duration-500"
                    style={{ width: `${simulation.co2ReductionPct}%` }}
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

      {/* AI Scenario Insight */}
      <AIInsightCard
        title="AI Financial & Payback Observation"
        insight={backendResult?.assumptions ? `Backend-verified scenario: ₹${(simulation.investment / 100000).toFixed(1)}L investment yields ₹${(simulation.annualSavings / 100000).toFixed(1)}L yearly savings, ${simulation.paybackYears}y payback. Assumptions include capped savings and site-specific factors. Estimated, not guaranteed.` : `This simulated scenario commits ₹${(simulation.investment / 100000).toFixed(1)} Lakh to yield an estimated ₹${(simulation.annualSavings / 100000).toFixed(1)} Lakh in yearly recurring utility savings. With a ${simulation.paybackYears}-year payback, the investments pay for themselves before Year 4, subsequently delivering pure operational margin expansion.`}
        actionText="Review Phased Implementation Timeline"
        onActionClick={() => onNavigate('transformation')}
      />
    </div>
  );
};
