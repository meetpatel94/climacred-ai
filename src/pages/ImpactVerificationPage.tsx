import React, { useState } from 'react';
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
import { EmptyState } from '../components/common/EmptyState';
import { submitImpactVerification } from '../services/api';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { EMPTY_STATES } from '../services/defaults';

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

const EMPTY_FORM = { energy_kwh: '', water_litres: '', waste_kg: '' };

export const ImpactVerificationPage: React.FC<ImpactVerificationPageProps> = ({
  metrics,
  onNavigate,
}) => {
  // The form starts blank - the user enters their own meter readings.
  const [formBefore, setFormBefore] = useState({ ...EMPTY_FORM });
  const [formAfter, setFormAfter] = useState({ ...EMPTY_FORM });
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<any>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const toNumber = (value: string) => (value === '' ? 0 : Number(value));
      const res = await submitImpactVerification({
        before: {
          energy_kwh: toNumber(formBefore.energy_kwh),
          water_litres: toNumber(formBefore.water_litres),
          waste_kg: toNumber(formBefore.waste_kg),
        },
        after: {
          energy_kwh: toNumber(formAfter.energy_kwh),
          water_litres: toNumber(formAfter.water_litres),
          waste_kg: toNumber(formAfter.waste_kg),
        },
      });
      setSubmitResult(res);
    } catch (err: any) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (
    label: string,
    value: string,
    onChange: (next: string) => void
  ) => (
    <label className="block text-xs font-semibold">
      {label}
      <input
        type="number"
        min={0}
        value={value}
        placeholder="Enter measured value"
        onChange={(e) => onChange(e.target.value)}
        className="w-full mt-1 px-2 py-1.5 rounded-lg border border-slate-300 text-sm bg-white"
      />
    </label>
  );

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
          </div>
          <p className="text-xs text-slate-600">
            ClimaCred compares the meter data you submit before and after green interventions to calculate observed
            environmental and economic change.
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
              After implementing a green intervention, ClimaCred compares the operational data you submit before and
              after implementation to estimate realized environmental improvements. Recorded results are reported as
              observed change, not certified carbon reduction.
            </p>
          </div>

          <div className="px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-center shrink-0">
            <span className="text-[10px] text-slate-400 block uppercase">Verified Records</span>
            <span className="text-lg font-black text-emerald-400">{metrics.length}</span>
          </div>
        </div>
      </div>

      {/* Before / After Comparison Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-extrabold text-slate-900">
            Comparative Verification Breakdown (Baseline vs Realized)
          </h3>
          {metrics.length > 0 && (
            <span className="text-xs text-slate-600 font-medium">{metrics.length} verified streams</span>
          )}
        </div>

        {metrics.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="No verified impact data yet"
            message={EMPTY_STATES.impact}
          />
        ) : (
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

                  {/* Before vs After Visual Columns */}
                  <div className="flex-1 w-full max-w-xl space-y-2">
                    <div className="grid grid-cols-2 gap-4 text-xs font-semibold">
                      <div>
                        <span className="text-[10px] uppercase text-slate-600 block">Baseline Before</span>
                        <span className="text-sm font-bold text-slate-900">
                          {metric.beforeValue.toLocaleString()} {metric.unitLabel}
                        </span>
                      </div>

                      <div>
                        <span className="text-[10px] uppercase text-emerald-700 block">Reported After</span>
                        <span className="text-sm font-bold text-emerald-700">
                          {metric.afterValue.toLocaleString()} {metric.unitLabel}
                        </span>
                      </div>
                    </div>

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
                      <span>Observed post-intervention load</span>
                      <span className="font-bold text-emerald-700">-{percentReduction}% change</span>
                    </div>
                  </div>

                  {/* Net Difference Badge */}
                  <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-right shrink-0 w-full lg:w-auto">
                    <span className="text-[10px] uppercase text-emerald-800 font-bold block">
                      Observed Change
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
        )}
      </div>

      {/* Submit New Impact Verification Form (Backend Connected) */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
        <h3 className="text-sm font-extrabold text-slate-900">Submit Post-Implementation Data (Backend Calculated)</h3>
        <p className="text-xs text-slate-600">
          Enter your own before/after meter values. The backend calculates the observed change and the estimated
          environmental impact. Reported outcomes represent observations from your submissions, not certified carbon
          reductions.
        </p>
        {submitError && (
          <div className="p-2 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800">{submitError}</div>
        )}
        {submitResult && (
          <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs space-y-1">
            <p className="font-bold text-emerald-800">Verification calculated – {submitResult.summary}</p>
            <ul className="list-disc pl-4">
              {submitResult.calculated_metrics?.map((m: any, i: number) => (
                <li key={i}>
                  {m.metric}: {m.before} → {m.after} ({m.percentage_change}%) – {m.estimated_impact}
                </li>
              ))}
            </ul>
            <p className="text-[11px] text-slate-600">Terminology note: {submitResult.terminology?.disclaimer}</p>
          </div>
        )}
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
            <h4 className="text-xs font-bold text-slate-900 uppercase">Before (Baseline)</h4>
            {renderField('Energy kWh/mo', formBefore.energy_kwh, (v) => setFormBefore({ ...formBefore, energy_kwh: v }))}
            {renderField('Water Litres/mo', formBefore.water_litres, (v) => setFormBefore({ ...formBefore, water_litres: v }))}
            {renderField('Waste kg/mo', formBefore.waste_kg, (v) => setFormBefore({ ...formBefore, waste_kg: v }))}
          </div>
          <div className="space-y-3 p-3 rounded-xl bg-emerald-50/50 border border-emerald-200">
            <h4 className="text-xs font-bold text-emerald-800 uppercase">After (Reported)</h4>
            {renderField('Energy kWh/mo', formAfter.energy_kwh, (v) => setFormAfter({ ...formAfter, energy_kwh: v }))}
            {renderField('Water Litres/mo', formAfter.water_litres, (v) => setFormAfter({ ...formAfter, water_litres: v }))}
            {renderField('Waste kg/mo', formAfter.waste_kg, (v) => setFormAfter({ ...formAfter, waste_kg: v }))}
          </div>
          <div className="md:col-span-2 flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md disabled:opacity-50"
            >
              {submitting ? 'Calculating...' : 'Calculate Observed Change'}
            </button>
          </div>
        </form>
      </div>

      {/* Verification note driven by the stored records */}
      <AIInsightCard
        title="Measurement & Verification Summary"
        insight={
          metrics.length > 0
            ? `${metrics.length} verified stream${metrics.length === 1 ? '' : 's'} recorded. Comparisons use only the before/after values you submitted and are recalculated by the backend whenever you add a new record.`
            : EMPTY_STATES.impact
        }
        actionText="Generate Climate Impact Report"
        onActionClick={() => onNavigate('report')}
      />
    </div>
  );
};
