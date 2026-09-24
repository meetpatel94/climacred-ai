import React, { useEffect, useState } from 'react';
import {
  CloudFog,
  Flame,
  Factory,
  Truck,
  ArrowRight,
  Activity,
  Layers,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import { MetricCard } from '../components/common/MetricCard';
import { EmptyState } from '../components/common/EmptyState';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { EMPTY_STATES } from '../services/defaults';
import { getEmissionsAnalytics, getMobilityAnalytics } from '../services/api';
import { PageId } from '../types';

interface EmissionsPageProps {
  onNavigate: (page: PageId) => void;
}

const BAR_COLORS = ['#334155', '#b45309', '#be123c', '#4f46e5'];

export const EmissionsPage: React.FC<EmissionsPageProps> = ({ onNavigate }) => {
  const [analytics, setAnalytics] = useState<any>(null);
  const [mobility, setMobility] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [emissions, mobilityAnalytics] = await Promise.all([getEmissionsAnalytics(), getMobilityAnalytics()]);
      if (cancelled) return;
      setAnalytics(emissions);
      setMobility(mobilityAnalytics?.available === true ? mobilityAnalytics : null);
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const available = analytics?.available === true;
  const breakdown = available ? analytics?.emissions_breakdown_tonnes_co2e_per_month || {} : {};
  const monthlyTotal: number | null = available ? breakdown.total ?? null : null;
  const annualTotal: number | null = available ? analytics?.annual_total_tonnes_co2e ?? null : null;
  const electricity: number | null = available ? breakdown.electricity ?? null : null;
  const diesel: number | null = available ? breakdown.diesel ?? null : null;
  const petrol: number | null = available ? breakdown.petrol ?? null : null;
  const naturalGas: number | null = available ? breakdown.natural_gas ?? null : null;
  const mobilityEmissions: number | null =
    mobility?.monthly_mobility_emissions_tonnes_co2e ?? null;

  const share = (part: number | null): string | undefined => {
    if (part === null || !monthlyTotal) return undefined;
    return `${((part / monthlyTotal) * 100).toFixed(1)}% of recorded emissions`;
  };

  const sourceData = [
    { source: 'Grid electricity (Scope 2)', tonnes: electricity },
    { source: 'Diesel (Scope 1)', tonnes: diesel },
    { source: 'Petrol (Scope 1)', tonnes: petrol },
    { source: 'Natural gas (Scope 1)', tonnes: naturalGas },
  ]
    .filter((row): row is { source: string; tonnes: number } => row.tonnes !== null && row.tonnes > 0)
    .map((row) => ({ source: row.source, tonnes: row.tonnes }));

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
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-800 flex items-center justify-center">
              <CloudFog className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Emissions & Air Quality Telemetry
            </h2>
          </div>
          <p className="text-xs text-slate-600">
            Scope 1 combustion and Scope 2 purchased power, calculated from your recorded consumption.
          </p>
        </div>

        <button
          onClick={() => onNavigate('simulator')}
          className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Simulate Decarbonization</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {!available ? (
        <EmptyState
          icon={CloudFog}
          title={EMPTY_STATES.emissions}
          message="Record your electricity, diesel, petrol and gas consumption in the Climate Assessment to calculate your emissions footprint."
          actionLabel="Complete Climate Assessment"
          onAction={() => onNavigate('assessment')}
        />
      ) : (
        <>
          {/* 4 Metric Cards - calculated */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Estimated Monthly CO₂e"
              value={monthlyTotal !== null ? monthlyTotal.toFixed(2) : '—'}
              unit="MT CO₂e / mo"
              icon={CloudFog}
              iconBgColor="bg-slate-100"
              iconColor="text-slate-800"
              helperText={annualTotal !== null ? `${Number(annualTotal).toLocaleString()} MT CO₂e annualized` : undefined}
            />

            <MetricCard
              title="Scope 2 Grid Electricity"
              value={electricity !== null ? electricity.toFixed(2) : '—'}
              unit="MT CO₂e / mo"
              icon={Factory}
              iconBgColor="bg-amber-50"
              iconColor="text-amber-700"
              helperText={share(electricity)}
            />

            <MetricCard
              title="Scope 1 Fuel Combustion"
              value={diesel !== null ? diesel.toFixed(2) : '—'}
              unit="MT CO₂e / mo"
              icon={Flame}
              iconBgColor="bg-rose-50"
              iconColor="text-rose-700"
              helperText={
                analytics?.monthly_diesel_litres !== undefined
                  ? `${Number(analytics.monthly_diesel_litres).toLocaleString()} L diesel recorded`
                  : undefined
              }
            />

            <MetricCard
              title="Mobility Fleet"
              value={mobilityEmissions !== null ? mobilityEmissions.toFixed(2) : '—'}
              unit="MT CO₂e / mo"
              icon={Activity}
              iconBgColor="bg-indigo-50"
              iconColor="text-indigo-700"
              helperText={
                mobility?.delivery_vehicles_count !== undefined
                  ? `${mobility.delivery_vehicles_count} delivery vehicles recorded`
                  : EMPTY_STATES.mobility
              }
            />
          </div>

          {/* Source breakdown - only the recorded sources appear */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            <div className="lg:col-span-7 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">
                  Estimated Monthly Greenhouse Gas Emissions by Recorded Source (MT CO₂e)
                </h3>
                <p className="text-xs text-slate-600">
                  Only sources with recorded consumption appear here. Emission factors are configurable and not
                  certified.
                </p>
              </div>

              {sourceData.length === 0 ? (
                <EmptyState icon={Layers} title="No combustion or power sources recorded" message={EMPTY_STATES.emissions} />
              ) : (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sourceData} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                      <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                      <YAxis
                        type="category"
                        dataKey="source"
                        tick={{ fontSize: 10, fill: '#475569' }}
                        stroke="#cbd5e1"
                        width={140}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                        formatter={(val: any) => [`${Number(val).toFixed(2)} MT CO₂e`, 'Monthly']}
                      />
                      <Bar dataKey="tonnes" radius={[0, 4, 4, 0]}>
                        {sourceData.map((entry, index) => (
                          <Cell key={entry.source} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Calculation transparency */}
            <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-3">
              <h3 className="text-sm font-extrabold text-slate-900">Recorded Inputs Used</h3>
              <div className="space-y-2 text-xs">
                {[
                  ['Electricity', analytics?.monthly_electricity_kwh, 'kWh / mo'],
                  ['Diesel', analytics?.monthly_diesel_litres, 'L / mo'],
                  ['Petrol', analytics?.monthly_petrol_litres, 'L / mo'],
                  ['Natural gas', analytics?.monthly_natural_gas_kg, 'kg / mo'],
                ].map(([label, value, unit]) => (
                  <div key={label as string} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                    <span className="text-slate-700 font-medium">{label}</span>
                    <span className="font-bold text-slate-900">
                      {value !== undefined && value !== null ? `${Number(value).toLocaleString()} ${unit}` : 'Not recorded'}
                    </span>
                  </div>
                ))}
              </div>

              {Array.isArray(analytics?.factors_used) && (
                <div className="pt-2">
                  <p className="text-xs font-bold text-slate-900 mb-1.5">Emission factors used</p>
                  <ul className="text-[11px] text-slate-600 space-y-0.5">
                    {analytics.factors_used.map((factor: any, idx: number) => (
                      <li key={idx}>
                        • {factor.factor} {factor.unit} — {factor.source_label}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="pt-2 flex items-center gap-2 text-[11px] text-slate-600">
                <Truck className="w-3.5 h-3.5 text-slate-500" />
                <span>
                  Assumes configurable emission factors. Estimated monthly, not verified carbon accounting.
                </span>
              </div>
            </div>
          </div>

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
        title="Ask The AI Assistant To Explain Your Footprint"
        insight={
          available
            ? 'The ClimaCred AI Assistant can explain which recorded source drives your footprint and which intervention shortens it — using these calculated figures only.'
            : EMPTY_STATES.chatNoData
        }
        actionText="Simulate decarbonization options"
        onActionClick={() => onNavigate('simulator')}
      />
    </div>
  );
};
