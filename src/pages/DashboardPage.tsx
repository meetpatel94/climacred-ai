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
  ClipboardList,
  TrendingUp,
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
import { ImpactBadge } from '../components/common/StatusBadge';
import { AIClimateIntelligence } from '../components/common/AIClimateIntelligence';
import { EmptyState } from '../components/common/EmptyState';
import { EMPTY_STATES, formatInrCompact, formatNumber } from '../services/defaults';
import { BusinessProfile, ClimateAssessmentData, ClimateFingerprint, PageId } from '../types';
import { getClimateFingerprintHistory, getEmissionsAnalytics, FingerprintSnapshot } from '../services/api';

interface DashboardPageProps {
  onNavigate: (page: PageId) => void;
  profile: BusinessProfile | null;
  assessment: ClimateAssessmentData | null;
  fingerprint: ClimateFingerprint | null;
}

// Local-time greeting shown at the top of the dashboard
const getGreeting = (): string => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good Morning';
  if (hour < 17) return 'Good Afternoon';
  return 'Good Evening';
};

const hasValue = (value: unknown): boolean => value !== null && value !== undefined && !Number.isNaN(Number(value));

/** One row of a resource trend chart, built from stored fingerprint snapshots. */
interface TrendRow {
  month: string;
  value: number;
}

const buildTrend = (snapshots: FingerprintSnapshot[], dimension: string, metricKey: string): TrendRow[] => {
  const rows: TrendRow[] = [];
  snapshots.forEach((snapshot) => {
    const value = snapshot.dimension_metrics?.[dimension]?.[metricKey];
    if (!hasValue(value)) return;
    const label = snapshot.created_at
      ? new Date(snapshot.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      : `#${rows.length + 1}`;
    rows.push({ month: label, value: Number(value) });
  });
  return rows;
};

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate, profile, assessment, fingerprint }) => {
  const [snapshots, setSnapshots] = useState<FingerprintSnapshot[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  // Calculated emissions (backend analytics); stays null until the backend has stored data
  const [emissionsTonnes, setEmissionsTonnes] = useState<number | null>(null);
  const greeting = getGreeting();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const history = await getClimateFingerprintHistory(12);
      if (!cancelled) {
        setSnapshots(history);
        setLoadingHistory(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const analytics = await getEmissionsAnalytics();
      if (!cancelled) {
        const total = analytics?.available === false
          ? null
          : analytics?.emissions_breakdown_tonnes_co2e_per_month?.total ?? null;
        setEmissionsTonnes(hasValue(total) ? Number(total) : null);
      }
    })();
    return () => { cancelled = true; };
  }, [assessment]);

  const hasBusinessData = Boolean(profile?.name) || Boolean(assessment);
  const businessName = profile?.name || null;
  const location = profile?.location || null;
  const employees = profile?.employees ?? null;
  const facility = profile?.facilityAreaSqFt ?? null;

  const overallScore = fingerprint?.overallScore ?? null;
  const scoreLabel = fingerprint?.scoreLabel || null;
  const topGaps = fingerprint?.topImprovementDimensions?.slice(0, 2) || [];

  // Data-quality / completeness of the store climate assessment (real calculation)
  const [dataQuality, setDataQuality] = useState<{ completeness_percent: number | null; level: string | null }>({
    completeness_percent: null,
    level: null,
  });
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { getDataQuality } = await import('../services/api');
      const quality = await getDataQuality();
      if (!cancelled && quality && quality.available !== false) {
        setDataQuality({
          completeness_percent: quality.completeness_percent ?? null,
          level: quality.level ?? null,
        });
      }
    })();
    return () => { cancelled = true; };
  }, [assessment]);

  const completeness = dataQuality.completeness_percent;
  const topPriorities = (fingerprint?.dimensions || [])
    .slice()
    .sort((a, b) => a.score - b.score)
    .slice(0, 3);

  const energyTrend = buildTrend(snapshots, 'Energy', 'monthly_kwh');
  const waterTrend = buildTrend(snapshots, 'Water', 'monthly_litres');

  if (loadingHistory && !hasBusinessData) {
    return (
      <div className="space-y-8 pb-12 animate-pulse">
        <div className="h-32 bg-slate-100 rounded-2xl" />
        <div className="grid grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-24 bg-slate-100 rounded-xl" />)}
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
              {hasBusinessData ? 'Active Facility' : 'Your Facility'}
            </span>
            {profile?.industry && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                {profile.industry}
              </span>
            )}
          </div>

          <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
            {greeting}
            {businessName ? `, ${businessName}` : ''}
          </h2>

          {hasBusinessData ? (
            <p className="text-xs sm:text-sm text-slate-600 max-w-2xl">
              {[
                location,
                employees !== null ? `${employees} Employees` : null,
                facility !== null ? `${facility.toLocaleString()} sq.ft facility` : null,
                overallScore !== null ? `Climate Readiness: ${overallScore}/100` : null,
              ]
                .filter(Boolean)
                .join(' • ')}
            </p>
          ) : (
            <p className="text-xs sm:text-sm text-slate-600 max-w-2xl">{EMPTY_STATES.dashboard}</p>
          )}
        </div>

        {/* Climate Readiness Score Widget - only shown when a real score exists */}
        <div className="flex items-center gap-4 bg-slate-50 border border-slate-200/80 p-4 rounded-xl shrink-0 w-full sm:w-auto justify-between sm:justify-start">
          {overallScore !== null ? (
            <>
              <div className="relative w-16 h-16 flex items-center justify-center">
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
                  {scoreLabel && (
                    <span className="text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded">
                      {scoreLabel}
                    </span>
                  )}
                </div>
                {topGaps.length > 0 && <p className="text-xs text-slate-600 mt-0.5">Top gap: {topGaps.join(' & ')}</p>}
                <button
                  onClick={() => onNavigate('fingerprint')}
                  className="text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline mt-1 inline-flex items-center gap-1"
                >
                  <span>Explore Fingerprint</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </>
          ) : (
            <div className="space-y-2">
              <p className="text-xs font-bold text-slate-900">Climate Readiness</p>
              <p className="text-xs text-slate-600 max-w-[260px]">{EMPTY_STATES.fingerprint}</p>
              <button
                onClick={() => onNavigate('assessment')}
                className="text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline inline-flex items-center gap-1"
              >
                <span>Complete Climate Assessment</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 5 Core Resource Metric Cards - each renders its own empty state */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Energy Impact"
          value={formatNumber(assessment?.energy.monthlyElectricityKwh) ?? '—'}
          unit={hasValue(assessment?.energy.monthlyElectricityKwh) ? 'kWh/mo' : undefined}
          icon={Zap}
          iconBgColor="bg-amber-50"
          iconColor="text-amber-600"
          helperText={
            formatInrCompact(assessment?.energy.monthlyElectricityBillInr)
              ? `${formatInrCompact(assessment?.energy.monthlyElectricityBillInr)} monthly grid bill`
              : EMPTY_STATES.energy
          }
        />

        <MetricCard
          title="Water Impact"
          value={formatNumber(assessment?.water.monthlyWaterLitres) ?? '—'}
          unit={hasValue(assessment?.water.monthlyWaterLitres) ? 'L/mo' : undefined}
          icon={Droplets}
          iconBgColor="bg-cyan-50"
          iconColor="text-cyan-600"
          helperText={
            hasValue(assessment?.water.monthlyWaterLitres)
              ? 'Your reported monthly freshwater use'
              : EMPTY_STATES.water
          }
        />

        <MetricCard
          title="Waste Impact"
          value={formatNumber(assessment?.waste.textileMaterialWasteKgPerMonth) ?? '—'}
          unit={hasValue(assessment?.waste.textileMaterialWasteKgPerMonth) ? 'kg/mo' : undefined}
          icon={Trash2}
          iconBgColor="bg-emerald-50"
          iconColor="text-emerald-600"
          helperText={
            hasValue(assessment?.waste.currentRecyclingPercent)
              ? `${assessment?.waste.currentRecyclingPercent}% currently recycled`
              : EMPTY_STATES.waste
          }
        />

        <MetricCard
          title="Emissions Impact"
          value={emissionsTonnes !== null ? emissionsTonnes.toFixed(1) : '—'}
          unit={emissionsTonnes !== null ? 'MT CO₂e/mo' : undefined}
          icon={CloudFog}
          iconBgColor="bg-slate-100"
          iconColor="text-slate-700"
          helperText={
            emissionsTonnes !== null
              ? 'Calculated from your reported energy and fuel use'
              : EMPTY_STATES.emissions
          }
        />

        <MetricCard
          title="Mobility Impact"
          value={formatNumber(assessment?.mobility.monthlyFleetFuelLitres) ?? '—'}
          unit={hasValue(assessment?.mobility.monthlyFleetFuelLitres) ? 'L Fuel' : undefined}
          icon={Truck}
          iconBgColor="bg-indigo-50"
          iconColor="text-indigo-600"
          helperText={
            hasValue(assessment?.mobility.deliveryVehiclesCount)
              ? `${assessment?.mobility.deliveryVehiclesCount} delivery vehicles`
              : EMPTY_STATES.mobility
          }
        />
      </div>

      {/* AI Climate Intelligence - auto-loads from the latest stored data */}
      <AIClimateIntelligence onNavigate={onNavigate} />

      {/* Top Climate Priorities & Next Step Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Next step card - driven by the real assessment completeness */}
        <div className="lg:col-span-7 bg-gradient-to-br from-emerald-900 via-teal-950 to-slate-900 text-white rounded-2xl p-6 shadow-md flex flex-col justify-between relative overflow-hidden">
          <div className="relative z-10 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-emerald-400" />
                Recommended Next Step
              </span>
              {completeness !== null && (
                <span className="text-xs font-mono font-semibold bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/30">
                  Assessment {Math.round(completeness)}%
                </span>
              )}
            </div>

            <h3 className="text-lg sm:text-xl font-extrabold text-white">
              {fingerprint
                ? 'Review your worst-performing dimension and convert it into a funded action.'
                : hasBusinessData
                ? 'Complete your Climate Assessment to generate a personalized Green Transformation Plan.'
                : 'Add your business data to begin.'}
            </h3>

            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-xl">
              {fingerprint
                ? `Your latest calculated fingerprint puts ${topGaps.join(' and ') || 'your weakest dimensions'} first. Use the simulator to test cost, payback and carbon outcomes before committing capital.`
                : hasBusinessData
                ? 'Your stored values are used to calculate emissions, the Climate Fingerprint and personalized interventions. Nothing is estimated until you submit data.'
                : 'Nothing has been stored yet. Enter your operational data and ClimaCred will calculate your footprint and recommendations.'}
            </p>

            {completeness !== null && (
              <div className="space-y-1.5 pt-1">
                <div className="flex justify-between text-xs font-semibold text-slate-300">
                  <span>Assessment Completion</span>
                  <span className="text-emerald-300">{Math.round(completeness)}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full"
                    style={{ width: `${Math.min(100, Math.max(0, completeness))}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="pt-6 relative z-10 flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigate(hasBusinessData ? 'assessment' : 'profile')}
              className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-md transition-all flex items-center gap-2"
            >
              <span>{hasBusinessData ? 'Continue Assessment' : 'Add Business Data'}</span>
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

        {/* Top climate priorities - calculated from the stored fingerprint */}
        <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-600" />
                Top Climate Priorities
              </h3>
              {topPriorities.length > 0 && <span className="text-[11px] font-semibold text-slate-600">Urgency Ranked</span>}
            </div>

            {topPriorities.length === 0 ? (
              <EmptyState
                icon={ClipboardList}
                title="No priorities yet"
                message={EMPTY_STATES.fingerprint}
                actionLabel="Complete Climate Assessment"
                onAction={() => onNavigate('assessment')}
              />
            ) : (
              <div className="space-y-3">
                {topPriorities.map((item, index) => (
                  <div
                    key={item.dimension}
                    onClick={() => {
                      const pageMap: Record<string, PageId> = {
                        Energy: 'energy',
                        Water: 'water',
                        Waste: 'waste',
                        Emissions: 'emissions',
                        Mobility: 'mobility',
                        Operations: 'transformation',
                      };
                      onNavigate(pageMap[item.dimension] || 'fingerprint');
                    }}
                    className="p-3 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-100 hover:border-slate-200 transition-all cursor-pointer flex items-start justify-between gap-3 group"
                  >
                    <div className="flex items-start gap-3">
                      <span className="w-6 h-6 rounded-lg bg-white border border-slate-200 text-slate-800 font-bold text-xs flex items-center justify-center shrink-0">
                        {index + 1}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-bold text-slate-900 group-hover:text-emerald-800">{item.dimension}</p>
                          <ImpactBadge level={item.impactLevel} size="sm" />
                        </div>
                        <p className="text-[11px] text-slate-600 mt-0.5 line-clamp-2">
                          {item.primaryCause || `Current score ${item.score}/100`}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-slate-700 shrink-0 mt-1" />
                  </div>
                ))}
              </div>
            )}
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

      {/* Analytics Charts Grid - real stored snapshots only */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Energy Consumption */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-slate-900">Energy Consumption by Stored Snapshot (kWh)</h4>
              <p className="text-xs text-slate-600">Built from your saved Climate Fingerprint records</p>
            </div>
            <button
              onClick={() => onNavigate('energy')}
              className="text-xs font-semibold text-emerald-700 hover:underline flex items-center gap-1"
            >
              <span>Details</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>

          {energyTrend.length >= 2 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={energyTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
                  <Area type="monotone" dataKey="value" stroke="#d97706" strokeWidth={2.5} fill="url(#colorEnergy)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState icon={TrendingUp} title="No energy history yet" message={EMPTY_STATES.history} />
          )}
        </div>

        {/* Monthly Water Consumption */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-slate-900">Water Extraction by Stored Snapshot (Litres)</h4>
              <p className="text-xs text-slate-600">Recorded freshwater volumes from your saved records</p>
            </div>
            <button
              onClick={() => onNavigate('water')}
              className="text-xs font-semibold text-cyan-700 hover:underline flex items-center gap-1"
            >
              <span>Details</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>

          {waterTrend.length >= 2 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={waterTrend} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    stroke="#cbd5e1"
                    tickFormatter={(v) => `${v / 1000}kL`}
                  />
                  <Tooltip
                    formatter={(val: any) => [`${Number(val).toLocaleString()} L`, 'Recorded water']}
                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                  />
                  <Bar dataKey="value" fill="#0284c7" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState icon={TrendingUp} title="No water history yet" message={EMPTY_STATES.history} />
          )}
        </div>
      </div>
    </div>
  );
};
