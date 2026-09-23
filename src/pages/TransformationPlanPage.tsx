import React, { useState } from 'react';
import {
  Milestone,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';
import { TransformationPhaseItem, PageId } from '../types';
import { DemoTag } from '../components/common/StatusBadge';
import { AIInsightCard } from '../components/common/AIInsightCard';

interface TransformationPlanPageProps {
  planItems: TransformationPhaseItem[];
  onUpdateStatus: (id: string, status: 'Pending' | 'In Progress' | 'Completed') => void;
  onNavigate: (page: PageId) => void;
}

export const TransformationPlanPage: React.FC<TransformationPlanPageProps> = ({
  planItems,
  onUpdateStatus,
  onNavigate,
}) => {
  const [filterPhase, setFilterPhase] = useState<string>('All');

  const phases = ['All', 'Phase 1', 'Phase 2', 'Phase 3', 'Phase 4'];

  const filteredItems = planItems.filter(
    (item) => filterPhase === 'All' || item.phase === filterPhase
  );

  const completedCount = planItems.filter((i) => i.status === 'Completed').length;
  const progressPercent = Math.round((completedCount / planItems.length) * 100);

  return (
    <div className="space-y-8 max-w-6xl pb-16">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <Milestone className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Personalized Green Transformation Roadmap
            </h2>
            <DemoTag label="Execution Blueprint" />
          </div>
          <p className="text-xs text-slate-600">
            A structured, 4-phase capital and operational sequence designed for plant engineers and finance managers.
          </p>
        </div>

        <button
          onClick={() => onNavigate('verification')}
          className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Verify Impact Post-Implementation</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Progress & Milestone Summary Strip */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Roadmap Execution
          </span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-black text-slate-900">{progressPercent}%</span>
            <span className="text-xs font-semibold text-emerald-700">
              {completedCount} of {planItems.length} Actions
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
            <div className="h-full bg-emerald-600 rounded-full" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Phase 1: Low-Hanging
          </span>
          <p className="text-lg font-extrabold text-slate-900">Month 1 – 3</p>
          <p className="text-[11px] text-emerald-700 font-semibold">Leak fixing & off-cut baling</p>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Phase 2: Efficiency
          </span>
          <p className="text-lg font-extrabold text-slate-900">Month 4 – 7</p>
          <p className="text-[11px] text-amber-700 font-semibold">VFD motors & boiler economizer</p>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Phase 3: CAPEX Solar & RO
          </span>
          <p className="text-lg font-extrabold text-slate-900">Month 8 – 14</p>
          <p className="text-[11px] text-cyan-700 font-semibold">75 kWp Solar & Water RO</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {phases.map((p) => (
          <button
            key={p}
            onClick={() => setFilterPhase(p)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              filterPhase === p
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Visual Roadmap Timeline List */}
      <div className="space-y-4">
        {filteredItems.map((item, index) => {
          const isDone = item.status === 'Completed';
          const isInProgress = item.status === 'In Progress';

          return (
            <div
              key={item.id}
              className={`bg-white border rounded-2xl p-5 shadow-xs transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
                isDone
                  ? 'border-emerald-200 bg-emerald-50/20'
                  : isInProgress
                  ? 'border-amber-200 bg-amber-50/20'
                  : 'border-slate-200/90'
              }`}
            >
              {/* Left identifier & timeline marker */}
              <div className="flex items-start gap-3.5 min-w-0">
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold ${
                    isDone
                      ? 'bg-emerald-600 text-white'
                      : isInProgress
                      ? 'bg-amber-500 text-white'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {isDone ? <CheckCircle2 className="w-5 h-5" /> : index + 1}
                </div>

                <div className="space-y-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                      {item.phase}
                    </span>
                    <span className="text-[10px] font-semibold text-slate-600">{item.timeframe}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        item.priority === 'High'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {item.priority} Priority
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      {item.category}
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-slate-900 leading-snug">{item.action}</h4>
                  <p className="text-xs text-slate-600 font-medium">{item.expectedBenefit}</p>
                </div>
              </div>

              {/* Right: Cost & Status Selector */}
              <div className="flex flex-wrap items-center gap-4 shrink-0 w-full md:w-auto justify-between md:justify-end pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
                <div className="text-left md:text-right">
                  <span className="text-[10px] font-semibold uppercase text-slate-600 block">
                    Estimated Outlay
                  </span>
                  <span className="text-xs font-bold text-slate-900">{item.estimatedCost}</span>
                </div>

                {/* Status Switcher (Interactive Phase 1 Feature) */}
                <div className="relative">
                  <select
                    value={item.status}
                    onChange={(e) =>
                      onUpdateStatus(item.id, e.target.value as 'Pending' | 'In Progress' | 'Completed')
                    }
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold border outline-hidden transition-colors cursor-pointer ${
                      item.status === 'Completed'
                        ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                        : item.status === 'In Progress'
                        ? 'bg-amber-100 text-amber-800 border-amber-300'
                        : 'bg-slate-100 text-slate-700 border-slate-300'
                    }`}
                  >
                    <option value="Pending">Pending</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Completed">Completed</option>
                  </select>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* AI Roadmap Advice */}
      <AIInsightCard
        title="Implementation Sequence Advisory"
        insight="Execute Phase 1 leak repairs and scrap baling immediately. The resulting ₹4,85,000 in immediate annualized utility savings and scrap income will directly co-finance the Phase 2 VFD and motor retrofits without stressing working capital."
        actionText="Proceed to Impact Verification"
        onActionClick={() => onNavigate('verification')}
      />
    </div>
  );
};
