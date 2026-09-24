import React, { useEffect, useState } from 'react';
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
  Loader2,
  UploadCloud,
  Play,
  FileSpreadsheet,
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
import { ImpactBadge } from '../components/common/StatusBadge';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { EmptyState } from '../components/common/EmptyState';
import { generateClimateFingerprint, syncAssessmentFromImports, getClimateFingerprint } from '../services/api';

interface ClimateFingerprintPageProps {
  /** null until the user has stored an assessment and a fingerprint was calculated */
  fingerprint: ClimateFingerprint | null;
  hasProfile?: boolean;
  hasAssessment?: boolean;
  onNavigate: (page: PageId) => void;
  onFingerprintGenerated?: (fingerprint: ClimateFingerprint) => void;
  notify?: (type: 'success' | 'info' | 'warning' | 'error', title: string, message?: string) => void;
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
  hasProfile = false,
  hasAssessment = false,
  onNavigate,
  onFingerprintGenerated,
  notify,
}) => {
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  // CASE C — Assessment exists: automatically attempt to load/generate the fingerprint
  useEffect(() => {
    if (!fingerprint && hasAssessment) {
      let active = true;
      (async () => {
        try {
          const fp = await getClimateFingerprint() || await generateClimateFingerprint();
          if (active && fp && onFingerprintGenerated) {
            onFingerprintGenerated(fp);
          }
        } catch (err) {
          console.warn('Auto-resolving fingerprint failed', err);
        }
      })();
      return () => {
        active = false;
      };
    }
  }, [fingerprint, hasAssessment, onFingerprintGenerated]);

  const handleRunAssessment = async () => {
    setRunning(true);
    setRunError(null);
    try {
      // First attempt to sync assessment from imported data
      const syncRes = await syncAssessmentFromImports();
      if (syncRes.synced) {
        const fp = await getClimateFingerprint() || await generateClimateFingerprint();
        if (fp && onFingerprintGenerated) {
          onFingerprintGenerated(fp);
        }
        if (notify) {
          notify(
            'success',
            'Climate Assessment Calculated',
            `Score: ${syncRes.overall_score}/100 (${syncRes.score_label}).`
          );
        }
      } else {
        // If not synced from import, try generating from stored assessment
        const fp = await generateClimateFingerprint();
        if (fp && onFingerprintGenerated) {
          onFingerprintGenerated(fp);
          if (notify) {
            notify('success', 'Climate Fingerprint Generated', `Overall score: ${fp.overallScore}/100.`);
          }
        } else {
          setRunError(syncRes.message || 'Could not calculate assessment from stored data.');
        }
      }
    } catch (err: any) {
      setRunError(err?.message || 'Failed to run climate assessment.');
    } finally {
      setRunning(false);
    }
  };

  // If no fingerprint yet, show the appropriate non-blocking state:
  if (!fingerprint) {
    // CASE A — No data exists
    if (!hasProfile && !hasAssessment) {
      return (
        <div className="space-y-8 max-w-4xl pb-16">
          <div className="bg-white border border-slate-200/90 rounded-3xl p-6 sm:p-8 shadow-xs space-y-3">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-emerald-50 text-emerald-700">
                <Fingerprint className="w-5 h-5" />
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
                Multi-Dimensional Diagnostic
              </span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Enterprise Climate Fingerprint
            </h2>
            <p className="text-sm text-slate-600">
              Import your business data to generate your Climate Fingerprint.
            </p>
          </div>

          <EmptyState
            icon={UploadCloud}
            title="No business data yet"
            message="Import your business data to generate your Climate Fingerprint."
            actionLabel="Import Business Data"
            onAction={() => onNavigate('import')}
          />
        </div>
      );
    }

    // CASE B — Business profile exists but assessment does not exist
    return (
      <div className="space-y-8 max-w-4xl pb-16">
        <div className="bg-white border border-slate-200/90 rounded-3xl p-6 sm:p-8 shadow-xs space-y-3">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-emerald-50 text-emerald-700">
              <Fingerprint className="w-5 h-5" />
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
              Multi-Dimensional Diagnostic
            </span>
          </div>
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Enterprise Climate Fingerprint
          </h2>
          <p className="text-sm text-slate-600">
            ClimaCred calculates your fingerprint from your stored business profile and Climate Assessment.
          </p>
        </div>

        <div className="bg-white border border-dashed border-slate-300 rounded-2xl p-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-700 mx-auto flex items-center justify-center">
            <Fingerprint className="w-6 h-6" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-base font-extrabold text-slate-900">Climate Assessment required</h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Calculate your multi-dimensional Climate Fingerprint from your stored business profile and imported resource streams.
            </p>
          </div>

          {runError && (
            <p className="text-xs font-semibold text-rose-700 max-w-md mx-auto">{runError}</p>
          )}

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleRunAssessment}
              disabled={running}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors disabled:opacity-50"
            >
              {running ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Calculating Fingerprint…</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Run Climate Assessment</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => onNavigate('import')}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-bold transition-colors"
            >
              <UploadCloud className="w-4 h-4 text-emerald-600" />
              <span>Import Business Data</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('assessment')}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold transition-colors"
            >
              <FileSpreadsheet className="w-4 h-4 text-slate-500" />
              <span>Assessment Form</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // CASE C — Assessment exists and Fingerprint exists: display full diagnostic
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
            </div>

            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight leading-tight">
              Enterprise Climate Fingerprint
            </h2>

            <p className="text-sm text-slate-600 leading-relaxed">
              Your business has the highest improvement opportunity in{' '}
              <strong className="text-slate-900 font-bold">
                {fingerprint.topImprovementDimensions.join(', ')}
              </strong>
              . Scores are calculated from the operational data you stored, weighted across six
              dimensions.
            </p>

            <div className="flex flex-wrap gap-2 pt-1">
              {fingerprint.benchmarkPercentile !== null && fingerprint.benchmarkPercentile !== undefined && (
                <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold">
                  Modelled benchmark percentile: {fingerprint.benchmarkPercentile}
                </span>
              )}
              <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold">
                {fingerprint.dimensions.length} dimensions scored
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

      {/* Diagnostic summary - uses the calculated dimension text only */}
      <AIInsightCard
        title="Fingerprint Summary"
        insight={`Your weakest dimension is ${fingerprint.topImprovementDimensions.join(', ') || 'not yet identified'} with an overall readiness of ${fingerprint.overallScore}/100 (${fingerprint.scoreLabel}). ${fingerprint.summaryNote}`}
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

export default ClimateFingerprintPage;
