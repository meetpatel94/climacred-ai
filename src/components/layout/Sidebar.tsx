import React from 'react';
import {
  Compass,
  LayoutDashboard,
  FileSpreadsheet,
  Building2,
  Zap,
  Droplets,
  Trash2,
  CloudFog,
  Truck,
  Fingerprint,
  Lightbulb,
  Sliders,
  Milestone,
  CheckCircle2,
  FileText,
  Settings,
  ChevronRight,
  ShieldCheck,
  X,
} from 'lucide-react';
import { PageId } from '../../types';

interface SidebarProps {
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  /** Real stored business name (null when the user has not saved a profile). */
  businessName?: string | null;
  businessSize?: string | null;
}

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ElementType;
  badge?: string;
  section?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'landing', label: 'Welcome / Home', icon: Compass, section: 'Overview' },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, section: 'Overview' },
  { id: 'profile', label: 'Business Profile', icon: Building2, section: 'Data & Assessment' },
  { id: 'assessment', label: 'Climate Assessment', icon: FileSpreadsheet, badge: 'Step 1', section: 'Data & Assessment' },
  { id: 'fingerprint', label: 'Climate Fingerprint', icon: Fingerprint, badge: 'Key', section: 'Climate Intelligence' },
  { id: 'energy', label: 'Energy', icon: Zap, section: 'Resource Streams' },
  { id: 'water', label: 'Water', icon: Droplets, section: 'Resource Streams' },
  { id: 'waste', label: 'Waste', icon: Trash2, section: 'Resource Streams' },
  { id: 'emissions', label: 'Emissions & Air', icon: CloudFog, section: 'Resource Streams' },
  { id: 'mobility', label: 'Mobility', icon: Truck, section: 'Resource Streams' },
  { id: 'solutions', label: 'Green Solutions', icon: Lightbulb, section: 'Decision Support' },
  { id: 'simulator', label: 'Scenario Simulator', icon: Sliders, badge: 'What-If', section: 'Decision Support' },
  { id: 'transformation', label: 'Transformation Plan', icon: Milestone, section: 'Roadmap & Action' },
  { id: 'verification', label: 'Impact Verification', icon: CheckCircle2, section: 'Roadmap & Action' },
  { id: 'report', label: 'Impact Report', icon: FileText, section: 'Roadmap & Action' },
  { id: 'settings', label: 'Settings', icon: Settings, section: 'System' },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onNavigate,
  mobileOpen,
  onCloseMobile,
  businessName = null,
  businessSize = null,
}) => {
  const initials = businessName
    ? businessName
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0]?.toUpperCase())
        .join('')
    : '—';
  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Main Sidebar */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-72 bg-white border-r border-slate-200/90 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-18 px-5 border-b border-slate-100 flex items-center justify-between">
          <div
            onClick={() => {
              onNavigate('landing');
              onCloseMobile();
            }}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 via-teal-600 to-emerald-700 flex items-center justify-center shadow-md shadow-emerald-500/20 group-hover:scale-105 transition-transform">
              <span className="text-white font-extrabold text-xl tracking-tighter">C</span>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-lg tracking-tight text-slate-900">
                  ClimaCred
                </span>
                <span className="text-[11px] font-bold px-1.5 py-0.5 rounded-md bg-emerald-100 text-emerald-800 tracking-wide uppercase">
                  AI
                </span>
              </div>
              <p className="text-[10px] text-slate-600 font-medium tracking-wide">
                Green Transformation Intel
              </p>
            </div>
          </div>

          <button
            onClick={onCloseMobile}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation scrollable items */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item, index) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            const prevItem = NAV_ITEMS[index - 1];
            const isNewSection = !prevItem || prevItem.section !== item.section;

            return (
              <React.Fragment key={item.id}>
                {isNewSection && item.section && (
                  <div className="pt-3 pb-1 px-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600">
                      {item.section}
                    </span>
                  </div>
                )}

                <button
                  onClick={() => {
                    onNavigate(item.id);
                    onCloseMobile();
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all group ${
                    isActive
                      ? 'bg-emerald-50 text-emerald-900 font-bold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon
                      className={`w-4 h-4 transition-colors ${
                        isActive ? 'text-emerald-700' : 'text-slate-500 group-hover:text-slate-700'
                      }`}
                    />
                    <span>{item.label}</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {item.badge && (
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                          isActive
                            ? 'bg-emerald-600 text-white'
                            : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                    {isActive && <ChevronRight className="w-3.5 h-3.5 text-emerald-600" />}
                  </div>
                </button>
              </React.Fragment>
            );
          })}
        </nav>

        {/* Bottom Profile & Version Area */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/60">
          <div className="p-2.5 rounded-xl bg-white border border-slate-200/80 shadow-2xs flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs shrink-0">
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-slate-800 truncate">
                  {businessName || 'No business profile'}
                </p>
                <div className="flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  <span className="text-[10px] text-slate-600 truncate">
                    {businessSize || 'Add your data to begin'}
                  </span>
                </div>
              </div>
            </div>
            <span className="text-[10px] font-mono font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
              v1.0
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};
