import React from 'react';
import {
  CheckCircle2,
  TrendingDown,
  Zap,
  Droplets,
  Trash2,
  CloudFog,
  FileCheck,
  ShieldCheck,
} from 'lucide-react';
import { ImpactVerificationMetric, PageId } from '../types';
import { DemoTag } from '../components/common/StatusBadge';
import { AIInsightCard } from '../components/common/AIInsightCard';

interface ImpactVerificationPageProps {
  metrics: ImpactVerificationMetric[];
  onNavigate: (page: PageId) => void;
}

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  Energy: Zap,
  Water: Droplets,
  Waste: Trash2,
  Emissions: CloudFog,
  Financial: TrendingDown,
};

export const ImpactVerificationPage: React.FC<ImpactVerificationPageProps> = ({
  metrics,
  onNavigate,
}) => {
  return (
    <div className="space-y-8 max-w-6xl pb-16">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Impact Verification (Before vs After)
            </h2>
            <DemoTag label="Verification Audit Mode" />
          </div>
          <p className="text-xs text-slate-600">
            ClimaCred AI compares operational meter data before and after green interventions to verify realized environmental and economic gains.
          </p>
        </div>

        <button
          onClick={() => onNavigate('report')}
          className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <FileCheck className="w-3.5 h-3.5" />
          <span>Generate Full Impact Report</span>
        </button>
      </div>

      {/* Explainer Box */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 border border-slate-800 shadow-md">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4" />
              <span>Audit-Ready Measurement & Verification (M&V)</span>
            </div>
            <p className="text-sm text-slate-300 max-w-3xl leading-relaxed">
              After implementing a green intervention, ClimaCred compares operational data before and after
              implementation to estimate realized environmental improvements. This telemetry is structured
              to meet ESG reporting standards and green bank audit guidelines.
            </p>
          </div>

          <div className="px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-center shrink-0">
            <span className="text-[10px] text-slate-400 block uppercase">Net Realized Saving</span>
            <span className="text-lg font-black text-emerald-400">₹20.8 Lakh / yr</span>
          </div>
        </div>
      </div>

      {/* Before / After Comparison Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-extrabold text-slate-900">
            Comparative Verification Breakdown (Baseline vs Realized)
          </h3>
          <span className="text-xs text-slate-600 font-medium">5 Audited Streams</span>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {metrics.map((metric) => {
            const Icon = CATEGORY_ICONS[metric.category] || TrendingDown;
            const percentReduction = Math.abs(metric.differencePercent);

            return (
              <div
                key={metric.id}
                className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs hover:border-slate-300 transition-all flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6"
              >
                {/* Metric Identity */}
                <div className="flex items-start gap-4 min-w-[280px]">
                  <div className="w-11 h-11 rounded-xl bg-slate-100 text-slate-800 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 block">
                      {metric.category}
                    </span>
                    <h4 className="text-base font-extrabold text-slate-900">{metric.name}</h4>
                    <p className="text-xs text-slate-600 mt-0.5">{metric.impactVerdict}</p>
                  </div>
                </div>

                {/* Before vs After Animated Visual Columns */}
                <div className="flex-1 w-full max-w-xl space-y-2">
                  <div className="grid grid-cols-2 gap-4 text-xs font-semibold">
                    <div>
                      <span className="text-[10px] uppercase text-slate-600 block">Baseline Before</span>
                      <span className="text-sm font-bold text-slate-900">
                        {metric.beforeValue.toLocaleString()} {metric.unitLabel}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase text-emerald-700 block">Audited After</span>
                      <span className="text-sm font-bold text-emerald-700">
                        {metric.afterValue.toLocaleString()} {metric.unitLabel}
                      </span>
                    </div>
                  </div>

                  {/* Relative Bar Visualization */}
                  <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden flex">
                    <div
                      className="h-full bg-emerald-500 rounded-full transition-all duration-700"
                      style={{ width: `${100 - percentReduction}%` }}
                    />
                    <div
                      className="h-full bg-rose-400/30 transition-all duration-700"
                      style={{ width: `${percentReduction}%` }}
                    />
                  </div>

                  <div className="flex justify-between text-[11px] text-slate-600">
                    <span>Active post-intervention load</span>
                    <span className="font-bold text-emerald-700">-{percentReduction}% Abated</span>
                  </div>
                </div>

                {/* Net Difference Badge */}
                <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-right shrink-0 w-full lg:w-auto">
                  <span className="text-[10px] uppercase text-emerald-800 font-bold block">
                    Verified Reduction
                  </span>
                  <span className="text-lg font-black text-emerald-700">
                    {metric.differenceValue.toLocaleString()} {metric.unitLabel}
                  </span>
                  <span className="text-[11px] font-bold text-emerald-800 block">
                    ({metric.differencePercent}%)
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* AI Verification Note */}
      <AIInsightCard
        title="AI Measurement & Verification Summary"
        insight="All 5 primary resource streams demonstrate sustained downward trends consistent with capital commissioning dates. Water extraction achieved the steepest contraction (-59%), directly resolving local groundwater compliance warnings."
        actionText="Generate Certified Climate Impact Dossier"
        onActionClick={() => onNavigate('report')}
      />
    </div>
  );
};
