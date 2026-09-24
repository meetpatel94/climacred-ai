import React from 'react';
import { Menu, Bell, Download, Sparkles, Moon, Sun } from 'lucide-react';
import { PageId } from '../../types';
import { useTheme } from '../../utils/theme';

interface HeaderProps {
  currentPage: PageId;
  onOpenMobile: () => void;
  onNavigate: (page: PageId) => void;
  onQuickAction?: () => void;
}

const PAGE_METADATA: Record<PageId, { title: string; description: string; badge?: string }> = {
  landing: {
    title: 'Turn Business Data Into Climate Action',
    description: 'Autonomous Climate Transformation and Green Investment Intelligence for SMEs.',
  },
  dashboard: {
    title: 'Business Climate Dashboard',
    description: 'Real-time overview of operational footprint, resource stresses, and next actionable steps.',
    badge: 'Live Overview',
  },
  profile: {
    title: 'Business Profile & Operations',
    description: 'Configure organization parameters, facility size, shift volume, and production baseline.',
  },
  assessment: {
    title: 'Climate Assessment Data Collection',
    description: 'Comprehensive resource audit covering Energy, Water, Waste, Emissions, and Mobility.',
    badge: 'Step 1 of 5',
  },
  fingerprint: {
    title: 'Multi-Dimensional Climate Fingerprint',
    description: 'AI-evaluated environmental readiness score and dimensional vulnerability breakdown.',
    badge: 'Core Diagnostic',
  },
  energy: {
    title: 'Energy Intelligence & Grid Decarbonization',
    description: 'Monthly electricity consumption, load telemetry, diesel gensets, and clean solar potential.',
  },
  water: {
    title: 'Water Intelligence & Effluent Management',
    description: 'Freshwater consumption, wastewater treatment status, leakage alerts, and circular recycling.',
  },
  waste: {
    title: 'Waste & Circular Economy Intelligence',
    description: 'Industrial scrap streams, hazardous waste, segregation compliance, and recovery yields.',
  },
  emissions: {
    title: 'Emissions & Air Quality Telemetry',
    description: 'Scope 1 & 2 carbon footprint analysis, combustion fuels, and stack abatement systems.',
  },
  mobility: {
    title: 'Mobility & Logistics Decarbonization',
    description: 'Commercial fleet dispatch, transport fuel efficiency, and commercial EV transition.',
  },
  solutions: {
    title: 'Green Intervention Library',
    description: 'Catalog of vetted climate solutions, equipment upgrades, and circular interventions.',
    badge: '10 Solutions Available',
  },
  simulator: {
    title: 'Scenario & Green Investment Simulator',
    description: 'Simulate the financial and environmental outcomes of deploying multiple green interventions.',
    badge: 'Interactive What-If',
  },
  transformation: {
    title: 'Green Transformation Roadmap',
    description: 'Phased, prioritized capital and operational intervention plan for management and engineers.',
  },
  verification: {
    title: 'Impact Verification (Before vs After)',
    description: 'Comparative verification telemetry to track realized savings and emission abatements.',
    badge: 'Audit Grade',
  },
  report: {
    title: 'Climate Impact & Transformation Report',
    description: 'Exportable executive summary and technical dossier for management, bankers, and buyers.',
    badge: 'Executive Dossier',
  },
  settings: {
    title: 'Platform Preferences & Data Management',
    description: 'Manage currency, measurement units, notification rules, and export controls.',
  },
};

export const Header: React.FC<HeaderProps> = ({
  currentPage,
  onOpenMobile,
  onNavigate,
}) => {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  const meta = PAGE_METADATA[currentPage] || {
    title: 'ClimaCred AI',
    description: 'Climate Transformation Intelligence',
  };

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-6 lg:px-8 py-3.5 transition-all">
      <div className="flex items-center justify-between gap-4">
        {/* Left: Mobile menu toggle + Page title */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onOpenMobile}
            className="p-2 -ml-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 lg:hidden focus:outline-hidden"
            aria-label="Open sidebar navigation"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight truncate">
                {meta.title}
              </h1>
              {meta.badge && (
                <span className="hidden sm:inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                  {meta.badge}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 hidden sm:block truncate">
              {meta.description}
            </p>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {currentPage !== 'simulator' && (
            <button
              onClick={() => onNavigate('simulator')}
              className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>Simulate ROI</span>
            </button>
          )}

          {currentPage !== 'report' && (
            <button
              onClick={() => onNavigate('report')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs shadow-emerald-600/30 transition-all hover:shadow-md"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Impact Report</span>
              <span className="sm:hidden">Report</span>
            </button>
          )}

          <div className="h-6 w-[1px] bg-slate-200 mx-1 hidden sm:block" />

          {/* Notification bell mock */}
          <button
            onClick={() => alert('ClimaCred AI Notifications: All 6 resource monitors operating normally.')}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 relative transition-colors"
            title="System alerts"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-white" />
          </button>

          {/* Dark mode toggle - keeps the existing navbar layout */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-pressed={isDark}
            data-testid="theme-toggle"
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
};
