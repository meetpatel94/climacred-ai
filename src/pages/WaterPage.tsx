import React, { useEffect, useState } from 'react';
import {
  Droplets,
  AlertTriangle,
  RotateCcw,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Factory,
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
import { MetricCard } from '../components/common/MetricCard';
import { EmptyState } from '../components/common/EmptyState';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { EMPTY_STATES } from '../services/defaults';
import { getWaterAnalytics, getClimateFingerprintHistory, FingerprintSnapshot } from '../services/api';
import { PageId } from '../types';
import { useImportedDataRevision } from '../utils/dataRevision';

interface WaterPageProps {
  onNavigate: (page: PageId) => void;
}

export const WaterPage: React.FC<WaterPageProps> = ({ onNavigate }) => {
  const importedRevision = useImportedDataRevision();
  const [analytics, setAnalytics] = useState<any>(null);
  const [history, setHistory] = useState<FingerprintSnapshot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [water, snapshots] = await Promise.all([getWaterAnalytics(), getClimateFingerprintHistory(12)]);
      if (cancelled) return;
      setAnalytics(water);
      setHistory(snapshots);
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [importedRevision]);

  const available = analytics?.available === true;
  const monthlyLitres: number | null = available ? analytics?.monthly_water_litres ?? null : null;
  const annualLitres: number | null = available ? analytics?.annual_water_litres ?? null : null;
  const savingsLitres: number | null = available ? analytics?.estimated_potential_annual_savings_litres ?? null : null;
  const savingsPercent: number | null = available ? analytics?.estimated_potential_savings_percent ?? null : null;
  const recyclingFactor: number | null = available ? analytics?.recycling_factor_used ?? null : null;
  const leakageFactor: number | null = available ? analytics?.leakage_factor_used ?? null : null;

  const snapshotPoints = history
    .map((snapshot) => {
      const metric = snapshot.dimension_metrics?.Water || {};
      const litres = metric.monthly_litres;
      if (litres === null || litres === undefined) return null;
      const leakage = leakageFactor !== null ? Number(litres) * leakageFactor : null;
      return {
        month: snapshot.created_at
          ? new Date(snapshot.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
          : '—',
        totalLitres: Number(litres),
        leakedEstimateLitres: leakage !== null ? Math.round(leakage) : 0,
      };
    })
    .filter(Boolean) as { month: string; totalLitres: number; leakedEstimateLitres: number }[];

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
            <div className="w-8 h-8 rounded-lg bg-cyan-50 text-cyan-700 flex items-center justify-center">
              <Droplets className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Water Intelligence & Effluent Management
            </h2>
          </div>
          <p className="text-xs text-slate-600">
            Water volumes, leakage exposure and recycling potential, calculated from your recorded data.
          </p>
        </div>

        <button
          onClick={() => onNavigate('simulator')}
          className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Simulate Water Actions</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {!available ? (
        <EmptyState
          icon={Droplets}
          title={EMPTY_STATES.water}
          message="Enter your monthly water consumption, recycling and leakage details in the Climate Assessment to see water analytics."
          actionLabel="Complete Climate Assessment"
          onAction={() => onNavigate('assessment')}
        />
      ) : (
        <>
          {/* 4 Metric Cards - calculated from the stored assessment */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Monthly Water Consumption"
              value={monthlyLitres !== null ? monthlyLitres.toLocaleString() : '—'}
              unit="Litres / mo"
              icon={Droplets}
              iconBgColor="bg-cyan-50"
              iconColor="text-cyan-600"
              helperText="Value recorded in your assessment"
            />

            <MetricCard
              title="Annual Water Consumption"
              value={annualLitres !== null ? annualLitres.toLocaleString() : '—'}
              unit="Litres / yr"
              icon={TrendingDown}
              iconBgColor="bg-slate-100"
              iconColor="text-slate-700"
              helperText="Monthly recorded volume × 12"
            />

            <MetricCard
              title="Recycling Savings Potential"
              value={savingsLitres !== null ? Math.round(savingsLitres).toLocaleString() : '—'}
              unit="Litres / yr"
              icon={RotateCcw}
              iconBgColor="bg-emerald-50"
              iconColor="text-emerald-600"
              helperText={
                recyclingFactor !== null
                  ? `Assumes up to ${Math.round(recyclingFactor * 100)}% recovery (configurable)`
                  : undefined
              }
            />

            <MetricCard
              title="Leakage Allowance Used"
              value={leakageFactor !== null ? `${Math.round(leakageFactor * 100)}%` : '—'}
              unit="of draw"
              icon={AlertTriangle}
              iconBgColor="bg-amber-50"
              iconColor="text-amber-600"
              helperText="Based on the leakage frequency you reported"
            />
          </div>

          {/* Trend chart from stored snapshots */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">
                  Water Extraction Across Stored Snapshots (Litres)
                </h3>
                <p className="text-xs text-slate-600">
                  Blue is the recorded monthly volume; pink is that volume at the leakage allowance used.
                </p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                Latest recorded: {monthlyLitres !== null ? `${monthlyLitres.toLocaleString()} L` : '—'}
              </span>
            </div>

            {snapshotPoints.length >= 2 ? (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={snapshotPoints} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                    <YAxis
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      stroke="#cbd5e1"
                      tickFormatter={(v) => `${v / 1000}kL`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                      formatter={(val: any, name: any) => [
                        `${Number(val).toLocaleString()} Litres`,
                        name === 'totalLitres' ? 'Recorded volume' : 'Leakage allowance',
                      ]}
                    />
                    <Bar dataKey="totalLitres" fill="#0284c7" name="Recorded volume" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="leakedEstimateLitres" fill="#fb7185" name="Leakage allowance" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState icon={TrendingUp} title="Not enough stored records for a trend" message={EMPTY_STATES.history} />
            )}
          </div>

          {/* Calculated savings summary */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-3">
            <div className="flex items-center gap-2.5">
              <Factory className="w-5 h-5 text-cyan-700" />
              <h3 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider">
                Calculated Water Efficiency Opportunity
              </h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {savingsLitres !== null && savingsPercent !== null ? (
                <>
                  On the recorded {annualLitres?.toLocaleString()} L/yr draw, closing the recycling and leakage gaps
                  could save an estimated <strong>{Math.round(savingsLitres).toLocaleString()} L/yr</strong> (~
                  {savingsPercent}% of the recorded volume). This is a modelled planning estimate, not a guarantee.
                </>
              ) : (
                'Savings potential is unavailable until water data is recorded.'
              )}
            </p>
            {Array.isArray(analytics?.assumptions) && (
              <ul className="text-[11px] text-slate-600 list-disc list-inside space-y-0.5">
                {analytics.assumptions.map((item: string, idx: number) => <li key={idx}>{item}</li>)}
              </ul>
            )}
          </div>
        </>
      )}

      <AIInsightCard
        title="Water Question For The AI Assistant"
        insight={
          available
            ? 'Ask the ClimaCred AI Assistant to explain this water picture, or continue to the solution catalog to see interventions ranked by payback.'
            : EMPTY_STATES.aiNoData
        }
        actionText="Open the solution catalog"
        onActionClick={() => onNavigate('solutions')}
      />
    </div>
  );
};
