import React from 'react';
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
import { AIInsightCard } from '../components/common/AIInsightCard';
import { DemoTag } from '../components/common/StatusBadge';
import { WASTE_COMPOSITION_DATA } from '../services/mockData';
import { PageId } from '../types';

interface WastePageProps {
  onNavigate: (page: PageId) => void;
}

export const WastePage: React.FC<WastePageProps> = ({ onNavigate }) => {
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
            <DemoTag />
          </div>
          <p className="text-xs text-slate-600">
            Material scrap monitoring, circular recovery, downcycling contracts, and landfill diversion.
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

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Monthly Waste"
          value="7,200"
          unit="kg / mo"
          icon={Trash2}
          iconBgColor="bg-slate-100"
          iconColor="text-slate-700"
          helperText="Aggregated solids & material scrap"
        />

        <MetricCard
          title="Recyclable Scrap"
          value="4,970"
          unit="kg / mo"
          icon={Recycle}
          iconBgColor="bg-emerald-50"
          iconColor="text-emerald-600"
          helperText="Fabric clips, packaging, cardboard"
        />

        <MetricCard
          title="Non-Recyclable Waste"
          value="2,230"
          unit="kg / mo"
          icon={TrendingDown}
          iconBgColor="bg-rose-50"
          iconColor="text-rose-600"
          badge="Landfill Risk"
          badgeColor="bg-rose-100 text-rose-800"
          helperText="Dye sludge & contaminated residues"
        />

        <MetricCard
          title="Current Recycling Rate"
          value="22%"
          unit="of Total"
          icon={Sparkles}
          iconBgColor="bg-amber-50"
          iconColor="text-amber-600"
          badge="Improvement Target: 65%"
          badgeColor="bg-emerald-100 text-emerald-800"
          helperText="Opportunity to monetize sorted scrap"
        />
      </div>

      {/* Waste Composition & Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Pie Chart */}
        <div className="lg:col-span-6 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">
              Monthly Waste Stream Composition (kg)
            </h3>
            <p className="text-xs text-slate-600">
              Fabric clipping waste makes up 50% of total facility solid waste output.
            </p>
          </div>

          <div className="h-64 w-full flex items-center justify-center my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={WASTE_COMPOSITION_DATA}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {WASTE_COMPOSITION_DATA.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                  formatter={(val: any) => [`${Number(val).toLocaleString()} kg`, 'Volume']}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
            {WASTE_COMPOSITION_DATA.map((item) => (
              <div key={item.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.fill }} />
                  <span className="text-slate-700 font-medium">{item.name}</span>
                </div>
                <span className="font-bold text-slate-900">{item.value.toLocaleString()} kg</span>
              </div>
            ))}
          </div>
        </div>

        {/* Circular Economy Opportunity Breakdown */}
        <div className="lg:col-span-6 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-extrabold text-slate-900">
                Circular Monetization & Landfill Avoidance
              </h3>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                +₹3.2L / yr Scrap Revenue
              </span>
            </div>

            <p className="text-xs text-slate-600 mb-4 leading-relaxed">
              Currently, ABC Textile pays landfill clearing haulers ₹42,000/month. Segregating clean
              cotton clips and compressing them with a hydraulic baler turns an expense into high-value
              feedstock for recycled yarn spinners.
            </p>

            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">1. Cotton & Synthetic Off-Cuts</span>
                  <span className="text-xs font-bold text-emerald-700">3,600 kg / mo</span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">
                  Route to mechanical shredders for automotive insulation, acoustics, and recycled yarn.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">2. Low-Density Polyethylene Film</span>
                  <span className="text-xs font-bold text-emerald-700">950 kg / mo</span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">
                  100% pelletizable via registered local recyclers for blow-molded industrial sheets.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">3. ETP Chemical Cake Sludge</span>
                  <span className="text-xs font-bold text-amber-700">1,850 kg / mo</span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">
                  Co-processing tie-up with local cement kiln for fuel substitute rather than secured landfill.
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => onNavigate('solutions')}
            className="w-full mt-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors"
          >
            <span>Review Textile Scrap Recovery Solution</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* AI Insight */}
      <AIInsightCard
        title="AI Circular Material Forecast"
        insight="By deploying an automated hydraulic baler and formalizing contracts with verified circular yarn spinners, ABC Textile can boost landfill diversion from 22% to 66%, yielding ₹3,20,000 annually in scrap revenue while avoiding landfill dump fees."
        actionText="View Fabric Recovery Intervention"
        onActionClick={() => onNavigate('solutions')}
      />

      {/* Recommended Waste Actions */}
      <div className="space-y-4">
        <h3 className="text-base font-extrabold text-slate-900">Recommended Circular Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              icon: Layers,
              title: 'Textile Fabric Off-Cut Circular Recovery & Baling',
              problem: '3.6 tonnes of yarn & clipping scrap disposed via unorganized low-recovery channels.',
              impact: '28.5 tonnes/yr diverted • ₹3,20,000 scrap earnings',
              cost: '₹3.8L – ₹5.2L',
              payback: '1.4 Years',
            },
            {
              icon: Recycle,
              title: 'Source Waste Color-Coded Segregation Bins',
              problem: 'Mixing plastic films with soiled rags diminishes scrap valuation.',
              impact: 'Prevents 100% cross-contamination on cutting floors',
              cost: '₹60,000 – ₹90,000',
              payback: '0.4 Years',
            },
          ].map((act, idx) => {
            const Icon = act.icon;
            return (
              <div
                key={idx}
                className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4"
              >
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0">
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
                    <p className="text-[10px] text-slate-600">Landfill Divert</p>
                    <p className="font-bold text-emerald-700">High Impact</p>
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
