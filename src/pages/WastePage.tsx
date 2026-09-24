import React, { useEffect, useState } from 'react';
import {
  Trash2,
  Recycle,
  Layers,
  ArrowRight,
  TrendingDown,
  Sparkles,
} from 'lucide-react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';
import { MetricCard } from '../components/common/MetricCard';
import { EmptyState } from '../components/common/EmptyState';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { EMPTY_STATES } from '../services/defaults';
import { getWasteAnalytics } from '../services/api';
import { PageId } from '../types';

interface WastePageProps {
  onNavigate: (page: PageId) => void;
}

// Muted palette used for the composition chart (presentation only, not data)
const STREAM_COLORS = ['#0f766e', '#0284c7', '#7c3aed', '#d97706', '#e11d48'];

export const WastePage: React.FC<WastePageProps> = ({ onNavigate }) => {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const waste = await getWasteAnalytics();
      if (cancelled) return;
      setAnalytics(waste);
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const available = analytics?.available === true;
  const total: number | null = available ? analytics?.total_waste_kg_per_month ?? null : null;
  const annual: number | null = available ? analytics?.annual_waste_kg ?? null : null;
  const recyclable: number | null = available ? analytics?.recyclable_waste_kg_per_month ?? null : null;
  const nonRecyclable: number | null = available ? analytics?.non_recyclable_waste_kg_per_month ?? null : null;
  const recyclingRate: number | null = available ? analytics?.recycling_rate_percent ?? null : null;
  const recoveryKg: number | null = available ? analytics?.material_recovery_opportunity_kg_per_month ?? null : null;
  const recoveryPercent: number | null = available
    ? analytics?.material_recovery_opportunity_percent ?? null
    : null;

  const breakdown = available ? analytics?.breakdown || {} : {};
  const composition = [
    { name: 'Textile / material', value: Number(breakdown.textile_material || 0) },
    { name: 'Plastic', value: Number(breakdown.plastic || 0) },
    { name: 'Paper / card', value: Number(breakdown.paper || 0) },
    { name: 'Industrial', value: Number(breakdown.industrial || 0) },
    { name: 'Organic / other', value: Number(breakdown.organic || 0) },
  ].filter((row) => row.value > 0);

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
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <Trash2 className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Waste & Circular Economy Intelligence
            </h2>
          </div>
          <p className="text-xs text-slate-600">
            Recorded waste streams, recycling rate and recovery potential, calculated by the backend.
          </p>
        </div>

        <button
          onClick={() => onNavigate('solutions')}
          className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Circular Solutions</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {!available ? (
        <EmptyState
          icon={Trash2}
          title={EMPTY_STATES.waste}
          message="Record your waste streams, current recycling rate and segregation practice to unlock the circular economy view."
          actionLabel="Complete Climate Assessment"
          onAction={() => onNavigate('assessment')}
        />
      ) : (
        <>
          {/* 4 Metric Cards - calculated */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Total Monthly Waste"
              value={total !== null ? total.toLocaleString() : '—'}
              unit="kg / mo"
              icon={Trash2}
              iconBgColor="bg-slate-100"
              iconColor="text-slate-700"
              helperText={annual !== null ? `${annual.toLocaleString()} kg / yr at current rate` : undefined}
            />

            <MetricCard
              title="Recyclable Stream"
              value={recyclable !== null ? recyclable.toLocaleString() : '—'}
              unit="kg / mo"
              icon={Recycle}
              iconBgColor="bg-emerald-50"
              iconColor="text-emerald-600"
              helperText={recyclingRate !== null ? `Based on your ${recyclingRate}% recycling rate` : undefined}
            />

            <MetricCard
              title="Non-Recyclable Residue"
              value={nonRecyclable !== null ? nonRecyclable.toLocaleString() : '—'}
              unit="kg / mo"
              icon={TrendingDown}
              iconBgColor="bg-rose-50"
              iconColor="text-rose-600"
              helperText="Remainder of the recorded streams"
            />

            <MetricCard
              title="Current Recycling Rate"
              value={recyclingRate !== null ? `${recyclingRate}` : '—'}
              unit="% of total"
              icon={Sparkles}
              iconBgColor="bg-amber-50"
              iconColor="text-amber-600"
              helperText="Value recorded in your assessment"
            />
          </div>

          {/* Composition + recovery opportunity */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* Pie chart built from the recorded streams */}
            <div className="lg:col-span-6 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">Monthly Waste Stream Composition (kg)</h3>
                <p className="text-xs text-slate-600">
                  Split of the waste quantities you recorded in the Climate Assessment.
                </p>
              </div>

              {composition.length === 0 ? (
                <EmptyState icon={Layers} title="No waste streams recorded" message={EMPTY_STATES.waste} />
              ) : (
                <>
                  <div className="h-64 w-full flex items-center justify-center my-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={composition}
                          cx="50%"
                          cy="50%"
                          innerRadius={55}
                          outerRadius={85}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {composition.map((entry, index) => (
                            <Cell key={`cell-${entry.name}`} fill={STREAM_COLORS[index % STREAM_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                          formatter={(val: any) => [`${Number(val).toLocaleString()} kg`, 'Recorded volume']}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
                    {composition.map((item, index) => (
                      <div key={item.name} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-2.5 h-2.5 rounded-full"
                            style={{ backgroundColor: STREAM_COLORS[index % STREAM_COLORS.length] }}
                          />
                          <span className="text-slate-700 font-medium">{item.name}</span>
                        </div>
                        <span className="font-bold text-slate-900">{item.value.toLocaleString()} kg</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Recovery opportunity (calculated) */}
            <div className="lg:col-span-6 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-extrabold text-slate-900">Material Recovery Opportunity</h3>
                  {recoveryKg !== null && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                      +{recoveryKg.toLocaleString()} kg / mo
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-600 mb-4 leading-relaxed">
                  {recoveryKg !== null && recoveryPercent !== null ? (
                    <>
                      With the recorded {total?.toLocaleString()} kg/mo of waste and {recyclingRate}% recycling rate,
                      improving segregation and recovery could divert an additional{' '}
                      <strong>{recoveryKg.toLocaleString()} kg/mo</strong> (~{recoveryPercent}% of the recorded
                      volume) from landfill. Modelled estimate, not a guarantee.
                    </>
                  ) : (
                    'Recovery opportunity is unavailable until waste data is recorded.'
                  )}
                </p>

                <div className="space-y-2.5 text-xs">
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">Recorded textile / material waste</span>
                    <span className="text-xs font-bold text-emerald-700">
                      {Number(breakdown.textile_material || 0).toLocaleString()} kg / mo
                    </span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">Recorded plastic waste</span>
                    <span className="text-xs font-bold text-emerald-700">
                      {Number(breakdown.plastic || 0).toLocaleString()} kg / mo
                    </span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">Recorded industrial / other waste</span>
                    <span className="text-xs font-bold text-amber-700">
                      {(
                        Number(breakdown.industrial || 0) + Number(breakdown.paper || 0) + Number(breakdown.organic || 0)
                      ).toLocaleString()}{' '}
                      kg / mo
                    </span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => onNavigate('solutions')}
                className="w-full mt-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors"
              >
                <span>Review Circular Interventions</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Modelling assumptions from the backend */}
          {Array.isArray(analytics?.assumptions) && (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs">
              <p className="text-xs font-bold text-slate-900 mb-1.5">How this was calculated</p>
              <ul className="text-[11px] text-slate-600 list-disc list-inside space-y-0.5">
                {analytics.assumptions.map((item: string, idx: number) => <li key={idx}>{item}</li>)}
              </ul>
            </div>
          )}
        </>
      )}

      <AIInsightCard
        title="Ask The AI Assistant About Your Waste Data"
        insight={
          available
            ? 'The ClimaCred AI Assistant can explain your recorded waste mix, recycling rate and recovery options using these calculated values only.'
            : EMPTY_STATES.chatNoData
        }
        actionText="Open the solution catalog"
        onActionClick={() => onNavigate('solutions')}
      />
    </div>
  );
};
