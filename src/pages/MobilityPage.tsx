import React, { useEffect, useState } from 'react';
import {
  Truck,
  Fuel,
  Zap,
  Navigation,
  ArrowRight,
  TrendingDown,
  Clock,
} from 'lucide-react';
import { MetricCard } from '../components/common/MetricCard';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { DemoTag } from '../components/common/StatusBadge';
import { getMobilityAnalytics } from '../services/api';
import { MOBILITY_EFFICIENCY_DATA } from '../services/mockData';
import { PageId } from '../types';

interface MobilityPageProps {
  onNavigate: (page: PageId) => void;
}

export const MobilityPage: React.FC<MobilityPageProps> = ({ onNavigate }) => {
  const [analytics, setAnalytics] = useState<any>(null);
  useEffect(()=> { getMobilityAnalytics().then(setAnalytics).catch(()=>{}); }, []);
  return (
    <div className="space-y-8 max-w-6xl pb-16">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center">
              <Truck className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Mobility & Commercial Logistics Decarbonization
            </h2>
            <DemoTag label={analytics ? "Live Backend Data" : "Illustrative"} />
          </div>
          <p className="text-xs text-slate-600">
            Intra-city dispatch fleet, route grouping algorithms, and commercial EV transition roadmap.
          </p>
        </div>

        <button
          onClick={() => onNavigate('solutions')}
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Commercial EV Fleet</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Fleet Size"
          value="8"
          unit="Commercial Vans"
          icon={Truck}
          iconBgColor="bg-indigo-50"
          iconColor="text-indigo-600"
          helperText="All diesel light commercial vehicles"
        />

        <MetricCard
          title="Monthly Fuel Consumption"
          value="1,950"
          unit="Litres / mo"
          icon={Fuel}
          iconBgColor="bg-rose-50"
          iconColor="text-rose-600"
          helperText="₹1.85 Lakh monthly fuel spend"
        />

        <MetricCard
          title="Mobility Emissions"
          value="5.2"
          unit="MT CO₂e / mo"
          icon={TrendingDown}
          iconBgColor="bg-slate-100"
          iconColor="text-slate-700"
          helperText="Tailpipe greenhouse gas & soot"
        />

        <MetricCard
          title="EV Fleet Adoption"
          value="0%"
          unit="Electric"
          icon={Zap}
          iconBgColor="bg-amber-50"
          iconColor="text-amber-600"
          badge="High EV Potential"
          badgeColor="bg-emerald-100 text-emerald-800"
          helperText="Urban routes ideal for 120km range"
        />
      </div>

      {/* Vehicle Fleet Efficiency Table */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">
              Vehicle Dispatch Efficiency Telemetry
            </h3>
            <p className="text-xs text-slate-600">
              Audit reveals low average fuel efficiency (8.0 – 9.4 km/L) across intra-cluster textile shuttles.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            Cluster Dispatch Radius: ~45 km
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-bold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Vehicle Identifier</th>
                <th className="py-3 px-4">Monthly Mileage</th>
                <th className="py-3 px-4">Fuel Burned</th>
                <th className="py-3 px-4">Avg Efficiency</th>
                <th className="py-3 px-4">EV Replacement Feasibility</th>
                <th className="py-3 px-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {MOBILITY_EFFICIENCY_DATA.map((v) => (
                <tr key={v.vehicle} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3 px-4 font-semibold text-slate-900">{v.vehicle}</td>
                  <td className="py-3 px-4 text-slate-700 font-medium">{v.mileageKm.toLocaleString()} km</td>
                  <td className="py-3 px-4 text-slate-700 font-medium">{v.litresUsed} L</td>
                  <td className="py-3 px-4 font-mono font-bold text-slate-800">{v.kmPerLitre} km/L</td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                        v.evPotential === 'High'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {v.evPotential} EV Feasibility
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <button
                      onClick={() => onNavigate('solutions')}
                      className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 hover:underline"
                    >
                      View EV Spec
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI Insight Card */}
      <AIInsightCard
        title="AI Fleet Decarbonization Observation"
        insight="All 8 delivery vans operate within a 45 km radius inside the Tirupur garment cluster, returning to depot nightly. This operational pattern is ideal for Phase 1 Commercial EV Van Transition, which would eliminate 9,200 litres of diesel per year with daytime solar depot charging."
        actionText="Review EV Fleet Transition Solution"
        onActionClick={() => onNavigate('solutions')}
      />

      {/* Recommended Mobility Actions */}
      <div className="space-y-4">
        <h3 className="text-base font-extrabold text-slate-900">Recommended Mobility Interventions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              icon: Zap,
              title: 'Commercial EV Cargo Van Transition (Phase 1)',
              problem: 'High recurring diesel bills and tailpipe emissions from intra-cluster hub runs.',
              impact: 'Replaces 4 diesel vans • Cuts 9,200 L fuel/yr',
              cost: '₹18.0L – ₹24.0L',
              payback: '4.2 Years',
            },
            {
              icon: Navigation,
              title: 'AI Delivery Route Dispatch & Load Optimization',
              problem: 'Sub-optimal delivery routing and partial-load empty return trips.',
              impact: 'Saves 3,100 L fuel/yr • ₹1,45,000 annual saving',
              cost: '₹80,000 – ₹1.5L',
              payback: '0.8 Years',
            },
            {
              icon: Clock,
              title: 'Shared Cluster Logistics Pool Program',
              problem: 'Multiple suppliers sending single partial-load vans to same port CFS.',
              impact: 'Consolidates 25% of outward fabric dispatches',
              cost: '₹40,000 onboarding',
              payback: 'Immediate',
            },
            {
              icon: Fuel,
              title: 'Depot Level Smart EV Chargers (11 kW)',
              problem: 'Lack of on-site depot vehicle charging infrastructure.',
              impact: 'Enables night & noon solar fleet top-ups',
              cost: '₹1.8L – ₹2.5L',
              payback: '2.0 Years',
            },
          ].map((act, idx) => {
            const Icon = act.icon;
            return (
              <div
                key={idx}
                className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4"
              >
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center shrink-0">
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
                    <p className="text-[10px] text-slate-600">ROI Speed</p>
                    <p className="font-bold text-slate-700">High</p>
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
