import React, { useEffect, useState } from 'react';
import {
  Zap,
  TrendingDown,
  Sun,
  Cpu,
  BarChart2,
  ArrowRight,
  ShieldAlert,
  TrendingUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { MetricCard } from '../components/common/MetricCard';
import { EmptyState } from '../components/common/EmptyState';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { EMPTY_STATES } from '../services/defaults';
import {
  getEnergyAnalytics,
  getClimateFingerprint,
  getClimateFingerprintHistory,
  getGreenSolutions,
  FingerprintSnapshot,
} from '../services/api';
import { GreenSolution, PageId } from '../types';

interface EnergyPageProps {
  onNavigate: (page: PageId) => void;
}

export const EnergyPage: React.FC<EnergyPageProps> = ({ onNavigate }) => {
  const [analytics, setAnalytics] = useState<any>(null);
  const [fingerprint, setFingerprint] = useState<any>(null);
  const [history, setHistory] = useState<FingerprintSnapshot[]>([]);
  const [solutions, setSolutions] = useState<GreenSolution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [energy, fp, snapshots, cat] = await Promise.all([
        getEnergyAnalytics(),
        getClimateFingerprint(),
        getClimateFingerprintHistory(12),
        getGreenSolutions('Energy'),
      ]);
      if (cancelled) return;
      setAnalytics(energy);
      setFingerprint(fp);
      setHistory(snapshots);
      setSolutions(cat);
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const available = analytics?.available === true;
  const monthlyKwh: number | null = available ? analytics?.monthly_electricity_kwh ?? null : null;
  const monthlyCost: number | null = available ? analytics?.monthly_electricity_cost_inr ?? null : null;
  const annualKwh: number | null = available ? analytics?.annual_electricity_kwh ?? null : null;
  const emissions: number | null = available
    ? analytics?.estimated_monthly_electricity_emissions_tonnes_co2e ?? null
    : null;
  const factor = available ? analytics?.emission_factor_used?.factor ?? null : null;
  const energyDimension = fingerprint?.dimensions?.find((d: any) => d.dimension === 'Energy');
  const energyScore: number | null = energyDimension?.score ?? null;
  const energyLevel: string | null = energyDimension?.impactLevel ?? null;

  const trend = history
    .map((snapshot) => {
      const value = snapshot.dimension_metrics?.Energy?.monthly_kwh;
      if (value === null || value === undefined) return null;
      return {
        month: snapshot.created_at
          ? new Date(snapshot.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
          : '—',
        consumptionKwh: Number(value),
      };
    })
    .filter(Boolean) as { month: string; consumptionKwh: number }[];

  const recommended = solutions
    .slice()
    .sort((a, b) => a.estimatedPaybackPeriodYears - b.estimatedPaybackPeriodYears)
    .slice(0, 4);

  if (loading) {
    return (
      <div className="space-y-8 max-w-6xl pb-16 animate-pulse">
        <div className="h-24 bg-slate-100 rounded-2xl" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-slate-100 rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl pb-16">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Energy Intelligence & Power Telemetry
            </h2>
          </div>
          <p className="text-xs text-slate-600">
            Grid draw, generator usage and efficiency, calculated from the values you recorded.
            {available && analytics?.assumptions?.[0] ? <span className="text-amber-700"> {analytics.assumptions[0]}</span> : ''}
          </p>
        </div>

        <button
          onClick={() => onNavigate('simulator')}
          className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Simulate Energy Actions</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {!available ? (
        <EmptyState
          icon={Zap}
          title={EMPTY_STATES.energy}
          message="Add your monthly electricity, generator and efficiency figures in the Climate Assessment and ClimaCred will calculate your energy footprint."
          actionLabel="Complete Climate Assessment"
          onAction={() => onNavigate('assessment')}
        />
      ) : (
        <>
          {/* 4 Metric Cards - live calculated analytics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Current Monthly Consumption"
              value={monthlyKwh !== null ? monthlyKwh.toLocaleString() : '—'}
              unit="kWh / mo"
              icon={Zap}
              iconBgColor="bg-amber-50"
              iconColor="text-amber-600"
              helperText={energyScore !== null ? `Energy score ${energyScore}/100` : undefined}
            />

            <MetricCard
              title="Monthly Utility Cost"
              value={monthlyCost !== null ? `₹${(monthlyCost / 1000).toFixed(1)}k` : '—'}
              unit="/ mo"
              icon={TrendingDown}
              iconBgColor="bg-slate-100"
              iconColor="text-slate-700"
              helperText={
                monthlyCost !== null && monthlyKwh
                  ? `Blended ~₹${(monthlyCost / monthlyKwh).toFixed(1)} / kWh`
                  : undefined
              }
            />

            <MetricCard
              title="Annual Consumption"
              value={annualKwh !== null ? annualKwh.toLocaleString() : '—'}
              unit="kWh / yr"
              icon={BarChart2}
              iconBgColor="bg-emerald-50"
              iconColor="text-emerald-600"
              helperText="Projected 12-mo run (monthly × 12)"
            />

            <MetricCard
              title="Estimated Emissions (Scope 2)"
              value={emissions !== null ? emissions.toString() : '—'}
              unit="MT CO₂e / mo"
              icon={ShieldAlert}
              iconBgColor="bg-rose-50"
              iconColor="text-rose-600"
              helperText={factor !== null ? `Grid factor ${factor} kg CO₂/kWh (configurable)` : undefined}
            />
          </div>

          {/* Consumption trend from stored snapshots */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">Energy Consumption Across Stored Snapshots</h3>
                <p className="text-xs text-slate-600">
                  Each point is a Climate Fingerprint you generated, using the electricity figure stored at that time.
                </p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                Latest recorded: {monthlyKwh !== null ? `${monthlyKwh.toLocaleString()} kWh` : '—'}
              </span>
            </div>

            {trend.length >= 2 ? (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trend} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="energyGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                      formatter={(val: any) => [`${Number(val).toLocaleString()} kWh`, 'Monthly energy']}
                    />
                    <Area type="monotone" dataKey="consumptionKwh" stroke="#d97706" strokeWidth={2.5} fill="url(#energyGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState icon={TrendingUp} title="Not enough stored records for a trend" message={EMPTY_STATES.history} />
            )}
          </div>

          {/* Calculation transparency - only when the backend calculated values */}
          {(factor !== null || energyLevel) && (
            <p className="text-[11px] text-slate-600">
              {monthlyKwh !== null && factor !== null && emissions !== null && (
                <>Calculation: monthly {monthlyKwh.toLocaleString()} kWh × {factor} kg/kWh = {emissions} MT • </>
              )}
              Version {analytics?.emission_factor_used?.calculation_version || '—'} • Impact level: {energyLevel || '—'}
            </p>
          )}
        </>
      )}

      {/* Fingerprint-based observation (calculated values, no fabricated text) */}
      {energyDimension && (
        <AIInsightCard
          title="Calculated Energy Finding"
          insight={`${energyDimension.currentStatus}. ${energyDimension.primaryCause}. Opportunity: ${energyDimension.improvementOpportunity}`}
          actionText="Review energy interventions"
          onActionClick={() => onNavigate('solutions')}
        />
      )}

      {/* Recommended energy interventions from the backend catalog */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-extrabold text-slate-900">Energy Interventions From The Catalog</h3>
          <span className="text-xs text-slate-600 font-medium">
            Payback estimates assume this facility's recorded baseline where available
          </span>
        </div>

        {recommended.length === 0 ? (
          <EmptyState
            icon={Cpu}
            title="No energy interventions available"
            message="The solution catalog could not be loaded, or no energy interventions apply yet."
            variant="inline"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommended.map((solution) => (
              <div
                key={solution.id}
                className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs hover:border-slate-300 transition-all flex flex-col justify-between space-y-4"
              >
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center shrink-0">
                    <Sun className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{solution.title}</h4>
                    <p className="text-xs text-slate-600 mt-0.5">{solution.problemAddressed || solution.shortDesc}</p>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-600">Est. Investment</p>
                    <p className="font-bold text-slate-900">{solution.investmentRange}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-emerald-50">
                    <p className="text-[10px] text-emerald-800">Payback</p>
                    <p className="font-bold text-emerald-700">{solution.estimatedPaybackPeriodYears} yrs</p>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-600">Annual Saving</p>
                    <p className="font-bold text-slate-700">₹{(solution.potentialAnnualSavingsInr / 100000).toFixed(1)}L</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
