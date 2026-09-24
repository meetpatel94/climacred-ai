import React, { useState } from 'react';
import {
  Zap,
  Droplets,
  Trash2,
  CloudFog,
  Truck,
  Leaf,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Loader2,
  CheckCircle,
} from 'lucide-react';
import { ClimateAssessmentData, PageId } from '../types';

interface ClimateAssessmentPageProps {
  initialData: ClimateAssessmentData;
  onSaveAssessment: (data: ClimateAssessmentData) => Promise<any>;
  onNavigate: (page: PageId) => void;
}

type AssessmentStep = 'energy' | 'water' | 'waste' | 'emissions' | 'mobility' | 'practices';

const STEPS: { id: AssessmentStep; label: string; icon: React.ElementType }[] = [
  { id: 'energy', label: 'Energy', icon: Zap },
  { id: 'water', label: 'Water', icon: Droplets },
  { id: 'waste', label: 'Waste', icon: Trash2 },
  { id: 'emissions', label: 'Emissions & Air', icon: CloudFog },
  { id: 'mobility', label: 'Mobility', icon: Truck },
  { id: 'practices', label: 'Green Practices', icon: Leaf },
];

export const ClimateAssessmentPage: React.FC<ClimateAssessmentPageProps> = ({
  initialData,
  onSaveAssessment,
  onNavigate,
}) => {
  const [data, setData] = useState<ClimateAssessmentData>(JSON.parse(JSON.stringify(initialData)));
  const [activeStep, setActiveStep] = useState<AssessmentStep>('energy');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const currentStepIndex = STEPS.findIndex((s) => s.id === activeStep);

  const handleNext = () => {
    if (currentStepIndex < STEPS.length - 1) {
      setActiveStep(STEPS[currentStepIndex + 1].id);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setActiveStep(STEPS[currentStepIndex - 1].id);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
      await onSaveAssessment(data);
      // Wait for simulated calculation delay
      setTimeout(() => {
        setIsAnalyzing(false);
        onNavigate('fingerprint');
      }, 900);
    } catch {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl pb-16">
      {/* Top Header */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Enterprise Climate Audit & Data Collection
            </h2>
          </div>
          <p className="text-xs text-slate-600">
            Fill in your resource consumption metrics. Clear units are indicated for monthly operational tracking.
          </p>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing Fingerprint...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Analyze My Business</span>
            </>
          )}
        </button>
      </div>

      {/* Stepper Navigation */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-3 shadow-xs overflow-x-auto">
        <div className="flex items-center justify-between min-w-[640px] px-2">
          {STEPS.map((step, idx) => {
            const Icon = step.icon;
            const isCompleted = idx < currentStepIndex;
            const isCurrent = step.id === activeStep;

            return (
              <button
                key={step.id}
                onClick={() => setActiveStep(step.id)}
                className={`flex items-center gap-2 py-2 px-3 rounded-xl transition-all ${
                  isCurrent
                    ? 'bg-emerald-50 text-emerald-900 font-bold border border-emerald-200'
                    : isCompleted
                    ? 'text-emerald-700 hover:bg-slate-50'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs ${
                    isCurrent
                      ? 'bg-emerald-600 text-white shadow-xs'
                      : isCompleted
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {isCompleted ? <CheckCircle className="w-4 h-4" /> : <Icon className="w-3.5 h-3.5" />}
                </div>
                <span className="text-xs">{step.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Form Section */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-8 shadow-xs">
        {/* Step 1: Energy */}
        {activeStep === 'energy' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Energy Consumption & Power Feeds</h3>
                <p className="text-xs text-slate-600">Track grid draw, backup diesel hours, and solar offset capacity.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Monthly Electricity Consumption
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.energy.monthlyElectricityKwh ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        energy: { ...data.energy, monthlyElectricityKwh: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    kWh / month
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Found on monthly utility meter invoice.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Monthly Electricity Bill
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    ₹
                  </span>
                  <input
                    type="number"
                    value={data.energy.monthlyElectricityBillInr ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        energy: { ...data.energy, monthlyElectricityBillInr: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-8 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    ₹ / month
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Total recurring utility grid expense.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Diesel Backup Generator Usage
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.energy.dieselGeneratorHoursPerMonth ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        energy: { ...data.energy, dieselGeneratorHoursPerMonth: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-24 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    hours / month
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Average run hours during grid outages.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Generator Fuel Consumption
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.energy.generatorFuelLitresPerMonth ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        energy: { ...data.energy, generatorFuelLitresPerMonth: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-24 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    litres / month
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">High Scope 1 emission and operational cost source.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Existing On-Site Solar PV Capacity
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.energy.existingSolarCapacityKw ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        energy: { ...data.energy, existingSolarCapacityKw: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    kWp
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Enter 0 if facility relies 100% on grid or diesel.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Energy-Efficient Machinery Ratio
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.energy.energyEfficientEquipmentPercent ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        energy: { ...data.energy, energyEfficientEquipmentPercent: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-14 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                    min={0}
                    max={100}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    %
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Percentage of motors equipped with VFDs or IE3/IE4 ratings.</p>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Water */}
        {activeStep === 'water' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
              <div className="w-10 h-10 rounded-xl bg-cyan-50 text-cyan-700 flex items-center justify-center">
                <Droplets className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Water Consumption & Effluent Management</h3>
                <p className="text-xs text-slate-600">Audit freshwater source, recycling loops, and pipe integrity.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Monthly Freshwater Consumption
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.water.monthlyWaterLitres ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        water: { ...data.water, monthlyWaterLitres: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-24 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    litres / month
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Enter the volume you actually draw each month.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Primary Water Intake Source
                </label>
                <select
                  value={data.water.waterSource ?? ''}
                  onChange={(e) =>
                    setData({
                      ...data,
                      water: { ...data.water, waterSource: e.target.value as any },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden bg-white"
                >
                  <option value="">Select water source…</option>
                  <option value="Municipal">Municipal Industrial Line</option>
                  <option value="Groundwater / Borewell">Groundwater / Borewell</option>
                  <option value="Water Tanker">Private Water Tanker</option>
                  <option value="Mixed">Mixed Sourcing</option>
                </select>
                <p className="text-[11px] text-slate-600 mt-1">Groundwater sources have strict extraction regulations.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Observed Pipe Leakage Frequency
                </label>
                <select
                  value={data.water.leakageFrequency ?? ''}
                  onChange={(e) =>
                    setData({
                      ...data,
                      water: { ...data.water, leakageFrequency: e.target.value as any },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden bg-white"
                >
                  <option value="">Select leakage frequency…</option>
                  <option value="Never">Never (Fully Inspected)</option>
                  <option value="Rarely">Rarely (Annual Repairs)</option>
                  <option value="Monthly">Monthly (Recurring Joint Leaks)</option>
                  <option value="Frequent">Frequent (Unmonitored Drops / Overflows)</option>
                </select>
                <p className="text-[11px] text-slate-600 mt-1">Ultrasonic IoT sensors eliminate hidden losses.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Wastewater / Effluent Treatment Sizing
                </label>
                <select
                  value={data.water.wastewaterTreatment ?? ''}
                  onChange={(e) =>
                    setData({
                      ...data,
                      water: { ...data.water, wastewaterTreatment: e.target.value as any },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden bg-white"
                >
                  <option value="">Select treatment level…</option>
                  <option value="None">None / Direct Drain</option>
                  <option value="Primary / Settling">Primary / Settling Tank Only</option>
                  <option value="Full ETP / STP">Full Multi-Stage ETP / STP</option>
                </select>
                <p className="text-[11px] text-slate-600 mt-1">Required for statutory Zero Liquid Discharge standards.</p>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Waste */}
        {activeStep === 'waste' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Waste Streams & Material Divergence</h3>
                <p className="text-xs text-slate-600">Breakdown of monthly solids, off-cuts, and circular recycling rates.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Textile / Raw Material Waste (Scrap)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.waste.textileMaterialWasteKgPerMonth ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        waste: { ...data.waste, textileMaterialWasteKgPerMonth: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    kg / month
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Yarn residue, cutting edge trimmings, rejected lots.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Industrial / Sludge / Chemical Waste
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.waste.industrialWasteKgPerMonth ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        waste: { ...data.waste, industrialWasteKgPerMonth: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    kg / month
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">ETP cake, salt brine residues, machine lubricants.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Plastic Packaging Scrap
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.waste.plasticWasteKgPerMonth ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        waste: { ...data.waste, plasticWasteKgPerMonth: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    kg / month
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Polybags, strapping tapes, protective film wraps.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Current Recycling / Recovery Percentage
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.waste.currentRecyclingPercent ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        waste: { ...data.waste, currentRecyclingPercent: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-14 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                    min={0}
                    max={100}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    %
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Percentage handed to authorized circular processors.</p>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Emissions & Air */}
        {activeStep === 'emissions' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
              <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-800 flex items-center justify-center">
                <CloudFog className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Emissions, Boilers & Combustion</h3>
                <p className="text-xs text-slate-600">Combustion fuels, boiler exhaust, and air scrubbers.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Primary Industrial Boiler Fuel
                </label>
                <select
                  value={data.emissions.primaryFuel ?? ''}
                  onChange={(e) =>
                    setData({
                      ...data,
                      emissions: { ...data.emissions, primaryFuel: e.target.value as any },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden bg-white"
                >
                  <option value="">Select primary fuel…</option>
                  <option value="Electricity Grid">Electricity Grid Only</option>
                  <option value="Diesel">Diesel / Furnace Oil</option>
                  <option value="Natural Gas / PNG">Natural Gas / PNG</option>
                  <option value="Coal / Biomass">Coal / Agro Biomass Briquettes</option>
                </select>
                <p className="text-[11px] text-slate-600 mt-1">Determines Scope 1 combustion emission factor.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Total Monthly Diesel Usage (Boiler + Genset)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.emissions.monthlyDieselLitres ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        emissions: { ...data.emissions, monthlyDieselLitres: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    litres / mo
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">1 litre diesel emits ~2.68 kg CO₂e.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Air Pollution Abatement System
                </label>
                <select
                  value={data.emissions.airPollutionControlSystem ?? ''}
                  onChange={(e) =>
                    setData({
                      ...data,
                      emissions: { ...data.emissions, airPollutionControlSystem: e.target.value as any },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden bg-white"
                >
                  <option value="None">None / Direct Chimney Vent</option>
                  <option value="Basic Scrubber">Basic Wet Venturi Scrubber</option>
                  <option value="Bag Filter / ESP">Bag Filter / Electrostatic Precipitator</option>
                  <option value="Advanced Multi-Stage">Advanced Multi-Stage Flue Treatment</option>
                </select>
                <p className="text-[11px] text-slate-600 mt-1">Controls particulate matter (PM2.5 / PM10) stack compliance.</p>
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Mobility */}
        {activeStep === 'mobility' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center">
                <Truck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Mobility & Logistics Operations</h3>
                <p className="text-xs text-slate-600">Company vehicle fleets, fuel consumption, and EV transition rate.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Number of Owned / Contracted Delivery Vehicles
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.mobility.deliveryVehiclesCount ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        mobility: { ...data.mobility, deliveryVehiclesCount: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    vehicles
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Light commercial cargo vans, pickups, or tempo trucks.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Fleet Primary Fuel Type
                </label>
                <select
                  value={data.mobility.vehicleFuelType ?? ''}
                  onChange={(e) =>
                    setData({
                      ...data,
                      mobility: { ...data.mobility, vehicleFuelType: e.target.value as any },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden bg-white"
                >
                  <option value="">Select fleet fuel type…</option>
                  <option value="Diesel">Diesel</option>
                  <option value="Petrol">Petrol</option>
                  <option value="CNG">CNG</option>
                  <option value="Electric">Electric (100% EV)</option>
                  <option value="Mixed Fleet">Mixed Fleet</option>
                </select>
                <p className="text-[11px] text-slate-600 mt-1">Used to compute fleet fuel economics.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Monthly Fleet Fuel Consumption
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.mobility.monthlyFleetFuelLitres ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        mobility: { ...data.mobility, monthlyFleetFuelLitres: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-20 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    litres / mo
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Aggregated diesel or fuel receipts for company transport.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Current EV Transition Rate
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={data.mobility.evAdoptedPercent ?? ''}
                    onChange={(e) =>
                      setData({
                        ...data,
                        mobility: { ...data.mobility, evAdoptedPercent: e.target.value === '' ? null : Number(e.target.value) },
                      })
                    }
                    className="w-full pl-3.5 pr-14 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 text-sm font-semibold text-slate-900 outline-hidden"
                    min={0}
                    max={100}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">
                    %
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">Percentage of deliveries executed with commercial EVs.</p>
              </div>
            </div>
          </div>
        )}

        {/* Step 6: Green Practices Checklist */}
        {activeStep === 'practices' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
              <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center">
                <Leaf className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Existing Sustainable Operational Practices</h3>
                <p className="text-xs text-slate-600">Check all systems or policies currently implemented on site.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { key: 'ledLighting', label: '100% LED Lighting in All Sheds', desc: 'Energy-efficient high bay luminaires installed' },
                { key: 'solarPanels', label: 'Rooftop Solar PV Connected', desc: 'Clean on-site renewable generation active' },
                { key: 'rainwaterHarvesting', label: 'Rainwater Harvesting Pit / Tank', desc: 'Rooftop rainwater channeled to storage or recharge' },
                { key: 'waterRecycling', label: 'Effluent / Water Recycling Plant', desc: 'Closed loop treatment reusing rinse waters' },
                { key: 'wasteSegregation', label: 'Source Waste Segregation', desc: 'Dedicated color-coded bins for yarn, paper & hazard scrap' },
                { key: 'energyEfficientMachinery', label: 'IE3 / IE4 Motors with VFD Drives', desc: 'Variable speed motors installed on major loads' },
                { key: 'evAdoption', label: 'Commercial EV Fleet Adoption', desc: 'Electric vans or 3-wheelers used for dispatch' },
                { key: 'sustainableMaterials', label: 'OEKO-TEX / GOTS Certified Inputs', desc: 'Certified sustainable dyes or recycled yarns used' },
              ].map((practice) => {
                const isChecked = !!(data.greenPractices as any)[practice.key];

                return (
                  <label
                    key={practice.key}
                    className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                      isChecked
                        ? 'bg-emerald-50/70 border-emerald-300 text-slate-900'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) =>
                        setData({
                          ...data,
                          greenPractices: {
                            ...data.greenPractices,
                            [practice.key]: e.target.checked,
                          },
                        })
                      }
                      className="mt-1 w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
                    />
                    <div>
                      <p className="text-xs font-bold text-slate-900">{practice.label}</p>
                      <p className="text-[11px] text-slate-600 mt-0.5">{practice.desc}</p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {/* Stepper Footer Controls */}
        <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between">
          <button
            type="button"
            onClick={handlePrev}
            disabled={currentStepIndex === 0}
            className={`px-4 py-2.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              currentStepIndex === 0
                ? 'border-slate-200 text-slate-300 cursor-not-allowed'
                : 'border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous Step</span>
          </button>

          <div className="flex items-center gap-3">
            {currentStepIndex < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={handleNext}
                className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center gap-1.5 transition-colors"
              >
                <span>Next: {STEPS[currentStepIndex + 1].label}</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={isAnalyzing}
                className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 shadow-md transition-all hover:scale-[1.02]"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Analyzing Fingerprint...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Analyze My Business</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
