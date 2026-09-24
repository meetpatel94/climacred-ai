import React, { useEffect, useRef, useState } from 'react';
import {
  Sparkles,
  History,
  AlertTriangle,
  Target,
  TrendingUp,
  Info,
  X,
  ChevronRight,
  Database,
  ListChecks,
  Gauge,
  CheckCircle2,
  ShieldAlert,
  Wand2,
  FileSearch,
} from 'lucide-react';
import { AIDashboardInsightsResponse } from '../../types';
import { PageId } from '../../types';
import { getAIDashboardInsights } from '../../services/api';

const SESSION_CACHE_KEY = 'climacred_ai_dashboard_insight';

function readSessionCache(): AIDashboardInsightsResponse | null {
  try {
    const raw = window.sessionStorage.getItem(SESSION_CACHE_KEY);
    return raw ? (JSON.parse(raw) as AIDashboardInsightsResponse) : null;
  } catch {
    return null;
  }
}

function writeSessionCache(payload: AIDashboardInsightsResponse): void {
  try {
    window.sessionStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(payload));
  } catch {
    // sessionStorage unavailable - the backend cache still prevents extra AI calls
  }
}

const shortTime = (iso: string): string => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
};

// Small helper: name the origin of every block so nothing is mistaken for a guarantee.
const SourceTag: React.FC<{ kind: 'ai' | 'calculated' | 'estimated' | 'demo' }> = ({ kind }) => {
  const styles: Record<string, string> = {
    ai: 'bg-emerald-50 text-emerald-800 border-emerald-200/90',
    calculated: 'bg-slate-100 text-slate-700 border-slate-200',
    estimated: 'bg-amber-50 text-amber-800 border-amber-200',
    demo: 'bg-slate-100 text-slate-600 border-slate-200',
  };
  const labels: Record<string, string> = {
    ai: 'AI interpretation',
    calculated: 'Calculated',
    estimated: 'Estimated',
    demo: 'Demo data',
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border ${styles[kind]}`}>
      {labels[kind]}
    </span>
  );
};

interface InsightCardProps {
  icon: React.ElementType;
  label: string;
  children: React.ReactNode;
  accent?: string;
}

const InsightCard: React.FC<InsightCardProps> = ({ icon: Icon, label, children, accent = 'text-emerald-700 bg-emerald-50' }) => (
  <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-3.5 flex flex-col gap-2">
    <div className="flex items-center gap-2">
      <span className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 ${accent}`}>
        <Icon className="w-3.5 h-3.5" />
      </span>
      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">{label}</span>
    </div>
    <div className="text-xs text-slate-700 leading-relaxed space-y-1">{children}</div>
  </div>
);

const DetailSection: React.FC<{ icon: React.ElementType; title: string; tag?: React.ReactNode; children: React.ReactNode }> = ({
  icon: Icon,
  title,
  tag,
  children,
}) => (
  <div className="border border-slate-200/90 rounded-xl p-3.5 bg-slate-50/50 space-y-2">
    <div className="flex items-center justify-between gap-2">
      <div className="flex items-center gap-2">
        <Icon className="w-3.5 h-3.5 text-emerald-700" />
        <span className="text-xs font-bold text-slate-900">{title}</span>
      </div>
      {tag}
    </div>
    <div className="text-[11px] text-slate-700 leading-relaxed space-y-1.5">{children}</div>
  </div>
);

const BulletList: React.FC<{ items: string[]; empty?: string }> = ({ items, empty = 'Not available yet.' }) => {
  if (!items || items.length === 0) return <p className="text-slate-600">{empty}</p>;
  return (
    <ul className="space-y-1">
      {items.map((item, index) => (
        <li key={index} className="flex items-start gap-1.5">
          <span className="w-1 h-1 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
};

interface AIClimateIntelligenceProps {
  onNavigate: (page: PageId) => void;
}

/**
 * AI Climate Intelligence (Phase 3).
 * Automatically reads the latest stored data through the backend and shows a compact,
 * Gemini-generated interpretation with a full "More Info" explanation on demand.
 */
export const AIClimateIntelligence: React.FC<AIClimateIntelligenceProps> = ({ onNavigate }) => {
  // Render the last known insight instantly (session cache), then revalidate in the
  // background. The backend returns the cached insight unless the stored data changed.
  const [data, setData] = useState<AIDashboardInsightsResponse | null>(() => readSessionCache());
  const [loading, setLoading] = useState(() => !readSessionCache());
  const [failed, setFailed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const fresh = await getAIDashboardInsights();
        if (cancelled) return;
        const previous = readSessionCache();
        if (!previous || previous.data_signature !== fresh.data_signature || previous.source !== fresh.source) {
          setData(fresh);
          writeSessionCache(fresh);
        } else {
          setData((current) => current ?? fresh);
        }
        setFailed(false);
      } catch (error) {
        console.warn('AI dashboard insight unavailable', error);
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDrawerOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    drawerRef.current?.focus();
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [drawerOpen]);

  if (loading && !data) {
    return (
      <section className="ai-surface bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4" aria-busy="true">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-slate-100 animate-pulse" />
          <div className="space-y-1.5">
            <div className="h-3.5 w-44 bg-slate-100 rounded animate-pulse" />
            <div className="h-2.5 w-56 bg-slate-100 rounded animate-pulse" />
          </div>
        </div>
        <div className="h-3 w-full bg-slate-100 rounded animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
        <p className="text-[11px] text-slate-600">Generating your climate intelligence from the latest stored data…</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="ai-surface bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex items-start gap-3">
        <span className="w-9 h-9 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center shrink-0">
          <AlertTriangle className="w-4 h-4" />
        </span>
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">AI Climate Intelligence</h3>
          <p className="text-xs text-slate-700 mt-0.5">
            {failed
              ? 'AI insights unavailable — showing calculated insights. Your Phase 2 dashboard data below is unaffected.'
              : 'Preparing climate intelligence from your latest stored data…'}
          </p>
        </div>
      </section>
    );
  }

  const { insight, calculated, history, source, notice, reason, model, generated_at } = data;
  const details = insight.details;
  const auditWarning = details.number_audit && details.number_audit.verified === false;

  return (
    <section className="ai-surface bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-600 via-teal-600 to-emerald-700 text-white flex items-center justify-center shrink-0 shadow-sm shadow-emerald-500/20">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <h3 className="text-sm font-extrabold text-slate-900 tracking-tight">AI Climate Intelligence</h3>
              <SourceTag kind={source === 'gemini' ? 'ai' : 'calculated'} />
            </div>
            <p className="text-[11px] text-slate-600">
              Based on your latest stored data • {source === 'gemini' ? `Gemini (${model})` : 'ClimaCred Phase 2 engine'}
              {generated_at ? ` • ${shortTime(generated_at)}` : ''}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
            <Gauge className="w-3 h-3 text-emerald-600" />
            Confidence: {insight.confidence}
          </span>
          <button
            onClick={() => setDrawerOpen(true)}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold transition-colors"
            aria-haspopup="dialog"
          >
            <Info className="w-3.5 h-3.5 text-emerald-600" />
            <span>More Info</span>
          </button>
        </div>
      </div>

      {/* Status strip when Gemini is unavailable */}
      {notice && (
        <div className="flex items-start gap-2 p-2.5 rounded-xl bg-amber-50 border border-amber-200">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-700 mt-0.5 shrink-0" />
          <p className="text-[11px] text-amber-900">
            {notice}
            {reason ? <span className="text-amber-800/80"> ({reason})</span> : null}
          </p>
        </div>
      )}

      {/* One concise insight */}
      <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">{insight.summary}</p>

      {/* Compact cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <InsightCard icon={History} label="What Changed" accent="bg-emerald-50 text-emerald-700">
          {insight.recent_changes.length ? (
            <ul className="space-y-1">
              {insight.recent_changes.slice(0, 2).map((change, index) => (
                <li key={index} className="flex items-start gap-1.5">
                  <span className="w-1 h-1 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                  <span>{change}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>{history.note}</p>
          )}
          {!history.available && (
            <p className="text-[10px] text-slate-500">Limited comparison — one stored snapshot.</p>
          )}
        </InsightCard>

        <InsightCard icon={AlertTriangle} label="Key Risk" accent="bg-rose-50 text-rose-700">
          <p>{insight.key_risk}</p>
        </InsightCard>

        <InsightCard icon={Target} label="What To Do Next" accent="bg-teal-50 text-teal-700">
          <p className="font-semibold text-slate-800">{insight.priority_action}</p>
          {insight.focus_now && <p className="text-slate-600">{insight.focus_now}</p>}
        </InsightCard>

        <InsightCard icon={TrendingUp} label="Forecast" accent="bg-indigo-50 text-indigo-700">
          <p>{insight.forecast}</p>
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-600">
            <SourceTag kind="estimated" /> not a guarantee
          </span>
        </InsightCard>
      </div>

      {/* Expected impact + actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-100">
        <div className="flex items-start gap-2 min-w-0">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
          <p className="text-[11px] text-slate-700 truncate max-w-2xl" title={insight.expected_impact}>
            <span className="font-bold text-slate-800">Expected impact: </span>
            {insight.expected_impact}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => onNavigate('transformation')}
            className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 hover:underline inline-flex items-center gap-1"
          >
            Transformation Plan <ChevronRight className="w-3 h-3" />
          </button>
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-[11px] font-bold text-slate-800 hover:underline inline-flex items-center gap-1"
          >
            <Info className="w-3 h-3" /> More Info
          </button>
        </div>
      </div>

      {/* Complete explanation drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-[70] flex justify-end" role="dialog" aria-modal="true" aria-label="AI insight explanation">
          <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-xs" onClick={() => setDrawerOpen(false)} />
          <div
            ref={drawerRef}
            tabIndex={-1}
            className="relative w-full sm:max-w-xl h-full bg-white border-l border-slate-200 shadow-2xl overflow-y-auto outline-hidden"
          >
            <div className="sticky top-0 z-10 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-5 py-3.5 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-600" /> AI Insight — Complete Explanation
                </h3>
                <p className="text-[11px] text-slate-600">
                  {source === 'gemini' ? `Generated by Gemini (${model})` : 'Generated by the ClimaCred calculation engine'}
                  {generated_at ? ` • ${new Date(generated_at).toLocaleString()}` : ''}
                </p>
              </div>
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                aria-label="Close explanation"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-3">
              {auditWarning && (
                <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-50 border border-amber-200">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-700 mt-0.5 shrink-0" />
                  <p className="text-[11px] text-amber-900">
                    Some figures in this AI text could not be matched to your stored data
                    {details.number_audit.unsupported_values.length
                      ? `: ${details.number_audit.unsupported_values.join(', ')}`
                      : ''}
                    . Treat them as unverified; the calculated values elsewhere on this page remain the source of truth.
                  </p>
                </div>
              )}

              <DetailSection icon={Database} title="Data used" tag={<SourceTag kind="calculated" />}>
                <div className="flex flex-wrap gap-1.5">
                  {(details.data_used.length ? details.data_used : ['Latest stored profile, assessment and fingerprint']).map(
                    (item, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[10px] font-medium text-slate-700"
                      >
                        {item}
                      </span>
                    )
                  )}
                </div>
              </DetailSection>

              <DetailSection icon={History} title="Recent changes" tag={<SourceTag kind="calculated" />}>
                <BulletList items={insight.recent_changes} empty="No comparable change recorded yet." />
              </DetailSection>

              <DetailSection icon={FileSearch} title="Historical comparison" tag={<SourceTag kind="calculated" />}>
                <p>{details.historical_comparison || 'No earlier snapshot stored yet.'}</p>
                <p className="text-slate-600">
                  {history.fingerprint_snapshots ?? 0} fingerprint snapshot(s) • {history.impact_records ?? 0} impact record(s) •{' '}
                  {history.scenario_runs ?? 0} scenario run(s) stored.
                </p>
              </DetailSection>

              <DetailSection icon={Wand2} title="Why Gemini generated this insight" tag={<SourceTag kind={source === 'gemini' ? 'ai' : 'calculated'} />}>
                <p>{details.reasoning_summary}</p>
              </DetailSection>

              <DetailSection icon={AlertTriangle} title="Main risks" tag={<SourceTag kind="calculated" />}>
                <BulletList items={details.main_risks} empty="No specific risk flagged." />
              </DetailSection>

              <DetailSection icon={ListChecks} title="Recommended actions" tag={<SourceTag kind="estimated" />}>
                <BulletList items={details.recommended_actions} empty="No action recommended yet." />
              </DetailSection>

              <DetailSection icon={TrendingUp} title="Expected impact" tag={<SourceTag kind="estimated" />}>
                <p>{details.expected_impact_detail || insight.expected_impact}</p>
                <p className="text-slate-600">
                  Estimated from ClimaCred catalog assumptions — not a guaranteed outcome.
                </p>
              </DetailSection>

              <DetailSection icon={Sparkles} title="Related ClimaCred recommendations" tag={<SourceTag kind="calculated" />}>
                {details.related_recommendations.length ? (
                  <div className="flex flex-wrap gap-1.5">
                    {details.related_recommendations.map((item, index) => (
                      <button
                        key={index}
                        onClick={() => {
                          setDrawerOpen(false);
                          onNavigate('solutions');
                        }}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-emerald-200/90 text-[10px] font-semibold text-emerald-800 hover:bg-emerald-50"
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-600">No linked recommendation.</p>
                )}
              </DetailSection>

              <DetailSection icon={Gauge} title="Confidence & data availability" tag={<SourceTag kind="calculated" />}>
                <p>
                  Confidence: <span className="font-semibold">{insight.confidence}</span>. {details.confidence_note}
                </p>
                <p className="text-slate-600">
                  Data completeness {calculated.data_quality_completeness_percent ?? '—'}% ({calculated.data_quality_level ?? 'n/a'}).
                  {' '}{history.note}
                </p>
              </DetailSection>

              <DetailSection icon={FileSearch} title="Assumptions used" tag={<SourceTag kind="estimated" />}>
                <BulletList items={details.assumptions} empty="No explicit assumption recorded." />
              </DetailSection>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/90 space-y-1.5">
                <p className="text-[11px] font-bold text-slate-800 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-emerald-600" /> How to read this
                </p>
                <div className="flex flex-wrap items-center gap-1.5">
                  <SourceTag kind="calculated" /> <span className="text-[10px] text-slate-600">Phase 2 engine values — the source of truth</span>
                  <SourceTag kind="ai" /> <span className="text-[10px] text-slate-600">Gemini interpretation</span>
                  <SourceTag kind="estimated" /> <span className="text-[10px] text-slate-600">catalog-based projection</span>
                  <SourceTag kind="demo" /> <span className="text-[10px] text-slate-600">illustrative sample data</span>
                </div>
                <p className="text-[10px] text-slate-600">{data.disclaimer}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
