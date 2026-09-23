import React from 'react';
import {
  Fingerprint,
  Zap,
  Droplets,
  Trash2,
  CloudFog,
  Truck,
  Layers,
  ArrowRight,
  TrendingDown,
} from 'lucide-react';
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
} from 'recharts';
import { ClimateFingerprint, PageId } from '../types';
import { ImpactBadge, DemoTag } from '../components/common/StatusBadge';
import { AIInsightCard } from '../components/common/AIInsightCard';

interface ClimateFingerprintPageProps {
  fingerprint: ClimateFingerprint;
  onNavigate: (page: PageId) => void;
}

const DIMENSION_ICONS: Record<string, React.ElementType> = {
  Energy: Zap,
  Water: Droplets,
  Waste: Trash2,
  Emissions: CloudFog,
  Mobility: Truck,
  Operations: Layers,
};

export const ClimateFingerprintPage: React.FC<ClimateFingerprintPageProps> = ({
  fingerprint,
  onNavigate,
}) => {
  const radarData = fingerprint.dimensions.map((d) => ({
    dimension: d.dimension,
    score: d.score,
    fullMark: 100,
  }));

  return (
    <div className="space-y-8 max-w-6xl pb-16">
      {/* Overview Diagnostic Card */}
      <div className="bg-white border border-slate-200/90 rounded-3xl p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col lg:flex-row items-center gap-8 justify-between">
          {/* Left: Score & High Level Narrative */}
          <div className="space-y-4 max-w-xl">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-emerald-50 text-emerald-700">
                <Fingerprint className="w-5 h-5" />
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
                Multi-Dimensional Diagnostic
              </span>
              <DemoTag />
            </div>

            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight leading-tight">
              Enterprise Climate Fingerprint
            </h2>

            <p className="text-sm text-slate-600 leading-relaxed">
              Your business has the highest improvement opportunity in{' '}
              <strong className="text-slate-900 font-bold">
                {fingerprint.topImprovementDimensions.join(', ')}
              </strong>
              . This fingerprint maps resource leakages against typical manufacturing benchmarks in
              your geographical cluster.
            </p>

            <div className="flex flex-wrap gap-2 pt-1">
              <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold">
                Peer Percentile: 46th
              </span>
              <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold">
                Projected with Roadmap: 86/100
              </span>
            </div>
          </div>

          {/* Center-Right: Central Circular Visualization & Radar Chart */}
          <div className="flex flex-col sm:flex-row items-center gap-6 w-full lg:w-auto justify-center">
            {/* Circular Gauge */}
            <div className="relative w-44 h-44 flex items-center justify-center bg-slate-50 rounded-full border border-slate-200/80 shadow-inner shrink-0">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="88" cy="88" r="74" stroke="#e2e8f0" strokeWidth="12" fill="transparent" />
                <circle
                  cx="88"
                  cy="88"
                  r="74"
                  stroke="#10b981"
                  strokeWidth="12"
                  fill="transparent"
                  strokeDasharray={464.95}
                  strokeDashoffset={464.95 * (1 - fingerprint.overallScore / 100)}
                  strokeLinecap="round"
                />
              </svg>

              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4">
                <span className="text-3xl font-black text-slate-900 tracking-tight">
                  {fingerprint.overallScore}
                  <span className="text-base font-normal text-slate-400">/100</span>
                </span>
                <span className="text-xs font-bold text-emerald-700 mt-0.5">
                  Climate Readiness
                </span>
                <span className="text-[10px] text-slate-400 font-medium">
                  {fingerprint.scoreLabel}
                </span>
              </div>
            </div>

            {/* Radar Chart */}
            <div className="w-56 h-56 sm:w-64 sm:h-64 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 10, fill: '#64748b', fontWeight: 600 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar
                    name="Readiness Score"
                    dataKey="score"
                    stroke="#059669"
                    fill="#10b981"
                    fillOpacity={0.35}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                    formatter={(val: any) => [`${val}/100`, 'Score']}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* AI Diagnostic Explanation Card */}
      <AIInsightCard
        title="AI Fingerprint Summary & Key Observations"
        insight="Water extraction stress and unoptimized peak-hour electricity drives over 74% of your environmental vulnerability. Deploying closed-loop water treatment along with rooftop solar reduces risk to 'Low' within 14 months."
        actionText="Open Scenario Simulator to test interventions"
        onActionClick={() => onNavigate('simulator')}
      />

      {/* Environmental Impact Breakdown */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-extrabold text-slate-900 tracking-tight">
              Environmental Impact Breakdown
            </h3>
            <p className="text-xs text-slate-600">
              Detailed root causes and quantified improvement opportunities per operational dimension.
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-600">6 Dimensions Audited</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {fingerprint.dimensions.map((dim) => {
            const Icon = DIMENSION_ICONS[dim.dimension] || Layers;

            return (
              <div
                key={dim.dimension}
                className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs hover:shadow-md transition-all space-y-4 group"
              >
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-800 flex items-center justify-center group-hover:bg-emerald-50 group-hover:text-emerald-700 transition-colors">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">{dim.dimension}</h4>
                      <p className="text-xs font-semibold text-slate-600">
                        Score: <span className="text-slate-900">{dim.score}/100</span>
                      </p>
                    </div>
                  </div>

                  <ImpactBadge level={dim.impactLevel} />
                </div>

                {/* Details Grid */}
                <div className="space-y-2.5 text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="font-bold text-slate-600 block text-[10px] uppercase">
                      Current Operational Status
                    </span>
                    <span className="text-slate-800 font-medium">{dim.currentStatus}</span>
                  </div>

                  <div>
                    <span className="font-bold text-slate-600 block text-[10px] uppercase">
                      Primary Root Cause
                    </span>
                    <span className="text-slate-700 font-normal">{dim.primaryCause}</span>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <span className="font-bold text-emerald-800 block text-[10px] uppercase flex items-center gap-1">
                        <TrendingDown className="w-3 h-3 text-emerald-600" />
                        Improvement Opportunity
                      </span>
                      <span className="text-slate-900 font-semibold">{dim.improvementOpportunity}</span>
                    </div>

                    <span className="text-[11px] font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded-md shrink-0 border border-emerald-200">
                      {dim.potentialReduction}
                    </span>
                  </div>
                </div>

                {/* Quick Link to Dimension Page */}
                <button
                  onClick={() => {
                    const pageMap: Record<string, PageId> = {
                      Energy: 'energy',
                      Water: 'water',
                      Waste: 'waste',
                      Emissions: 'emissions',
                      Mobility: 'mobility',
                      Operations: 'transformation',
                    };
                    onNavigate(pageMap[dim.dimension] || 'dashboard');
                  }}
                  className="w-full pt-2 flex items-center justify-center gap-1.5 text-xs font-bold text-emerald-700 hover:text-emerald-800 transition-colors"
                >
                  <span>Drill into {dim.dimension} Stream</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
