import React, { useState } from 'react';
import {
  Settings,
  Save,
  Bell,
  Globe,
  Database,
  Check,
  Trash2,
} from 'lucide-react';
import { UserPreferences } from '../types';
import { resetAllStoredData } from '../services/api';

interface SettingsPageProps {
  preferences: UserPreferences;
  onSavePreferences: (updated: Partial<UserPreferences>) => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  preferences,
  onSavePreferences,
}) => {
  const [formData, setFormData] = useState<UserPreferences>({ ...preferences });
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSavePreferences(formData);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="space-y-6 max-w-4xl pb-16">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-800 flex items-center justify-center">
              <Settings className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Platform Configuration & Preferences
            </h2>
          </div>
          <p className="text-xs text-slate-600">
            Configure currency units, metric thresholds, notification cadences and the backend connection.
          </p>
        </div>

        {savedSuccess && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-800 text-xs font-semibold">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>Preferences Saved</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section 1: Units & Regional Formats */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <h3 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Globe className="w-4 h-4 text-emerald-600" />
            Regional & Unit Standards
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Currency Display
              </label>
              <select
                value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value as any })}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden bg-white"
              >
                <option value="INR">Indian Rupee (₹ INR)</option>
                <option value="USD">US Dollar ($ USD)</option>
                <option value="EUR">Euro (€ EUR)</option>
              </select>
              <p className="text-[11px] text-slate-600 mt-1">Converts CAPEX estimates and annual utility savings.</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Measurement Unit Standard
              </label>
              <select
                value={formData.measurementUnit}
                onChange={(e) => setFormData({ ...formData, measurementUnit: e.target.value as any })}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden bg-white"
              >
                <option value="Metric">Metric (kWh, Litres, kg, MT CO₂e)</option>
                <option value="Imperial">Imperial (kWh, Gallons, lbs, Short Tons)</option>
              </select>
              <p className="text-[11px] text-slate-600 mt-1">Used across all resource stream diagnostics.</p>
            </div>
          </div>
        </div>

        {/* Section 2: Notifications & Reporting Rules */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <h3 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Bell className="w-4 h-4 text-emerald-600" />
            Alerts & Automated Dispatch
          </h3>

          <div className="space-y-3">
            <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50 transition-colors">
              <input
                type="checkbox"
                checked={formData.emailAlerts}
                onChange={(e) => setFormData({ ...formData, emailAlerts: e.target.checked })}
                className="mt-0.5 w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
              />
              <div>
                <p className="text-xs font-bold text-slate-900">Monthly Diagnostic Anomaly Alerts</p>
                <p className="text-[11px] text-slate-600">
                  Receive an automated email alert when utility draw surges &gt;15% above seasonal factory baseline.
                </p>
              </div>
            </label>

            <label className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50 transition-colors">
              <input
                type="checkbox"
                checked={formData.benchmarkSharing}
                onChange={(e) => setFormData({ ...formData, benchmarkSharing: e.target.checked })}
                className="mt-0.5 w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
              />
              <div>
                <p className="text-xs font-bold text-slate-900">Anonymized Regional Cluster Benchmarking</p>
                <p className="text-[11px] text-slate-600">
                  Allow your anonymized energy and water efficiency data to be aggregated into regional cluster peer percentiles.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Section 3: Phase 2 Backend Readiness */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-teal-600" />
              Phase 2 System Architecture Readiness
            </h3>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-teal-100 text-teal-800 font-mono">
              FASTAPI_REST_READY
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 text-white font-mono text-xs space-y-1.5 overflow-x-auto">
            <p className="text-emerald-400 font-bold">// Phase 2 Endpoint Mappings</p>
            <p className="text-slate-300">GET  /api/v1/profile         → Backend (stored data only)</p>
            <p className="text-slate-300">POST /api/v1/assessment      → Backend (calculations)</p>
            <p className="text-slate-300">GET  /api/v1/climate-fingerprint → Backend (calculations)</p>
            <p className="text-slate-300">POST /api/v1/scenarios/simulate  → Backend (simulator)</p>
            <p className="text-slate-300">GET  /api/v1/transformation-plan → Backend (generated plan)</p>
            <p className="text-slate-300">POST /api/v1/ai/chat          → Backend + Gemini (key server-side)</p>
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="submit"
            className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md flex items-center gap-2 transition-all hover:scale-[1.01]"
          >
            <Save className="w-4 h-4" />
            <span>Save Preferences</span>
          </button>

          <button
            type="button"
            onClick={async () => {
              if (
                confirm(
                  'Delete ALL stored business data (profile, assessment, fingerprint, plans, scenarios, reports, impact records and AI chat history)? The app will be empty afterwards. This cannot be undone.'
                )
              ) {
                try {
                  await resetAllStoredData();
                  window.location.reload();
                } catch (err: any) {
                  alert(`Reset failed - nothing was deleted: ${err?.message || 'backend unreachable'}`);
                }
              }
            }}
            data-testid="reset-all-data"
            className="text-xs font-semibold text-rose-600 hover:text-rose-700 hover:underline flex items-center gap-1"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Reset All Stored Data</span>
          </button>
        </div>
      </form>
    </div>
  );
};
