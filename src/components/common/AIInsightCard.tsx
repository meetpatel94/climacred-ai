import React from 'react';
import { Sparkles, AlertTriangle, ArrowRight } from 'lucide-react';

interface AIInsightCardProps {
  title?: string;
  insight: string;
  actionText?: string;
  onActionClick?: () => void;
  type?: 'insight' | 'warning' | 'recommendation';
}

export const AIInsightCard: React.FC<AIInsightCardProps> = ({
  title = 'ClimaCred AI Observation',
  insight,
  actionText,
  onActionClick,
  type = 'insight',
}) => {
  const isWarning = type === 'warning';

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border p-5 transition-all ${
        isWarning
          ? 'bg-amber-50/70 border-amber-200/80 text-amber-950'
          : 'bg-gradient-to-br from-emerald-50/70 via-teal-50/40 to-slate-50 border-emerald-200/80 text-emerald-950'
      }`}
    >
      <div className="flex items-start gap-3.5">
        <div
          className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
            isWarning ? 'bg-amber-100 text-amber-700' : 'bg-emerald-600 text-white shadow-sm'
          }`}
        >
          {isWarning ? <AlertTriangle className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
              {title}
            </span>
            <span className="text-[10px] font-semibold bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded">
              AI Forecast
            </span>
          </div>
          <p className="text-sm font-medium text-slate-700 leading-relaxed">{insight}</p>

          {actionText && (
            <button
              onClick={onActionClick}
              className="mt-3 inline-flex items-center text-xs font-semibold text-emerald-700 hover:text-emerald-800 hover:underline gap-1 transition-colors"
            >
              <span>{actionText}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
