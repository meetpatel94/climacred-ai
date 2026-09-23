import React, { useState } from 'react';
import {
  FileText,
  Download,
  Printer,
  ShieldCheck,
  Share2,
  Check,
  Building2,
  Calendar,
} from 'lucide-react';
import { BusinessProfile, ClimateFingerprint, ImpactVerificationMetric } from '../types';
import { DemoTag } from '../components/common/StatusBadge';

interface ClimateImpactReportPageProps {
  profile: BusinessProfile;
  fingerprint: ClimateFingerprint;
  verificationMetrics: ImpactVerificationMetric[];
}

export const ClimateImpactReportPage: React.FC<ClimateImpactReportPageProps> = ({
  profile,
  fingerprint,
  verificationMetrics,
}) => {
  const [downloadNotified, setDownloadNotified] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  const handleDownload = () => {
    setDownloadNotified(true);
    setTimeout(() => {
      window.print();
      setDownloadNotified(false);
    }, 500);
  };

  const handleShare = () => {
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-20">
      {/* Top Action Header */}
      <div className="no-print bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Executive Climate Transformation Report
            </h2>
            <DemoTag label="Executive Dossier" />
          </div>
          <p className="text-xs text-slate-600">
            Audit-grade summary report prepared for board review, bank green-credit applications, and supply chain audits.
          </p>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={handleShare}
            className="flex-1 sm:flex-none px-3.5 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center justify-center gap-1.5 transition-colors"
          >
            {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Share2 className="w-3.5 h-3.5" />}
            <span>{copiedLink ? 'Link Copied' : 'Share Dossier'}</span>
          </button>

          <button
            onClick={handleDownload}
            className="flex-1 sm:flex-none px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
          >
            <Download className="w-4 h-4" />
            <span>Download PDF Report</span>
          </button>
        </div>
      </div>

      {downloadNotified && (
        <div className="no-print p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2">
          <Printer className="w-4 h-4 text-emerald-600" />
          <span>Generating printable executive PDF view. (Full backend PDF generation will connect to FastAPI in Phase 2).</span>
        </div>
      )}

      {/* Report Document Canvas (Printable Layout) */}
      <div className="bg-white border border-slate-200 rounded-3xl p-8 sm:p-12 shadow-md space-y-10 print:border-none print:shadow-none print:p-0">
        {/* Document Header & Branding */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 pb-6 border-b border-slate-200">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center text-white font-black text-lg">
                C
              </div>
              <span className="text-xl font-extrabold text-slate-900 tracking-tight">
                ClimaCred <span className="text-emerald-600">AI</span>
              </span>
            </div>
            <p className="text-xs text-slate-600 font-semibold tracking-wide uppercase">
              Climate Transformation & Green Investment Intelligence
            </p>
          </div>

          <div className="text-left sm:text-right space-y-0.5 text-xs text-slate-600">
            <p className="font-mono text-slate-900 font-bold">Report ID: CC-2026-TX-8492</p>
            <p className="flex items-center gap-1 sm:justify-end">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>Assessment Date: March 2026</span>
            </p>
            <p className="text-[11px] text-emerald-700 font-semibold">Standard: SME ESG Decarbonization v1.0</p>
          </div>
        </div>

        {/* Section 1: Business Identification & Executive Summary */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-emerald-600" />
              1. Business Organization & Audit Scope
            </h3>
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
              Verified Audit
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-5 rounded-2xl bg-slate-50 border border-slate-100 text-xs">
            <div>
              <span className="text-[10px] uppercase text-slate-600 block">Organization</span>
              <span className="font-bold text-slate-900 text-sm">{profile.name}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase text-slate-600 block">Industry Sector</span>
              <span className="font-bold text-slate-900 text-sm">{profile.industry}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase text-slate-600 block">Facility Location</span>
              <span className="font-medium text-slate-800 text-xs">{profile.location}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase text-slate-600 block">Covered Footprint</span>
              <span className="font-bold text-slate-900 text-sm">{profile.facilityAreaSqFt.toLocaleString()} sq ft</span>
            </div>
          </div>
        </div>

        {/* Section 2: Climate Readiness & Score Summary */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
            2. Climate Readiness & Diagnostic Summary
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-6 rounded-2xl border border-slate-200 items-center">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-200 flex flex-col items-center justify-center shrink-0">
                <span className="text-2xl font-black text-emerald-700">{fingerprint.overallScore}</span>
                <span className="text-[9px] font-bold text-slate-600">/ 100</span>
              </div>
              <div>
                <span className="text-xs font-bold text-slate-900 block">Climate Readiness Rating</span>
                <span className="text-xs text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded">
                  {fingerprint.scoreLabel}
                </span>
                <p className="text-[11px] text-slate-600 mt-1">Percentile: 46th in Textile Sector</p>
              </div>
            </div>

            <div className="md:col-span-2 space-y-1.5 text-xs text-slate-600 leading-relaxed">
              <span className="font-bold text-slate-900 block">Lead Assessor Diagnostic Narrative:</span>
              <p>
                {fingerprint.summaryNote} Priority resource stresses are concentrated in single-pass
                borewell extraction (480 kL/mo) and reliance on peak grid electricity without on-site
                renewables.
              </p>
            </div>
          </div>
        </div>

        {/* Section 3: Dimensional Audit Performance Table */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
            3. Multi-Stream Environmental Audit Scores
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border border-slate-200 rounded-xl overflow-hidden">
              <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-bold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Resource Dimension</th>
                  <th className="py-3 px-4">Dimension Score</th>
                  <th className="py-3 px-4">Vulnerability Level</th>
                  <th className="py-3 px-4">Identified Root Cause</th>
                  <th className="py-3 px-4">Primary Corrective Opportunity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {fingerprint.dimensions.map((dim) => (
                  <tr key={dim.dimension}>
                    <td className="py-3 px-4 font-bold text-slate-900">{dim.dimension}</td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-700">{dim.score}/100</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          dim.impactLevel === 'Very High'
                            ? 'bg-rose-100 text-rose-800'
                            : dim.impactLevel === 'High'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {dim.impactLevel}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-600">{dim.primaryCause}</td>
                    <td className="py-3 px-4 text-emerald-800 font-semibold">{dim.improvementOpportunity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 4: Verified Implementation Impact (Before vs After) */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
            4. Post-Intervention Realized Impact (Telemetry Verification)
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {verificationMetrics.map((met) => (
              <div key={met.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2 text-xs">
                <span className="font-bold text-slate-900 block">{met.name}</span>
                <div className="flex items-baseline justify-between text-slate-600">
                  <span>Baseline: {met.beforeValue.toLocaleString()} {met.unitLabel}</span>
                  <span className="font-bold text-emerald-700">Now: {met.afterValue.toLocaleString()} {met.unitLabel}</span>
                </div>
                <div className="pt-2 border-t border-slate-200/80 flex items-center justify-between font-bold">
                  <span className="text-[11px] text-slate-600">Verified Reduction:</span>
                  <span className="text-emerald-700">{met.differencePercent}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section 5: Legal & Phase 1 Disclaimer */}
        <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1.5">
          <div className="flex items-center gap-1.5 font-bold text-slate-900 uppercase text-[10px]">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Phase 1 Demonstration Disclaimer</span>
          </div>
          <p className="leading-relaxed text-[11px]">
            This report represents simulated and illustrative operational diagnostic intelligence generated by ClimaCred AI
            Phase 1 Frontend Architecture. In Phase 2, measurements will be directly calibrated against IoT meter telemetry,
            certified lab effluent reports, and third-party ISO 14064 GHG verification protocols.
          </p>
        </div>

        {/* Signatures Footer */}
        <div className="pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 text-xs text-slate-600">
          <div>
            <p className="font-bold text-slate-900">ABC Textile Manufacturing Ltd.</p>
            <p className="text-[11px]">Operations & Plant Management Authorization</p>
          </div>
          <div>
            <p className="font-bold text-emerald-800">ClimaCred AI Intelligence Engine</p>
            <p className="text-[11px]">System Verified Hash: 0x89b1c...4f2a</p>
          </div>
        </div>
      </div>
    </div>
  );
};
