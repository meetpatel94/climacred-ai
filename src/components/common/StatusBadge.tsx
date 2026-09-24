import React from 'react';
import { ImpactSeverity } from '../../types';

interface ImpactBadgeProps {
  level: ImpactSeverity;
  size?: 'sm' | 'md';
}

export const ImpactBadge: React.FC<ImpactBadgeProps> = ({ level, size = 'md' }) => {
  const styles = {
    Low: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Moderate: 'bg-amber-50 text-amber-700 border-amber-200',
    High: 'bg-orange-50 text-orange-700 border-orange-200',
    'Very High': 'bg-rose-50 text-rose-700 border-rose-200',
  }[level] || 'bg-slate-50 text-slate-700 border-slate-200';

  const dotColor = {
    Low: 'bg-emerald-500',
    Moderate: 'bg-amber-500',
    High: 'bg-orange-500',
    'Very High': 'bg-rose-500',
  }[level] || 'bg-slate-400';

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 font-semibold rounded-full border ${styles} ${sizeClasses}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      {level} Impact
    </span>
  );
};
