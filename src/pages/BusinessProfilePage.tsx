import React, { useState } from 'react';
import { Building2, Save, Check, MapPin, Users, Calendar, Clock, Gauge, Mail } from 'lucide-react';
import { BusinessProfile, PageId } from '../types';
import { DemoTag } from '../components/common/StatusBadge';

interface BusinessProfilePageProps {
  profile: BusinessProfile;
  onSave: (updated: BusinessProfile) => void;
  onNavigate: (page: PageId) => void;
}

const INDUSTRIES = [
  'Manufacturing',
  'Textile',
  'Food & Beverage',
  'Retail',
  'Agriculture',
  'Hospitality',
  'Logistics',
  'Healthcare',
  'Construction',
  'Other',
];

const SIZES: Array<'Micro' | 'Small' | 'Medium' | 'Mid-Market'> = [
  'Micro',
  'Small',
  'Medium',
  'Mid-Market',
];

export const BusinessProfilePage: React.FC<BusinessProfilePageProps> = ({
  profile,
  onSave,
  onNavigate,
}) => {
  const [formData, setFormData] = useState<BusinessProfile>({ ...profile });
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleChange = (field: keyof BusinessProfile, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setSavedSuccess(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-5xl pb-12">
      {/* Intro Header */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-5 h-5 text-emerald-600" />
            <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Enterprise Profile & Baseline Parameters
            </h2>
            <DemoTag />
          </div>
          <p className="text-xs text-slate-600">
            ClimaCred AI uses your industry cluster, facility area, and shift hours to benchmark
            resource intensity against similar manufacturing peers.
          </p>
        </div>

        {savedSuccess && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-800 text-xs font-semibold animate-fade-in">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>Profile Saved</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section 1: General Business Details */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <h3 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-emerald-50 text-emerald-700 flex items-center justify-center text-xs font-black">
              1
            </span>
            General Organization Info
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Business Legal Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden transition-colors"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Industry Sector
              </label>
              <select
                value={formData.industry}
                onChange={(e) => handleChange('industry', e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden bg-white transition-colors"
              >
                {INDUSTRIES.map((ind) => (
                  <option key={ind} value={ind}>
                    {ind}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Specific Business / Process Type
              </label>
              <input
                type="text"
                value={formData.businessType}
                onChange={(e) => handleChange('businessType', e.target.value)}
                placeholder="e.g., Fabric Dyeing & Finishing"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden transition-colors"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Enterprise Classification Size
              </label>
              <div className="grid grid-cols-4 gap-2">
                {SIZES.map((size) => (
                  <button
                    type="button"
                    key={size}
                    onClick={() => handleChange('businessSize', size)}
                    className={`py-2 px-2 text-xs font-semibold rounded-xl border text-center transition-all ${
                      formData.businessSize === size
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                        : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                Facility Location & Industrial Cluster
              </label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => handleChange('location', e.target.value)}
                placeholder="City, Industrial Cluster, State, Country"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden transition-colors"
                required
              />
            </div>
          </div>
        </div>

        {/* Section 2: Operations & Capacity */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <h3 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-teal-50 text-teal-700 flex items-center justify-center text-xs font-black">
              2
            </span>
            Operational Metrics & Plant Sizing
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-slate-400" />
                Number of Full-Time Employees
              </label>
              <input
                type="number"
                value={formData.employees}
                onChange={(e) => handleChange('employees', Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden"
                min={1}
              />
              <p className="text-[11px] text-slate-600 mt-1">Used to compute per-capita waste and commute load.</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                Working Days per Month
              </label>
              <input
                type="number"
                value={formData.workingDaysPerMonth}
                onChange={(e) => handleChange('workingDaysPerMonth', Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden"
                min={1}
                max={31}
              />
              <p className="text-[11px] text-slate-600 mt-1">Typically 24 - 26 days for textile plants.</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                Operating Hours per Day
              </label>
              <input
                type="number"
                value={formData.operatingHoursPerDay}
                onChange={(e) => handleChange('operatingHoursPerDay', Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden"
                min={1}
                max={24}
              />
              <p className="text-[11px] text-slate-600 mt-1">Single shift (8h), dual (16h), or continuous (24h).</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Gauge className="w-3.5 h-3.5 text-slate-400" />
                Production / Service Volume
              </label>
              <input
                type="text"
                value={formData.productionVolume}
                onChange={(e) => handleChange('productionVolume', e.target.value)}
                placeholder="e.g. 42,000 meters / month"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden"
              />
              <p className="text-[11px] text-slate-600 mt-1">Output units for specific carbon intensity.</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Facility Covered Area (Sq Ft)
              </label>
              <input
                type="number"
                value={formData.facilityAreaSqFt}
                onChange={(e) => handleChange('facilityAreaSqFt', Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden"
              />
              <p className="text-[11px] text-slate-600 mt-1">Calculates rooftop solar potential and rainwater capture.</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-slate-400" />
                Operations Lead Email
              </label>
              <input
                type="email"
                value={formData.contactEmail}
                onChange={(e) => handleChange('contactEmail', e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 text-sm font-medium text-slate-900 outline-hidden"
              />
              <p className="text-[11px] text-slate-600 mt-1">Receives automated monthly report dossiers.</p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
          <button
            type="submit"
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md flex items-center justify-center gap-2 transition-all hover:scale-[1.01]"
          >
            <Save className="w-4 h-4" />
            <span>Save Profile Parameters</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('assessment')}
            className="w-full sm:w-auto px-5 py-3 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
          >
            <span>Proceed to Climate Assessment</span>
          </button>
        </div>
      </form>
    </div>
  );
};
