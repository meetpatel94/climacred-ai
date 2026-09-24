import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  /** compact = inline card used inside sections */
  variant?: 'card' | 'inline';
}

/**
 * Standard empty state used everywhere real data is missing.
 * Missing data is never replaced by zeros, demo values or sample charts.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  message,
  actionLabel,
  onAction,
  variant = 'card',
}) => {
  const content = (
    <div className="flex flex-col items-center justify-center text-center gap-2 py-6 px-4">
      <span className="w-10 h-10 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center">
        <Icon className="w-5 h-5" />
      </span>
      <p className="text-sm font-bold text-slate-800">{title}</p>
      {message && <p className="text-xs text-slate-600 max-w-md leading-relaxed">{message}</p>}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-1 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );

  if (variant === 'inline') return content;

  return (
    <div className="bg-white border border-dashed border-slate-300 rounded-2xl">{content}</div>
  );
};
