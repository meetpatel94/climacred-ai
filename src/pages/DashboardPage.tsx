import React, { useEffect, useState } from 'react';
import {
  Zap,
  Droplets,
  Trash2,
  CloudFog,
  Truck,
  ArrowRight,
  Building2,
  Clock,
  ChevronRight,
  Activity,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { MetricCard } from '../components/common/MetricCard';
import { ImpactBadge, DemoTag } from '../components/common/StatusBadge';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { AIClimateIntelligence } from '../components/common/AIClimateIntelligence';
import { MONTHLY_ENERGY_DATA, MONTHLY_WATER_DATA } from '../services/mockData';
import { PageId } from '../types';
import { getClimateFingerprint, getClimateAssessment, getBusinessProfile } from '../services/api';
import { ClimateFingerprint, ClimateAssessmentData, BusinessProfile } from '../types';

interface DashboardPageProps {
  onNavigate: (page: PageId) => void;
}

// Local-time greeting shown at the top of the dashboard
const getGreeting = (): string => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good Morning';
  if (hour < 17) return 'Good Afternoon';
  return 'Good Evening';
};

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [fingerprint, setFingerprint] = useState<ClimateFingerprint | null>(null);
  const [assessment, setAssessment] = useState<ClimateAssessmentData | null>(null);
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const greeting = getGreeting();

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [fp, ass, prof] = await Promise.all([
          getClimateFingerprint(),
          getClimateAssessment(),
          getBusinessProfile(),
        ]);
        if (!cancelled) {
          setFingerprint(fp);
          setAssessment(ass);
          setProfile(prof);
        }
      } catch (e) {
        console.warn('Dashboard load failed', e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const overallScore = fingerprint?.overallScore ?? 58;
  const scoreLabel = fingerprint?.scoreLabel ?? 'Transition Stage';
  const topGaps = fingerprint?.topImprovementDimensions?.slice(0,2).join(' & ') || 'Water & Power';
  const energyKwh = assessment?.energy.monthlyElectricityKwh ?? 38500;
  const energyCost = assessment?.energy.monthlyElectricityBillInr ?? 346500;
  const waterLitres = assessment?.water.monthlyWaterLitres ?? 480000;
  const wasteKg = assessment?.waste.textileMaterialWasteKgPerMonth ?? 3600;
  const recyclingPct = assessment?.waste.currentRecyclingPercent ?? 22;
  const emissionsTonnes = 41.2; // could derive from emissions analytics if available
  const fuelLitres = assessment?.mobility.monthlyFleetFuelLitres ?? 1950;
  const vehicleCount = assessment?.mobility.deliveryVehiclesCount ?? 8;
  const facility = profile?.facilityAreaSqFt ?? 38000;
  const employees = profile?.employees ?? 145;
  const businessName = profile?.name ?? 'ABC Textile Manufacturing Ltd.';
  const businessLocation = profile?.location ?? 'Tirupur Cluster, TN';

  if (loading) {
    return (
      <div className="space-y-8 pb-12 animate-pulse">
        <div className="h-32 bg-slate-100 rounded-2xl" />
        <div className="grid grid-cols-5 gap-4">
          {[1,2,3,4,5].map(i => <div key={i} className="h-24 bg-slate-100 rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-12">
      {/* Top Banner: Organization Context & Readiness Indicator */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-slate-600" />
              Active Facility
            </span>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
              Textile & Garment Dyeing
            </span>
            <DemoTag />
          </div>

          <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
            {greeting}, {businessName}
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 max-w-2xl">
            {businessLocation} • {employees} Employees • {facility.toLocaleString()} sq.ft facility • Climate Readiness: {overallScore}/100
          </p>
        </div>

        {/* Climate Readiness Score Widget */}
        <div className="flex items-center gap-4 bg-slate-50 border border-slate-200/80 p-4 rounded-xl shrink-0 w-full sm:w-auto justify-between sm:justify-start">
          <div className="relative w-16 h-16 flex items-center justify-center">
            {/* SVG Circular Ring */}
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="32" cy="32" r="26" stroke="#e2e8f0" strokeWidth="6" fill="transparent" />
              <circle
                cx="32"
                cy="32"
                r="26"
                stroke="#10b981"
                strokeWidth="6"
                fill="transparent"
                strokeDasharray={163.36}
                strokeDashoffset={163.36 * (1 - overallScore / 100)}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-lg font-black text-slate-900 leading-none">{overallScore}</span>
              <span className="text-[9px] font-bold text-slate-600">/100</span>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-900">Climate Readiness</span>
              <span className="text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded">
                {scoreLabel}
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-0.5">Top gap: {topGaps}</p>
            <button
              onClick={() => onNavigate('fingerprint')}
              className="text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline mt-1 inline-flex items-center gap-1"
            >
              <span>Explore Fingerprint</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* 5 Core Resource Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Energy Impact"
          value={energyKwh.toLocaleString()}
          unit="kWh/mo"
          icon={Zap}
          iconBgColor="bg-amber-50"
          iconColor="text-amber-600"
          badge="High"
          badgeColor="bg-orange-50 text-orange-700 border border-orange-200"
          helperText={`₹${(energyCost/100000).toFixed(2)}L monthly grid bill`}
        />

        <MetricCard
          title="Water Impact"
          value={waterLitres.toLocaleString()}
          unit="L/mo"
          icon={Droplets}
          iconBgColor="bg-cyan-50"
          iconColor="text-cyan-600"
          badge="Very High"
          badgeColor="bg-rose-50 text-rose-700 border border-rose-200"
          helperText="Groundwater extraction stress"
        />

        <MetricCard
          title="Waste Impact"
          value={wasteKg.toLocaleString()}
          unit="kg/mo"
          icon={Trash2}
          iconBgColor="bg-emerald-50"
          iconColor="text-emerald-600"
          badge="High"
          badgeColor="bg-orange-50 text-orange-700 border border-orange-200"
          helperText={`${recyclingPct}% currently recycled`}
        />

        <MetricCard
          title="Emissions Impact"
          value={emissionsTonnes.toString()}
          unit="MT CO₂e"
          icon={CloudFog}
          iconBgColor="bg-slate-100"
          iconColor="text-slate-700"
          badge="Med-High"
          badgeColor="bg-amber-50 text-amber-700 border border-amber-200"
          helperText="Scope 1 & 2 emissions"
        />

        <MetricCard
          title="Mobility Impact"
          value={fuelLitres.toLocaleString()}
          unit="L Fuel"
          icon={Truck}
          iconBgColor="bg-indigo-50"
          iconColor="text-indigo-600"
          badge="Medium"
          badgeColor="bg-slate-100 text-slate-700 border border-slate-200"
          helperText={`${vehicleCount} active diesel delivery vans`}
        />
      </div>

      {/* AI Climate Intelligence - auto-loads from the latest stored data */}
      <AIClimateIntelligence onNavigate={onNavigate} />

      {/* Top Climate Priorities & Next Step Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recommended Next Step Card */}
        <div className="lg:col-span-7 bg-gradient-to-br from-emerald-900 via-teal-950 to-slate-900 text-white rounded-2xl p-6 shadow-md flex flex-col justify-between relative overflow-hidden">
          <div className="relative z-10 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-emerald-400" />
                Recommended Next Step
              </span>
              <span className="text-xs font-mono font-semibold bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/30">
                Assessment 68%
              </span>
            </div>

            <h3 className="text-lg sm:text-xl font-extrabold text-white">
              Complete your Climate Assessment to generate a personalized Green Transformation Plan.
            </h3>

            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-xl">
              We have completed your Energy and Water profiles. Finalizing waste stream composition
              and diesel backup hours unlocks machine-grade ROI estimates for solar and water
              recycling.
            </p>

            {/* Progress bar */}
            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between text-xs font-semibold text-slate-300">
                <span>Assessment Completion</span>
                <span className="text-emerald-300">68%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full w-[68%]" />
              </div>
            </div>
          </div>

          <div className="pt-6 relative z-10 flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigate('assessment')}
              className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-md transition-all flex items-center gap-2"
            >
              <span>Continue Assessment</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onNavigate('simulator')}
              className="px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white font-semibold text-xs border border-white/20 transition-all"
            >
              Simulate Green ROI
            </button>
          </div>
        </div>

        {/* Top 3 Climate Priorities */}
        <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-600" />
                Top Climate Priorities
              </h3>
              <span className="text-[11px] font-semibold text-slate-600">Urgency Ranked</span>
            </div>

            <div className="space-y-3">
              {[
                {
                  rank: '1',
                  title: 'Water Management',
                  desc: '480,000 L/mo freshwater extraction with 0% recycling and recurring dye rinse waste.',
                  impact: 'Very High',
                  page: 'water',
                },
                {
                  rank: '2',
                  title: 'Energy Efficiency',
                  desc: 'High daytime thermal grid draw without solar offset; old pump motors lack VFDs.',
                  impact: 'High',
                  page: 'energy',
                },
                {
                  rank: '3',
                  title: 'Waste Reduction',
                  desc: '3.6 tonnes fabric scrap unsegregated; circular yarn recovery channel missing.',
                  impact: 'High',
                  page: 'waste',
                },
              ].map((item) => (
                <div
                  key={item.rank}
                  onClick={() => onNavigate(item.page as PageId)}
                  className="p-3 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-100 hover:border-slate-200 transition-all cursor-pointer flex items-start justify-between gap-3 group"
                >
                  <div className="flex items-start gap-3">
                    <span className="w-6 h-6 rounded-lg bg-white border border-slate-200 text-slate-800 font-bold text-xs flex items-center justify-center shrink-0">
                      {item.rank}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-bold text-slate-900 group-hover:text-emerald-800">
                          {item.title}
                        </p>
                        <ImpactBadge level={item.impact as any} size="sm" />
                      </div>
                      <p className="text-[11px] text-slate-600 mt-0.5 line-clamp-1">{item.desc}</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-slate-700 shrink-0 mt-1" />
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => onNavigate('fingerprint')}
            className="w-full mt-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center justify-center gap-1.5 transition-colors"
          >
            <span>View Full Diagnostic Breakdown</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Energy Consumption */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-slate-900">Monthly Energy Consumption (kWh)</h4>
              <p className="text-xs text-slate-600">Grid electricity trend vs. 28,000 kWh target</p>
            </div>
            <button
              onClick={() => onNavigate('energy')}
              className="text-xs font-semibold text-emerald-700 hover:underline flex items-center gap-1"
            >
              <span>Details</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MONTHLY_ENERGY_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorEnergy" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <Tooltip
                  formatter={(val: any) => [`${Number(val).toLocaleString()} kWh`, 'Consumption']}
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="consumptionKwh" stroke="#d97706" strokeWidth={2.5} fill="url(#colorEnergy)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Monthly Water Consumption */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-slate-900">Monthly Water Extraction (Litres)</h4>
              <p className="text-xs text-slate-600">Freshwater borewell volume and estimated pipe leak loss</p>
            </div>
            <button
              onClick={() => onNavigate('water')}
              className="text-xs font-semibold text-cyan-700 hover:underline flex items-center gap-1"
            >
              <span>Details</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MONTHLY_WATER_DATA} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <YAxis
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  stroke="#cbd5e1"
                  tickFormatter={(v) => `${v / 1000}kL`}
                />
                <Tooltip
                  formatter={(val: any, name: any) => [
                    `${Number(val).toLocaleString()} L`,
                    name === 'totalLitres' ? 'Total Water' : 'Leak Loss Est.',
                  ]}
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="totalLitres" fill="#0284c7" radius={[4, 4, 0, 0]} />
                <Bar dataKey="leakedEstimateLitres" fill="#fb7185" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* AI Intelligence Notification */}
      <AIInsightCard
        title="ClimaCred AI Priority Assessment"
        insight="Your factory currently extracts 480,000 litres of groundwater monthly with zero closed-loop recycling. Combining ultrafiltration water recycling with rooftop solar would reduce recurring operational utility spend by ₹1,74,000 per month."
        actionText="Simulate combined solar + water scenario"
        onActionClick={() => onNavigate('simulator')}
      />
    </div>
  );
};
