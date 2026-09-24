import React from 'react';
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  Droplets,
  Trash2,
  CloudFog,
  Truck,
  Activity,
  Layers,
  TrendingDown,
  BarChart3,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import { PageId } from '../types';

interface LandingPageProps {
  onNavigate: (page: PageId) => void;
  /** true once the user has stored a business profile */
  hasProfile?: boolean;
  /** true once the user has stored climate assessment data */
  hasAssessment?: boolean;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onNavigate,
  hasProfile = false,
  hasAssessment = false,
}) => {
  return (
    <div className="space-y-16 pb-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 text-white p-8 sm:p-12 lg:p-16 shadow-xl border border-slate-700/60">
        {/* Subtle grid pattern overlay */}
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:16px_16px]" />

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Hero Content */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-400/30 text-emerald-300 text-xs font-semibold backdrop-blur-md">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Next-Gen Climate Transformation Platform for SMEs</span>
            </div>

            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.12]">
              Turn Business Data Into{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-green-300">
                Climate Action.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-300 max-w-2xl font-normal leading-relaxed">
              ClimaCred AI helps businesses understand their environmental impact, discover their
              biggest inefficiencies, evaluate green investments, and build a measurable path toward
              sustainable operations.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={() => onNavigate('assessment')}
                className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-sm shadow-lg shadow-emerald-500/25 flex items-center gap-2 group transition-all hover:scale-[1.02]"
              >
                <span>{hasAssessment ? 'Review Climate Assessment' : 'Start Climate Assessment'}</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>

              <button
                onClick={() => onNavigate('dashboard')}
                className="px-6 py-3.5 rounded-xl bg-white/10 hover:bg-white/15 border border-white/20 text-white font-semibold text-sm backdrop-blur-md transition-all hover:scale-[1.02]"
              >
                {hasProfile || hasAssessment ? 'Open Dashboard' : 'View Dashboard'}
              </button>
            </div>

            {/* Trust statement */}
            <div className="pt-6 border-t border-slate-700/80 flex items-center gap-2 text-xs font-semibold tracking-wide text-emerald-400 uppercase">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Measure. Understand. Transform. Verify.</span>
            </div>
          </div>

          {/* Right Hero Visual: Connected Climate Engine */}
          <div className="lg:col-span-5 flex justify-center">
            <div className="relative w-full max-w-[380px] aspect-square rounded-3xl bg-slate-800/80 border border-slate-700 p-6 flex flex-col justify-between shadow-2xl backdrop-blur-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-700/60 pb-3">
                <span className="flex items-center gap-1.5 font-mono text-[11px] text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  ENGINE v1.0 ONLINE
                </span>
                <span className="font-semibold text-slate-300">Continuous Audit</span>
              </div>

              {/* Central Core & Orbital Resource Streams */}
              <div className="relative my-6 flex items-center justify-center">
                {/* Orbit ring */}
                <div className="w-60 h-60 rounded-full border border-dashed border-emerald-500/30 flex items-center justify-center animate-spin-slow">
                  {/* Subtle orbital nodes */}
                </div>

                {/* Center Node: ClimaCred Intelligence */}
                <div className="absolute w-32 h-32 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-800 p-3.5 text-center flex flex-col items-center justify-center shadow-lg shadow-emerald-500/30 border border-emerald-400/40">
                  <Activity className="w-6 h-6 text-emerald-200 mb-1" />
                  <span className="text-xs font-extrabold text-white">Climate Engine</span>
                  <span className="text-[10px] text-emerald-200 font-mono">Six Dimensions</span>
                </div>

                {/* 5 Input Streams as Orbiting Badges */}
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-slate-900/90 border border-amber-500/50 px-2.5 py-1 rounded-full text-[11px] text-amber-300 shadow-md">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>Energy</span>
                </div>

                <div className="absolute top-1/4 -right-4 flex items-center gap-1.5 bg-slate-900/90 border border-cyan-500/50 px-2.5 py-1 rounded-full text-[11px] text-cyan-300 shadow-md">
                  <Droplets className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Water</span>
                </div>

                <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-slate-900/90 border border-emerald-500/50 px-2.5 py-1 rounded-full text-[11px] text-emerald-300 shadow-md">
                  <Trash2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Waste</span>
                </div>

                <div className="absolute top-1/4 -left-4 flex items-center gap-1.5 bg-slate-900/90 border border-rose-500/50 px-2.5 py-1 rounded-full text-[11px] text-rose-300 shadow-md">
                  <CloudFog className="w-3.5 h-3.5 text-rose-400" />
                  <span>Emissions</span>
                </div>

                <div className="absolute bottom-1/4 -right-3 flex items-center gap-1.5 bg-slate-900/90 border border-indigo-500/50 px-2.5 py-1 rounded-full text-[11px] text-indigo-300 shadow-md">
                  <Truck className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Mobility</span>
                </div>
              </div>

              {/* Bottom capability strip (no sample figures - your own data drives every number) */}
              <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-700/60 text-center">
                <div className="bg-slate-900/60 p-2 rounded-xl border border-slate-700/40">
                  <p className="text-[10px] text-slate-400">Baseline</p>
                  <p className="text-xs font-bold text-white">Your Data</p>
                </div>
                <div className="bg-slate-900/60 p-2 rounded-xl border border-slate-700/40">
                  <p className="text-[10px] text-slate-400">Payback</p>
                  <p className="text-xs font-bold text-emerald-400">Modelled</p>
                </div>
                <div className="bg-slate-900/60 p-2 rounded-xl border border-slate-700/40">
                  <p className="text-[10px] text-slate-400">Forecast</p>
                  <p className="text-xs font-bold text-teal-300">Calculated</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Global Product Journey Section */}
      <section className="space-y-6">
        <div className="text-center max-w-3xl mx-auto space-y-2">
          <span className="text-xs font-bold uppercase tracking-widest text-emerald-700">
            End-To-End Climate Lifecycle
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            How ClimaCred AI Transforms Your Enterprise
          </h2>
          <p className="text-sm text-slate-600">
            A clear, verified 5-stage transformation sequence built specifically for small and
            medium industrial operations.
          </p>
        </div>

        {/* 5 Capability Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {[
            {
              icon: BarChart3,
              title: 'Measure Impact',
              desc: 'Collect comprehensive operational data across energy, water, waste, and transport in 15 minutes.',
              color: 'text-blue-600 bg-blue-50 border-blue-200',
              page: 'assessment',
            },
            {
              icon: TrendingDown,
              title: 'Detect Inefficiencies',
              desc: 'Synthesize your multi-dimensional Climate Fingerprint to pinpoint severe resource leaks and waste.',
              color: 'text-amber-600 bg-amber-50 border-amber-200',
              page: 'fingerprint',
            },
            {
              icon: Layers,
              title: 'Explore Solutions',
              desc: 'Review vetted equipment, solar, circular recycling, and process interventions tailored to your sector.',
              color: 'text-emerald-600 bg-emerald-50 border-emerald-200',
              page: 'solutions',
            },
            {
              icon: Sliders,
              title: 'Simulate Investments',
              desc: 'Test what-if combinations with live capital cost, annual savings, payback duration, and carbon reductions.',
              color: 'text-teal-600 bg-teal-50 border-teal-200',
              page: 'simulator',
            },
            {
              icon: CheckCircle2,
              title: 'Verify Results',
              desc: 'Audit real before-and-after operational metrics to generate verified investor-ready impact reports.',
              color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
              page: 'verification',
            },
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                onClick={() => onNavigate(item.page as PageId)}
                className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-1 transition-all cursor-pointer flex flex-col justify-between group"
              >
                <div>
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${item.color} group-hover:scale-105 transition-transform`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 mb-1.5">{item.title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{item.desc}</p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-emerald-700 group-hover:text-emerald-800">
                  <span>Explore</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Target SME Sector Overview */}
      <section className="bg-white rounded-2xl border border-slate-200/90 p-6 sm:p-8 shadow-xs">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-8 space-y-3">
            <h3 className="text-lg font-extrabold text-slate-900 tracking-tight">
              Built for Manufacturing, Textiles, Food Processing & Industrial SMEs
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Medium enterprises consume up to 40% of regional industrial power and water yet lack
              dedicated sustainability departments. ClimaCred AI provides institutional-grade
              climate intelligence at fractional software speeds.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              {['Textiles & Apparel', 'Food & Beverage', 'Auto Ancillaries', 'Plastics & Packaging', 'Foundries & Machining'].map((t) => (
                <span key={t} className="text-xs font-medium px-3 py-1 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
                  {t}
                </span>
              ))}
            </div>
          </div>

          <div className="lg:col-span-4 flex flex-col sm:flex-row lg:flex-col gap-3 justify-center">
            <button
              onClick={() => onNavigate('fingerprint')}
              className="w-full py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
            >
              <span>View Climate Fingerprint</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onNavigate('transformation')}
              className="w-full py-3 px-4 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
            >
              <span>View Roadmap Template</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
