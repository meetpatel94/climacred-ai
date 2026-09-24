import React, { useEffect, useState } from 'react';
import {
  Truck,
  Fuel,
  Zap,
  Navigation,
  ArrowRight,
  TrendingDown,
} from 'lucide-react';
import { MetricCard } from '../components/common/MetricCard';
import { EmptyState } from '../components/common/EmptyState';
import { AIInsightCard } from '../components/common/AIInsightCard';
import { EMPTY_STATES } from '../services/defaults';
import { getMobilityAnalytics, getClimateFingerprint } from '../services/api';
import { PageId } from '../types';

interface MobilityPageProps {
  onNavigate: (page: PageId) => void;
}

export const MobilityPage: React.FC<MobilityPageProps> = ({ onNavigate }) => {
  const [analytics, setAnalytics] = useState<any>(null);
  const [dimension, setDimension] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [mobility, fingerprint] = await Promise.all([getMobilityAnalytics(), getClimateFingerprint()]);
      if (cancelled) return;
      setAnalytics(mobility);
      setDimension(fingerprint?.dimensions?.find((d: any) => d.dimension === 'Mobility') || null);
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const available = analytics?.available === true;
  const vehicles: number | null = available ? analytics?.delivery_vehicles_count ?? null : null;
  const monthlyFuel: number | null = available ? analytics?.monthly_fuel_litres ?? null : null;
  const annualFuel: number | null = available ? analytics?.annual_fuel_litres ?? null : null;
  const fuelType: string | null = available ? analytics?.vehicle_fuel_type ?? null : null;
  const emissions: number | null = available ? analytics?.monthly_mobility_emissions_tonnes_co2e ?? null : null;
  const evPercent: number | null = available ? analytics?.ev_adopted_percent ?? null : null;
  const evCount: number | null = available ? analytics?.ev_adopted_count_estimate ?? null : null;
  const fuelPerVehicle =
    monthlyFuel !== null && vehicles ? monthlyFuel / vehicles : null;
  const potentialSaving: number | null = available ? analytics?.potential_monthly_fuel_saving_litres ?? null : null;
  const potentialEmissionSaving: number | null = available
    ? analytics?.potentialMonthlyEmissionsSaving_tonnes ?? null
    : null;
  const factor = available ? analytics?.fuel_emission_factor_used?.factor ?? null : null;

  if (loading) {
    return (
      <div className="space-y-8 max-w-6xl pb-16 animate-pulse">
        <div className="h-24 bg-slate-100 rounded-2xl" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-slate-100 rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl pb-16">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center">
              <Truck className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Mobility & Commercial Logistics Decarbonization
            </h2>
          </div>
          <p className="text-xs text-slate-600">
            Fleet size, fuel burn and EV transition potential, calculated from your recorded mobility data.
          </p>
        </div>

        <button
          onClick={() => onNavigate('solutions')}
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Commercial EV Fleet</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {!available ? (
        <EmptyState
          icon={Truck}
          title={EMPTY_STATES.mobility}
          message="Record your delivery fleet size, fuel type and monthly fuel use to calculate mobility emissions and EV potential."
          actionLabel="Complete Climate Assessment"
          onAction={() => onNavigate('assessment')}
        />
      ) : (
        <>
          {/* 4 Metric Cards - calculated */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Active Fleet Size"
              value={vehicles !== null ? vehicles.toLocaleString() : '—'}
              unit="Delivery Vehicles"
              icon={Truck}
              iconBgColor="bg-indigo-50"
              iconColor="text-indigo-600"
              helperText={fuelType ? `Recorded fuel type: ${fuelType}` : undefined}
            />

            <MetricCard
              title="Monthly Fuel Consumption"
              value={monthlyFuel !== null ? monthlyFuel.toLocaleString() : '—'}
              unit="Litres / mo"
              icon={Fuel}
              iconBgColor="bg-rose-50"
              iconColor="text-rose-600"
              helperText={annualFuel !== null ? `${annualFuel.toLocaleString()} L / yr at current rate` : undefined}
            />

            <MetricCard
              title="Mobility Emissions"
              value={emissions !== null ? emissions.toFixed(2) : '—'}
              unit="MT CO₂e / mo"
              icon={TrendingDown}
              iconBgColor="bg-slate-100"
              iconColor="text-slate-700"
              helperText={factor !== null ? `Factor ${factor} kg CO₂e/L (configurable)` : undefined}
            />

            <MetricCard
              title="EV Fleet Adoption"
              value={evPercent !== null ? `${evPercent}` : '—'}
              unit="% of fleet"
              icon={Zap}
              iconBgColor="bg-amber-50"
              iconColor="text-amber-600"
              helperText={
                evCount !== null && vehicles
                  ? `≈${evCount} of ${vehicles} recorded vehicles`
                  : 'Recorded in your assessment'
              }
            />
          </div>

          {/* Fleet telemetry summary - computed, not per-vehicle fiction */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">Fleet Fuel Intensity (From Recorded Data)</h3>
                <p className="text-xs text-slate-600">
                  Derived from the fleet size and monthly fuel volume you recorded. Per-vehicle mileage telemetry is
                  not collected by ClimaCred, so none is shown.
                </p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                Latest recorded month
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-4">Metric</th>
                    <th className="py-3 px-4">Recorded / Calculated Value</th>
                    <th className="py-3 px-4">Basis</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">Vehicles recorded</td>
                    <td className="py-3 px-4 text-slate-700 font-medium">{vehicles ?? '—'}</td>
                    <td className="py-3 px-4 text-slate-600">Mobility section of your assessment</td>
                  </tr>
                  <tr className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">Fuel per vehicle</td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {fuelPerVehicle !== null ? `${fuelPerVehicle.toFixed(1)} L / month` : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-600">Monthly fuel ÷ vehicles</td>
                  </tr>
                  <tr className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">Annual fuel</td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {annualFuel !== null ? `${annualFuel.toLocaleString()} L / yr` : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-600">Monthly fuel × 12</td>
                  </tr>
                  <tr className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">Annual mobility emissions</td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {analytics?.annual_mobility_emissions_tonnes_co2e !== undefined
                        ? `${analytics.annual_mobility_emissions_tonnes_co2e} MT CO₂e / yr`
                        : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-600">Monthly emissions × 12</td>
                  </tr>
                  <tr className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">Potential monthly fuel saving</td>
                    <td className="py-3 px-4 text-emerald-700 font-bold">
                      {potentialSaving !== null ? `${potentialSaving.toLocaleString()} L / month` : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      30% cut via EV + route optimization on non-electric fleet
                      {potentialEmissionSaving !== null ? ` (≈${potentialEmissionSaving} MT CO₂e/mo)` : ''}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {Array.isArray(analytics?.assumptions) && (
              <ul className="text-[11px] text-slate-600 list-disc list-inside space-y-0.5">
                {analytics.assumptions.map((item: string, idx: number) => <li key={idx}>{item}</li>)}
              </ul>
            )}
          </div>

          {/* Roadmap block driven by the calculated EV gap */}
          <div className="bg-gradient-to-br from-indigo-50/70 via-slate-50 to-white border border-indigo-100 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-2.5">
              <Navigation className="w-5 h-5 text-indigo-700" />
              <h3 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider">
                EV Transition Gap (Calculated)
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-white border border-indigo-100 shadow-2xs space-y-1">
                <span className="text-xs font-bold text-slate-800">Current electric share</span>
                <p className="text-slate-600">
                  {evPercent !== null ? `${evPercent}% of the recorded fleet is electric.` : 'Not recorded.'}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-white border border-indigo-100 shadow-2xs space-y-1">
                <span className="text-xs font-bold text-slate-800">Non-electric vehicles</span>
                <p className="text-slate-600">
                  {vehicles !== null && evCount !== null
                    ? `${Math.max(0, vehicles - Math.round(evCount))} of ${vehicles} recorded vehicles still use combustion fuel.`
                    : 'Not recorded.'}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-white border border-indigo-100 shadow-2xs space-y-1">
                <span className="text-xs font-bold text-slate-800">Modelled improvement</span>
                <p className="text-slate-600">
                  {analytics?.potential_improvement_percent !== undefined
                    ? `Up to ${analytics.potential_improvement_percent}% improvement potential modelled on the current mix.`
                    : 'Not available.'}
                </p>
              </div>
            </div>
          </div>
        </>
      )}

      {dimension && (
        <AIInsightCard
          title="Calculated Mobility Finding"
          insight={`${dimension.currentStatus}. ${dimension.primaryCause}. Opportunity: ${dimension.improvementOpportunity}`}
          actionText="Review mobility interventions"
          onActionClick={() => onNavigate('solutions')}
        />
      )}

      <AIInsightCard
        title="Ask The AI Assistant About Fleet Options"
        insight={
          available
            ? 'Ask the ClimaCred AI Assistant which mobility interventions fit your recorded fleet and budget — it will only use the calculated figures above.'
            : EMPTY_STATES.aiNoData
        }
        actionText="Open the solution catalog"
        onActionClick={() => onNavigate('solutions')}
      />
    </div>
  );
};
