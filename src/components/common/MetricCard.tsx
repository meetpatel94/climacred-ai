import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: LucideIcon;
  iconBgColor?: string;
  iconColor?: string;
  helperText?: string;
  badge?: string;
  badgeColor?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  change,
  changeType = 'neutral',
  icon: Icon,
  iconBgColor = 'bg-emerald-50',
  iconColor = 'text-emerald-700',
  helperText,
  badge,
  badgeColor = 'bg-slate-100 text-slate-700',
}) => {
  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between group">
      <div>
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">{title}</span>
          <div className="flex items-center space-x-2">
            {badge && (
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${badgeColor}`}>
                {badge}
              </span>
            )}
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${iconBgColor} ${iconColor} group-hover:scale-105 transition-transform`}>
              <Icon className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="flex items-baseline space-x-1.5 mt-1">
          <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">{value}</span>
          {unit && <span className="text-xs font-medium text-slate-600">{unit}</span>}
        </div>
      </div>

      {(change || helperText) && (
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          {change && (
            <span
              className={`font-semibold flex items-center ${
                changeType === 'positive'
                  ? 'text-emerald-600'
                  : changeType === 'negative'
                  ? 'text-rose-600'
                  : 'text-slate-600'
              }`}
            >
              {change}
            </span>
          )}
          {helperText && <span className="text-slate-600 text-[11px] truncate max-w-[200px]" title={helperText}>{helperText}</span>}
        </div>
      )}
    </div>
  );
};
