import React, { useEffect, useState } from 'react';
import {
  Droplets,
  AlertTriangle,
  RotateCcw,
  CloudRain,
  ArrowRight,
  TrendingDown,
  ShieldCheck,
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
import { getWaterAnalytics } from '../services/api';
import { MONTHLY_WATER_DATA } from '../services/mockData';
import { PageId } from '../types';

interface WaterPageProps {
  onNavigate: (page: PageId) => void;
}

export const WaterPage: React.FC<WaterPageProps> = ({ onNavigate }) => {
  const [analytics, setAnalytics] = useState<any>(null);
  useEffect(()=> { getWaterAnalytics().then(setAnalytics).catch(()=>{}); }, []);
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
            <DemoTag label={analytics ? "Live Backend Data" : "Illustrative"} />
          </div>
          <p className="text-xs text-slate-600">
            Freshwater borewell extraction, pipe leakage risks, and closed-loop ultrafiltration.
          </p>
        </div>

        <button
          onClick={() => onNavigate('simulator')}
          className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Simulate Water RO</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Monthly Water Consumption"
          value="4,80,000"
          unit="Litres / mo"
          icon={Droplets}
          iconBgColor="bg-cyan-50"
          iconColor="text-cyan-600"
          helperText="16,000 L / day average draw"
        />

        <MetricCard
          title="Estimated Water Cost"
          value="₹1,24,000"
          unit="/ mo"
          icon={TrendingDown}
          iconBgColor="bg-slate-100"
          iconColor="text-slate-700"
          helperText="Pumping power + tanker charges"
        />

        <MetricCard
          title="Recycling Status"
          value="0%"
          unit="Closed Loop"
          icon={RotateCcw}
          iconBgColor="bg-rose-50"
          iconColor="text-rose-600"
          badge="Urgent Gap"
          badgeColor="bg-rose-100 text-rose-800"
          helperText="100% single-pass effluent discharge"
        />

        <MetricCard
          title="Leakage Risk"
          value="High"
          unit="Monthly Events"
          icon={AlertTriangle}
          iconBgColor="bg-amber-50"
          iconColor="text-amber-600"
          badge="~40k L Lost"
          badgeColor="bg-amber-100 text-amber-800"
          helperText="Distribution line pressure drops"
        />
      </div>

      {/* Water Risk Visualization Box */}
      <div className="bg-gradient-to-br from-rose-50/60 via-amber-50/40 to-slate-50 border border-rose-200/80 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2.5">
          <AlertTriangle className="w-5 h-5 text-rose-600" />
          <h3 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider">
            Water Stress & Regulatory Risk Profile
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-white border border-rose-100 shadow-2xs space-y-1">
            <span className="text-xs font-bold text-slate-800">Groundwater Table Depletion</span>
            <p className="text-xs text-slate-600 leading-relaxed">
              Tirupur cluster groundwater depth has deepened by 4.2m over 5 years. Local authorities
              require commercial water audits for textile units extracting &gt;300 kL/mo.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-amber-100 shadow-2xs space-y-1">
            <span className="text-xs font-bold text-slate-800">Effluent Discharge Compliance</span>
            <p className="text-xs text-slate-600 leading-relaxed">
              Discharging primary treated dye bath wastewater risks environmental notices. Transition
              to closed-loop ultrafiltration ensures 100% zero-penalty operation.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-cyan-100 shadow-2xs space-y-1">
            <span className="text-xs font-bold text-slate-800">Freshwater Financial Savings</span>
            <p className="text-xs text-slate-600 leading-relaxed">
              Recycling 65% of rinse waters eliminates tanker dependence in dry months and saves an
              estimated ₹6,40,000 annually in pumping and chemical costs.
            </p>
          </div>
        </div>
      </div>

      {/* Main Consumption & Leakage Chart */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">
              Monthly Water Extraction vs Estimated Leakage Loss (Litres)
            </h3>
            <p className="text-xs text-slate-600">
              Blue represents total pumped water; pink represents estimated unmetered distribution loss.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            Source: Groundwater Borewells
          </span>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={MONTHLY_WATER_DATA} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                  name === 'totalLitres' ? 'Pumped Volume' : 'Leakage Loss',
                ]}
              />
              <Bar dataKey="totalLitres" fill="#0284c7" name="Total Water" radius={[4, 4, 0, 0]} />
              <Bar dataKey="leakedEstimateLitres" fill="#fb7185" name="Leakage Loss" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AI Water Insight */}
      <AIInsightCard
        title="AI Water Optimization Analysis"
        insight="Water extraction is ABC Textile's highest environmental vulnerability. 65% of your water is discarded after single dyeing cycles. Installing multi-stage ultrafiltration with reverse osmosis will recycle 3.74 million litres annually with a 3.8-year payback."
        actionText="View Closed-Loop Water Recycling Solution"
        onActionClick={() => onNavigate('solutions')}
      />

      {/* Recommended Water Actions */}
      <div className="space-y-4">
        <h3 className="text-base font-extrabold text-slate-900">Recommended Water Interventions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              icon: RotateCcw,
              title: 'Closed-Loop Ultrafiltration & RO Recycling',
              problem: 'Single-pass fabric rinse baths discarded to primary settling ponds.',
              impact: 'Recycles 65% water • Saves 37.4 Lakh litres / yr',
              cost: '₹22.0L – ₹29.0L',
              payback: '3.8 Years',
            },
            {
              icon: ShieldCheck,
              title: 'Smart Ultrasonic Leak Sensors & Flow Telemetry',
              problem: 'Unnoticed underground distribution pipe leaks losing ~40k L/mo.',
              impact: 'Cuts 4,20,000 L leak loss • Immediate payback',
              cost: '₹2.2L – ₹3.5L',
              payback: '1.6 Years',
            },
            {
              icon: CloudRain,
              title: 'Rooftop Rainwater Harvesting & Recharge Well',
              problem: 'Zero rainwater collection from 38,000 sq ft factory roof sheds.',
              impact: 'Recharges 9,80,000 L water / yr back into aquifer',
              cost: '₹4.5L – ₹6.0L',
              payback: '2.8 Years',
            },
            {
              icon: Droplets,
              title: 'Low-Liquor-Ratio Dyeing Machine Nozzle Kits',
              problem: 'High liquor bath ratios (1:10) consuming excess water & chemicals.',
              impact: 'Reduces batch dye water use by 22%',
              cost: '₹3.8L – ₹5.0L',
              payback: '2.1 Years',
            },
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs hover:border-slate-300 transition-all flex flex-col justify-between space-y-4"
              >
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-cyan-50 text-cyan-700 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{item.title}</h4>
                    <p className="text-xs text-slate-600 mt-0.5">{item.problem}</p>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-600">Est. Cost</p>
                    <p className="font-bold text-slate-900">{item.cost}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-emerald-50">
                    <p className="text-[10px] text-emerald-800">Payback</p>
                    <p className="font-bold text-emerald-700">{item.payback}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-600">Impact</p>
                    <p className="font-bold text-slate-700">Significant</p>
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
