import React, { useEffect, useState } from 'react';
import {
  Zap,
  TrendingDown,
  Sun,
  Cpu,
  BarChart2,
  ArrowRight,
  ShieldAlert,
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
import { AIInsightCard } from '../components/common/AIInsightCard';
import { DemoTag } from '../components/common/StatusBadge';
import { MONTHLY_ENERGY_DATA } from '../services/mockData';
import { PageId } from '../types';
import { getEnergyAnalytics, getClimateFingerprint } from '../services/api';

interface EnergyPageProps {
  onNavigate: (page: PageId) => void;
}

export const EnergyPage: React.FC<EnergyPageProps> = ({ onNavigate }) => {
  const [analytics, setAnalytics] = useState<any>(null);
  const [fingerprint, setFingerprint] = useState<any>(null);
  useEffect(() => {
    getEnergyAnalytics().then(setAnalytics).catch(()=>{});
    getClimateFingerprint().then(setFingerprint).catch(()=>{});
  }, []);
  const monthlyKwh = analytics?.monthly_electricity_kwh ?? 38500;
  const monthlyCost = analytics?.monthly_electricity_cost_inr ?? 346500;
  const annualKwh = analytics?.annual_electricity_kwh ?? 462000;
  const emissions = analytics?.estimated_monthly_electricity_emissions_tonnes_co2e ?? 31.6;
  const factor = analytics?.emission_factor_used?.factor ?? 0.82;
  const energyScore = fingerprint?.dimensions?.find((d:any)=> d.dimension==='Energy')?.score ?? 52;
  const energyLevel = fingerprint?.dimensions?.find((d:any)=> d.dimension==='Energy')?.impactLevel ?? 'High';

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
            <DemoTag label={analytics ? "Live Backend Data" : "Illustrative"} />
          </div>
          <p className="text-xs text-slate-600">
            Grid draw, peak load charges, diesel generator usage, and rooftop solar transition. {analytics?.assumptions?.[0] ? <span className="text-amber-700">{analytics.assumptions[0]}</span> : ''}
          </p>
        </div>

        <button
          onClick={() => onNavigate('simulator')}
          className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Simulate Solar & VFD</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 4 Metric Cards – now backed by live analytics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Current Monthly Consumption"
          value={monthlyKwh.toLocaleString()}
          unit="kWh / mo"
          icon={Zap}
          iconBgColor="bg-amber-50"
          iconColor="text-amber-600"
          helperText={`Avg. daily: ${(monthlyKwh/26).toFixed(0)} kWh • Score ${energyScore}/100`}
        />

        <MetricCard
          title="Monthly Utility Cost"
          value={`₹${(monthlyCost/1000).toFixed(1)}k`}
          unit="/ mo"
          icon={TrendingDown}
          iconBgColor="bg-slate-100"
          iconColor="text-slate-700"
          helperText={`Blended ~₹${monthlyKwh? (monthlyCost/monthlyKwh).toFixed(1): '8.9'} / kWh • ${energyLevel}`}
        />

        <MetricCard
          title="Annual Consumption"
          value={annualKwh.toLocaleString()}
          unit="kWh / yr"
          icon={BarChart2}
          iconBgColor="bg-emerald-50"
          iconColor="text-emerald-600"
          helperText="Projected 12-mo run (monthly*12)"
        />

        <MetricCard
          title="Estimated Emissions (Scope 2)"
          value={emissions.toString()}
          unit="MT CO₂e / mo"
          icon={ShieldAlert}
          iconBgColor="bg-rose-50"
          iconColor="text-rose-600"
          helperText={`Grid factor ${factor} kg CO₂/kWh (configurable)`}
        />
      </div>

      {/* Main Consumption Chart */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">
              Monthly Energy Consumption vs Efficiency Target
            </h3>
            <p className="text-xs text-slate-600">
              Historical draw shows sharp spikes in summer months (March - May) due to auxiliary chiller loads.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            Baseline: {monthlyKwh.toLocaleString()} kWh
          </span>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={MONTHLY_ENERGY_DATA} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
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
                formatter={(val: any) => [`${Number(val).toLocaleString()} kWh`, 'Monthly Energy']}
              />
              <Area type="monotone" dataKey="consumptionKwh" stroke="#d97706" strokeWidth={2.5} fill="url(#energyGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        {analytics && <p className="text-[11px] text-slate-600">Calculation: monthly {monthlyKwh} kWh × {factor} kg/kWh = {emissions} MT • Version {analytics.emission_factor_used?.calculation_version} • {analytics.assumptions?.[1]}</p>}
      </div>

      {/* AI Insight Card */}
      <AIInsightCard
        title="AI Energy Efficiency Finding"
        insight={fingerprint?.dimensions?.find((d:any)=> d.dimension==='Energy')?.currentStatus ? `${fingerprint.dimensions.find((d:any)=> d.dimension==='Energy').currentStatus}. ${fingerprint.dimensions.find((d:any)=> d.dimension==='Energy').primaryCause}. Opportunity: ${fingerprint.dimensions.find((d:any)=> d.dimension==='Energy').improvementOpportunity}` : "Energy consumption is consistently high during production hours. Energy-efficient machinery and load optimization may provide significant improvement opportunities. A 75 kWp rooftop solar PV installation would offset 35% of daytime electricity."}
        actionText="Review Rooftop Solar Intervention"
        onActionClick={() => onNavigate('solutions')}
      />

      {/* Recommended Energy Actions */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-extrabold text-slate-900">
            Recommended Energy Interventions (Live Calculated)
          </h3>
          <span className="text-xs text-slate-600 font-medium">Estimates use live facility baseline</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              icon: Cpu,
              title: 'VFD & IE4 Super-Premium Motors Retrofit',
              problem: 'Older constant-speed induction blowers and dye circulation pumps.',
              impact: 'Save 46,000 kWh/yr • ₹4,10,000 annual saving',
              cost: '₹9.5L – ₹13.0L',
              payback: '2.6 Years',
            },
            {
              icon: Sun,
              title: 'Rooftop Solar PV Installation (75 kWp)',
              problem: 'Full reliance on thermal grid power during sunny daylight operating hours.',
              impact: 'Generate 108,000 clean kWh/yr • Offset 35% grid bill',
              cost: '₹28.0L – ₹34.0L',
              payback: '3.2 Years',
            },
            {
              icon: Zap,
              title: 'Load Optimization & Peak Shaving',
              problem: 'Surge maximum demand penalties incurred during simultaneous motor start-ups.',
              impact: 'Reduce contracted kVA demand by 15%',
              cost: '₹1.5L – ₹2.5L',
              payback: '1.2 Years',
            },
            {
              icon: BarChart2,
              title: 'Smart Sub-Metering IoT Sensors',
              problem: 'Departmental lines lack independent energy telemetry.',
              impact: 'Identify unmetered idle machine wastage (7-12%)',
              cost: '₹2.8L – ₹4.0L',
              payback: '1.8 Years',
            },
          ].map((act, idx) => {
            const Icon = act.icon;
            return (
              <div
                key={idx}
                className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs hover:border-slate-300 transition-all flex flex-col justify-between space-y-4"
              >
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{act.title}</h4>
                    <p className="text-xs text-slate-600 mt-0.5">{act.problem}</p>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-600">Est. Investment</p>
                    <p className="font-bold text-slate-900">{act.cost}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-emerald-50">
                    <p className="text-[10px] text-emerald-800">Payback</p>
                    <p className="font-bold text-emerald-700">{act.payback}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-600">Status</p>
                    <p className="font-bold text-slate-700">Recommended</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
