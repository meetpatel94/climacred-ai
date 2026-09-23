import React, { useEffect, useState } from 'react';
import {
  CloudFog,
  Flame,
  Factory,
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
} from 'recharts';
import { MetricCard } from '../components/common/MetricCard';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { DemoTag } from '../components/common/StatusBadge';
import { getEmissionsAnalytics } from '../services/api';
import { EMISSIONS_BY_SOURCE_DATA } from '../services/mockData';
import { PageId } from '../types';

interface EmissionsPageProps {
  onNavigate: (page: PageId) => void;
}

export const EmissionsPage: React.FC<EmissionsPageProps> = ({ onNavigate }) => {
  const [analytics, setAnalytics] = useState<any>(null);
  useEffect(()=> { getEmissionsAnalytics().then(setAnalytics).catch(()=>{}); }, []);
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
            <DemoTag label={analytics ? "Live Backend Data" : "Illustrative"} />
          </div>
          <p className="text-xs text-slate-600">
            Scope 1 direct combustion, Scope 2 purchased grid power, boiler flue gases, and stack abatement.
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

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Estimated Monthly CO₂e"
          value="41.2"
          unit="MT CO₂e / mo"
          icon={CloudFog}
          iconBgColor="bg-slate-100"
          iconColor="text-slate-800"
          helperText="494.4 MT CO₂e annualized"
        />

        <MetricCard
          title="Scope 2 Grid Electricity"
          value="31.6"
          unit="MT CO₂e (76.7%)"
          icon={Factory}
          iconBgColor="bg-amber-50"
          iconColor="text-amber-700"
          helperText="Highest single decarbonization target"
        />

        <MetricCard
          title="Scope 1 Boiler & Genset"
          value="6.8"
          unit="MT CO₂e (16.5%)"
          icon={Flame}
          iconBgColor="bg-rose-50"
          iconColor="text-rose-700"
          helperText="1,620 litres monthly diesel burn"
        />

        <MetricCard
          title="Mobility Scope 1 Fleet"
          value="2.8"
          unit="MT CO₂e (6.8%)"
          icon={Activity}
          iconBgColor="bg-indigo-50"
          iconColor="text-indigo-700"
          helperText="8 company delivery cargo vans"
        />
      </div>

      {/* Source Breakdown Chart & Scope Explainer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-7 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">
              Estimated Monthly Greenhouse Gas Emissions by Source (MT CO₂e)
            </h3>
            <p className="text-xs text-slate-600">
              Electricity purchased from the state grid dominates the total greenhouse gas footprint.
            </p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={EMISSIONS_BY_SOURCE_DATA}
                layout="vertical"
                margin={{ top: 10, right: 20, left: 40, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" unit=" MT" />
                <YAxis
                  dataKey="source"
                  type="category"
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  stroke="#cbd5e1"
                  width={120}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                  formatter={(val: any) => [`${val} MT CO₂e`, 'Emissions']}
                />
                <Bar dataKey="tonnesCo2e" fill="#047857" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Scope 1 vs Scope 2 Breakdown */}
        <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="text-sm font-extrabold text-slate-900">Scope 1 & 2 Decarbonization Levers</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Global supply chain buyers and European import compliance (CBAM) mandate verified Scope 1 & 2
              intensity reductions for apparel and textiles.
            </p>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
              <div className="flex items-center justify-between text-xs font-bold text-slate-900">
                <span>Scope 1 (Direct Fuels)</span>
                <span className="text-rose-700">9.6 MT / mo</span>
              </div>
              <p className="text-[11px] text-slate-600">
                Boiler diesel combustion + genset backup. Flue heat economizers reduce fuel by 12%.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
              <div className="flex items-center justify-between text-xs font-bold text-slate-900">
                <span>Scope 2 (Purchased Power)</span>
                <span className="text-emerald-700">31.6 MT / mo</span>
              </div>
              <p className="text-[11px] text-slate-600">
                Grid thermal base load. On-site solar + IE4 motors abates up to 14.2 MT CO₂e monthly.
              </p>
            </div>
          </div>

          <button
            onClick={() => onNavigate('transformation')}
            className="w-full mt-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors"
          >
            <span>View Decarbonization Roadmap</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* AI Insight */}
      <AIInsightCard
        title="AI Emissions & Decarbonization Forecast"
        insight="Purchased grid electricity represents 76.7% of ABC Textile's operational emissions footprint. Deploying the 75 kWp rooftop solar PV installation along with VFD motor optimization will reduce Scope 2 emissions by 126 tonnes CO₂e per year."
        actionText="View Energy Solutions Library"
        onActionClick={() => onNavigate('solutions')}
      />

      {/* Recommended Emissions Actions */}
      <div className="space-y-4">
        <h3 className="text-base font-extrabold text-slate-900">Recommended Decarbonization Interventions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              icon: Factory,
              title: 'Boiler Flue Gas Waste Heat Economizer',
              problem: 'High flue stack temperatures dumping heat rather than pre-heating boiler feedwater.',
              impact: 'Saves 7,400 L boiler fuel/yr • 19.8 MT CO₂e abated',
              cost: '₹6.5L – ₹8.5L',
              payback: '2.5 Years',
            },
            {
              icon: Layers,
              title: 'Biomass Briquette Boiler Conversion Assessment',
              problem: 'High carbon intensity of fossil diesel boiler operations.',
              impact: 'Replaces fossil diesel with carbon-neutral agricultural briquettes',
              cost: '₹14.0L – ₹18.0L',
              payback: '3.1 Years',
            },
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4"
              >
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-800 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{item.title}</h4>
                    <p className="text-xs text-slate-600 mt-0.5">{item.problem}</p>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-600">Est. Investment</p>
                    <p className="font-bold text-slate-900">{item.cost}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-emerald-50">
                    <p className="text-[10px] text-emerald-800">Payback</p>
                    <p className="font-bold text-emerald-700">{item.payback}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-600">Abatement</p>
                    <p className="font-bold text-slate-700">Verified Lever</p>
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
