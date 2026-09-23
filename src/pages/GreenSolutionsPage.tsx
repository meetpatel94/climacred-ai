import React, { useState, useEffect } from 'react';
import {
  Lightbulb,
  Search,
  Zap,
  Droplets,
  Trash2,
  Truck,
  Layers,
  Sparkles,
  ArrowRight,
  TrendingDown,
  Clock,
  ShieldAlert,
  Loader2,
} from 'lucide-react';
import { GreenSolution, PageId } from '../types';
import { GREEN_SOLUTIONS_LIBRARY } from '../services/mockData';
import { DemoTag } from '../components/common/StatusBadge';
import { getGreenSolutions, getRecommendedSolutions } from '../services/api';

interface GreenSolutionsPageProps {
  onNavigate: (page: PageId) => void;
  onSelectSolutionForSimulator?: (solutionId: string) => void;
}

const CATEGORIES = ['All', 'Energy', 'Water', 'Waste', 'Mobility', 'Operations', 'Materials'];

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  Energy: Zap,
  Water: Droplets,
  Waste: Trash2,
  Mobility: Truck,
  Operations: Layers,
  Materials: Layers,
};

export const GreenSolutionsPage: React.FC<GreenSolutionsPageProps> = ({
  onNavigate,
  onSelectSolutionForSimulator,
}) => {
  const [activeCategory, setActiveCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModalSolution, setSelectedModalSolution] = useState<GreenSolution | null>(null);
  const [solutions, setSolutions] = useState<GreenSolution[]>(GREEN_SOLUTIONS_LIBRARY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommendedIds, setRecommendedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const fetched = await getGreenSolutions(activeCategory);
        if (!cancelled) {
          setSolutions(fetched.length ? fetched : GREEN_SOLUTIONS_LIBRARY);
        }
        // Also fetch recommendations to highlight personalized top picks
        try {
          const recs = await getRecommendedSolutions(5);
          if (!cancelled && recs.length) {
            setRecommendedIds(new Set(recs.map((r: any) => r.solution_id || r.solution?.id)));
          }
        } catch {}
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message || 'Failed to load solutions catalog');
          // Keep mock fallback already set
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [activeCategory]);

  const filteredSolutions = solutions.filter((s) => {
    const matchesCategory = activeCategory === 'All' || s.category.toLowerCase() === activeCategory.toLowerCase();
    const matchesSearch =
      s.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.problemAddressed.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.shortDesc.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-8 max-w-6xl pb-16">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <Lightbulb className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Green Intervention Library & Solutions Catalog
            </h2>
            <DemoTag label={loading ? "Loading live catalog..." : "Live Backend Catalog"} />
          </div>
          <p className="text-xs text-slate-600">
            A curated database of vetted hardware, clean technology, and operational retrofits designed for SME payback periods under 4 years. <span className="text-emerald-700 font-semibold">{recommendedIds.size ? "Personalized recommendations highlighted." : ""}</span>
          </p>
          {error && <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1 mt-1">{error} – showing cached data.</p>}
        </div>

        <button
          onClick={() => onNavigate('simulator')}
          className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span>Launch Scenario Simulator</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                activeCategory === cat
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search solutions or equipment..."
            className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:border-emerald-600 outline-hidden"
          />
        </div>
      </div>

      {loading && <div className="flex items-center gap-2 text-xs text-slate-600"><Loader2 className="w-4 h-4 animate-spin" /> Loading solutions from backend...</div>}

      {/* Solutions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredSolutions.map((sol) => {
          const Icon = CATEGORY_ICONS[sol.category] || Layers;
          const isRecommended = recommendedIds.has(sol.id);

          return (
            <div
              key={sol.id}
              className={`bg-white border rounded-2xl p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between group space-y-4 ${isRecommended ? 'border-emerald-300 ring-1 ring-emerald-200' : 'border-slate-200/90'}`}
            >
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600">
                      {sol.category}
                    </span>
                  </div>

                  {sol.featured && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      Top SME ROI
                    </span>
                  )}
                </div>
                {isRecommended && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 inline-flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Personalized Top Pick
                  </span>
                )}

                {/* Title & Short Description */}
                <div>
                  <h3 className="text-sm font-bold text-slate-900 group-hover:text-emerald-800 transition-colors leading-snug">
                    {sol.title}
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 line-clamp-2">{sol.shortDesc}</p>
                </div>

                {/* Problem Addressed Box */}
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-[11px] text-slate-700">
                  <span className="font-bold text-slate-900 block text-[10px] uppercase mb-0.5">
                    Problem Addressed:
                  </span>
                  <p className="line-clamp-2">{sol.problemAddressed}</p>
                </div>

                {/* Financial & Environmental Specs */}
                <div className="grid grid-cols-2 gap-2 pt-1 text-xs">
                  <div className="p-2 rounded-lg bg-slate-50">
                    <span className="text-[10px] text-slate-600 block">Est. Investment Range</span>
                    <span className="font-bold text-slate-900 text-xs">{sol.investmentRange}</span>
                  </div>

                  <div className="p-2 rounded-lg bg-emerald-50">
                    <span className="text-[10px] text-emerald-800 block">Potential Annual Savings</span>
                    <span className="font-bold text-emerald-700 text-xs">
                      ₹{(sol.potentialAnnualSavingsInr / 100000).toFixed(2)} Lakh / yr
                    </span>
                  </div>
                </div>

                {/* Payback & Difficulty Badges */}
                <div className="flex items-center justify-between text-[11px] pt-1">
                  <span className="flex items-center gap-1 text-slate-600 font-medium">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    Payback: <strong className="text-slate-900">{sol.estimatedPaybackPeriodYears} yrs</strong>
                  </span>

                  <span className="flex items-center gap-1 text-slate-600 font-medium">
                    <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />
                    CO₂: <strong className="text-emerald-700">{sol.co2ReductionTonnesPerYear} MT/yr</strong>
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-100 flex items-center gap-2">
                <button
                  onClick={() => setSelectedModalSolution(sol)}
                  className="flex-1 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  View Details
                </button>

                <button
                  onClick={() => {
                    if (onSelectSolutionForSimulator) {
                      onSelectSolutionForSimulator(sol.id);
                    }
                    onNavigate('simulator');
                  }}
                  className="px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1 transition-colors"
                  title="Simulate in Scenario"
                >
                  <span>Simulate</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filteredSolutions.length === 0 && (
        <div className="text-center py-12 bg-white border border-slate-200 rounded-2xl">
          <p className="text-sm font-semibold text-slate-700">No solutions match your filter.</p>
          <p className="text-xs text-slate-600">Try adjusting category or search term.</p>
        </div>
      )}

      {/* Detail Modal */}
      {selectedModalSolution && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-scale-up">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">
                  {selectedModalSolution.category} Intervention Dossier
                </span>
                <h3 className="text-lg font-extrabold text-slate-900 mt-0.5">
                  {selectedModalSolution.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedModalSolution(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1.5 text-xs">
              <span className="font-bold text-slate-900 block uppercase text-[10px]">
                Target Inefficiency & Context
              </span>
              <p className="text-slate-700 leading-relaxed">
                {selectedModalSolution.problemAddressed}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl border border-slate-100 bg-slate-50/50">
                <span className="text-[10px] text-slate-600 uppercase font-semibold">
                  Investment Estimate
                </span>
                <p className="text-sm font-bold text-slate-900">{selectedModalSolution.investmentRange}</p>
              </div>

              <div className="p-3 rounded-xl border border-emerald-100 bg-emerald-50/50">
                <span className="text-[10px] text-emerald-800 uppercase font-semibold">
                  Annual OPEX Savings
                </span>
                <p className="text-sm font-bold text-emerald-700">
                  ₹{(selectedModalSolution.potentialAnnualSavingsInr / 100000).toFixed(2)} Lakh / year
                </p>
              </div>

              <div className="p-3 rounded-xl border border-slate-100 bg-slate-50/50">
                <span className="text-[10px] text-slate-600 uppercase font-semibold">
                  Payback Period
                </span>
                <p className="text-sm font-bold text-slate-900">
                  {selectedModalSolution.estimatedPaybackPeriodYears} Years
                </p>
              </div>

              <div className="p-3 rounded-xl border border-slate-100 bg-slate-50/50">
                <span className="text-[10px] text-slate-600 uppercase font-semibold">
                  Abatement Impact
                </span>
                <p className="text-sm font-bold text-emerald-700">
                  {selectedModalSolution.co2ReductionTonnesPerYear} MT CO₂e / yr
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-amber-50/80 border border-amber-200 text-xs text-amber-900 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <span>
                All pricing and reduction metrics are backend-calculated estimates using configurable assumptions. Formal quotes require site audit verification. Not a guaranteed saving.
              </span>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => setSelectedModalSolution(null)}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
              <button
                onClick={() => {
                  if (onSelectSolutionForSimulator) {
                    onSelectSolutionForSimulator(selectedModalSolution.id);
                  }
                  setSelectedModalSolution(null);
                  onNavigate('simulator');
                }}
                className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md"
              >
                Simulate Scenario
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
